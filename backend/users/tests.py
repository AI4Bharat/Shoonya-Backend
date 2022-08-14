from urllib import response
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

    def test_invite_users(self, email="sample2@email.com", org=1):
        """
        Check invite user API.
        """
        # Creating Request data
        data = {
            "emails": [email],
            "organization_id": org,
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
        # Logout client
        self.client.logout()
        # Checking if the response is correct
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, correct_response)

    def test_sign_up_user(self):
        """
        Check sign up user API.
        """
        self.test_invite_users(email="test@user.com", org=2)
        invite = Invite.objects.all().first()
        data = {
            "email": "test@user.com",
            "username": "testing_user",
            "password": "newpassword",
        }
        correct_response = {"message": "User signed up"}
        url = reverse("users:invite-sign_up_user", args=[invite.invite_code])
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, correct_response)

        # Check user cannot sign up once done already.
        response_two = self.client.patch(url, data, format="json")
        self.assertEqual(response_two.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response_two.data, {"message": "User has already accepted invite"}
        )

    # def test_edit_profile(self):
    #     """
    #     Test edit profile view.
    #     """

    #     data = {
    #         "username": "new_username",
    #         "email": "new_email@email.com",
    #     }
    #     url = reverse("users:account-edit_profile")
    #     self.client.login(username="test@user.com", password="newpassword")
    #     response = self.client.patch(url, data, format="json")
    #     self.client.logout()
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(response.data, {"message": "User profile edited"})
