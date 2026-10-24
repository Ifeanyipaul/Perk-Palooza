"""Typed ports between business logic and teammate-owned persistence/integrations.

Implement these protocols against the agreed database schema. In particular,
``atomic`` and ``claim_redemption`` must use a real DB transaction/row lock or a
conditional update so concurrent requests cannot redeem twice.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Protocol


CardStatus = Literal[
    "inactive", "active", "redeemed", "cancelled", "expired", "lost",
]


@dataclass(frozen=True)
class CardRequest:
    giver_id: str
    amount: Decimal
    currency: str
    purpose: str
    restriction_type: Literal["business", "category"]
    restriction_target_id: str
    expires_at: datetime
    delivery_method: Literal["email", "whatsapp", "physical"]
    recipient_destination: str | None = None
    physical_shipping_details: dict[str, Any] | None = None
    idempotency_key: str = ""


@dataclass(frozen=True)
class Card:
    id: str
    giver_id: str
    amount: Decimal
    currency: str
    purpose: str
    restriction_type: str
    restriction_target_id: str
    # Database permits null for historical rows. New CardRequest requires expiry;
    # lifecycle policy treats a missing expiry as expired/locked (fail closed).
    expires_at: datetime | None
    delivery_method: str
    status: CardStatus
    code: str = ""
    payment_reference: str | None = None
    recipient_destination: str | None = None
    physical_shipping_details: dict[str, Any] | None = None
    replacement_for_id: str | None = None
    created_at: datetime | None = None
    delivery_status: str | None = None


@dataclass(frozen=True)
class Business:
    id: str
    category_id: str
    approved: bool
    active: bool


@dataclass(frozen=True)
class CheckoutQuote:
    face_value: Decimal
    payment_fee: Decimal
    platform_fee: Decimal
    total: Decimal
    currency: str


class UnitOfWork(Protocol):
    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool | None: ...


class Repository(Protocol):
    """Persistence port; redemption claims require a row lock in atomic()."""
    def atomic(self) -> AbstractContextManager[UnitOfWork]: ...
    def get_card(self, card_id: str) -> Card | None: ...
    def list_cards_for_giver(self, giver_id: str) -> list[Card]: ...
    def list_cards_due_for_expiry(self, *, now: datetime, limit: int) -> list[str]: ...
    def get_card_by_payment_reference(self, reference: str) -> Card | None: ...
    def get_card_by_code(self, code: str) -> Card | None: ...
    def get_business(self, business_id: str) -> Business | None: ...
    def is_category_approved(self, category_id: str) -> bool: ...
    def describe_restriction(self, restriction_type: str, target_id: str) -> str | None: ...
    def get_checkout(self, reference: str) -> dict[str, Any] | None: ...
    def get_checkout_by_reference(self, reference: str) -> dict[str, Any] | None: ...
    def save_checkout(self, reference: str, values: dict[str, Any]) -> None: ...
    def claim_checkout_initialization(self, *, idempotency_key: str, now: datetime, lease_until: datetime) -> bool: ...
    def create_card(self, values: dict[str, Any]) -> Card:
        """Create a prepaid CardBatch and its Card, mapping domain fields to schema fields.

        Create the required CardBatch, generate a unique serial_number and 20-character
        code, link the verified Payment, map face_value in integer kobo, map card_type/
        status, and set exactly one business/category FK. The adapter must not store
        domain-only fields that have no model column.
        Do not persist domain-only fields the model does not contain.
        """
        ...
    def get_replacement(self, *, original_card_id: str, request_key: str) -> Card | None: ...
    def transition_card(self, card_id: str, expected: tuple[str, ...], new_status: str, **values: Any) -> bool: ...
    def create_redemption(self, *, card_id: str, business_id: str, amount_spent: Decimal,
                         leftover: Decimal, cashback_amount: Decimal, redeemed_at: datetime) -> None:
        """Create the Card's required OneToOne Redemption within the same atomic transaction."""
        ...
    def claim_redemption(self, card_id: str, business_id: str, now: datetime, *,
                         request_key: str, request_started_at: datetime,
                         expiry_grace: Any = None) -> Card | None:
        """Under select_for_update, recheck status, expiry, restriction, and
        current business status while holding the card/business locks. Use a
        database-authoritative current time. Grace is valid only when the request
        began before expiry and finishes by expiry + configured grace. Return the
        locked active Card; the service creates Redemption and transitions it to
        redeemed in the same transaction. Card/Redemption uniqueness must make
        retries side-effect-safe because request_key has no schema column.
        """
        ...
    def get_float_balance_for_update(self, *, business_id: str, currency: str) -> Decimal:
        """Read the ledger-derived balance while locking this business float."""
        ...
    def record_giver_ledger(self, **entry: Any) -> None:
        """Map to WalletEntry's entry_type/amount/change/card/payment/note/time fields.

        WalletEntry has no currency, source/destination, or unique reference column;
        use NGN Wallet, kobo BigIntegers, and locked Payment/Card checks for replay safety.
        """
        ...
    def list_giver_ledger_entries(self, *, giver_id: str, currency: str) -> list[Any]: ...
    def record_float_ledger(self, **entry: Any) -> None:
        """Map to FloatEntry and calculate its required balance_after under the float lock."""
        ...
    def record_audit(self, **event: Any) -> None: ...
    def enqueue_outbox(self, *, event_key: str, event_type: str, payload: dict[str, Any]) -> None: ...


class PaymentGateway(Protocol):
    def initiate(self, *, reference: str, amount: Decimal, currency: str, email: str) -> dict[str, Any]: ...
    def verify(self, reference: str) -> dict[str, Any]: ...
    def valid_webhook(self, raw_body: bytes, signature: str) -> bool: ...


class CodeGenerator(Protocol):
    def new_code(self) -> str: ...
    def digest(self, code: str) -> str: ...
    def encrypt_for_delivery(self, code: str) -> str: ...


class FeePolicy(Protocol):
    def calculate(self, face_value: Decimal, currency: str) -> tuple[Decimal, Decimal]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class DeliveryPolicy(Protocol):
    def send_card(self, *, method: str, destination: str, code: str, card: Card) -> None: ...
