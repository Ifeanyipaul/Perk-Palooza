"""Standardized, redacted audit event logic for the entire backend."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from .errors import DomainError


class AuditRepository(Protocol):
    def record_audit(self, **event: Any) -> None: ...


class AuditTrailLogger:
    """Append validated events; the repository must enforce append-only storage."""

    def __init__(self, repo: AuditRepository):
        self.repo = repo

    def log(self, *, event_type: str, actor_id: str, reference: str,
            occurred_at: datetime, data: dict[str, Any] | None = None,
            entity_type: str | None = None, entity_id: str | None = None,
            idempotency_key: str | None = None) -> None:
        if not event_type or not actor_id or not reference:
            raise DomainError("Audit events require type, actor, and reference", code="invalid_audit_event")
        if occurred_at.tzinfo is None:
            raise DomainError("Audit timestamp must be timezone-aware", code="invalid_audit_timestamp")
        safe_data = self._redact(data or {})
        self.repo.record_audit(event_type=event_type, actor_id=str(actor_id),
            entity_type=entity_type or "system", entity_id=str(entity_id or reference),
            reference=reference, occurred_at=occurred_at,
            idempotency_key=idempotency_key or f"{event_type}:{reference}", data=safe_data)

    @classmethod
    def _redact(cls, value: Any, key: str = "") -> Any:
        normalized = key.casefold().replace("-", "_")
        sensitive = ("password", "secret", "token", "authorization", "raw_code", "card_code", "encrypted_code")
        if normalized in {"code_fingerprint", "card_code_fingerprint", "code_digest", "code_hash"}:
            return value
        if any(marker in normalized for marker in sensitive) or normalized in {"code", "activation_proof"}:
            return "[REDACTED]"
        if isinstance(value, dict):
            return {str(child_key): cls._redact(child_value, str(child_key))
                    for child_key, child_value in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._redact(item, key) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)
