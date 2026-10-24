"""Digital delivery dispatch and physical-card lifecycle workflows.

Provider transports, activation-proof rules, code decryption, and persistence are
ports so this module contains no credentials or database schema.
"""

from __future__ import annotations

from typing import Any, Protocol

from cryptography.fernet import Fernet, InvalidToken

from .audit import AuditTrailLogger
from .auth import Principal
from .contracts import Card, Clock, CodeGenerator, Repository
from .errors import Conflict, DomainError, Forbidden, NotFound, Unavailable
from .lifecycle import CardLifecycleService


class DeliveryCodeProtector(Protocol):
    def decrypt_for_delivery(self, encrypted_code: str) -> str: ...


class FernetDeliveryCodeProtector:
    """Decrypt outbox codes with the same dedicated key as SecureCodeGenerator."""

    def __init__(self, *, encryption_key: bytes | str):
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode("ascii")
        self._fernet = Fernet(encryption_key)

    def decrypt_for_delivery(self, encrypted_code: str) -> str:
        if not isinstance(encrypted_code, str) or not encrypted_code:
            raise DomainError("Encrypted card code is invalid", code="invalid_encrypted_card_code")
        try:
            return self._fernet.decrypt(encrypted_code.encode("ascii")).decode("ascii")
        except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError) as exc:
            raise Forbidden("Card delivery code could not be authenticated",
                            code="invalid_encrypted_card_code") from exc


class MessageSender(Protocol):
    def send(self, *, channel: str, destination: str, content: dict[str, Any], idempotency_key: str) -> None: ...


class ShipmentGateway(Protocol):
    def request_shipment(self, *, recipient_details: dict[str, Any], card_reference: str,
                         printed_code: str, idempotency_key: str) -> dict[str, Any]: ...


class ActivationVerifier(Protocol):
    def verify(self, *, card: Card, proof: str) -> bool: ...


class DigitalDeliveryDispatcher:
    """Outbox worker logic for sending recipient card details via email/WhatsApp."""

    def __init__(self, *, repo: Repository, code_protector: DeliveryCodeProtector,
                 sender: MessageSender):
        self.repo, self.code_protector, self.sender = repo, code_protector, sender

    def dispatch(self, *, card_id: str, method: str, destination: str,
                 encrypted_code: str, event_key: str) -> None:
        if method not in {"email", "whatsapp"}:
            raise DomainError("Digital delivery channel is unsupported", code="invalid_delivery_method")
        card = self.repo.get_card(card_id)
        if not card:
            raise NotFound("Card not found")
        if card.status != "active" or card.delivery_method != method:
            raise Conflict("Card is no longer eligible for digital delivery", code="delivery_not_allowed")
        if not destination or destination != card.recipient_destination:
            raise Forbidden("Delivery destination does not match the issued card", code="delivery_destination_mismatch")
        restriction = self.repo.describe_restriction(card.restriction_type, card.restriction_target_id)
        if not restriction:
            raise Unavailable("Card restriction details are unavailable", code="restriction_details_unavailable")
        code = self.code_protector.decrypt_for_delivery(encrypted_code)
        content = {
            "purpose": card.purpose,
            "face_value": str(card.amount),
            "currency": card.currency,
            "restriction": restriction,
            "expires_at": card.expires_at.isoformat() if card.expires_at else None,
            "code": code,
            "instructions": "Present this code at the approved business. It can be used once before expiry.",
        }
        # The outbox worker owns retry/backoff. Provider idempotency prevents a
        # retry from sending duplicate messages where the provider supports it.
        self.sender.send(channel=method, destination=destination, content=content, idempotency_key=event_key)


class PhysicalShipmentDispatcher:
    """Outbox worker logic for printing/dispatching an inactive physical card."""

    def __init__(self, *, repo: Repository, code_protector: DeliveryCodeProtector,
                 shipment_gateway: ShipmentGateway):
        self.repo, self.code_protector, self.shipment_gateway = repo, code_protector, shipment_gateway

    def dispatch(self, *, card_id: str, encrypted_code: str, event_key: str) -> dict[str, Any]:
        card = self.repo.get_card(card_id)
        if not card:
            raise NotFound("Card not found")
        if card.delivery_method != "physical" or card.status != "inactive":
            raise Conflict("Physical card is no longer eligible for shipment", code="shipment_not_allowed")
        if not card.physical_shipping_details:
            raise Unavailable("Physical shipping details are unavailable", code="shipping_details_unavailable")
        code = self.code_protector.decrypt_for_delivery(encrypted_code)
        return self.shipment_gateway.request_shipment(recipient_details=card.physical_shipping_details,
            card_reference=card.id, printed_code=code, idempotency_key=event_key)


