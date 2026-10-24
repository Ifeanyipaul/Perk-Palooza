"""Dispute workflow rules mapped to the teammate-owned Dispute model.

Persistence and atomic state transitions are provided by a repository adapter;
this module contains authorization, validation, audit, and notification logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from .audit import AuditTrailLogger
from .auth import Principal
from .errors import Conflict, DomainError, Forbidden, NotFound


@dataclass(frozen=True)
class DisputeRecord:
    id: str
    card_id: str
    raised_by: str
    reason: str
    status: Literal["open", "resolved"]
    resolution: str = ""
    created_at: datetime | None = None
    resolved_at: datetime | None = None


class DisputeRepository(Protocol):
    def atomic(self) -> Any: ...
    def get_card_for_update(self, card_id: str) -> Any | None:
        """Lock the Card row so duplicate open-dispute checks serialize."""
        ...
    def get_redemption_for_card(self, card_id: str) -> Any | None: ...
    def get_dispute(self, dispute_id: str) -> DisputeRecord | None: ...
    def get_open_dispute_for_card(self, card_id: str) -> DisputeRecord | None: ...
    def create_dispute(self, *, card_id: str, raised_by: str, reason: str, created_at: datetime) -> DisputeRecord: ...
    def list_open_disputes(self) -> list[DisputeRecord]: ...
    def resolve_dispute(self, *, dispute_id: str, resolution: str, resolved_at: datetime, expected_status: str = "open") -> bool: ...
    def record_audit(self, **event: Any) -> None: ...
    def enqueue_outbox(self, *, event_key: str, event_type: str, payload: dict[str, Any]) -> None: ...


class DisputeService:
    """Givers and the redeeming business may raise; only platform admins resolve."""

    def __init__(self, *, repo: DisputeRepository, clock: Any):
        self.repo, self.clock = repo, clock
        self.audit = AuditTrailLogger(repo)

    def raise_dispute(self, *, principal: Principal, card_id: str, reason: str) -> DisputeRecord:
        reason = reason.strip() if isinstance(reason, str) else ""
        if not reason or len(reason) > 2000:
            raise DomainError("A dispute reason of 1 to 2000 characters is required", code="invalid_dispute_reason")
        if principal.role not in {"giver", "business"}:
            raise Forbidden("Only a giver or the redeeming business may raise a dispute", code="dispute_role_forbidden")
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            card = self.repo.get_card_for_update(card_id)
            if not card:
                raise NotFound("Card not found")
            if principal.role == "giver":
                if str(card.giver_id) != str(principal.user_id):
                    raise Forbidden("Card does not belong to this giver", code="card_scope_forbidden")
            else:
                business_id = principal.business_id
                redemption = self.repo.get_redemption_for_card(card_id)
                if (not business_id or not redemption
                        or str(redemption.business_id) != str(business_id)):
                    raise Forbidden("Only the redeeming business may dispute this card", code="business_scope_forbidden")
            existing = self.repo.get_open_dispute_for_card(card_id)
            if existing:
                raise Conflict("An open dispute already exists for this card", code="dispute_already_open")
            dispute = self.repo.create_dispute(card_id=card_id, raised_by=principal.user_id,
                reason=reason, created_at=now)
            self.audit.log(event_type="dispute.raised", actor_id=principal.user_id,
                entity_type="dispute", entity_id=dispute.id, reference=f"dispute:{dispute.id}:raised",
                occurred_at=now, data={"card_id": card_id, "raiser_role": principal.role})
            self.repo.enqueue_outbox(event_key=f"dispute:{dispute.id}:raised",
                event_type="dispute.raised", payload={"dispute_id": dispute.id, "card_id": card_id})
        return dispute

    def list_open_for_operations(self, *, principal: Principal) -> list[DisputeRecord]:
        self._require_admin(principal)
        return self.repo.list_open_disputes()

    def resolve(self, *, principal: Principal, dispute_id: str, resolution: str) -> DisputeRecord:
        self._require_admin(principal)
        resolution = resolution.strip() if isinstance(resolution, str) else ""
        if not resolution or len(resolution) > 2000:
            raise DomainError("A resolution of 1 to 2000 characters is required", code="invalid_dispute_resolution")
        now = self.clock.now()
        self._aware(now)
        with self.repo.atomic():
            dispute = self.repo.get_dispute(dispute_id)
            if not dispute:
                raise NotFound("Dispute not found")
            if dispute.status != "open":
                raise Conflict("Only open disputes can be resolved", code="dispute_not_open")
            if not self.repo.resolve_dispute(dispute_id=dispute.id, resolution=resolution,
                                             resolved_at=now, expected_status="open"):
                raise Conflict("Dispute changed while being resolved", code="dispute_state_changed")
            self.audit.log(event_type="dispute.resolved", actor_id=principal.user_id,
                entity_type="dispute", entity_id=dispute.id, reference=f"dispute:{dispute.id}:resolved",
                occurred_at=now, data={"card_id": dispute.card_id})
            self.repo.enqueue_outbox(event_key=f"dispute:{dispute.id}:resolved",
                event_type="dispute.resolved", payload={"dispute_id": dispute.id,
                    "card_id": dispute.card_id, "raised_by": dispute.raised_by})
        return DisputeRecord(id=dispute.id, card_id=dispute.card_id, raised_by=dispute.raised_by,
            reason=dispute.reason, status="resolved", resolution=resolution,
            created_at=dispute.created_at, resolved_at=now)

    @staticmethod
    def _require_admin(principal: Principal) -> None:
        if principal.role != "admin":
            raise Forbidden("Platform operations access is required", code="operations_role_required")

    @staticmethod
    def _aware(now: datetime) -> None:
        if now.tzinfo is None:
            raise DomainError("Dispute timestamps must be timezone-aware", code="invalid_dispute_timestamp")
