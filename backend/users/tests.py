from rest_framework.test import APITestCase, APIClient, APIRequestFactory
from rest_framework import status
from django.urls import reverse

from .views import *

# Create your tests here.


class UserTestcase(APITestCase):
    client = APIClient()

    EMAILS = {
        "emails": [
            "sample@email.com",
            "sample@email.com",
        ],
        "organization_id": "1"
    }
    SUCCESS_RESPONSE = {"message": "Invite sent"}

    def test_invite_users(self):
        """
        Check invite user API.
        """
        request = APIRequestFactory().post(data=self.EMAILS, path='invite/generate/')
        view = InviteViewSet.as_view({'post': 'invite_users'})
        self.client.login(username='admin@admin.com', password='admin')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, status.HTTP_201_CREATED)

