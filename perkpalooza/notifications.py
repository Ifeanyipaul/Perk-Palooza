"""Retry-safe notification dispatch for persisted outbox events."""

from __future__ import annotations

from typing import Any, Literal, Protocol


class NotificationGateway(Protocol):
    def notify(self, *, recipient_type: Literal["giver", "business", "operations"],
               recipient_id: str | None, event_type: str, payload: dict[str, Any],
               idempotency_key: str) -> None: ...


class NotificationDispatcher:
    """Deliver one already-committed outbox event without changing domain state.

    Do not call inside payment/redemption transactions. The outbox worker should
    mark events delivered only after this returns and retry exceptions using the
    same event key. The gateway resolves current contact preferences/channels.
    """

    ROUTES = {
        "payment.confirmed": (("giver", "giver_id"),),
        "payment.pending": (("giver", "giver_id"),),
        "payment.failed": (("giver", "giver_id"),),
        "payment.cancelled": (("giver", "giver_id"),),
        "card.redeemed": (("giver", "giver_id"),),
        "card.expired": (("giver", "giver_id"),),
        "card.cancelled": (("giver", "giver_id"),),
        "card.activated": (("giver", "giver_id"),),
        "business.low_float_alert": (("business", "business_id"), ("operations", None)),
        "business.float_overdraft_alert": (("business", "business_id"), ("operations", None)),
        "business.failed_validation_reported": (("business", "business_id"), ("operations", None)),
        "business.float_topup_review_requested": (("operations", None),),
        "business.float_topup_approved": (("business", "business_id"),),
        "business.float_topup_rejected": (("business", "business_id"),),
        "business.float_updated": (("business", "business_id"),),
        "business.active_cards_need_resolution": (("operations", None),),
    }

    def __init__(self, gateway: NotificationGateway):
        self.gateway = gateway

    def dispatch(self, *, event_type: str, event_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        routes = self.ROUTES.get(event_type)
        if routes is None:
            return {"status": "ignored", "event_type": event_type}
        delivered = 0
        for recipient_type, id_field in routes:
            recipient_id = str(payload[id_field]) if id_field and payload.get(id_field) else None
            self.gateway.notify(recipient_type=recipient_type, recipient_id=recipient_id,
                event_type=event_type, payload=payload,
                idempotency_key=f"{event_key}:{recipient_type}:{recipient_id or 'all'}")
            delivered += 1
        return {"status": "dispatched", "recipient_count": delivered}
