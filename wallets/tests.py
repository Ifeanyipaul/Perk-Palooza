from decimal import Decimal
from rest_framework.test import APIClient
from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from wallets.models import Wallet, WalletTransaction
from wallets.services import credit_verified_funding, commit_wallet_funds, release_committed_funds, create_pending_funding


class WalletFundingTests(TestCase):

    def setUp(self):
        # Create a test giver.
        self.user = User.objects.create_user(
            username="testgiver",
            email="testgiver@example.com",
            password="TestPassword123!",
            role="GIVER"
        )

        # The signal should automatically create this wallet.
        self.wallet = Wallet.objects.get(user=self.user)

        # Create a pending funding transaction.
        self.funding = WalletTransaction.objects.create(
            wallet=self.wallet,
            transaction_type="FUNDING",
            amount=Decimal("50000.00"),
            status="PENDING",
            reference="TEST-FUNDING-001",
            description="Test wallet funding"
        )

    def test_successful_wallet_funding(self):
        wallet = credit_verified_funding(
            "TEST-FUNDING-001",
            Decimal("50000.00")
        )

        wallet.refresh_from_db()
        self.funding.refresh_from_db()

        self.assertEqual(
            wallet.available_balance,
            Decimal("50000.00")
        )

        self.assertEqual(
            wallet.total_funded,
            Decimal("50000.00")
        )

        self.assertEqual(
            self.funding.status,
            "SUCCESS"
        )

    def test_reject_incorrect_amount(self):
        with self.assertRaises(ValidationError):
            credit_verified_funding(
                "TEST-FUNDING-001",
                Decimal("30000.00")
            )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("0.00")
        )

    def test_prevent_duplicate_funding(self):
        credit_verified_funding(
            "TEST-FUNDING-001",
            Decimal("50000.00")
        )

        with self.assertRaises(ValidationError):
            credit_verified_funding(
                "TEST-FUNDING-001",
                Decimal("50000.00")
            )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("50000.00")
        )

    def test_reject_non_funding_transaction(self):
        self.funding.transaction_type = "CARD_COMMITMENT"
        self.funding.save()

        with self.assertRaises(ValidationError):
            credit_verified_funding(
                "TEST-FUNDING-001",
                Decimal("50000.00")
            )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("0.00")
        )

    def test_reject_zero_amount(self):
        with self.assertRaises(ValidationError):
            credit_verified_funding(
                "TEST-FUNDING-001",
                Decimal("0.00")
            )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("0.00")
        )

    def test_reject_unknown_reference(self):
        with self.assertRaises(ValidationError):
            credit_verified_funding(
                "UNKNOWN-REFERENCE",
                Decimal("50000.00")
            )



class WalletCommitmentTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="commitgiver",
            email="commitgiver@example.com",
            password="TestPassword123!",
            role="GIVER"
        )

        self.wallet = Wallet.objects.get(user=self.user)

        self.wallet.available_balance = Decimal("50000.00")
        self.wallet.total_funded = Decimal("50000.00")
        self.wallet.save()

    def test_successful_commitment(self):
        transaction_record = commit_wallet_funds(
            self.user,
            Decimal("10000.00"),
            "COMMIT-001"
        )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("40000.00")
        )

        self.assertEqual(
            self.wallet.committed_balance,
            Decimal("10000.00")
        )

        self.assertEqual(
            transaction_record.transaction_type,
            "CARD_COMMITMENT"
        )

    def test_reject_insufficient_balance(self):
        with self.assertRaises(ValidationError):
            commit_wallet_funds(
                self.user,
                Decimal("60000.00"),
                "COMMIT-002"
            )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("50000.00")
        )

    def test_reject_duplicate_reference(self):
        commit_wallet_funds(
            self.user,
            Decimal("10000.00"),
            "COMMIT-003"
        )

        with self.assertRaises(ValidationError):
            commit_wallet_funds(
                self.user,
                Decimal("10000.00"),
                "COMMIT-003"
            )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("40000.00")
        )


class WalletReleaseTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="releasegiver",
            email="releasegiver@example.com",
            password="TestPassword123!",
            role="GIVER"
        )

        self.wallet = Wallet.objects.get(user=self.user)

        self.wallet.available_balance = Decimal("40000.00")
        self.wallet.committed_balance = Decimal("10000.00")
        self.wallet.total_funded = Decimal("50000.00")
        self.wallet.save()

        self.commitment = WalletTransaction.objects.create(
            wallet=self.wallet,
            transaction_type="CARD_COMMITMENT",
            amount=Decimal("10000.00"),
            status="SUCCESS",
            reference="COMMIT-RELEASE-001",
        )

    def test_successful_release(self):
        release_committed_funds(
            "COMMIT-RELEASE-001",
            "RELEASE-001"
        )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("50000.00")
        )

        self.assertEqual(
            self.wallet.committed_balance,
            Decimal("0.00")
        )

    def test_prevent_duplicate_release(self):
        release_committed_funds(
            "COMMIT-RELEASE-001",
            "RELEASE-002"
        )

        with self.assertRaises(ValidationError):
            release_committed_funds(
                "COMMIT-RELEASE-001",
                "RELEASE-003"
            )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("50000.00")
        )

    def test_reject_unknown_commitment(self):
        with self.assertRaises(ValidationError):
            release_committed_funds(
                "UNKNOWN-COMMITMENT",
                "RELEASE-004"
            )

    def test_reject_insufficient_committed_balance(self):
        self.wallet.committed_balance = Decimal("5000.00")
        self.wallet.save()

        with self.assertRaises(ValidationError):
            release_committed_funds(
                "COMMIT-RELEASE-001",
                "RELEASE-005"
            )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("40000.00")
        )
        
        

class PendingFundingCreationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="pendinggiver",
            email="pendinggiver@example.com",
            password="TestPassword123!",
            role="GIVER"
        )

        self.wallet = Wallet.objects.get(user=self.user)

    def test_create_pending_funding(self):
        funding = create_pending_funding(
            self.user,
            Decimal("25000.00")
        )

        self.wallet.refresh_from_db()

        self.assertEqual(funding.amount, Decimal("25000.00"))
        self.assertEqual(funding.transaction_type, "FUNDING")
        self.assertEqual(funding.status, "PENDING")
        self.assertTrue(funding.reference.startswith("PP-FUND-"))

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("0.00")
        )

        self.assertEqual(
            self.wallet.total_funded,
            Decimal("0.00")
        )

    def test_reject_zero_amount(self):
        with self.assertRaises(ValidationError):
            create_pending_funding(
                self.user,
                Decimal("0.00")
            )

    def test_reject_negative_amount(self):
        with self.assertRaises(ValidationError):
            create_pending_funding(
                self.user,
                Decimal("-100.00")
            )

    def test_reject_amount_with_more_than_two_decimal_places(self):
        with self.assertRaises(ValidationError):
            create_pending_funding(
                self.user,
                Decimal("100.555")
            )

    def test_reject_non_giver(self):
        business_user = User.objects.create_user(
            username="pendingbusiness",
            email="pendingbusiness@example.com",
            password="TestPassword123!",
            role="BUSINESS"
        )

        with self.assertRaises(ValidationError):
            create_pending_funding(
                business_user,
                Decimal("10000.00")
            )

    def test_each_funding_gets_unique_reference(self):
        first = create_pending_funding(
            self.user,
            Decimal("10000.00")
        )

        second = create_pending_funding(
            self.user,
            Decimal("20000.00")
        )

        self.assertNotEqual(first.reference, second.reference)
        
        
class WalletFundingAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="api_funding_giver",
            email="api_funding_giver@example.com",
            password="TestPassword123!",
            role="GIVER"
        )

        self.wallet = Wallet.objects.get(user=self.user)

        self.url = "/api/wallets/fund/"

    def test_giver_can_initiate_funding(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {"amount": "25000.00"},
            format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["transaction"]["amount"],
            "25000.00"
        )
        self.assertEqual(
            response.data["transaction"]["status"],
            "PENDING"
        )

    def test_funding_does_not_credit_wallet(self):
        self.client.force_authenticate(user=self.user)

        self.client.post(
            self.url,
            {"amount": "25000.00"},
            format="json"
        )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.available_balance,
            Decimal("0.00")
        )

        self.assertEqual(
            self.wallet.total_funded,
            Decimal("0.00")
        )

    def test_unauthenticated_user_cannot_fund(self):
        response = self.client.post(
            self.url,
            {"amount": "25000.00"},
            format="json"
        )

        self.assertEqual(response.status_code, 401)

    def test_business_user_cannot_fund(self):
        business_user = User.objects.create_user(
            username="api_funding_business",
            email="api_funding_business@example.com",
            password="TestPassword123!",
            role="BUSINESS"
        )

        self.client.force_authenticate(user=business_user)

        response = self.client.post(
            self.url,
            {"amount": "25000.00"},
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    def test_zero_amount_is_rejected(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {"amount": "0.00"},
            format="json"
        )

        self.assertEqual(response.status_code, 400)