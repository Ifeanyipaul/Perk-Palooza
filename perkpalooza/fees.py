"""Configurable checkout fee calculation with auditable monetary rounding.

No production rate is hard-coded: the PRD leaves both platform pricing and
Paystack fee treatment open. Supply approved policy callables at app startup.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Callable

from .errors import DomainError
from .money import MAX_CARD_VALUE, money


FeeCalculator = Callable[[Decimal, str], Decimal]


class FeeCalculationService:
    """Return the separate fee components and one combined payable amount.

    Calculators receive the face value and uppercase ISO currency. Each policy
    must define its own approved basis, including whether provider charges are
    calculated on face value or grossed up on the total charged to the giver.
    """

    def __init__(self, *, paystack_fee: FeeCalculator, platform_fee: FeeCalculator):
        self._paystack_fee = paystack_fee
        self._platform_fee = platform_fee

    def calculate(self, face_value: Decimal, currency: str) -> tuple[Decimal, Decimal]:
        face = money(face_value)
        if face <= 0 or face > MAX_CARD_VALUE:
            raise DomainError("Card amount is outside the allowed range", code="amount_out_of_range")
        currency = str(currency).upper()
        if len(currency) != 3 or not currency.isalpha():
            raise DomainError("A valid three-letter currency is required", code="invalid_currency")
        try:
            paystack = money(self._paystack_fee(face, currency))
            platform = money(self._platform_fee(face, currency))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise DomainError("Fee policy returned an invalid amount", code="invalid_fee_policy") from exc
        if paystack < 0 or platform < 0:
            raise DomainError("Fee policy returned a negative amount", code="invalid_fee_policy")
        return paystack, platform

    def quote(self, face_value: Decimal, currency: str) -> dict[str, Decimal | str]:
        face = money(face_value)
        paystack, platform = self.calculate(face, currency)
        return {"face_value": face, "paystack_fee": paystack, "platform_fee": platform,
                "total_payable": money(face + paystack + platform), "currency": currency.upper()}


def rate_fee(*, base: Decimal, rate: Decimal, fixed: Decimal = Decimal("0"),
             cap: Decimal | None = None) -> Decimal:
    """Reusable configured percent + fixed + optional cap calculation.

    This helper does not declare which Paystack or platform rates to use.
    """
    try:
        base, rate, fixed = money(base), Decimal(str(rate)), money(fixed)
        if rate < 0 or fixed < 0 or (cap is not None and money(cap) < 0):
            raise ValueError("negative fee setting")
        result = money(base * rate + fixed)
        return min(result, money(cap)) if cap is not None else result
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise DomainError("Configured fee rule is invalid", code="invalid_fee_policy") from exc
