from rest_framework.test import APITestCase, APIClient, APIRequestFactory
from rest_framework import status
from django.urls import reverse

from .views import *

# Create your tests here.


class UserTestcase(APITestCase):
    client = APIClient()

    DATA = {
        "emails": [
            "sample@email.com",
            "sampl1e@email.com",
        ],
        "organization_id": 1
    }

    def setUp(self):
        Organization.objects.create(title="Test Organization")

    def test_invite_users(self):
        """
        Check invite user API.
        """
        request = APIRequestFactory().post(data=self.DATA, path='invite/generate/',format='json')
        view = InviteViewSet.as_view({'post': 'invite_users'})
        correct_response = {"message": "Invite sent"}
        self.client.login(username='admin@admin.com', password='admin')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, correct_response)

