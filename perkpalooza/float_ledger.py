"""Business float drawdown and temporary overdraft accounting logic."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from .audit import AuditTrailLogger
from .errors import DomainError
from .money import money


class FloatRepository(Protocol):
    def get_float_balance_for_update(self, *, business_id: str, currency: str) -> Decimal: ...
    def record_float_ledger(self, **entry: Any) -> None: ...
    def record_audit(self, **event: Any) -> None: ...
    def enqueue_outbox(self, *, event_key: str, event_type: str, payload: dict[str, Any]) -> None: ...


class BusinessFloatLedgerService:
    """Draw the full face value and separately record any temporary shortfall.

    Call inside the same atomic transaction as card redemption. The repository
    must lock the business float account when reading its balance so concurrent
    redemptions cannot spend the same available float twice.
    """

    def __init__(self, repo: FloatRepository):
        self.repo = repo
        self.audit = AuditTrailLogger(repo)

    def draw_down(self, *, business_id: str, card_id: str, amount: Any,
                  currency: str, occurred_at: datetime) -> Decimal:
        currency = str(currency).upper()
        if currency != "NGN":
            raise DomainError("Business float currently supports NGN only", code="unsupported_currency")
        value = money(amount)
        if value <= 0 or occurred_at.tzinfo is None:
            raise DomainError("Float drawdown amount and timestamp are invalid", code="invalid_float_drawdown")
        available = money(self.repo.get_float_balance_for_update(business_id=business_id, currency=currency))
        overdraft = max(Decimal("0.00"), value - available)
        base = f"card:{card_id}:business-float"
        self.repo.record_float_ledger(entry_type="redemption_draw", business_id=business_id,
            card_id=card_id, amount=value, currency=currency, reference=f"{base}:drawdown",
            occurred_at=occurred_at, source=f"business:{business_id}:float",
            destination="platform:redemption_payable", allow_overdraft=True,
            idempotency_key=f"{base}:drawdown")
        self.audit.log(event_type="business.float_drawdown", actor_id="system",
            entity_type="business", entity_id=business_id, reference=f"{base}:drawdown",
            occurred_at=occurred_at, data={"card_id": card_id, "amount": str(value), "currency": currency})
        if overdraft > 0:
            self.repo.record_float_ledger(entry_type="overdraft_cover", business_id=business_id,
                card_id=card_id, amount=overdraft, currency=currency,
                reference=f"{base}:overdraft", occurred_at=occurred_at,
                source="platform:overdraft_facility", destination=f"business:{business_id}:overdraft_receivable",
                idempotency_key=f"{base}:overdraft")
            self.audit.log(event_type="business.float_overdraft_created", actor_id="system",
                entity_type="business", entity_id=business_id,
                reference=f"{base}:overdraft", occurred_at=occurred_at,
                data={"business_id": business_id, "amount": str(overdraft), "currency": currency})
            self.repo.enqueue_outbox(event_key=f"{base}:overdraft-alert", event_type="business.float_overdraft_alert",
                payload={"business_id": business_id, "card_id": card_id,
                         "overdraft_amount": str(overdraft), "currency": currency})
        return overdraft
