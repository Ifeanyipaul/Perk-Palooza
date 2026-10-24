"""Paystack transaction adapter.

All business amounts use major currency units (for example NGN naira) inside
Perk Palooza. Paystack's API receives and returns the currency's minor units.
Supply an approved currency-to-exponent map; NGN uses 2 decimal places.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from decimal import Decimal
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import DomainError, Unavailable


class PaystackGateway:
    def __init__(self, *, secret_key: str,
                 currency_exponents: dict[str, int] | None = None,
                 base_url: str = "https://api.paystack.co",
                 timeout_seconds: float = 15,
                 transport: Callable[[str, bytes | None, dict[str, str], float], dict[str, Any]] | None = None):
        self.secret_key = secret_key
        self.currency_exponents = {k.upper(): v for k, v in (currency_exponents or {"NGN": 2}).items()}
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._transport = transport or self._request_json

    def initiate(self, *, reference: str, amount: Decimal, currency: str, email: str) -> dict[str, Any]:
        if not reference or not email or "@" not in email:
            raise DomainError("A payment reference and valid giver email are required", code="invalid_checkout")
        payload = {"email": email, "amount": self.to_minor_units(amount, currency),
                   "currency": currency.upper(), "reference": reference}
        result = self._transport("/transaction/initialize", json.dumps(payload).encode("utf-8"),
                                 self._headers(json_body=True), self.timeout_seconds)
        data = result.get("data") or {}
        if result.get("status") is not True or data.get("reference") != reference or not data.get("authorization_url"):
            raise Unavailable("Paystack could not initialize checkout", code="payment_initialization_failed")
        return {"reference": reference, "authorization_url": data["authorization_url"],
                "access_code": data.get("access_code")}

    def verify(self, reference: str) -> dict[str, Any]:
        if not reference or len(reference) > 128 or not re.fullmatch(r"[A-Za-z0-9_-]+", reference):
            raise DomainError("Invalid payment reference", code="invalid_payment_reference")
        result = self._transport(f"/transaction/verify/{reference}", None,
                                 self._headers(), self.timeout_seconds)
        data = result.get("data") or {}
        if result.get("status") is not True or data.get("reference") != reference:
            raise Unavailable("Paystack verification is unavailable", code="payment_verification_failed")
        currency = str(data.get("currency", "")).upper()
        status = str(data.get("status", "")).lower()
        return {"reference": reference, "status": normalize_paystack_status(status),
                "amount": self.from_minor_units(data.get("amount"), currency), "currency": currency,
                "gateway_status": status}

    def valid_webhook(self, raw_body: bytes, signature: str) -> bool:
        if not raw_body or not signature or not self.secret_key:
            return False
        expected = hmac.new(self.secret_key.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature.strip())

    def to_minor_units(self, amount: Decimal, currency: str) -> int:
        currency = currency.upper()
        exponent = self._exponent(currency)
        major = Decimal(str(amount))
        if not major.is_finite() or major <= 0:
            raise DomainError("Payment amount must be positive", code="invalid_amount")
        minor = major * (10 ** exponent)
        if minor != minor.to_integral_value():
            raise DomainError("Amount has more precision than the currency supports", code="invalid_amount_precision")
        return int(minor)

    def from_minor_units(self, amount: Any, currency: str) -> Decimal:
        exponent = self._exponent(currency)
        try:
            minor = Decimal(str(amount))
        except Exception as exc:
            raise DomainError("Paystack returned an invalid amount", code="invalid_provider_amount") from exc
        if not minor.is_finite() or minor != minor.to_integral_value() or minor < 0:
            raise DomainError("Paystack returned an invalid amount", code="invalid_provider_amount")
        return minor / Decimal(10 ** exponent)

    def _exponent(self, currency: str) -> int:
        exponent = self.currency_exponents.get(currency.upper())
        if exponent is None or not isinstance(exponent, int) or exponent < 0 or exponent > 4:
            raise DomainError("Currency minor-unit precision is not configured", code="unsupported_currency")
        return exponent

    def _headers(self, *, json_body: bool = False) -> dict[str, str]:
        if not self.secret_key:
            raise Unavailable("Paystack credentials are not configured", code="payment_not_configured")
        headers = {"Authorization": f"Bearer {self.secret_key}", "Accept": "application/json"}
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _request_json(self, path: str, body: bytes | None, headers: dict[str, str], timeout: float) -> dict[str, Any]:
        request = Request(self.base_url + path, data=body, headers=headers,
                          method="POST" if body is not None else "GET")
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
            decoded = json.loads(payload.decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise Unavailable("Could not contact Paystack", code="payment_provider_unavailable") from exc
        if not isinstance(decoded, dict):
            raise Unavailable("Paystack returned an invalid response", code="invalid_provider_response")
        return decoded


def normalize_paystack_status(status: str) -> str:
    """Normalize Paystack transaction outcomes to the requested state vocabulary."""
    normalized = status.strip().lower()
    if normalized in {"success", "successful"}:
        return "success"
    if normalized in {"pending", "ongoing", "processing", "queued", "otp"}:
        return "pending"
    if normalized in {"abandoned", "cancelled", "canceled"}:
        return "cancelled"
    if normalized in {"failed", "reversed", "expired", "timeout"}:
        return "failed"
    return "pending"
