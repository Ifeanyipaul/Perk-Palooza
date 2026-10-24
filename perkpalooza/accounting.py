"""Append-only giver wallet ledger and balance projections.

All amounts are positive transfers between named accounts. Balances are
projections of immutable entries; this module never writes a balance field.
The repository must append entries only and enforce unique reference/idempotency
keys using the teammate-owned database schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Protocol

from .errors import DomainError
from .money import money


@dataclass(frozen=True)
class LedgerEntry:
    """WalletEntry projection using the teammate schema's persisted fields.

    The adapter resolves ``giver_id`` to Wallet.user and converts NGN decimals
    to integer kobo for BigInteger columns. Currency is fixed to NGN by Wallet.
    """
    giver_id: str
    entry_type: str
    amount: Decimal
    available_change: Decimal
    committed_change: Decimal
    locked_change: Decimal
    created_at: datetime
    card_id: str | None = None
    payment_reference: str | None = None


@dataclass(frozen=True)
class WalletBalances:
    available: Decimal
    committed: Decimal
    redeemed: Decimal
    locked: Decimal
    currency: str = "NGN"


class LedgerRepository(Protocol):
    def record_giver_ledger(self, **entry: Any) -> None: ...
    def list_giver_ledger_entries(self, *, giver_id: str, currency: str) -> Iterable[LedgerEntry | dict[str, Any]]: ...


class WalletLedgerService:
    CURRENCY = "NGN"

    def __init__(self, repo: LedgerRepository):
        self.repo = repo

    def record_issuance(self, *, giver_id: str, card_id: str, payment_reference: str,
                        face_value: Any, paystack_fee: Any, platform_fee: Any, currency: str,
                        occurred_at: datetime) -> None:
        """Book the paid split, then commit the card face value to the card."""
        self._validate_currency(currency)
        if occurred_at.tzinfo is None:
            raise DomainError("Ledger timestamp must be timezone-aware", code="invalid_ledger_timestamp")
        face, processor, platform = money(face_value), money(paystack_fee), money(platform_fee)
        if face <= 0 or processor < 0 or platform < 0:
            raise DomainError("Ledger amounts are invalid", code="invalid_ledger_amount")
        # Provider and platform fees are already recorded on Payment; WalletEntry
        # has no fee/source/destination columns. Only card face value affects the
        # giver's wallet projection.
        self._transfer(giver_id=giver_id, card_id=card_id, payment_reference=payment_reference,
            entry_type="funded", occurred_at=occurred_at, amount=face,
            available_change=face, committed_change=Decimal("0"), locked_change=Decimal("0"))
        self._transfer(giver_id=giver_id, card_id=card_id, payment_reference=payment_reference,
            entry_type="committed", occurred_at=occurred_at, amount=face,
            available_change=-face, committed_change=face, locked_change=Decimal("0"))

    def release_cancelled(self, *, giver_id: str, card_id: str, amount: Any,
                          occurred_at: datetime) -> None:
        value = money(amount)
        self._transfer(giver_id=giver_id, card_id=card_id, entry_type="released",
            occurred_at=occurred_at, amount=value, available_change=value,
            committed_change=-value, locked_change=Decimal("0"))

    def debit_redeemed(self, *, giver_id: str, card_id: str, amount: Any,
                       occurred_at: datetime) -> None:
        value = money(amount)
        self._transfer(giver_id=giver_id, card_id=card_id, entry_type="redeemed",
            occurred_at=occurred_at, amount=value, available_change=Decimal("0"),
            committed_change=-value, locked_change=Decimal("0"))

    def lock_expired(self, *, giver_id: str, card_id: str, amount: Any,
                     occurred_at: datetime) -> None:
        value = money(amount)
        self._transfer(giver_id=giver_id, card_id=card_id, entry_type="locked",
            occurred_at=occurred_at, amount=value, available_change=Decimal("0"),
            committed_change=-value, locked_change=value)

    def balances(self, *, giver_id: str) -> WalletBalances:
        accounts = {name: Decimal("0.00") for name in ("available", "committed", "redeemed", "locked")}
        for row in self.repo.list_giver_ledger_entries(giver_id=giver_id, currency=self.CURRENCY):
            entry = row if isinstance(row, LedgerEntry) else LedgerEntry(**row)
            self._validate_entry(entry)
            accounts["available"] += money(entry.available_change)
            accounts["committed"] += money(entry.committed_change)
            accounts["locked"] += money(entry.locked_change)
            if entry.entry_type == "redeemed":
                accounts["redeemed"] += money(entry.amount)
        if any(balance < 0 for balance in accounts.values()):
            raise DomainError("Wallet ledger projection is inconsistent", code="ledger_projection_invalid")
        return WalletBalances(**accounts)

    def _transfer(self, *, giver_id: str, card_id: str, payment_reference: str | None = None,
                  entry_type: str, occurred_at: datetime, amount: Any,
                  available_change: Any, committed_change: Any, locked_change: Any) -> None:
        value = money(amount)
        changes = tuple(money(v) for v in (available_change, committed_change, locked_change))
        if entry_type not in {"funded", "committed", "redeemed", "released", "locked", "refunded", "reissued"}:
            raise DomainError("Wallet entry type is not in the database schema", code="invalid_ledger_entry")
        if value <= 0 or not giver_id or occurred_at.tzinfo is None:
            raise DomainError("Ledger entry is invalid", code="invalid_ledger_entry")
        self.repo.record_giver_ledger(giver_id=giver_id, card_id=card_id,
            payment_reference=payment_reference, entry_type=entry_type, amount=value,
            available_change=changes[0], committed_change=changes[1], locked_change=changes[2],
            created_at=occurred_at)

    @classmethod
    def _validate_currency(cls, currency: str) -> None:
        if str(currency).upper() != cls.CURRENCY:
            raise DomainError("Wallet ledger currently supports NGN only", code="unsupported_currency")

    def _validate_entry(self, entry: LedgerEntry) -> None:
        if entry.created_at.tzinfo is None or entry.amount <= 0:
            raise DomainError("Ledger contains an invalid immutable entry", code="ledger_entry_invalid")
        if entry.entry_type not in {"funded", "committed", "redeemed", "released", "locked", "refunded", "reissued"}:
            raise DomainError("Wallet entry type is invalid", code="ledger_entry_invalid")


