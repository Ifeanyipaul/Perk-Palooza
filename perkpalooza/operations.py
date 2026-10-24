"""Business onboarding, status, float monitoring, and top-up workflows.

All persistence operations are ports for the database adapter; this module adds
only business rules, role checks, audit, and ledger orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Protocol

from .audit import AuditTrailLogger
from .auth import Principal
from .errors import Conflict, DomainError, Forbidden, NotFound
from .money import money


BusinessStatus = Literal["pending", "active", "paused", "removed"]
TopUpStatus = Literal["pending", "completed", "rejected"]


@dataclass(frozen=True)
class ManagedBusiness:
    id: str
    name: str
    category_id: str
    status: BusinessStatus
    approved: bool
    active: bool
    low_float_threshold: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class TopUpRequest:
    id: str
    business_id: str
    amount: Decimal
    currency: str
    reason: str
    requested_by: str
    status: TopUpStatus


class OperationsRepository(Protocol):
    def atomic(self) -> Any: ...
    def is_category_approved(self, category_id: str) -> bool: ...
    def create_business_profile(self, *, name: str, category_id: str, user_id: str,
                                registration_number: str, created_at: datetime) -> ManagedBusiness: ...
    def get_business_profile(self, business_id: str) -> ManagedBusiness | None: ...
    def update_business_status(self, *, business_id: str, expected: tuple[str, ...],
                               new_status: str, changed_at: datetime, actor_id: str,
                               **values: Any) -> bool: ...
    def save_business_vetting(self, *, business_id: str, decision: str, evidence_reference: str,
                              notes: str, vetted_by: str, vetted_at: datetime) -> None: ...
    def has_passed_vetting(self, business_id: str) -> bool: ...
    def list_active_businesses(self) -> list[ManagedBusiness]: ...
    def get_float_balance_for_update(self, *, business_id: str, currency: str) -> Decimal: ...
    def get_float_balance(self, *, business_id: str, currency: str) -> Decimal: ...
    def list_float_entries(self, *, business_id: str) -> list[Any]: ...
    def record_float_ledger(self, **entry: Any) -> None: ...
    def create_topup_request(self, *, business_id: str, amount: Decimal, currency: str, reason: str,
                             requested_by: str, request_key: str, requested_at: datetime) -> TopUpRequest: ...
    def get_topup_request(self, request_id: str) -> TopUpRequest | None: ...
    def record_topup_approval(self, *, request_id: str, actor_id: str, note: str, approved_at: datetime) -> None: ...
    def has_topup_approval(self, request_id: str) -> bool: ...
    def transition_topup_request(self, *, request_id: str, expected: tuple[str, ...], new_status: str,
                                 changed_at: datetime, actor_id: str, **values: Any) -> bool: ...
    def list_active_cards_restricted_to_business(self, business_id: str) -> list[dict[str, Any]]: ...
    def record_audit(self, **event: Any) -> None: ...
    def enqueue_outbox(self, *, event_key: str, event_type: str, payload: dict[str, Any]) -> None: ...


def _require_operations(principal: Principal) -> None:
    if principal.role != "admin":
        raise Forbidden("Platform operations access is required", code="operations_role_required")


def _require_business_operator(principal: Principal) -> str:
    if principal.role != "business" or not principal.business_id:
        raise Forbidden("Business operator access is required", code="business_role_required")
    return principal.business_id


class BusinessOperationsService:
    TRANSITIONS: dict[str, frozenset[str]] = {
        "pending": frozenset({"active", "paused", "removed"}),
        "active": frozenset({"paused", "removed"}),
        "paused": frozenset({"active", "removed"}),
        "removed": frozenset(),
    }

    def __init__(self, *, repo: OperationsRepository, clock: Any):
        self.repo, self.clock = repo, clock
        self.audit = AuditTrailLogger(repo)

    def create_business(self, *, principal: Principal, name: str, category_id: str,
                        operator_user_id: str, registration_number: str) -> ManagedBusiness:
        _require_operations(principal)
        now = self.clock.now()
        self._aware(now)
        name = name.strip() if isinstance(name, str) else ""
        registration_number = registration_number.strip() if isinstance(registration_number, str) else ""
        if (not name or len(name) > 160 or not category_id
                or not self.repo.is_category_approved(category_id)
                or not operator_user_id or not registration_number):
            raise DomainError("Business name, assigned operator, registration number, and category are required",
                              code="invalid_business_profile")
        with self.repo.atomic():
            business = self.repo.create_business_profile(name=name, category_id=category_id,
                user_id=operator_user_id, registration_number=registration_number, created_at=now)
            self.audit.log(event_type="business.created", actor_id=principal.user_id,
                entity_type="business", entity_id=business.id,
                reference=f"business:{business.id}:created", occurred_at=now,
                data={"category_id": category_id, "operator_user_id": operator_user_id})
        return business

    def record_vetting(self, *, principal: Principal, business_id: str, decision: str,
                       evidence_reference: str, notes: str = "") -> None:
        _require_operations(principal)
        if decision not in {"passed", "failed"} or not evidence_reference:
            raise DomainError("Vetting decision and evidence reference are required", code="invalid_vetting_record")
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            business = self._get(business_id)
            if business.status != "pending":
                raise Conflict("Vetting can only be recorded for a pending business", code="business_not_pending")
            self.repo.save_business_vetting(business_id=business_id, decision=decision,
                evidence_reference=evidence_reference, notes=notes, vetted_by=principal.user_id, vetted_at=now)
            self.audit.log(event_type="business.vetting_recorded", actor_id=principal.user_id,
                entity_type="business", entity_id=business_id,
                reference=f"business:{business_id}:vetting:{evidence_reference}",
                occurred_at=now, data={"decision": decision})

    def approve_business(self, *, principal: Principal, business_id: str) -> None:
        _require_operations(principal)
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            business = self._get(business_id)
            if business.status != "pending":
                raise Conflict("Only a pending business can be approved", code="business_not_pending")
            if not self.repo.has_passed_vetting(business_id):
                raise Conflict("Business must pass vetting before approval", code="vetting_not_passed")
            self.audit.log(event_type="business.approved", actor_id=principal.user_id,
                entity_type="business", entity_id=business_id,
                reference=f"business:{business_id}:approved", occurred_at=now, data={})

    def go_live(self, *, principal: Principal, business_id: str,
                 initial_float: Any, funding_reference: str) -> None:
        _require_operations(principal)
        amount = money(initial_float)
        funding_reference = funding_reference.strip() if isinstance(funding_reference, str) else ""
        if amount <= 0 or not funding_reference:
            raise DomainError("A positive initial float and funding reference are required", code="invalid_initial_float")
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            business = self._get(business_id)
            if business.status != "pending" or not self.repo.has_passed_vetting(business_id):
                raise Conflict("Only a vetted pending business can go live", code="business_not_approved")
            self.repo.record_float_ledger(entry_type="deposit", business_id=business_id,
                amount=amount, currency="NGN", reference=f"business:{business_id}:opening:{funding_reference}",
                occurred_at=now, source="platform:treasury", destination=f"business:{business_id}:float",
                idempotency_key=f"opening-float:{business_id}:{funding_reference}")
            if not self.repo.update_business_status(business_id=business_id,
                    expected=("pending",), new_status="active", changed_at=now,
                    actor_id=principal.user_id):
                raise Conflict("Business state changed", code="business_state_changed")
            self.audit.log(event_type="business.went_live", actor_id=principal.user_id,
                entity_type="business", entity_id=business_id,
                reference=f"business:{business_id}:go-live", occurred_at=now,
                data={"opening_float": str(amount), "currency": "NGN"})

    def pause_business(self, *, principal: Principal, business_id: str, reason: str) -> dict[str, Any]:
        return self._stop_business(principal=principal, business_id=business_id,
                                   new_status="paused", reason=reason)

    def remove_business(self, *, principal: Principal, business_id: str, reason: str) -> dict[str, Any]:
        return self._stop_business(principal=principal, business_id=business_id,
                                   new_status="removed", reason=reason)

    def resume_business(self, *, principal: Principal, business_id: str) -> None:
        _require_operations(principal)
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            business = self._get(business_id)
            if business.status != "paused":
                raise Conflict("Only a paused business can be resumed", code="business_not_paused")
            balance = money(self.repo.get_float_balance_for_update(business_id=business_id, currency="NGN"))
            if balance <= 0:
                raise Conflict("Business needs positive float before resuming", code="float_required_to_resume")
            if not self.repo.update_business_status(business_id=business_id,
                    expected=("paused",), new_status="active", changed_at=now,
                    actor_id=principal.user_id):
                raise Conflict("Business state changed", code="business_state_changed")
            self.audit.log(event_type="business.resumed", actor_id=principal.user_id,
                entity_type="business", entity_id=business_id,
                reference=f"business:{business_id}:resumed:{now.isoformat()}",
                occurred_at=now, data={"float_balance": str(balance), "currency": "NGN"})

    def _stop_business(self, *, principal: Principal, business_id: str,
                       new_status: Literal["paused", "removed"], reason: str) -> dict[str, Any]:
        _require_operations(principal)
        reason = reason.strip() if isinstance(reason, str) else ""
        if not reason:
            raise DomainError("A reason is required", code="business_status_reason_required")
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            business = self._get(business_id)
            if new_status not in self.TRANSITIONS.get(business.status, frozenset()):
                raise Conflict(f"Business cannot transition from {business.status} to {new_status}",
                               code="invalid_business_transition")
            # Existing cards are preserved with their original restriction.
            # They are never redirected automatically; redemption checks active.
            affected = self.repo.list_active_cards_restricted_to_business(business_id)
            if not self.repo.update_business_status(business_id=business_id,
                    expected=(business.status,), new_status=new_status, changed_at=now,
                    actor_id=principal.user_id):
                raise Conflict("Business state changed", code="business_state_changed")
            self.audit.log(event_type=f"business.{new_status}", actor_id=principal.user_id,
                entity_type="business", entity_id=business_id,
                reference=f"business:{business_id}:{new_status}:{int(now.timestamp() * 1000000)}",
                occurred_at=now, data={"reason": reason.strip(), "affected_card_count": len(affected)})
            self.repo.enqueue_outbox(event_key=f"business:{business_id}:{new_status}:{int(now.timestamp())}",
                event_type="business.active_cards_need_resolution",
                payload={"business_id": business_id, "status": new_status,
                         "card_ids": [str(card["id"]) for card in affected],
                         "resolution_required": True})
        return {"status": new_status, "affected_active_card_count": len(affected),
                "cards_redirected": False}

    def _get(self, business_id: str) -> ManagedBusiness:
        business = self.repo.get_business_profile(business_id)
        if not business:
            raise NotFound("Business not found")
        return business

    @staticmethod
    def _aware(value: datetime) -> None:
        if value.tzinfo is None:
            raise DomainError("Operations timestamp must be timezone-aware", code="invalid_datetime")


class BusinessFloatManagementService:
    def __init__(self, *, repo: OperationsRepository, clock: Any,
                 low_float_threshold: Any | None = None):
        self.repo, self.clock = repo, clock
        self.audit = AuditTrailLogger(repo)
        self.default_low_float_threshold = (money(low_float_threshold)
            if low_float_threshold is not None else None)
        if self.default_low_float_threshold is not None and self.default_low_float_threshold <= 0:
            raise ValueError("low_float_threshold must be positive and approved by operations")

    def monitor_low_float(self) -> list[dict[str, Any]]:
        now = self.clock.now()
        self._aware(now)
        alerts = []
        for business in self.repo.list_active_businesses():
            threshold = self._threshold(business)
            if threshold <= 0:  # Schema default 0 means no alert threshold configured.
                continue
            balance = money(self.repo.get_float_balance(
                business_id=business.id, currency="NGN"))
            if balance <= threshold:
                # Daily idempotency key bounds alert duplication while preserving
                # recurring notices if the balance remains low.
                day = now.date().isoformat()
                key = f"business:{business.id}:low-float:{day}"
                self.repo.enqueue_outbox(event_key=key, event_type="business.low_float_alert",
                    payload={"business_id": business.id, "balance": str(balance),
                             "threshold": str(threshold), "currency": "NGN"})
                alerts.append({"business_id": business.id, "balance": str(balance), "currency": "NGN"})
        return alerts

    def dashboard(self, *, principal: Principal) -> dict[str, Any]:
        """Return the authenticated operator's float and ledger history summary."""
        business_id = _require_business_operator(principal)
        business = self.repo.get_business_profile(business_id)
        if not business or business.status not in {"active", "paused"}:
            raise Forbidden("Business float is unavailable", code="business_unavailable")
        threshold = self._threshold(business)
        rows = self.repo.list_float_entries(business_id=business_id)
        normalized = []
        provided = Decimal("0.00")
        redeemed = Decimal("0.00")
        adjustments = Decimal("0.00")
        overdraft_entries = Decimal("0.00")
        for row in rows:
            get = row.get if isinstance(row, dict) else lambda key, default=None: getattr(row, key, default)
            entry_type = str(get("entry_type", ""))
            amount = money(get("amount", 0))
            if entry_type in {"deposit", "top_up"}:
                provided += amount
            elif entry_type == "redemption_draw":
                redeemed += amount
            elif entry_type == "adjustment":
                adjustments += amount
            elif entry_type == "overdraft_cover":
                overdraft_entries += amount
            created_at = get("created_at")
            normalized.append({"entry_type": entry_type, "amount": str(amount),
                "balance_after": str(money(get("balance_after", 0))),
                "created_at": created_at.isoformat() if created_at else None,
                "redemption_id": str(get("redemption_id", "")) or None})
        current = money(self.repo.get_float_balance(business_id=business_id, currency="NGN"))
        return {"business_id": business_id, "currency": "NGN", "current_float": str(current),
            "low_float_threshold": str(threshold), "total_provided": str(provided),
            "total_redeemed": str(redeemed), "adjustments": str(adjustments),
            "overdraft_entries": str(overdraft_entries), "history": normalized}

    def request_top_up(self, *, principal: Principal, amount: Any, reason: str,
                       request_key: str) -> TopUpRequest:
        business_id = _require_business_operator(principal)
        value = money(amount)
        reason = reason.strip() if isinstance(reason, str) else ""
        if value <= 0 or not reason or len(reason) > 500 or not request_key:
            raise DomainError("Positive amount, reason, and idempotency key are required", code="invalid_topup_request")
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            business = self.repo.get_business_profile(business_id)
            if not business or business.status not in {"active", "paused"}:
                raise Forbidden("Business cannot request float while unavailable", code="business_unavailable")
            request = self.repo.create_topup_request(business_id=business_id, amount=value,
                currency="NGN", reason=reason, requested_by=principal.user_id,
                request_key=request_key, requested_at=now)
            self.audit.log(event_type="business.float_topup_requested", actor_id=principal.user_id,
                entity_type="topup_request", entity_id=request.id,
                reference=f"topup:{request.id}:requested", occurred_at=now,
                data={"amount": str(value), "currency": "NGN"})
            self.repo.enqueue_outbox(event_key=f"topup:{request.id}:requested",
                event_type="business.float_topup_review_requested",
                payload={"request_id": request.id, "business_id": business_id,
                         "amount": str(value), "currency": "NGN"})
        return request

    def review_top_up(self, *, principal: Principal, request_id: str,
                      decision: Literal["approved", "rejected"], note: str = "") -> None:
        _require_operations(principal)
        if decision not in {"approved", "rejected"}:
            raise DomainError("Top-up decision must be approved or rejected", code="invalid_topup_decision")
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            request = self.repo.get_topup_request(request_id)
            if not request:
                raise NotFound("Top-up request not found")
            if decision == "rejected":
                if not self.repo.transition_topup_request(request_id=request_id,
                        expected=("pending",), new_status="rejected", changed_at=now,
                        actor_id=principal.user_id, review_note=note.strip()):
                    raise Conflict("Top-up request has already been reviewed", code="topup_already_reviewed")
            else:
                if request.status != "pending":
                    raise Conflict("Only a pending top-up can be approved", code="topup_not_pending")
                self.repo.record_topup_approval(request_id=request_id, actor_id=principal.user_id,
                    note=note.strip(), approved_at=now)
            self.audit.log(event_type=f"business.float_topup_{decision}", actor_id=principal.user_id,
                entity_type="topup_request", entity_id=request.id,
                reference=f"topup:{request.id}:{decision}",
                occurred_at=now, data={"amount": str(request.amount), "currency": request.currency})
            self.repo.enqueue_outbox(event_key=f"topup:{request.id}:{decision}",
                event_type=f"business.float_topup_{decision}", payload={
                    "request_id": request.id, "business_id": request.business_id,
                    "amount": str(request.amount), "currency": request.currency})

    def fulfill_top_up(self, *, principal: Principal, request_id: str,
                       funding_reference: str) -> dict[str, str]:
        _require_operations(principal)
        funding_reference = funding_reference.strip() if isinstance(funding_reference, str) else ""
        if not funding_reference:
            raise DomainError("Funding reference is required", code="funding_reference_required")
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            request = self.repo.get_topup_request(request_id)
            if not request:
                raise NotFound("Top-up request not found")
            if request.status != "pending" or not self.repo.has_topup_approval(request_id):
                raise Conflict("Only an approved pending top-up can be fulfilled", code="topup_not_approved")
            self.repo.record_float_ledger(entry_type="top_up", business_id=request.business_id,
                amount=request.amount, currency="NGN",
                reference=f"topup:{request.id}:funding:{funding_reference}", occurred_at=now,
                source="platform:treasury", destination=f"business:{request.business_id}:float",
                idempotency_key=f"topup:{request.id}:fulfillment")
            if not self.repo.transition_topup_request(request_id=request_id,
                    expected=("pending",), new_status="completed", changed_at=now,
                    actor_id=principal.user_id, funding_reference=funding_reference):
                raise Conflict("Top-up request state changed", code="topup_state_changed")
            self.audit.log(event_type="business.float_topup_fulfilled", actor_id=principal.user_id,
                entity_type="topup_request", entity_id=request.id,
                reference=f"topup:{request.id}:fulfilled", occurred_at=now,
                data={"amount": str(request.amount), "currency": "NGN", "funding_reference": funding_reference})
            self.repo.enqueue_outbox(event_key=f"topup:{request.id}:fulfilled", event_type="business.float_updated",
                payload={"business_id": request.business_id, "amount": str(request.amount),
                         "currency": "NGN"})
        return {"status": "completed", "business_id": request.business_id,
                "amount": str(request.amount), "currency": "NGN"}

    @staticmethod
    def _aware(value: datetime) -> None:
        if value.tzinfo is None:
            raise DomainError("Monitoring timestamp must be timezone-aware", code="invalid_datetime")

    def _threshold(self, business: ManagedBusiness) -> Decimal:
        configured = getattr(business, "low_float_threshold", None)
        if configured is None:
            configured = self.default_low_float_threshold
        return money(configured or 0)
