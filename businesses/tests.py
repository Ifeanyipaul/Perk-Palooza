
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from businesses.models import Business, BusinessCategory


class BusinessAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Create test users
        self.giver = User.objects.create_user(
            username="testgiver",
            email="giver@test.com",
            password="TestPassword123!",
            role=User.Role.GIVER,
        )

        self.business_user = User.objects.create_user(
            username="testbusiness",
            email="business@test.com",
            password="TestPassword123!",
            role=User.Role.BUSINESS,
        )

        self.admin = User.objects.create_user(
            username="testadmin",
            email="admin@test.com",
            password="TestPassword123!",
            role=User.Role.ADMIN,
        )

        # Create a business category
        self.category = BusinessCategory.objects.create(
            name="Food",
            description="Food and groceries",
        )

        # Create an approved business
        self.business = Business.objects.create(
            name="Test Restaurant",
            category=self.category,
            email="restaurant@test.com",
            phone="08012345678",
            address="Lagos, Nigeria",
            status=Business.Status.ACTIVE,
            is_verified=True,
            is_approved=True,
            owner=self.business_user,
        )

        self.business_url = "/api/businesses/"
        self.my_businesses_url = "/api/businesses/my/"
        self.approval_url = (
            f"/api/businesses/{self.business.id}/approval/"
        )

    def test_giver_cannot_create_business(self):
        self.client.force_authenticate(user=self.giver)

        response = self.client.post(
            self.business_url,
            {
                "name": "New Restaurant",
                "category": self.category.id,
                "email": "new@test.com",
                "phone": "08011111111",
                "address": "Abuja, Nigeria",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_business_user_cannot_create_business(self):
        self.client.force_authenticate(user=self.business_user)

        response = self.client.post(
            self.business_url,
            {
                "name": "Another Restaurant",
                "category": self.category.id,
                "email": "another@test.com",
                "phone": "08022222222",
                "address": "Abuja, Nigeria",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_business(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.business_url,
            {
                "name": "Admin Created Restaurant",
                "category": self.category.id,
                "email": "created@test.com",
                "phone": "08033333333",
                "address": "Lagos, Nigeria",
            },
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(
            Business.objects.filter(
                email="created@test.com"
            ).exists()
        )

    def test_unauthenticated_user_cannot_approve_business(self):
        response = self.client.patch(
            self.approval_url,
            {"action": "approve"},
            format="json",
        )

        self.assertIn(response.status_code, [401, 403])

    def test_giver_cannot_approve_business(self):
        self.client.force_authenticate(user=self.giver)

        response = self.client.patch(
            self.approval_url,
            {"action": "approve"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_approve_business(self):
        pending_business = Business.objects.create(
            name="Pending Restaurant",
            category=self.category,
            email="pending@test.com",
            phone="08044444444",
            address="Abuja, Nigeria",
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f"/api/businesses/{pending_business.id}/approval/",
            {"action": "approve"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        pending_business.refresh_from_db()

        self.assertEqual(
            pending_business.status,
            Business.Status.ACTIVE,
        )
        self.assertTrue(pending_business.is_approved)
        self.assertTrue(pending_business.is_verified)

    def test_public_list_only_shows_approved_businesses(self):
        Business.objects.create(
            name="Pending Restaurant",
            category=self.category,
            email="pending2@test.com",
            phone="08055555555",
            address="Lagos, Nigeria",
            status=Business.Status.PENDING,
        )

        response = self.client.get(self.business_url)

        self.assertEqual(response.status_code, 200)

        returned_names = [
            item["name"] for item in response.data
        ]

        self.assertIn("Test Restaurant", returned_names)
        self.assertNotIn("Pending Restaurant", returned_names)



    def test_business_owner_can_view_own_business(self):
        self.client.force_authenticate(user=self.business_user)

        response = self.client.get(self.my_businesses_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        returned_names = [
            item["name"] for item in response.data["businesses"]
        ]

        self.assertIn("Test Restaurant", returned_names)

    def test_business_owner_cannot_view_another_owners_business(self):
        another_owner = User.objects.create_user(
            username="anotherbusiness",
            email="anotherbusiness@test.com",
            password="TestPassword123!",
            role=User.Role.BUSINESS,
        )

        Business.objects.create(
            name="Another Owner Restaurant",
            category=self.category,
            email="anotherrestaurant@test.com",
            phone="08066666666",
            address="Abuja, Nigeria",
            status=Business.Status.ACTIVE,
            is_verified=True,
            is_approved=True,
            owner=another_owner,
        )

        self.client.force_authenticate(user=self.business_user)

        response = self.client.get(self.my_businesses_url)

        self.assertEqual(response.status_code, 200)

        returned_names = [
            item["name"] for item in response.data["businesses"]
        ]

        self.assertIn("Test Restaurant", returned_names)
        self.assertNotIn("Another Owner Restaurant", returned_names)

    def test_giver_cannot_access_my_businesses(self):
        self.client.force_authenticate(user=self.giver)

        response = self.client.get(self.my_businesses_url)

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_access_my_businesses(self):
        response = self.client.get(self.my_businesses_url)

        self.assertIn(response.status_code, [401, 403])

    def test_business_owner_without_business_gets_empty_list(self):
        new_owner = User.objects.create_user(
            username="newbusiness",
            email="newbusiness@test.com",
            password="TestPassword123!",
            role=User.Role.BUSINESS,
        )

        self.client.force_authenticate(user=new_owner)

        response = self.client.get(self.my_businesses_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["businesses"], [])