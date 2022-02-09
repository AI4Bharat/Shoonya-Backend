import secrets
import string
from rest_framework import viewsets, status
import re
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .serializers import UserSignUpSerializer
from organizations.models import Invite, Organization
from organizations.serializers import InviteGenerationSerializer
from users.models import User
from rest_framework.decorators import action


regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"


def generate_random_string(length=12):
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(length))


class InviteViewSet(viewsets.ViewSet):
    @swagger_auto_schema(request_body=InviteGenerationSerializer)
    @action(detail=False, methods=["post"], url_path="generate")
    def invite_users(self, request):
        emails = request.data.get("emails")
        organization_id = request.data.get("organization_id")
        users = []
        for email in emails:
            if re.fullmatch(regex, email):
                user = User(username=generate_random_string(12), email=email, password=generate_random_string())
                users.append(user)
            else:
                print("Invalide email: " + email)
        users = User.objects.bulk_create(users)
        try:
            org = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist():
            return Response({"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        Invite.create_invite(organization=org, users=users)
        return Response({"message": "Invite sent"}, status=status.HTTP_200_OK)
        
    @swagger_auto_schema(request_body=UserSignUpSerializer)
    @action(detail=False, methods=["patch"],url_path="accept")
    def sign_up_user(self, request):
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist():
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serialized = UserSignUpSerializer(user,request.data,partial=True)
        if serialized.is_valid():
            serialized.save()
            return Response({"message": "User signed up"}, status=status.HTTP_200_OK)

class UserViewSet(viewsets.ViewSet):
    pass