"""Shared monetary bounds and two-decimal rounding for NGN V1."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from .errors import DomainError


CENT = Decimal("0.01")
MAX_CARD_VALUE = Decimal("10000000")


def money(value: Any, *, name: str = "amount") -> Decimal:
    try:
        result = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise DomainError(f"{name} must be a valid monetary amount", code="invalid_amount")
    if not result.is_finite():
        raise DomainError(f"{name} must be finite", code="invalid_amount")
    return result
