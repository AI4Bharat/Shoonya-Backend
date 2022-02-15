from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

# Create your tests here.


class OrganizationTests(APITestCase):
    client = APIClient()
