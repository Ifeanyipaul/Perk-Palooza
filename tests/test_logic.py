"""Focused unit tests for framework-independent business rules."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from cryptography.fernet import Fernet

from perkpalooza.auth import Principal, ROLES, assert_business_scope, assert_giver_ownership
from perkpalooza.delivery import FernetDeliveryCodeProtector
from perkpalooza.errors import DomainError, Forbidden
from perkpalooza.fees import FeeCalculationService
from perkpalooza.lifecycle import CardLifecycleService
from perkpalooza.paystack import PaystackGateway, normalize_paystack_status
from perkpalooza.services import CardService, SecureCodeGenerator


class MoneyAndPaymentLogicTests(unittest.TestCase):
    def test_fee_quote_sums_face_value_and_configured_fees(self):
        fees = FeeCalculationService(
            paystack_fee=lambda amount, currency: Decimal("10.00"),
            platform_fee=lambda amount, currency: Decimal("5.00"),
        )
        quote = fees.quote(Decimal("100.00"), "NGN")
        self.assertEqual(quote["total_payable"], Decimal("115.00"))

    def test_fee_quote_rejects_negative_policy_output(self):
        fees = FeeCalculationService(
            paystack_fee=lambda amount, currency: Decimal("-1.00"),
            platform_fee=lambda amount, currency: Decimal("0.00"),
        )
        with self.assertRaises(DomainError):
            fees.calculate(Decimal("100.00"), "NGN")

    def test_paystack_uses_minor_units_and_normalizes_terminal_states(self):
        gateway = PaystackGateway(secret_key="unit-test-secret")
        self.assertEqual(gateway.to_minor_units(Decimal("123.45"), "NGN"), 12345)
        self.assertEqual(gateway.from_minor_units(12345, "NGN"), Decimal("123.45"))
        self.assertEqual(normalize_paystack_status("abandoned"), "cancelled")
        self.assertEqual(normalize_paystack_status("success"), "success")


class CardSecurityAndLifecycleTests(unittest.TestCase):
    def test_code_is_20_character_alphanumeric_and_encrypted_for_delivery(self):
        key = Fernet.generate_key()
        generator = SecureCodeGenerator(encryption_key=key)
        protector = FernetDeliveryCodeProtector(encryption_key=key)
        code = generator.new_code()
        token = generator.encrypt_for_delivery(code)
        self.assertEqual(len(code), 20)
        self.assertTrue(code.isalnum())
        self.assertNotEqual(token, code)
        self.assertEqual(protector.decrypt_for_delivery(token), code)

    def test_delivery_code_rejects_wrong_encryption_key(self):
        generator = SecureCodeGenerator(encryption_key=Fernet.generate_key())
        token = generator.encrypt_for_delivery("A" * 20)
        protector = FernetDeliveryCodeProtector(encryption_key=Fernet.generate_key())
        with self.assertRaises(Forbidden):
            protector.decrypt_for_delivery(token)

    def test_missing_expiry_fails_closed_and_boundary_is_expired(self):
        now = datetime(2026, 10, 24, tzinfo=timezone.utc)
        self.assertTrue(CardLifecycleService.is_expired(expires_at=None, now=now))
        self.assertTrue(CardLifecycleService.is_expired(expires_at=now, now=now))
        self.assertFalse(CardLifecycleService.is_expired(
            expires_at=datetime(2026, 10, 25, tzinfo=timezone.utc), now=now))

    def test_database_role_values_are_used_and_scoped(self):
        self.assertEqual(ROLES, frozenset({"giver", "business", "admin"}))
        assert_giver_ownership(Principal("giver-id", "giver"), "giver-id")
        assert_business_scope(Principal("operator-id", "business", "business-id"), "business-id")
        with self.assertRaises(Forbidden):
            assert_business_scope(Principal("other", "business", "business-a"), "business-b")

    def test_service_rejects_wrong_role_before_any_repository_access(self):
        service = CardService.__new__(CardService)
        with self.assertRaises(Forbidden):
            service.validate_redemption(code="untrusted", principal=Principal("giver-id", "giver"))


if __name__ == "__main__":
    unittest.main()
