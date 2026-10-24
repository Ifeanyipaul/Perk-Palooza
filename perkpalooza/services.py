"""Core Perk Palooza workflows; no persistence schema or framework coupling."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from cryptography.fernet import Fernet
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from .accounting import WalletLedgerService
from .audit import AuditTrailLogger
from .auth import Principal, authorize_redemption
from .contracts import Card, CardRequest, CheckoutQuote, Clock, CodeGenerator, DeliveryPolicy, FeePolicy, PaymentGateway, Repository
from .delivery import ActivationVerifier, PhysicalCardService
from .errors import Conflict, DomainError, Forbidden, NotFound, Unavailable
from .float_ledger import BusinessFloatLedgerService
from .lifecycle import CardLifecycleService
from .money import CENT, MAX_CARD_VALUE, money


def validate_card_request(request: CardRequest, now: datetime) -> None:
    amount = money(request.amount)
    if amount <= 0 or amount > MAX_CARD_VALUE:
        raise DomainError("Card amount is outside the allowed range", code="amount_out_of_range")
    if not request.giver_id or not request.idempotency_key:
        raise DomainError("Giver and idempotency key are required", code="missing_idempotency_key")
    if not request.purpose or len(request.purpose.strip()) > 240:
        raise DomainError("Purpose is required and must be 240 characters or fewer", code="invalid_purpose")
    if request.restriction_type not in ("business", "category") or not request.restriction_target_id:
        raise DomainError("Choose exactly one approved business or category", code="invalid_restriction")
    if (not isinstance(request.expires_at, datetime) or request.expires_at.tzinfo is None
            or now.tzinfo is None):
        raise DomainError("Expiry and server time must be timezone-aware", code="invalid_datetime")
    if request.expires_at <= now:
        raise DomainError("Expiry must be in the future", code="invalid_expiry")
    if request.delivery_method not in ("email", "whatsapp", "physical"):
        raise DomainError("Unsupported delivery method", code="invalid_delivery_method")
    if request.delivery_method in ("email", "whatsapp") and not request.recipient_destination:
        raise DomainError("Recipient destination is required for digital delivery", code="missing_destination")
    if request.delivery_method == "physical" and not request.physical_shipping_details:
        raise DomainError("Shipping details are required for physical delivery", code="missing_shipping_details")


class SecureCodeGenerator:
    """Generate schema-compatible 20-character cryptographically random codes.

    The current Card schema stores the code directly with max_length=20.
    At-rest hashing requires a schema migration and cannot be claimed here.
    """

    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

    def __init__(self, *, encryption_key: bytes | str):
        """Use a dedicated Fernet key from secret management, never the DB/source."""
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode("ascii")
        self._fernet = Fernet(encryption_key)

    def new_code(self) -> str:
        return "".join(secrets.choice(self.ALPHABET) for _ in range(20))

    def digest(self, code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def encrypt_for_delivery(self, code: str) -> str:
        if not isinstance(code, str) or not code:
            raise DomainError("Card code cannot be empty", code="invalid_card_code")
        return self._fernet.encrypt(code.encode("ascii")).decode("ascii")


class CardService:
    def __init__(self, *, repo: Repository, fees: FeePolicy, payments: PaymentGateway,
                 codes: CodeGenerator, clock: Clock, delivery: DeliveryPolicy | None = None,
                 payment_webhook_secret: str = "", expiry_grace: timedelta | None = None,
                 checkout_init_lease: timedelta = timedelta(seconds=30),
                 activation_verifier: ActivationVerifier | None = None):
        self.repo, self.fees, self.payments = repo, fees, payments
        self.audit = AuditTrailLogger(repo)
        self.wallet_ledger = WalletLedgerService(repo)
        self.float_ledger = BusinessFloatLedgerService(repo)
        self.codes, self.clock, self.delivery = codes, clock, delivery
        self.payment_webhook_secret = payment_webhook_secret
        self.expiry_grace = expiry_grace  # must be configured only after policy approval
        self.checkout_init_lease = checkout_init_lease
        self.activation_verifier = activation_verifier

    def quote(self, amount: Any, currency: str) -> CheckoutQuote:
        face = money(amount)
        if face <= 0 or face > MAX_CARD_VALUE:
            raise DomainError("Card amount is outside the allowed range", code="amount_out_of_range")
        if str(currency).upper() != "NGN":
            raise DomainError("Card checkout currently supports NGN only", code="unsupported_currency")
        payment_fee, platform_fee = self.fees.calculate(face, "NGN")
        payment_fee, platform_fee = money(payment_fee), money(platform_fee)
        if payment_fee < 0 or platform_fee < 0:
            raise DomainError("Fee policy returned an invalid fee", code="invalid_fee_policy")
        return CheckoutQuote(face, payment_fee, platform_fee, face + payment_fee + platform_fee, "NGN")

    def start_checkout(self, request: CardRequest, *, principal: Principal,
                       giver_email: str) -> dict[str, Any]:
        if principal.role != "giver" or str(request.giver_id) != str(principal.user_id):
            raise Forbidden("Checkout must be started by the owning giver", code="giver_scope_forbidden")
        now = self.clock.now()
        validate_card_request(request, now)
        self._validate_restriction_target(request)
        quote = self.quote(request.amount, request.currency)
        fingerprint = self._fingerprint(request, quote)
        existing = self.repo.get_checkout(request.idempotency_key)
        if existing:
            if existing.get("request_fingerprint") != fingerprint:
                raise Conflict("Idempotency key was already used for different checkout data", code="idempotency_conflict")
            if existing.get("state") != "initializing":
                return existing
            record = existing
        else:
            # Stable reference plus unique idempotency reservation prevents
            # application retries from initiating an unrelated second payment.
            reference_seed = f"{request.giver_id}\0{request.idempotency_key}".encode("utf-8")
            ref = "PP-" + hashlib.sha256(reference_seed).hexdigest()[:32]
            record = {"reference": ref, "request": asdict(request), "quote": asdict(quote),
                      "request_fingerprint": fingerprint, "gateway": {}, "state": "initializing",
                      "created_at": now, "idempotency_key": request.idempotency_key}
            with self.repo.atomic():
                # Adapter must insert once under a unique idempotency key. If a
                # concurrent request wins, fetch and validate its reservation.
                concurrent = self.repo.get_checkout(request.idempotency_key)
                if concurrent:
                    if concurrent.get("request_fingerprint") != fingerprint:
                        raise Conflict("Idempotency key was already used for different checkout data", code="idempotency_conflict")
                    record = concurrent
                    if record.get("state") != "initializing":
                        return record
                else:
                    self.repo.save_checkout(request.idempotency_key, record)

        with self.repo.atomic():
            owns_initialization = self.repo.claim_checkout_initialization(
                idempotency_key=request.idempotency_key, now=now,
                lease_until=now + self.checkout_init_lease)
        if not owns_initialization:
            latest = self.repo.get_checkout(request.idempotency_key) or record
            latest["status_check_required"] = True
            return latest

        # The reservation survives provider/network failures. A retry reuses the
        # same reference; the provider adapter must treat repeated references as
        # the same checkout attempt and never create a second charge.
        checkout = self.payments.initiate(reference=record["reference"], amount=quote.total,
                                          currency=quote.currency, email=giver_email)
        record["gateway"] = checkout
        record["state"] = "pending"
        record["initialized_at"] = self.clock.now()
        with self.repo.atomic():
            self.repo.save_checkout(request.idempotency_key, record)
            self.audit.log(event_type="payment.initiated", actor_id=request.giver_id,
                entity_type="payment", entity_id=record["reference"], reference=f"payment:{record['reference']}:initiated",
                occurred_at=record["initialized_at"],
                idempotency_key=f"payment-initiated:{record['reference']}",
                data={"amount": str(quote.total), "currency": quote.currency})
        return record

    @staticmethod
    def _fingerprint(request: CardRequest, quote: CheckoutQuote) -> str:
        payload = asdict(request)
        payload["amount"] = str(money(request.amount))
        payload["expires_at"] = request.expires_at.isoformat()
        payload["quote"] = {"face_value": str(quote.face_value), "payment_fee": str(quote.payment_fee),
                            "platform_fee": str(quote.platform_fee), "total": str(quote.total), "currency": quote.currency}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

    def _validate_restriction_target(self, request: CardRequest) -> None:
        """Ensure there is one existing, approved restriction target before payment."""
        if request.restriction_type == "business":
            business = self.repo.get_business(request.restriction_target_id)
            if not business or not business.approved or not business.active:
                raise DomainError("Choose one approved and active business", code="restriction_target_unavailable")
            return
        if request.restriction_type == "category" and self.repo.is_category_approved(request.restriction_target_id):
            return
        raise DomainError("Choose one approved business category", code="restriction_target_unavailable")

    @staticmethod
    def _assert_transition(old_status: str, new_status: str) -> None:
        CardLifecycleService.assert_transition(old_status, new_status)

    def _transition(self, card: Card, expected: tuple[str, ...], new_status: str, **values: Any) -> None:
        for old_status in expected:
            self._assert_transition(old_status, new_status)
        if not self.repo.transition_card(card.id, expected, new_status, **values):
            raise Conflict("Card state changed; refresh and try again", code="card_state_changed")

    def handle_payment_webhook(self, *, raw_body: bytes, signature: str) -> dict[str, Any]:
        if not self.payments.valid_webhook(raw_body, signature):
            raise Forbidden("Invalid payment webhook signature", code="invalid_webhook_signature")
        try:
            event = json.loads(raw_body)
            if not isinstance(event, dict) or not isinstance(event.get("data"), dict):
                raise ValueError("invalid event shape")
            event_type = event.get("event")
            if event_type not in {"charge.success", "charge.pending", "charge.failed"}:
                return {"status": "ignored", "event": str(event_type or "unknown")}
            reference = event["data"]["reference"]
            if not isinstance(reference, str) or not reference:
                raise ValueError("invalid reference")
        except (ValueError, KeyError, TypeError):
            raise DomainError("Malformed payment webhook", code="invalid_webhook")
        return self._confirm_payment(reference)

    def payment_status_for_giver(self, *, reference: str, principal: Principal) -> dict[str, Any]:
        if principal.role != "giver":
            raise Forbidden("Giver access is required", code="giver_role_required")
        checkout = self.repo.get_checkout_by_reference(reference)
        if not checkout:
            raise NotFound("Checkout reference was not found", code="checkout_not_found")
        if str(checkout["request"]["giver_id"]) != str(principal.user_id):
            raise Forbidden("Checkout does not belong to this giver", code="giver_scope_forbidden")
        return self._confirm_payment(reference)

    def _confirm_payment(self, reference: str) -> dict[str, Any]:
        # Verify through the provider API: webhook content and browser redirects are not proof.
        verified = self.payments.verify(reference)
        now = self.clock.now()
        payment_status = str(verified.get("status", "pending")).lower()
        if payment_status not in {"success", "pending", "failed", "cancelled"}:
            payment_status = "pending"
        preview = self.repo.get_checkout_by_reference(reference)
        if not preview:
            raise NotFound("Checkout reference was not found", code="checkout_not_found")
        if payment_status == "success" and not self.repo.get_card_by_payment_reference(reference):
            mismatch = (verified.get("reference") != reference
                or money(verified.get("amount")) != money(preview["quote"]["total"])
                or str(verified.get("currency", "")).upper() != preview["quote"]["currency"])
            if mismatch:
                # This occurs before the issuance transaction so the integrity
                # failure itself remains in the audit trail after the API error.
                self.audit.log(event_type="payment.mismatch", actor_id=preview["request"]["giver_id"],
                    entity_type="payment", entity_id=reference, reference=f"payment:{reference}:mismatch",
                    occurred_at=now, data={"provider_status": "success"})
                raise Conflict("Verified payment details do not match checkout", code="payment_mismatch")
        with self.repo.atomic():
            checkout = self.repo.get_checkout_by_reference(reference)
            if not checkout:
                raise NotFound("Checkout reference was not found", code="checkout_not_found")
            existing = self.repo.get_card_by_payment_reference(reference)
            if existing:
                # Success is immutable. Late failed/pending webhook retries cannot downgrade it.
                return {"status": "success", "card_id": existing.id, "duplicate": True}
            expected = checkout["quote"]
            if payment_status != "success":
                # Keep terminal outcomes stable; a delayed pending webhook cannot reopen them.
                if checkout.get("state") not in {"failed", "cancelled", "success"}:
                    checkout["state"] = payment_status
                    checkout["verification"] = {"status": payment_status, "verified_at": now}
                    self.repo.save_checkout(checkout["idempotency_key"], checkout)
                    self.audit.log(event_type=f"payment.{payment_status}", actor_id=checkout["request"]["giver_id"],
                        entity_type="payment", entity_id=reference, reference=f"payment:{reference}:{payment_status}",
                        occurred_at=now, data={"status": payment_status})
                    self.repo.enqueue_outbox(
                        event_key=f"payment:{reference}:{payment_status}",
                        event_type=f"payment.{payment_status}",
                        payload={"reference": reference,
                                 "giver_id": checkout["request"]["giver_id"],
                                 "status": payment_status})
                return {"status": checkout.get("state", payment_status), "reference": reference}

            raw_code = self._new_unique_code()
            request_data = checkout["request"]
            req = CardRequest(**request_data)
            status = "inactive" if req.delivery_method == "physical" else "active"
            # The repository must enforce uniqueness on payment_reference and ledger/outbox keys.
            card = self.repo.create_card({"giver_id": req.giver_id, "amount": money(req.amount), "currency": req.currency.upper(),
                "purpose": req.purpose.strip(), "restriction_type": req.restriction_type,
                "restriction_target_id": req.restriction_target_id, "expires_at": req.expires_at,
                "delivery_method": req.delivery_method, "status": status,
                "code": raw_code, "payment_reference": reference,
                "recipient_destination": req.recipient_destination,
                "physical_shipping_details": req.physical_shipping_details})
            if card.code != raw_code:
                # The repository returned a card already created for this payment
                # by a concurrent webhook; never deliver this request's unused code.
                return {"status": "success", "card_id": card.id, "duplicate": True}
            self.wallet_ledger.record_issuance(giver_id=req.giver_id, card_id=card.id,
                payment_reference=reference, face_value=money(req.amount),
                paystack_fee=expected["payment_fee"], platform_fee=expected["platform_fee"],
                currency=req.currency, occurred_at=now)
            self.audit.log(event_type="card.issued", actor_id=req.giver_id,
                entity_type="card", entity_id=card.id, reference=f"card:{card.id}:issued", occurred_at=now,
                data={"status": status, "delivery_method": req.delivery_method})
            self.repo.enqueue_outbox(event_key=f"payment-success:{reference}", event_type="payment.confirmed",
                payload={"card_id": card.id, "giver_id": req.giver_id, "reference": reference})
            if status == "active":
                self.repo.enqueue_outbox(event_key=f"card-delivery:{card.id}", event_type="card.delivery_requested",
                    payload={"card_id": card.id, "method": req.delivery_method,
                        "destination": req.recipient_destination,
                        "encrypted_code": self.codes.encrypt_for_delivery(raw_code)})
            else:
                self.repo.enqueue_outbox(event_key=f"physical-shipment:{card.id}",
                    event_type="physical_card.shipment_requested", payload={
                        "card_id": card.id,
                        "encrypted_code": self.codes.encrypt_for_delivery(raw_code),
                    })
            checkout["state"] = "success"
            checkout["card_id"] = card.id
            checkout["verification"] = {"status": "success", "verified_at": now}
            self.repo.save_checkout(req.idempotency_key, checkout)
        # Delivery must happen asynchronously via an outbox worker, never in this transaction.
        return {"status": "success", "card_id": card.id,
                "delivery_queued": status == "active", "physical_activation_required": status == "inactive"}

    def _new_unique_code(self) -> str:
        """Preflight the schema's unique plaintext code; DB uniqueness closes races."""
        for _ in range(10):
            code = self.codes.new_code()
            if len(code) <= 20 and not self.repo.get_card_by_code(code):
                return code
        raise Unavailable("Could not allocate a unique card code", code="card_code_generation_failed")

    def list_giver_cards(self, *, principal: Principal) -> list[dict[str, Any]]:
        """Return dashboard-safe card details without bearer codes or internal secrets."""
        if principal.role != "giver":
            raise Forbidden("Giver access is required", code="giver_role_required")
        cards = self.repo.list_cards_for_giver(principal.user_id)
        return [{"id": card.id, "amount": str(card.amount), "currency": card.currency,
                 "purpose": card.purpose, "restriction_type": card.restriction_type,
                 "restriction_target_id": card.restriction_target_id,
                 "created_at": card.created_at.isoformat() if card.created_at else None,
                 "expires_at": card.expires_at.isoformat() if card.expires_at else None,
                 "delivery_method": card.delivery_method, "delivery_status": card.delivery_status,
                 "status": card.status} for card in cards]

    def validate_redemption(self, *, code: str, principal: Principal) -> dict[str, Any]:
        if principal.role != "business" or not principal.business_id:
            raise Forbidden("Business operator access is required", code="business_role_required")
        business_id = authorize_redemption(principal, principal.business_id)
        card = self._find_by_code(code)
        business = self.repo.get_business(business_id)
        if not business or not business.approved or not business.active:
            return {"valid": False, "reason": "business_unavailable"}
        reason = self._redemption_failure(card, business, self.clock.now())
        if reason:
            return {"valid": False, "reason": reason}
        return {"valid": True, "card": {"reference": card.id, "amount": str(card.amount),
            "currency": card.currency, "purpose": card.purpose,
            "restriction_type": card.restriction_type,
            "expires_at": card.expires_at.isoformat() if card.expires_at else None}}

    def _redeem(self, *, code: str, business_id: str, operator_id: str,
                request_key: str) -> dict[str, Any]:
        if not request_key:
            raise DomainError("Idempotency key is required", code="missing_idempotency_key")
        request_started_at = self.clock.now()
        with self.repo.atomic():
            now = self.clock.now()
            card = self._find_by_code(code)
            business = self.repo.get_business(business_id)
            if not business or not business.approved or not business.active:
                raise Forbidden("Business is not approved to redeem cards", code="business_unavailable")
            failure = self._redemption_failure(card, business, now,
                redemption_started_at=request_started_at)
            if failure:
                raise Conflict(self._safe_reason(failure), code=failure)
            # The adapter locks the Card and Business, then rechecks all rules
            # using DB-authoritative time before returning the locked active card.
            self._assert_transition(card.status, "redeemed")
            now = self.clock.now()
            failure = self._redemption_failure(card, business, now,
                redemption_started_at=request_started_at)
            if failure:
                raise Conflict(self._safe_reason(failure), code=failure)
            claimed = self.repo.claim_redemption(card.id, business_id, now,
                request_key=request_key, request_started_at=request_started_at,
                expiry_grace=self.expiry_grace)
            if not claimed:
                current_card = self._find_by_code(code)
                current_business = self.repo.get_business(business_id)
                if not current_business or not current_business.approved or not current_business.active:
                    raise Forbidden("Business is not approved to redeem cards", code="business_unavailable")
                reason = self._redemption_failure(current_card, current_business, self.clock.now())
                if reason:
                    raise Conflict(self._safe_reason(reason), code=reason)
                raise Conflict("Card is already redeemed or being processed", code="already_redeemed_or_in_progress")
            # Redemption is OneToOne with Card in the database; persist it before
            # the state transition but in this same transaction.
            card = claimed
            self.repo.create_redemption(card_id=card.id, business_id=business_id,
                amount_spent=money(card.amount), leftover=money(0), cashback_amount=money(0),
                redeemed_at=now)
            self._transition(card, ("active",), "redeemed", redeemed_at=now)
            self.wallet_ledger.debit_redeemed(giver_id=card.giver_id, card_id=card.id,
                amount=card.amount, occurred_at=now)
            # Always draw down the full face value; the platform fee is not taken
            # from float. Any shortfall is separately recorded as overdraft.
            self.float_ledger.draw_down(business_id=business_id, card_id=card.id,
                amount=card.amount, currency=card.currency, occurred_at=now)
            self.audit.log(event_type="card.redeemed", actor_id=operator_id,
                entity_type="card", entity_id=card.id, reference=f"card:{card.id}:redeemed",
                occurred_at=now, idempotency_key=f"audit:redemption:{card.id}",
                data={"business_id": business_id, "amount": str(card.amount), "currency": card.currency})
            self.repo.enqueue_outbox(event_key=f"redemption:{card.id}", event_type="card.redeemed",
                payload={"card_id": card.id, "giver_id": card.giver_id, "business_id": business_id,
                         "amount": str(card.amount), "currency": card.currency, "redeemed_at": now.isoformat()})
        return {"status": "redeemed", "card_id": card.id, "amount": str(card.amount), "currency": card.currency}

    def redeem_as_operator(self, *, code: str, principal: Principal, request_key: str) -> dict[str, Any]:
        """Derive operator/business identity from the authenticated principal."""
        if not principal.business_id:
            raise Forbidden("Operator is not assigned to a business", code="business_scope_forbidden")
        business_id = authorize_redemption(principal, principal.business_id)
        return self._redeem(code=code, business_id=business_id,
                           operator_id=principal.user_id, request_key=request_key)

    def cancel(self, *, card_id: str, principal: Principal) -> dict[str, Any]:
        if principal.role != "giver":
            raise Forbidden("Giver access is required", code="giver_role_required")
        giver_id = principal.user_id
        now = self.clock.now()
        with self.repo.atomic():
            card = self.repo.get_card(card_id)
            if not card:
                raise NotFound("Card not found")
            if card.giver_id != giver_id:
                raise Forbidden("Card does not belong to this giver")
            if CardLifecycleService.is_expired(expires_at=card.expires_at, now=now):
                raise Conflict("Expired card value is locked and cannot be cancelled", code="expired")
            self._transition(card, ("active", "inactive"), "cancelled")
            self.wallet_ledger.release_cancelled(giver_id=giver_id, card_id=card.id,
                amount=card.amount, occurred_at=now)
            self.audit.log(event_type="card.cancelled", actor_id=giver_id,
                entity_type="card", entity_id=card.id, reference=f"card:{card.id}:cancelled", occurred_at=now,
                data={"value_released": str(card.amount), "currency": card.currency})
            self.repo.enqueue_outbox(event_key=f"cancel:{card.id}", event_type="card.cancelled",
                payload={"card_id": card.id, "giver_id": giver_id, "amount": str(card.amount)})
        return {"status": "cancelled", "value_released": str(card.amount), "currency": card.currency}

    def activate_physical(self, *, card_id: str, activation_proof: str) -> dict[str, Any]:
        if self.activation_verifier is None:
            raise Unavailable("Physical activation verification is not configured", code="activation_not_configured")
        return PhysicalCardService(repo=self.repo, codes=self.codes, clock=self.clock,
                                   activation_verifier=self.activation_verifier).activate(
                                       card_id=card_id, proof=activation_proof)

    def report_physical_card_lost(self, *, card_id: str, principal: Principal,
                                  request_key: str) -> dict[str, Any]:
        if principal.role != "giver":
            raise Forbidden("Giver access is required", code="giver_role_required")
        return PhysicalCardService(repo=self.repo, codes=self.codes, clock=self.clock,
            activation_verifier=self.activation_verifier).report_lost_and_replace(
                card_id=card_id, principal=principal, request_key=request_key)

    def expire(self, *, card_id: str) -> bool:
        now = self.clock.now()
        with self.repo.atomic():
            card = self.repo.get_card(card_id)
            if not card:
                raise NotFound("Card not found")
            return self._expire_locked(card, now)

    def expire_due_cards(self, *, batch_size: int = 200) -> dict[str, int]:
        """Worker entry point; schedule periodically after product expiry policy is approved."""
        if not isinstance(batch_size, int) or batch_size < 1 or batch_size > 2000:
            raise DomainError("Expiry batch size must be between 1 and 2000", code="invalid_expiry_batch_size")
        now = self.clock.now()
        if now.tzinfo is None:
            raise DomainError("Expiry worker time must be timezone-aware", code="invalid_datetime")
        due_ids = self.repo.list_cards_due_for_expiry(now=now, limit=batch_size)
        expired = sum(1 for card_id in due_ids if self.expire(card_id=card_id))
        return {"scanned": len(due_ids), "expired": expired}

    def _expire_locked(self, card: Card, now: datetime) -> bool:
        if card.status not in ("active", "inactive") or not CardLifecycleService.is_expired(expires_at=card.expires_at, now=now):
            return False
        if (card.status == "active" and self.expiry_grace is not None
                and now < card.expires_at + self.expiry_grace):
            return False
        self._transition(card, ("active", "inactive"), "expired")
        self.wallet_ledger.lock_expired(giver_id=card.giver_id, card_id=card.id,
            amount=card.amount, occurred_at=now)
        self.audit.log(event_type="card.expired", actor_id="system",
            entity_type="card", entity_id=card.id, reference=f"card:{card.id}:expired", occurred_at=now,
            data={"value_locked": str(card.amount), "currency": card.currency})
        self.repo.enqueue_outbox(event_key=f"expiry:{card.id}", event_type="card.expired",
            payload={"card_id": card.id, "giver_id": card.giver_id, "amount": str(card.amount)})
        return True

    def _find_by_code(self, code: str) -> Card:
        if not code or len(code) > 20:
            raise NotFound("Card code was not recognized", code="invalid_code")
        # The current database schema has a unique plaintext Card.code field.
        # Lookup is exact and the raw code must never be logged or audited.
        card = self.repo.get_card_by_code(code)
        if not card:
            raise NotFound("Card code was not recognized", code="invalid_code")
        return card

    def _redemption_failure(self, card: Card, business: Any, now: datetime,
                            redemption_started_at: datetime | None = None) -> str | None:
        if card.status != "active":
            try:
                CardLifecycleService.assert_redeemable_state(card.status)
            except Conflict as error:
                return error.code
        # A fresh redemption must start before expiry. A repository may permit
        # completion of an already-claimed redemption during an approved grace
        # period, but must not use grace to start a new redemption after expiry.
        if CardLifecycleService.is_expired(expires_at=card.expires_at, now=now):
            grace = self.expiry_grace
            started_before_expiry = (redemption_started_at is not None
                                     and redemption_started_at < card.expires_at)
            if (not started_before_expiry or grace is None
                    or now > card.expires_at + grace):
                return "expired"
        if card.restriction_type == "business" and card.restriction_target_id != business.id: return "wrong_business"
        if card.restriction_type == "category" and card.restriction_target_id != business.category_id: return "wrong_category"
        return None

    @staticmethod
    def _safe_reason(reason: str) -> str:
        messages = {"already_redeemed": "Card has already been redeemed", "redemption_in_progress": "Redemption is already in progress",
            "activation_required": "Physical card must be activated first", "cancelled": "Card has been cancelled",
            "expired": "Card has expired", "wrong_business": "Card is not valid at this business",
            "wrong_category": "Card is not valid in this business category", "card_unavailable": "Card is not available for redemption",
            "payment_pending": "Payment has not been confirmed"}
        return messages.get(reason, "Card could not be redeemed")


def verify_paystack_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Standalone Paystack HMAC-SHA512 verifier for gateway adapters."""
    if not raw_body or not signature or not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)
