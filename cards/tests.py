from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from businesses.models import Business, BusinessCategory
from cards.models import GiftCard


User = get_user_model()


class GiftCardAPITests(APITestCase):

    def setUp(self):
        self.client = APIClient()

        self.giver = User.objects.create_user(
            username="giver1",
            email="giver1@example.com",
            password="TestPass123!",
            role="GIVER",
        )

        self.another_giver = User.objects.create_user(
            username="giver2",
            email="giver2@example.com",
            password="TestPass123!",
            role="GIVER",
        )

        self.business_user = User.objects.create_user(
            username="business1",
            email="business1@example.com",
            password="TestPass123!",
            role="BUSINESS",
        )

        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password="TestPass123!",
            role="ADMIN",
        )

        self.category = BusinessCategory.objects.create(
            name="Restaurants",
            slug="restaurants",
        )

        self.business = Business.objects.create(
            name="Test Restaurant",
            slug="test-restaurant",
            category=self.category,
            email="restaurant@example.com",
            phone="08012345678",
            address="Lagos, Nigeria",
            status=Business.Status.ACTIVE,
            is_approved=True,
            is_verified=True,
        )

        self.url = reverse("giftcard-list-create")

        self.valid_data = {
            "recipient_name": "John Doe",
            "recipient_email": "john@example.com",
            "amount": "5000.00",
            "category": self.category.id,
            "expires_at": (
                timezone.now() + timedelta(days=30)
            ).isoformat(),
        }

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_giver_can_create_gift_card(self):
        self.authenticate(self.giver)

        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        card = GiftCard.objects.get()

        self.assertEqual(card.giver, self.giver)
        self.assertEqual(card.status, GiftCard.Status.PENDING)
        self.assertEqual(card.amount, Decimal("5000.00"))
        self.assertTrue(card.card_code)

    def test_business_cannot_create_gift_card(self):
        self.authenticate(self.business_user)

        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_create_gift_card(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_create_gift_card(self):
        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_giver_can_only_see_own_gift_cards(self):
        GiftCard.objects.create(
            giver=self.giver,
            recipient_name="John",
            recipient_email="john@example.com",
            amount=5000,
            category=self.category,
            expires_at=timezone.now() + timedelta(days=30),
        )

        GiftCard.objects.create(
            giver=self.another_giver,
            recipient_name="Jane",
            recipient_email="jane@example.com",
            amount=3000,
            category=self.category,
            expires_at=timezone.now() + timedelta(days=30),
        )

        self.authenticate(self.giver)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["recipient_name"],
            "John"
        )
    def test_giver_cannot_view_another_givers_card(self):
        card = GiftCard.objects.create(
            giver=self.another_giver,
            recipient_name="Jane",
            recipient_email="jane@example.com",
            amount=3000,
            category=self.category,
            expires_at=timezone.now() + timedelta(days=30),
        )

        self.authenticate(self.giver)

        response = self.client.get(
            reverse("giftcard-detail", kwargs={"pk": card.id})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_giver_can_create_business_restricted_card(self):
        self.authenticate(self.giver)

        data = {
            "recipient_name": "John Doe",
            "recipient_email": "john@example.com",
            "amount": "5000.00",
            "business": self.business.id,
            "expires_at": (
                timezone.now() + timedelta(days=30)
            ).isoformat(),
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_card_cannot_have_both_business_and_category(self):
        self.authenticate(self.giver)

        data = {
            **self.valid_data,
            "business": self.business.id,
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_card_must_have_a_restriction(self):
        self.authenticate(self.giver)

        data = {
            "recipient_name": "John Doe",
            "recipient_email": "john@example.com",
            "amount": "5000.00",
            "expires_at": (
                timezone.now() + timedelta(days=30)
            ).isoformat(),
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_amount_is_rejected(self):
        self.authenticate(self.giver)

        data = {
            **self.valid_data,
            "amount": "0.00",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_amount_is_rejected(self):
        self.authenticate(self.giver)

        data = {
            **self.valid_data,
            "amount": "-100.00",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_past_expiry_date_is_rejected(self):
        self.authenticate(self.giver)

        data = {
            **self.valid_data,
            "expires_at": (
                timezone.now() - timedelta(days=1)
            ).isoformat(),
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unapproved_business_is_rejected(self):
        self.authenticate(self.giver)

        self.business.is_approved = False
        self.business.save()

        data = {
            "recipient_name": "John Doe",
            "recipient_email": "john@example.com",
            "amount": "5000.00",
            "business": self.business.id,
            "expires_at": (
                timezone.now() + timedelta(days=30)
            ).isoformat(),
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_category_is_rejected(self):
        self.authenticate(self.giver)

        self.category.is_active = False
        self.category.save()

        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_cannot_activate_card_during_creation(self):
        self.authenticate(self.giver)

        data = {
            **self.valid_data,
            "status": "ACTIVE",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        card = GiftCard.objects.get()

        self.assertEqual(card.status, GiftCard.Status.PENDING)