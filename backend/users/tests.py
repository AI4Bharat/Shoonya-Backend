import email
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import User
from .views import *

# Create your tests here.


class UserTestcase(APITestCase):
    client = APIClient()

    def setUp(self):
        Organization.objects.create(title="Test Organization")
        User.objects.create_superuser(username="admin", email="admin@admin.com", password="admin")

    def test_invite_users(self):
        """
        Check invite user API.
        """
        data = {"emails": ["sample@email.com", "sampl1e@email.com",], "organization_id": 1}
        correct_response = {"message": "Invite sent"}
        url = reverse("users:invite-invite_users")
        self.client.login(email="admin@admin.com", password="admin")
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, correct_response)