class PhysicalCardService:
    """Activation and lost-before-activation replacement logic."""

    def __init__(self, *, repo: Repository, codes: CodeGenerator, clock: Clock,
                 activation_verifier: ActivationVerifier | None = None):
        self.repo, self.codes, self.clock = repo, codes, clock
        self.audit = AuditTrailLogger(repo)
        self.activation_verifier = activation_verifier

    def activate(self, *, card_id: str, proof: str) -> dict[str, Any]:
        if self.activation_verifier is None:
            raise Unavailable("Physical activation verification is not configured", code="activation_not_configured")
        card = self.repo.get_card(card_id)
        if not card:
            raise NotFound("Card not found")
        if card.delivery_method != "physical" or card.status != "inactive":
            raise Conflict("Card is not awaiting physical activation", code="not_activatable")
        if CardLifecycleService.is_expired(expires_at=card.expires_at, now=self.clock.now()):
            raise Conflict("Card has expired", code="expired")
        if not proof or not self.activation_verifier.verify(card=card, proof=proof):
            raise Forbidden("Physical card activation could not be verified", code="activation_failed")
        now = self.clock.now()
        with self.repo.atomic():
            # Re-read the authoritative state after the proof check to prevent
            # activation if cancellation/replacement/expiry won the race.
            current = self.repo.get_card(card_id)
            if not current or current.status != "inactive" or current.delivery_method != "physical":
                raise Conflict("Physical card state changed during activation", code="card_state_changed")
            if CardLifecycleService.is_expired(expires_at=current.expires_at, now=now):
                raise Conflict("Card has expired", code="expired")
            CardLifecycleService.assert_transition("inactive", "active")
            if not self.repo.transition_card(current.id, ("inactive",), "active", activated_at=now):
                raise Conflict("Physical card state changed during activation", code="card_state_changed")
            self.audit.log(event_type="card.activated", actor_id="recipient",
                entity_type="card", entity_id=current.id,
                reference=f"card:{current.id}:activation", occurred_at=now, data={})
            self.repo.enqueue_outbox(event_key=f"activation:{current.id}", event_type="card.activated",
                payload={"card_id": current.id, "giver_id": current.giver_id})
        return {"status": "active", "card_id": card_id}

    def report_lost_and_replace(self, *, card_id: str, principal: Principal,
                                request_key: str) -> dict[str, Any]:
        if principal.role != "giver":
            raise Forbidden("Giver access is required", code="giver_role_required")
        if not request_key:
            raise DomainError("Idempotency key is required", code="missing_idempotency_key")
        now = self.clock.now()
        with self.repo.atomic():
            original = self.repo.get_card(card_id)
            if not original:
                raise NotFound("Card not found")
            if str(original.giver_id) != str(principal.user_id):
                raise Forbidden("Card does not belong to this giver")
            existing = self.repo.get_replacement(original_card_id=card_id, request_key=request_key)
            if existing:
                return {"status": "replacement_created", "card_id": existing.id, "duplicate": True}
            if original.delivery_method != "physical" or original.status != "inactive":
                raise Conflict("Only a physical card lost before activation can be replaced", code="not_replaceable")
            if CardLifecycleService.is_expired(expires_at=original.expires_at, now=now):
                raise Conflict("Expired physical card cannot be replaced", code="expired")
            code = self._new_unique_code()
            CardLifecycleService.assert_transition("inactive", "lost")
            if not self.repo.transition_card(original.id, ("inactive",), "lost"):
                raise Conflict("Physical card state changed before replacement", code="card_state_changed")
            replacement = self.repo.create_card({
                "giver_id": original.giver_id,
                "amount": original.amount,
                "currency": original.currency,
                "purpose": original.purpose,
                "restriction_type": original.restriction_type,
                "restriction_target_id": original.restriction_target_id,
                "expires_at": original.expires_at,
                "delivery_method": "physical",
                "status": "inactive",
                "code": code,
                "payment_reference": None,
                "recipient_destination": original.recipient_destination,
                "physical_shipping_details": original.physical_shipping_details,
                "replacement_for_id": original.id,
            })
            self.audit.log(event_type="card.lost_replaced", actor_id=principal.user_id,
                entity_type="card", entity_id=original.id,
                reference=f"replacement:{request_key}", occurred_at=now,
                data={"replacement_card_id": replacement.id})
            self.repo.enqueue_outbox(event_key=f"physical-shipment:{replacement.id}",
                event_type="physical_card.shipment_requested", payload={
                    "card_id": replacement.id,
                    "encrypted_code": self.codes.encrypt_for_delivery(code),
                    "replacement_for_id": original.id,
                })
        return {"status": "replacement_created", "card_id": replacement.id, "duplicate": False}

    def _new_unique_code(self) -> str:
        for _ in range(10):
            code = self.codes.new_code()
            if len(code) <= 20 and not self.repo.get_card_by_code(code):
                return code
        raise Unavailable("Could not allocate a unique card code", code="card_code_generation_failed")
