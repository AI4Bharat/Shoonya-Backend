import secrets
import string
from wsgiref.util import request_uri
from rest_framework import viewsets, status
import re
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes
from drf_yasg.utils import swagger_auto_schema
from .serializers import UserProfileSerializer, UserSignUpSerializer
from organizations.models import Invite, Organization
from organizations.serializers import InviteGenerationSerializer
from organizations.decorators import is_organization_owner
from users.models import User
from rest_framework.decorators import action


regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"


def generate_random_string(length=12):
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(length))


class InviteViewSet(viewsets.ViewSet):
    @swagger_auto_schema(request_body=InviteGenerationSerializer)
    @permission_classes((IsAuthenticated,))
    @is_organization_owner
    @action(detail=False, methods=["post"], url_path="generate", url_name="invite_users")
    def invite_users(self, request):
        """
        Invite users to join your organization. This generates a new invite
        with an invite code or adds users to an existing one.
        """
        emails = request.data.get("emails")
        organization_id = request.data.get("organization_id")
        users = []
        try:
            org = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response({"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        for email in emails:
            # Checking if the email is in valid format.
            if re.fullmatch(regex, email):
                user = User(username=generate_random_string(12), email=email,)
                user.set_password(generate_random_string(10))
                user.organization = org
                users.append(user)
            else:
                print("Invalide email: " + email)
        # Creating users in bulk
        users = User.objects.bulk_create(users)
        Invite.create_invite(organization=org, users=users)
        return Response({"message": "Invite sent"}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(request_body=UserSignUpSerializer)
    @permission_classes((AllowAny,))
    @action(detail=False, methods=["patch"], url_path="accept", url_name="sign_up_user")
    def sign_up_user(self, request, pk=None):
        """
        Users to sign up for the first time.
        """
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist():
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        if user.has_accepted_invite:
            return Response({"message": "User has already accepted invite"}, status=status.HTTP_400_BAD_REQUEST,)
        try:
            Invite.objects.get(users=user, invite_code=pk)
        except Invite.DoesNotExist:
            return Response({"message": "Invite not found"}, status=status.HTTP_404_NOT_FOUND)

        serialized = UserSignUpSerializer(user, request.data, partial=True)
        if serialized.is_valid():
            serialized.save()
            return Response({"message": "User signed up"}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(request_body=UserSignUpSerializer)
    @action(detail=False, methods=["patch"], url_path="update")
    def edit_profile(self, request):
        """
        Updatinng user profile.
        """
        user = User.objects.get(email=request.data.get("email"))
        serialized = UserProfileSerializer(user, request.data, partial=True)
        if serialized.is_valid():
            serialized.save()
            return Response({"message": "User profile edited"}, status=status.HTTP_200_OK)
