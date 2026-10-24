"""Business failed-card validation reports with code redaction and audit."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .audit import AuditTrailLogger
from .auth import Principal, authorize_redemption
from .errors import Conflict, DomainError, Forbidden


FAILED_VALIDATION_REASONS = frozenset({
    "invalid_code", "already_redeemed", "redemption_in_progress", "activation_required",
    "cancelled", "expired", "wrong_business", "wrong_category", "card_unavailable",
    "payment_pending", "business_unavailable",
})


@dataclass(frozen=True)
class FailedValidationReport:
    id: str
    business_id: str
    operator_id: str
    code_fingerprint: str
    reason: str
    reported_at: datetime
    matched_card_id: str | None = None


class FailedValidationRepository(Protocol):
    def atomic(self) -> Any: ...
    def get_business(self, business_id: str) -> Any | None: ...
    def get_failed_validation_by_request(self, *, business_id: str, request_key: str) -> FailedValidationReport | None: ...
    def get_card_by_code(self, code: str) -> Any | None: ...
    def allow_failed_report(self, *, business_id: str, operator_id: str, now: datetime) -> bool: ...
    def create_failed_validation_report(self, *, business_id: str, operator_id: str,
        code_fingerprint: str, reason: str, reported_at: datetime,
        matched_card_id: str | None, request_key: str) -> FailedValidationReport: ...
    def record_audit(self, **event: Any) -> None: ...
    def enqueue_outbox(self, *, event_key: str, event_type: str, payload: dict[str, Any]) -> None: ...


class FailedValidationReportService:
    def __init__(self, *, repo: FailedValidationRepository, clock: Any,
                 fingerprint_secret: str):
        if not fingerprint_secret:
            raise ValueError("fingerprint_secret must be configured")
        self.repo, self.clock = repo, clock
        self.fingerprint_secret = fingerprint_secret.encode("utf-8")
        self.audit = AuditTrailLogger(repo)

    def submit(self, *, principal: Principal, code: str, reason: str,
               request_key: str) -> FailedValidationReport:
        if not principal.business_id:
            raise Forbidden("Operator is not assigned to a business", code="business_scope_forbidden")
        business_id = authorize_redemption(principal, principal.business_id)
        business = self.repo.get_business(business_id)
        if not business or not business.approved or not business.active:
            raise Forbidden("Only active approved businesses can report validations", code="business_unavailable")
        if not isinstance(code, str) or not code.strip() or len(code.strip()) > 128:
            raise DomainError("Presented code is required", code="invalid_report_code")
        reason = reason.strip().lower() if isinstance(reason, str) else ""
        if reason not in FAILED_VALIDATION_REASONS:
            raise DomainError("Choose a recognized failed-validation reason", code="invalid_report_reason")
        if not isinstance(request_key, str) or not request_key.strip() or len(request_key) > 160:
            raise DomainError("Idempotency key is required", code="missing_idempotency_key")
        now = self.clock.now()
        if now.tzinfo is None:
            raise DomainError("Report timestamp must be timezone-aware", code="invalid_report_timestamp")
        if not self.repo.allow_failed_report(business_id=business_id, operator_id=principal.user_id, now=now):
            raise Forbidden("Too many failed-validation reports; try again later", code="report_rate_limited")
        normalized_code = code.strip()
        code_fingerprint = hmac.new(self.fingerprint_secret, normalized_code.encode("utf-8"), hashlib.sha256).hexdigest()[:48]
        # Match against the schema's Card.code value, but persist only this keyed
        # fingerprint in ValidationReport.code_entered; never store/log raw code.
        matched = self.repo.get_card_by_code(normalized_code)
        matched_card_id = matched.id if matched else None
        with self.repo.atomic():
            previous = self.repo.get_failed_validation_by_request(business_id=business_id,
                                                                   request_key=request_key.strip())
            if previous:
                if (previous.operator_id != principal.user_id or previous.code_fingerprint != code_fingerprint
                        or previous.reason != reason):
                    raise Conflict("Idempotency key was used for a different report", code="idempotency_conflict")
                return previous
            report = self.repo.create_failed_validation_report(business_id=business_id,
                operator_id=principal.user_id, code_fingerprint=code_fingerprint, reason=reason,
                reported_at=now, matched_card_id=matched_card_id,
                request_key=request_key.strip())
            self.audit.log(event_type="business.failed_validation_reported", actor_id=principal.user_id,
                entity_type="failed_validation_report", entity_id=report.id,
                reference=f"failed-validation:{report.id}", occurred_at=now,
                idempotency_key=f"failed-validation:{business_id}:{request_key.strip()}",
                data={"business_id": business_id, "reason": reason,
                      "code_fingerprint": code_fingerprint, "matched_card_id": matched_card_id})
            self.repo.enqueue_outbox(event_key=f"failed-validation:{report.id}",
                event_type="business.failed_validation_reported",
                payload={"report_id": report.id, "business_id": business_id,
                         "operator_id": principal.user_id, "reason": reason,
                         "reported_at": now.isoformat()})
        return report
