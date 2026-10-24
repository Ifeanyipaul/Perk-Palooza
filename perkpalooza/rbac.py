"""Django decorators and optional middleware for role and data-scope checks."""

from __future__ import annotations

from functools import wraps
from django.conf import settings
from django.http import JsonResponse

from .auth import ROLES, Principal, assert_business_scope, assert_giver_ownership, require_principal
from .errors import DomainError, Forbidden


def _error_response(error: DomainError):
    return JsonResponse({"error": {"code": error.code, "message": str(error)}}, status=error.http_status)


def roles_required(*allowed_roles: str):
    """Apply to each protected Django view; public views should be explicit."""
    invalid = set(allowed_roles) - ROLES
    if not allowed_roles or invalid:
        raise ValueError(f"Invalid role policy: {sorted(invalid)}")

    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                principal = require_principal(request)
                if principal.role not in allowed_roles:
                    raise Forbidden("Your role cannot access this resource", code="role_forbidden")
                request.principal = principal
            except DomainError as error:
                return _error_response(error)
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


giver_required = roles_required("giver")
business_operator_required = roles_required("business")
operations_required = roles_required("admin")


def giver_resource_required(owner_id_getter):
    """Require giver role and ownership for a URL/resource resolved by the view."""
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                principal = require_principal(request)
                assert_giver_ownership(principal, str(owner_id_getter(request, *args, **kwargs)))
                request.principal = principal
            except DomainError as error:
                return _error_response(error)
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


def business_resource_required(business_id_getter):
    """Require operator role and membership in the business owning the resource."""
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                principal = require_principal(request)
                assert_business_scope(principal, str(business_id_getter(request, *args, **kwargs)))
                request.principal = principal
            except DomainError as error:
                return _error_response(error)
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


class BearerAuthenticationMiddleware:
    """Resolve bearer sessions using a configured AuthService.

    Set ``PERK_PALOOZA_AUTH_SERVICE`` to an initialized AuthService instance and
    add this middleware after Django's session middleware. Requests without a
    bearer header remain anonymous; protected views enforce authentication.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header = request.headers.get("Authorization", "")
        if not header:
            return self.get_response(request)
        scheme, separator, token = header.partition(" ")
        if not separator or scheme.casefold() != "bearer" or not token.strip():
            return _error_response(Forbidden("Authorization header is invalid", code="invalid_authorization_header"))
        service = getattr(settings, "PERK_PALOOZA_AUTH_SERVICE", None)
        if service is None:
            return JsonResponse({"error": {"code": "auth_unavailable", "message": "Authentication is not configured"}}, status=503)
        try:
            request.principal = service.authenticate(bearer_token=token.strip())
        except DomainError as error:
            return _error_response(error)
        return self.get_response(request)


class RolePolicyMiddleware:
    """Enforce path-prefix roles as a backstop to per-view decorators.

    Defaults cover giver, business, operations, and Django admin URL namespaces.
    Override with ``PERK_PALOOZA_RBAC_RULES`` as ``[(prefix, roles), ...]``.
    Public authentication endpoints should live below ``/api/auth/``.
    """

    DEFAULT_RULES = (
        ("/admin/", ("admin",)),
        ("/api/giver/", ("giver",)),
        ("/api/business/", ("business",)),
        ("/api/operations/", ("admin",)),
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path.startswith("/api/auth/"):
            return self.get_response(request)
        rules = getattr(settings, "PERK_PALOOZA_RBAC_RULES", self.DEFAULT_RULES)
        rule = next(((prefix, roles) for prefix, roles in rules if path.startswith(prefix)), None)
        if rule is None:
            return self.get_response(request)
        try:
            principal: Principal = require_principal(request)
            if principal.role not in rule[1]:
                raise Forbidden("Your role cannot access this resource", code="role_forbidden")
            request.principal = principal
        except DomainError as error:
            return _error_response(error)
        return self.get_response(request)
