import secrets
import string
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
    @is_organization_owner
    @swagger_auto_schema(request_body=InviteGenerationSerializer)
    @permission_classes((IsAuthenticated,))
    @action(detail=False, methods=["post"], url_path="generate")
    def invite_users(self, request):
        emails = request.data.get("emails")
        organization_id = request.data.get("organization_id")
        users = []
        valid_user_emails = []
        try:
            org = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response({"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        for email in emails:
            if re.fullmatch(regex, email):
                user = User(
                    username=generate_random_string(12),
                    email=email,
                    password=generate_random_string(),
                    organization_id=org,
                )
                valid_user_emails.append(email)
                users.append(user)
            else:
                print("Invalide email: " + email)
        if len(valid_user_emails) <= 0:
            return Response({"message": "No valid emails found"}, status=status.HTTP_400_BAD_REQUEST)
        users = User.objects.bulk_create(users)

        Invite.create_invite(organization=org, users=users, valid_user_emails=valid_user_emails)
        return Response({"message": "Invite sent"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=UserSignUpSerializer)
    @permission_classes((AllowAny,))
    @action(detail=False, methods=["patch"], url_path="accept")
    def sign_up_user(self, request, pk=None):
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist():
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        if user.has_accepted_invite:
            return Response({"message": "User has already accepted invite"}, status=status.HTTP_400_BAD_REQUEST)
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
        user = User.objects.get(email=request.data.get("email"))
        serialized = UserProfileSerializer(user, request.data, partial=True)
        if serialized.is_valid():
            serialized.save()
            return Response({"message": "User profile edited"}, status=status.HTTP_200_OK)

    @swagger_auto_schema()
    @action(detail=False, methods=["get"], url_path="fetch")
    def fetch_profile(self, request):
        '''
        Fetches profile for logged in user
        '''
        serialized = UserProfileSerializer(request.user)
        return Response(serialized.data, status=status.HTTP_200_OK)
