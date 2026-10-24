"""Explicit card-state and expiry rules shared by card workflows."""

from __future__ import annotations

from datetime import datetime

from .errors import Conflict


CARD_TRANSITIONS: dict[str, frozenset[str]] = {
    # Payment remains a Payment.status; cards are created only after success.
    "inactive": frozenset({"active", "cancelled", "expired", "lost"}),
    "active": frozenset({"redeemed", "cancelled", "expired"}),
    "redeemed": frozenset(),
    "cancelled": frozenset(),
    "expired": frozenset(),
    "lost": frozenset(),
}


class CardLifecycleService:
    """Pure lifecycle rules; state persistence remains with the repository."""

    @staticmethod
    def assert_transition(old_status: str, new_status: str) -> None:
        if new_status not in CARD_TRANSITIONS.get(old_status, frozenset()):
            raise Conflict(f"Card cannot transition from {old_status} to {new_status}", code="invalid_card_transition")

    @staticmethod
    def is_expired(*, expires_at: datetime | None, now: datetime) -> bool:
        if now.tzinfo is None:
            raise Conflict("Card expiry and current time must be timezone-aware", code="invalid_card_datetime")
        # New cards require an expiry. A nullable legacy row is fail-closed so
        # it cannot remain redeemable forever because its expiry was omitted.
        if expires_at is None:
            return True
        if expires_at.tzinfo is None:
            raise Conflict("Card expiry and current time must be timezone-aware", code="invalid_card_datetime")
        return now >= expires_at

    @classmethod
    def assert_redeemable_state(cls, status: str) -> None:
        if status != "active":
            reasons = {
                "pending_payment": ("Payment has not been confirmed", "payment_pending"),
                "inactive": ("Physical card must be activated first", "activation_required"),
                "redeemed": ("Card has already been redeemed", "already_redeemed"),
                "cancelled": ("Card has been cancelled", "cancelled"),
                "expired": ("Card has expired", "expired"),
                "lost": ("Card has been reported lost", "lost"),
            }
            message, code = reasons.get(status, ("Card is not available for redemption", "card_unavailable"))
            raise Conflict(message, code=code)
