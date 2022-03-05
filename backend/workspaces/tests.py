from urllib import response
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import Workspace
from .views import *
from users.models import User
from organizations.models import Organization


class UserTestcase(APITestCase):
    client = APIClient()

    def setUp(self):
        # Setting up a dummy organization, dummy workspace and creating a user and a superuser for testing purposes.
        org1 = Organization.objects.create(title="Test Organization", id=11)

        users = []
        user = User.objects.create_user(
            username="testUser", email="test@email.com", password="admin"
        )
        user.organization_id = 11
        users.append(user)

        ws = Workspace.objects.create(
            organization=org1, workspace_name="Workspace_Test", id=2
        )
        for user1 in users:
            ws.users.add(user1)

        User.objects.create_superuser(
            username="admin", email="admin@admin.com", password="admin"
        )

    def test_assign_manager(self, email="test@email.com"):
        """
        Check assign manager API.
        """
        # Creating Request data
        data = {
            "email": "test@email.com",
            "workspace_name": "WS1",
            "organization": "11",
        }

        # Writing the URL of the API to be tested [Format is appname:basename-urlname]
        # For basename, refer urls.py of that app. For urlname, refer the action decorator of the viewset function.
        url = reverse(
            "workspace-assign_manager",
            args={2},
        )
        # Logging in as the admin user
        self.client.login(email="admin@admin.com", password="admin")
        # Sending the request to the API
        response = self.client.post(url, data, format="json")
        # Logout client
        self.client.logout()
        # Checking if the response is correct
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_archive(self, email="test@email.com"):
        """
        Check workspace archive API.
        """
        # Creating Request data
        data = {
            "email": "test@email.com",
            "workspace_name": "WS1",
            "organization": "11",
        }

        # Writing the URL of the API to be tested [Format is appname:basename-urlname]
        # For basename, refer urls.py of that app. For urlname, refer the action decorator of the viewset function.
        url = reverse(
            "workspace-archive",
            args={2},
        )
        # Logging in as the admin user
        self.client.login(email="admin@admin.com", password="admin")
        # Sending the request to the API
        response = self.client.post(url, data, format="json")
        # Logout client
        self.client.logout()
        # Checking if the response is correct
        self.assertEqual(response.status_code, status.HTTP_200_OK)
