"""Authentication and account lifecycle logic, independent of the DB schema.

The repository owns identity persistence, session storage, recovery-token
storage, and rate limits. Passwords are hashed with Django's configured password
hashers; plaintext credentials and recovery tokens are never persisted here.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Protocol

from django.contrib.auth.hashers import check_password, make_password

from .errors import Conflict, DomainError, Forbidden


Role = Literal["giver", "business", "admin"]
ROLES: frozenset[str] = frozenset({"giver", "business", "admin"})


@dataclass(frozen=True)
class Identity:
    id: str
    email: str
    password_hash: str
    role: Role
    is_active: bool
    business_id: str | None = None
    must_reset_password: bool = False


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    business_id: str | None = None
    is_authenticated: bool = True


@dataclass(frozen=True)
class BusinessAccess:
    business_id: str
    approved: bool
    active: bool


class AuthRepository(Protocol):
    """Persistence/security port to implement against the teammate's schema.

    Identity.role and Principal.role use the exact persisted values from
    ``accounts.User.Role``: ``giver``, ``business``, and ``admin``.
    """

    def atomic(self) -> Any: ...
    def get_identity_by_email(self, email: str) -> Identity | None: ...
    def get_identity(self, user_id: str) -> Identity | None: ...
    def get_operator_business_access(self, user_id: str) -> BusinessAccess | None: ...
    def create_giver(self, *, email: str, password_hash: str, created_at: datetime) -> Identity: ...
    def save_password_hash(self, user_id: str, password_hash: str, changed_at: datetime) -> None: ...
    def create_session(self, *, user_id: str, session_digest: str, expires_at: datetime, created_at: datetime) -> None: ...
    def get_session(self, session_digest: str, now: datetime) -> Identity | None: ...
    def revoke_session(self, session_digest: str, revoked_at: datetime) -> None: ...
    def revoke_all_sessions(self, user_id: str, revoked_at: datetime) -> None: ...
    def save_recovery_token(self, *, user_id: str, token_digest: str, expires_at: datetime, created_at: datetime) -> None: ...
    def consume_recovery_token(self, *, token_digest: str, now: datetime) -> str | None: ...
    def enqueue_auth_message(self, *, event_key: str, event_type: str, payload: dict[str, Any]) -> None: ...
    def encrypt_auth_secret(self, secret: str) -> str: ...
    def allow_auth_attempt(self, *, key: str, now: datetime) -> bool: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class AuthService:
    def __init__(self, *, repo: AuthRepository, clock: Clock,
                 session_ttl: timedelta = timedelta(hours=12),
                 recovery_ttl: timedelta = timedelta(minutes=30),
                 minimum_password_length: int = 12):
        self.repo, self.clock = repo, clock
        self.session_ttl, self.recovery_ttl = session_ttl, recovery_ttl
        self.minimum_password_length = minimum_password_length

    def create_giver(self, *, email: str, password: str) -> dict[str, str]:
        email = self._email(email)
        self._validate_new_password(password)
        if self.repo.get_identity_by_email(email):
            raise Conflict("An account with this email already exists", code="email_already_registered")
        identity = self.repo.create_giver(email=email, password_hash=make_password(password), created_at=self.clock.now())
        return {"user_id": identity.id, "email": identity.email, "role": "giver"}

    def login(self, *, email: str, password: str, remote_key: str) -> dict[str, Any]:
        """Giver login endpoint logic. Use dedicated methods for other roles."""
        return self._login(email=email, password=password, remote_key=remote_key, allowed_role="giver")

    def login_business_operator(self, *, email: str, password: str, remote_key: str) -> dict[str, Any]:
        """Separate operator login; paused/unapproved businesses cannot sign in."""
        return self._login(email=email, password=password, remote_key=remote_key, allowed_role="business")

    def login_operations(self, *, email: str, password: str, remote_key: str) -> dict[str, Any]:
        """Internal login. Deployment should add MFA/SSO policy for this role."""
        return self._login(email=email, password=password, remote_key=remote_key, allowed_role="admin")

    def _login(self, *, email: str, password: str, remote_key: str, allowed_role: Role) -> dict[str, Any]:
        now = self.clock.now()
        email = self._email(email)
        if not self.repo.allow_auth_attempt(key=f"login:{allowed_role}:{remote_key}:{email}", now=now):
            raise Forbidden("Too many login attempts; try again later", code="login_rate_limited")
        identity = self.repo.get_identity_by_email(email)
        # Run a hash check even for unknown emails to reduce account enumeration timing differences.
        valid_password = check_password(password or "", identity.password_hash if identity else make_password("invalid-login-placeholder"))
        if not identity or not identity.is_active or identity.role != allowed_role or not valid_password:
            raise Forbidden("Email or password is incorrect", code="invalid_credentials")
        if allowed_role == "business":
            access = self.repo.get_operator_business_access(identity.id)
            if not access or not access.approved or not access.active or access.business_id != identity.business_id:
                raise Forbidden("Business account is not approved or active", code="business_unavailable")
        if identity.must_reset_password:
            raise Forbidden("Password reset is required before login", code="password_reset_required")
        raw_token = secrets.token_urlsafe(48)
        self.repo.create_session(user_id=identity.id, session_digest=self._digest(raw_token),
                                 expires_at=now + self.session_ttl, created_at=now)
        return {"access_token": raw_token, "token_type": "Bearer", "expires_at": (now + self.session_ttl).isoformat(),
                "principal": self._principal(identity)}

    def authenticate(self, *, bearer_token: str) -> Principal:
        if not bearer_token or len(bearer_token) > 256:
            raise Forbidden("Authentication is required", code="not_authenticated")
        identity = self.repo.get_session(self._digest(bearer_token), self.clock.now())
        if not identity or not identity.is_active or identity.role not in ROLES:
            raise Forbidden("Session is invalid or expired", code="invalid_session")
        if identity.role == "business":
            access = self.repo.get_operator_business_access(identity.id)
            if not access or not access.approved or not access.active or access.business_id != identity.business_id:
                raise Forbidden("Business account is not approved or active", code="business_unavailable")
        return self._principal(identity)

    def logout(self, *, bearer_token: str) -> None:
        if not bearer_token:
            return
        # Revoking an unknown token remains harmless and idempotent.
        self.repo.revoke_session(self._digest(bearer_token), self.clock.now())

    def request_recovery(self, *, email: str) -> None:
        """Always return success to the caller so email existence is not exposed."""
        email = self._email(email)
        identity = self.repo.get_identity_by_email(email)
        if not identity or not identity.is_active or identity.role != "giver":
            return
        now = self.clock.now()
        token = secrets.token_urlsafe(48)
        self.repo.save_recovery_token(user_id=identity.id, token_digest=self._digest(token),
                                      expires_at=now + self.recovery_ttl, created_at=now)
        self.repo.enqueue_auth_message(event_key=f"account-recovery:{self._digest(token)}",
            event_type="account.recovery_requested", payload={"user_id": identity.id, "email": identity.email,
                "encrypted_token": self.repo.encrypt_auth_secret(token),
                "expires_at": (now + self.recovery_ttl).isoformat()})

    def reset_password(self, *, token: str, new_password: str) -> None:
        self._validate_new_password(new_password)
        if not token or len(token) > 256:
            raise Forbidden("Recovery token is invalid or expired", code="invalid_recovery_token")
        now = self.clock.now()
        if not self.repo.allow_auth_attempt(key=f"recovery:{self._digest(token)}", now=now):
            raise Forbidden("Too many recovery attempts; request a new link", code="recovery_rate_limited")
        # consume_recovery_token must be a one-time atomic conditional update.
        with self.repo.atomic():
            user_id = self.repo.consume_recovery_token(token_digest=self._digest(token), now=now)
            if not user_id:
                raise Forbidden("Recovery token is invalid or expired", code="invalid_recovery_token")
            identity = self.repo.get_identity(user_id)
            if not identity or not identity.is_active or identity.role != "giver":
                raise Forbidden("Account is not eligible for recovery", code="recovery_not_allowed")
            self.repo.save_password_hash(user_id, make_password(new_password), now)
            self.repo.revoke_all_sessions(user_id, now)

    @staticmethod
    def _principal(identity: Identity) -> Principal:
        return Principal(user_id=identity.id, role=identity.role, business_id=identity.business_id)

    def _validate_new_password(self, password: str) -> None:
        if not isinstance(password, str) or len(password) < self.minimum_password_length or len(password) > 256:
            raise DomainError(f"Password must be {self.minimum_password_length} to 256 characters", code="weak_password")

    @staticmethod
    def _email(email: str) -> str:
        if not isinstance(email, str):
            raise DomainError("A valid email address is required", code="invalid_email")
        email = email.strip().casefold()
        if len(email) > 254 or email.count("@") != 1 or any(ch.isspace() for ch in email):
            raise DomainError("A valid email address is required", code="invalid_email")
        local, domain = email.split("@")
        if not local or not domain or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise DomainError("A valid email address is required", code="invalid_email")
        return email

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require_principal(request: Any) -> Principal:
    """Resolve a trusted principal injected by authentication middleware."""
    principal = getattr(request, "principal", None)
    if principal is None:
        principal = getattr(request, "user", None)
    if not principal or not getattr(principal, "is_authenticated", False):
        raise Forbidden("Authentication is required", code="not_authenticated")
    role = getattr(principal, "role", None)
    user_id = getattr(principal, "user_id", None) or getattr(principal, "id", None)
    if role not in ROLES or not user_id:
        raise Forbidden("Account has no valid application role", code="role_not_configured")
    return Principal(user_id=str(user_id), role=role, business_id=getattr(principal, "business_id", None))


def require_roles(*allowed_roles: Role):
    """Django view decorator enforcing role separation after auth middleware."""
    invalid = set(allowed_roles) - ROLES
    if not allowed_roles or invalid:
        raise ValueError(f"Invalid role policy: {sorted(invalid)}")

    def decorator(view):
        from functools import wraps

        @wraps(view)
        def wrapped(request, *args, **kwargs):
            principal = require_principal(request)
            if principal.role not in allowed_roles:
                raise Forbidden("Your role cannot access this resource", code="role_forbidden")
            request.principal = principal
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def assert_giver_ownership(principal: Principal, resource_owner_id: str) -> None:
    if principal.role != "giver" or principal.user_id != str(resource_owner_id):
        raise Forbidden("You cannot access another giver's data", code="giver_scope_forbidden")


def assert_business_scope(principal: Principal, resource_business_id: str) -> None:
    if principal.role != "business" or not principal.business_id or principal.business_id != str(resource_business_id):
        raise Forbidden("You cannot access another business's data", code="business_scope_forbidden")


def authorize_redemption(principal: Principal, business_id: str) -> str:
    """Authorize a redemption for the operator's own currently assigned business.

    Call after authenticating the operator and rechecking business approval and
    active status. The card service's public validation/redemption entry points
    derive the business ID from this principal rather than caller input.
    """
    assert_business_scope(principal, business_id)
    return principal.business_id
