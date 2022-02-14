import email
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import User
from .views import *


class UserTestcase(APITestCase):
    client = APIClient()

    def setUp(self):
        # Setting up a dummy organization and creating a superuser for testing purposes.
        Organization.objects.create(title="Test Organization")
        User.objects.create_superuser(
            username="admin", email="admin@admin.com", password="admin"
        )

    def test_invite_users(self):
        """
        Check invite user API.
        """
        # Creating Request data
        data = {
            "emails": [
                "sample@email.com",
                "sampl1e@email.com",
            ],
            "organization_id": 1,
        }
        # Giving the correct expected response from the view
        correct_response = {"message": "Invite sent"}
        # Writing the URL of the API to be tested [Format is appname:basename-urlname]
        # For basename, refer urls.py of that app. For urlname, refer the action decorator of the viewset function.
        url = reverse("users:invite-invite_users")
        # Logging in as the admin user
        self.client.login(email="admin@admin.com", password="admin")
        # Sending the request to the API
        response = self.client.post(url, data, format="json")
        # Checking if the response is correct
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, correct_response)
