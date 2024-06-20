import json
import os
from http.client import responses
import secrets
import string
from azure.storage.blob import BlobClient
from io import BytesIO
import pathlib
from wsgiref.util import request_uri
from django.db import IntegrityError
import jwt
from jwt import DecodeError, InvalidSignatureError
import requests
from rest_framework import viewsets, status
import re
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import (
    UserLoginSerializer,
    UserProfileSerializer,
    UserSignUpSerializer,
    UsersPendingSerializer,
    UserUpdateSerializer,
    LanguageSerializer,
    ChangePasswordSerializer,
    ChangePasswordWithoutOldPassword,
)
from organizations.models import Invite, Organization
from organizations.serializers import InviteGenerationSerializer
from organizations.decorators import is_organization_owner
from users.models import LANG_CHOICES, User, CustomPeriodicTask
from rest_framework.decorators import action
from tasks.models import (
    Task,
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
)
from workspaces.models import Workspace
from projects.models import Project
from tasks.models import Annotation
from organizations.models import Organization
from django.db.models import Q
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from projects.utils import (
    no_of_words,
    is_valid_date,
    convert_seconds_to_hours,
    get_audio_project_types,
    get_audio_transcription_duration,
    ocr_word_count,
)
from datetime import datetime
import calendar
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from workspaces.views import WorkspaceCustomViewSet
from .utils import generate_random_string, get_role_name
from rest_framework_simplejwt.tokens import RefreshToken
from dotenv import load_dotenv
import pyrebase
from workspaces.views import WorkspaceusersViewSet
from utils.email_template import send_email_template

regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
load_dotenv()

config = {
    "apiKey": os.getenv("API_KEY"),
    "authDomain": os.getenv("AUTH_DOMAIN"),
    "projectId": os.getenv("PROJECT_ID"),
    "storageBucket": os.getenv("STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("MSG_SENDER_ID"),
    "appId": os.getenv("APP_ID"),
    "measurementId": os.getenv("MEASUREMENT_ID"),
    "databaseURL": "",
}


class InviteViewSet(viewsets.ViewSet):
    @swagger_auto_schema(request_body=InviteGenerationSerializer)
    @permission_classes((IsAuthenticated,))
    @is_organization_owner
    @action(
        detail=False, methods=["post"], url_path="generate", url_name="invite_users"
    )
    def invite_users(self, request):
        """
        Invite users to join your organization. This generates a new invite
        with an invite code or adds users to an existing one.
        """
        all_emails = request.data.get("emails")
        distinct_emails = list(set(all_emails))
        organization_id = request.data.get("organization_id")
        users = []
        try:
            org = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        already_existing_emails = []
        valid_user_emails = []
        invalid_emails = []
        existing_emails_set = set(Invite.objects.values_list("user__email", flat=True))
        for email in distinct_emails:
            # Checking if the email is in valid format.
            if re.fullmatch(regex, email):
                if email in existing_emails_set:
                    already_existing_emails.append(email)
                    continue
                try:
                    user = User(
                        username=generate_random_string(12),
                        email=email.lower(),
                        organization_id=org.id,
                        role=request.data.get("role"),
                    )
                    user.is_approved = True
                    user.set_password(generate_random_string(10))
                    valid_user_emails.append(email)
                    users.append(user)
                except:
                    return Response(
                        {"message": "Error in creating user"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                invalid_emails.append(email)
        # setting error messages
        (
            additional_message_for_existing_emails,
            additional_message_for_invalid_emails,
        ) = ("", "")
        additional_message_for_valid_emails = ""
        if already_existing_emails:
            additional_message_for_existing_emails += (
                f", Invites already sent to: {','.join(already_existing_emails)}"
            )
        if invalid_emails:
            additional_message_for_invalid_emails += (
                f", Invalid emails: {','.join(invalid_emails)}"
            )
        if valid_user_emails:
            additional_message_for_valid_emails += (
                f", Invites sent to : {','.join(valid_user_emails)}"
            )
        if len(valid_user_emails) == 0:
            return Response(
                {
                    "message": "No invites sent"
                    + additional_message_for_invalid_emails
                    + additional_message_for_existing_emails
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif len(invalid_emails) == 0:
            ret_dict = {
                "message": "Invites sent"
                + additional_message_for_valid_emails
                + additional_message_for_existing_emails
            }
        else:
            ret_dict = {
                "message": f"Invites sent partially!"
                + additional_message_for_valid_emails
                + additional_message_for_invalid_emails
                + additional_message_for_existing_emails
            }
        try:
            users = User.objects.bulk_create(users)
            Invite.create_invite(organization=org, users=users)
            return Response(ret_dict, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            return Response(
                {"message": "Email Id already present in database"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @swagger_auto_schema(request_body=InviteGenerationSerializer)
    @permission_classes((IsAuthenticated,))
    @is_organization_owner
    @action(detail=False, methods=["post"], url_path="regenerate", url_name="re_invite")
    def re_invite(self, request):
        """
        The invited user are again invited if they have not accepted the
        invitation previously.
        """
        all_emails = request.data.get("emails")
        distinct_emails = list(set(all_emails))
        existing_emails_set = set(Invite.objects.values_list("user__email", flat=True))
        # absent_users- for those who have never been invited
        # present_users- for those who have been invited earlier
        (
            absent_user_emails,
            present_users,
            present_user_emails,
            already_accepted_invite,
        ) = ([], [], [], [])
        for user_email in distinct_emails:
            if user_email in existing_emails_set:
                user = User.objects.get(email=user_email)
                if user.has_accepted_invite:
                    already_accepted_invite.append(user_email)
                    continue
                present_users.append(user)
                present_user_emails.append(user_email)
            else:
                absent_user_emails.append(user_email)
        if present_users:
            Invite.re_invite(users=present_users)
        # setting up error messages
        (
            message_for_already_invited,
            message_for_absent_users,
            message_for_present_users,
        ) = ("", "", "")
        if already_accepted_invite:
            message_for_already_invited = (
                f" {','.join(already_accepted_invite)} have already accepted invite"
            )
        if absent_user_emails:
            message_for_absent_users = (
                f"Kindly send a new invite to: {','.join(absent_user_emails)}"
            )
        if present_user_emails:
            message_for_present_users = f"{','.join(present_user_emails)} re-invited"

        if absent_user_emails and present_user_emails:
            return Response(
                {
                    "message": message_for_absent_users
                    + ", "
                    + message_for_present_users
                    + "."
                    + message_for_already_invited
                },
                status=status.HTTP_201_CREATED,
            )
        elif absent_user_emails:
            return Response(
                {
                    "message": message_for_absent_users
                    + "."
                    + message_for_already_invited
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif present_user_emails:
            return Response(
                {
                    "message": message_for_present_users
                    + "."
                    + message_for_already_invited
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"message": message_for_already_invited}, status=status.HTTP_201_CREATED
            )

    @permission_classes([AllowAny])
    @swagger_auto_schema(request_body=UserSignUpSerializer)
    @action(detail=True, methods=["patch"], url_path="accept", url_name="sign_up_user")
    def sign_up_user(self, request, pk=None):
        """
        Users to sign up for the first time.
        """
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if user.has_accepted_invite:
            return Response(
                {"message": "User has already accepted invite"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            Invite.objects.get(user=user, invite_code=pk)
        except Invite.DoesNotExist:
            return Response(
                {"message": "Invite not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            firebase = pyrebase.initialize_app(config)
            auth = firebase.auth()
            auth.create_user_with_email_and_password(
                email, request.data.get("password")
            )
            serialized = UserSignUpSerializer(user, request.data, partial=True)
        except requests.exceptions.HTTPError as e:
            if str(e).find("EMAIL_EXISTS") >= 0:
                return Response(
                    {"message": "Email Id already present in firebase"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                return Response(
                    {"message": "User signed up failed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if serialized.is_valid():
            serialized.save()
            return Response({"message": "User signed up"}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "User signed up failed"}, status=status.HTTP_400_BAD_REQUEST
            )

    @permission_classes([IsAuthenticated])
    @swagger_auto_schema(responses={200: UsersPendingSerializer})
    @action(detail=False, methods=["get"], url_path="pending_users")
    def pending_users(self, request):
        """
        List of users who have not accepted the invite yet in that organisation/workspace
        """
        organisation_id = request.query_params.get("organisation_id")
        users = User.objects.filter(organization_id=organisation_id, is_approved=False)
        serialized = UsersPendingSerializer(users, many=True)

        if serialized.data:
            return Response(serialized.data, status=status.HTTP_200_OK)

        return Response({"message": "No pending users"}, status=status.HTTP_200_OK)

    # function to reject the user request to join the workspace by organiastion owner and delete the user from the table
    @permission_classes([IsAuthenticated])
    @is_organization_owner
    @swagger_auto_schema(request_body=UsersPendingSerializer)
    @action(detail=False, methods=["delete"], url_path="reject_user")
    def reject_user(self, request):
        """
        Reject the user request to join the workspace
        """
        try:
            user_id = request.query_params.get("userId", None)
            user = User.objects.get(id=user_id)

            if user.is_approved == True:
                return Response(
                    {"message": "User is already approved"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        user.delete()
        return Response({"message": "User rejected"}, status=status.HTTP_200_OK)

    # function to approve the user request to join the workspace by organiastion owner and update the user.is_approved to true
    @permission_classes([IsAuthenticated])
    @is_organization_owner
    @swagger_auto_schema(request_body=UsersPendingSerializer)
    @action(detail=False, methods=["patch"], url_path="approve_user")
    def approve_user(self, request):
        """
        Approve the user request to join the workspace
        """
        try:
            user_id = request.query_params.get("userId", None)
            user = User.objects.get(id=user_id)
            organisation_id = user.organization_id

            try:
                organisation = Organization.objects.get(id=organisation_id)
            except Organization.DoesNotExist:
                return Response(
                    {"message": "Organization not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if user.is_approved == True:
                return Response(
                    {"message": "User is already approved"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.is_approved = True
            user.save()
            # invite the user via mail now
            try:
                users = []
                users.append(user)
                Invite.create_invite(organization=organisation, users=users)
            except:
                return Response(
                    {"message": "Error in sending invite"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response({"message": "User approved"}, status=status.HTTP_200_OK)

    # function to request workspace owner to add the users to the workspace by workspace manager
    @permission_classes([IsAuthenticated])
    @swagger_auto_schema(request_body=InviteGenerationSerializer)
    @action(detail=False, methods=["post"], url_path="request_user")
    def request_user(self, request):
        """
        Request the workspace owner to add the user to the workspace from manager
        """
        all_emails = request.data.get("emails")
        distinct_emails = list(set(all_emails))
        organization_id = request.data.get("organization_id")
        users = []

        try:
            org = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        already_existing_emails = []
        valid_user_emails = []
        invalid_emails = []
        existing_emails_set = set(Invite.objects.values_list("user__email", flat=True))

        for email in distinct_emails:
            # Checking if the email is in valid format.
            if re.fullmatch(regex, email):
                if email in existing_emails_set:
                    already_existing_emails.append(email)
                    continue
                try:
                    user = User(
                        username=generate_random_string(12),
                        email=email.lower(),
                        organization_id=org.id,
                        role=request.data.get("role"),
                        has_accepted_invite=False,
                        is_approved=False,
                    )
                    user.set_password(generate_random_string(10))
                    valid_user_emails.append(email)
                    users.append(user)
                except:
                    pass
            else:
                invalid_emails.append(email)
        # setting error messages
        (
            additional_message_for_existing_emails,
            additional_message_for_invalid_emails,
        ) = ("", "")
        additional_message_for_valid_emails = ""
        if already_existing_emails:
            additional_message_for_existing_emails += (
                f", Invites already sent to: {','.join(already_existing_emails)}"
            )
        if invalid_emails:
            additional_message_for_invalid_emails += (
                f", Invalid emails: {','.join(invalid_emails)}"
            )
        if valid_user_emails:
            additional_message_for_valid_emails += (
                f", Requested users: {','.join(valid_user_emails)}"
            )
        if len(valid_user_emails) == 0:
            return Response(
                {
                    "message": "No invites sent"
                    + additional_message_for_invalid_emails
                    + additional_message_for_existing_emails
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif len(invalid_emails) == 0:
            ret_dict = {
                "The invites to this users will be sent after approval from the organization owner"
                + additional_message_for_valid_emails
                + additional_message_for_existing_emails
            }
        else:
            ret_dict = {
                "message": f"Request sent partially!"
                + additional_message_for_valid_emails
                + additional_message_for_invalid_emails
                + additional_message_for_existing_emails
            }
        users = User.objects.bulk_create(users)
        return Response(ret_dict, status=status.HTTP_201_CREATED)


class AuthViewSet(viewsets.ViewSet):
    @permission_classes([AllowAny])
    @swagger_auto_schema(request_body=UserLoginSerializer)
    @action(
        detail=True,
        methods=["post"],
        url_path="login",
        url_name="login",
    )
    def login(self, request, *args, **kwargs):
        """
        User login functionality
        """

        try:
            email = request.data.get("email")
            password = request.data.get("password")
            if email == "" and password == "":
                return Response(
                    {"message": "Please Enter an Email and a Password"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif email == "":
                return Response(
                    {"message": "Please Enter an Email"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif password == "":
                return Response(
                    {"message": "Please Enter a Password"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": "Incorrect email, User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_active:
            return Response(
                {"message": "User is inactive."}, status=status.HTTP_400_BAD_REQUEST
            )

        # serializer = UserLoginSerializer(user, request.data)
        # serializer.is_valid(raise_exception=True)

        # response = serializer.validate_login(serializer.validated_data)
        # if response != "Correct password":
        #     return Response(
        #         {"message": "Incorrect Password."}, status=status.HTTP_400_BAD_REQUEST
        #     )

        try:
            firebase = pyrebase.initialize_app(config)
            auth = firebase.auth()
            auth.sign_in_with_email_and_password(email, password)
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
        except:
            return Response(
                {"message": "Authentication failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Logged in successfully.",
                "refresh": refresh_token,
                "access": access_token,
            },
            status=status.HTTP_200_OK,
        )

    @permission_classes([AllowAny])
    @action(
        detail=True,
        methods=["post"],
        url_path="reset_password",
        url_name="reset_password",
    )
    def reset_password(self, request, *args, **kwargs):
        """
        User change password functionality
        """
        try:
            email = request.data.get("email")
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": "Incorrect email, User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        firebase = pyrebase.initialize_app(config)
        auth = firebase.auth()
        try:
            auth.send_password_reset_email(email)
            return Response(
                {
                    "message": "Please check your registered email and click on the link to reset your password.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as error:
            return Response(
                {"message": "Error: " + error},
                status=status.HTTP_400_BAD_REQUEST,
            )


class GoogleLogin(viewsets.ViewSet):
    @permission_classes([AllowAny])
    @action(
        detail=True,
        methods=["post"],
        url_path="google_login",
        url_name="google_login",
    )
    def google_login(self, request, *args, **kwargs):
        """
        Google login functionality
        """

        try:
            token = request.data.get("token")
            if token == "":
                raise ValueError
        except ValueError:
            return Response(
                {"message": "Please Send a Token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            firebase = pyrebase.initialize_app(config)
            auth = firebase.auth()
            fire_user = auth.get_account_info(token)
            email = fire_user["users"][0]["email"]
            photoUrl = fire_user["users"][0]["photoUrl"]
            name = str(fire_user["users"][0]["displayName"]).rsplit(" ", 1)
            fName = name[0]
            lName = name[1] if len(name) > 1 else ""
        except Exception as e:
            return Response(
                {"message": "Authentication failed.", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except:
            user = User(
                username=str(email).split("@")[0],
                email=email.lower(),
                role=1,
                first_name=fName,
                last_name=lName,
                profile_photo=photoUrl,
            )
            user.set_password("")
            users = []
            users.append(user)
            User.objects.bulk_create(users)
            user = User.objects.get(email=email)

        try:
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
        except:
            return Response(
                {"message": "Token generation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Logged in successfully.",
                "refresh": refresh_token,
                "access": access_token,
            },
            status=status.HTTP_200_OK,
        )


class UserViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(request_body=UserUpdateSerializer)
    @action(detail=False, methods=["patch"], url_path="update", url_name="edit_profile")
    def edit_profile(self, request):
        """
        Updating user profile.
        """
        user = request.user
        serialized = UserUpdateSerializer(user, request.data, partial=True)
        if serialized.is_valid():
            serialized.save()
            return Response(
                {"message": "User profile edited"}, status=status.HTTP_200_OK
            )

    @swagger_auto_schema(responses={200: UserProfileSerializer})
    @action(detail=False, methods=["get"], url_path="me/fetch")
    def fetch_profile(self, request):
        """
        Fetches profile for logged in user
        """
        serialized = UserProfileSerializer(request.user)
        return Response(serialized.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: UserProfileSerializer})
    @action(detail=True, methods=["get"], url_path="fetch")
    def fetch_other_profile(self, request, pk=None):
        """
        Fetches profile for any user
        """
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if user.organization_id is not request.user.organization_id:
            return Response(
                {"message": "Not Authorized"}, status=status.HTTP_403_FORBIDDEN
            )
        serialized = UserProfileSerializer(user)
        return Response(serialized.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING, format="email", description="New email"
                )
            },
            required=["email"],
        ),
        responses={
            200: "Verification email sent to both of your email ids.Please verify to update your email",
            403: "Please enter a valid email!",
        },
    )
    @action(
        detail=False, methods=["post"], url_path="update_email", url_name="update_email"
    )
    def update_email(self, request):
        """
        Updates the User Email
        """
        try:
            user = request.user
            unverified_email = request.data.get("email")

            old_email_update_code = generate_random_string(10)
            new_email_verification_code = generate_random_string(10)
            subject = "Email Verification"
            message = f"<p>Your email verification code is:{old_email_update_code}</p>"

            compiled_code = send_email_template(subject, message)

            msg = EmailMultiAlternatives(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            msg.attach_alternative(compiled_code, "text/html")
            msg.send()

            # send_mail(
            #     "Email Verification",
            #     f"Your email verification code is:{old_email_update_code}",
            #     settings.DEFAULT_FROM_EMAIL,
            #     [user.email],
            # )

            # send_mail(
            #     "Email Verification",
            #     f"Your email verification code is:{new_email_verification_code}",
            #     settings.DEFAULT_FROM_EMAIL,
            #     [unverified_email],
            # )

            message = f"Your email verification code is: {new_email_verification_code} "
            msg1 = EmailMultiAlternatives(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [unverified_email],
            )
            msg1.attach_alternative(compiled_code, "text/html")
            msg1.send()
            user.unverified_email = unverified_email
            user.old_email_update_code = old_email_update_code
            user.new_email_verification_code = new_email_verification_code
            user.save()

            return Response(
                {
                    "message": "Verification email sent to both of your email ids.Please verify to update your email"
                },
                status=status.HTTP_200_OK,
            )
        except:
            return Response(
                {"message": "Please enter a valid email!"},
                status=status.HTTP_403_FORBIDDEN,
            )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "old_email_update_code": openapi.Schema(type=openapi.TYPE_STRING),
                "new_email_verification_code": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["old_email_update_code", "new_email_verification_code"],
        ),
        responses={
            200: "Email verification Successful!",
            403: "Invalid verification codes!",
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="verify_email_updation",
        url_name="verify_email_updation",
    )
    def verify_email_updation(self, request):
        """
        Verify email updation
        """
        user = request.user
        if (user.unverified_email) != "":
            old_email_update_code = request.data.get("old_email_update_code")
            new_email_verification_code = request.data.get(
                "new_email_verification_code"
            )
            if (user.old_email_update_code) == old_email_update_code and (
                user.new_email_verification_code
            ) == new_email_verification_code:
                user.email = user.unverified_email
                user.unverified_email = ""
                user.old_email_update_code = ""
                user.new_email_verification_code = ""
                user.save()
                ret_dict = {"message": "Email verification Successful!"}
                ret_status = status.HTTP_200_OK
            else:
                ret_dict = {"message": "Invalid verification codes!"}
                ret_status = status.HTTP_403_FORBIDDEN
        else:
            ret_dict = {"message": "Invalid verification codes!"}
            ret_status = status.HTTP_403_FORBIDDEN

        return Response(ret_dict, status=ret_status)

    @action(
        detail=False, methods=["post"], url_path="enable_email", url_name="enable_email"
    )
    def enable_email(self, request):
        """
        Update the mail enable service for  any user
        """
        requested_id = request.data.get("user_id")
        enable_mail = request.data.get("enable_mail")

        if enable_mail == True or enable_mail == False:
            pass
        else:
            return Response(
                {
                    "message": "please enter valid  input(True/False) for enable_mail field"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            user = User.objects.get(id=requested_id)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        requested_id = request.data.get("user_id")

        if requested_id == request.user.id or (
            request.user.role == User.ORGANIZATION_OWNER
            and request.user.organization == user.organization
        ):
            user.enable_mail = enable_mail
            user.save()
            return Response(
                {"message": "Daily e-mail service settings changed."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"message": "Not Authorized"}, status=status.HTTP_403_FORBIDDEN
            )

    @swagger_auto_schema(responses={200: UserProfileSerializer, 403: "Not Authorized"})
    @action(detail=False, methods=["get"], url_path="user_details")
    def user_details(self, request):
        if request.user.role == User.ADMIN:
            user_details = User.objects.all()
            serializer = UserProfileSerializer(user_details, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "Not Authorized"}, status=status.HTTP_403_FORBIDDEN
            )

    @swagger_auto_schema(
        operation_description="Upload file...",
    )
    @action(detail=True, methods=["post"], url_path="edit_user_profile_image")
    def user_profile_image_update(self, request, pk=None):
        try:
            user = User.objects.filter(id=pk)
            if len(user) == 0:
                return Response(
                    {"message": "Invalid User"}, status=status.HTTP_403_FORBIDDEN
                )
            user = user[0]
            file = request.FILES["image"]
            file_extension = pathlib.Path(file.name).suffix
            file_upload_name = user.username + file_extension
            try:
                blob = BlobClient.from_connection_string(
                    conn_str=os.getenv("STORAGE_ACCOUNT_CONNECTION_STRING"),
                    container_name=os.getenv(
                        "STORAGE_ACCOUNT_PROFILE_IMAGE_CONTAINER_NAME"
                    ),
                    blob_name=file_upload_name,
                )
                blob.upload_blob(BytesIO(file.read()), overwrite=True)
            except:
                return Response(
                    {"message": "Could not connect to azure blob storage"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            record = User.objects.get(id=user.id)
            record.profile_photo = blob.url
            record.save(update_fields=["profile_photo"])
            print(blob.url + " created in blob container")
            return Response(
                {"status": "profile photo uploaded successfully"}, status=201
            )
        except:
            return Response(
                {"message": "Could not upload image"}, status=status.HTTP_403_FORBIDDEN
            )

    @swagger_auto_schema(request_body=UserUpdateSerializer)
    @action(detail=True, methods=["patch"], url_path="edit_user_details")
    def user_details_update(self, request, pk=None):
        if request.user.role != User.ADMIN:
            return Response(
                {"message": "Not Authorized"}, status=status.HTTP_403_FORBIDDEN
            )
        user = User.objects.get(id=pk)
        serializer = UserUpdateSerializer(user, request.data, partial=True)

        existing_is_active = user.is_active
        is_active_payload = request.data.get("is_active", None)

        if existing_is_active == is_active_payload:
            pass
        else:
            if is_active_payload is False:
                if user.enable_mail:
                    user.enable_mail = False
                    user.save()
                workspaces = Workspace.objects.filter(
                    Q(members=user) | Q(managers=user)
                ).distinct()

                workspacecustomviewset_obj = WorkspaceCustomViewSet()
                request.data["ids"] = [user.id]

                workspaceusersviewset_obj = WorkspaceusersViewSet()
                request.data["user_id"] = user.id

                for workspace in workspaces:
                    workspacecustomviewset_obj.unassign_manager(
                        request=request, pk=workspace.pk
                    )

                    workspaceusersviewset_obj.remove_members(
                        request=request, pk=workspace.pk
                    )
                user.is_active = False
                user.save()
                return Response(
                    {
                        "message": "User removed from all workspaces both as workspace member and workspace manager"
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                if is_active_payload is True:
                    workspaces = Workspace.objects.filter(
                        Q(members=user) | Q(managers=user)
                    ).distinct()

                workspaceusersviewset_obj = WorkspaceusersViewSet()
                request.data["user_id"] = user.id

                for workspace in workspaces:
                    workspaceusersviewset_obj.remove_frozen_user(
                        request=request, pk=workspace.pk
                    )

        if request.data["role"] != user.role:
            new_role = int(request.data["role"])
            old_role = int(user.role)

            if get_role_name(old_role) == "Workspace Manager" and get_role_name(
                new_role
            ) in ("Annotator", "Reviewer", "Super Checker"):
                workspaces_viewset = WorkspaceCustomViewSet()
                request.data["ids"] = [user.id]
                workspaces = Workspace.objects.filter(managers__in=[user])
                for workspace in workspaces:
                    response = workspaces_viewset.unassign_manager(
                        request=request, pk=workspace.id
                    )
                    if user not in workspace.members.all():
                        workspace.members.add(user)
                        workspace.save()

            elif get_role_name(new_role) == "Admin":
                user.is_superuser = True
                user.save()

            elif get_role_name(old_role) == "Admin":
                user.is_superuser = False
                user.save()

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User details edited"}, status=status.HTTP_200_OK
            )
        return Response(
            {"message": "Error in updating user details"},
            status=status.HTTP_403_FORBIDDEN,
        )

    @swagger_auto_schema(request_body=ChangePasswordSerializer)
    @action(
        detail=True,
        methods=["patch"],
        url_path="update_my_password",
        url_name="update_my_password",
    )
    def update_password(self, request, pk=None, *args, **kwargs):
        """
        Update user password
        """

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ChangePasswordSerializer(user, request.data)
        serializer.is_valid(raise_exception=True)

        if not serializer.match_old_password(user, request.data):
            return Response(
                {
                    "message": "Your old password was entered incorrectly. Please enter it again."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validation_response = serializer.validation_checks(
            user, request.data
        )  # checks for min_length, whether password is similar to user details etc.
        if validation_response != "Validation successful":
            return Response(
                {"message": validation_response},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save(user, request.data)
        return Response(
            {"message": "User password changed."}, status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="update_ui_prefs",
        url_name="update_ui_prefs",
    )
    def update_ui_prefs(self, request):
        """
        Update UI preferences for user
        """
        prefer_cl_ui = request.data.get("prefer_cl_ui")

        if prefer_cl_ui == True or prefer_cl_ui == False:
            pass
        else:
            return Response(
                {"message": "Please enter valid input(True/False)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.is_authenticated:
            user = request.user
        else:
            return Response(
                {"message": "Not Authorized"}, status=status.HTTP_403_FORBIDDEN
            )

        user.prefer_cl_ui = prefer_cl_ui
        user.save()
        return Response(
            {"message": "Successfully updated UI preferences."},
            status=status.HTTP_200_OK,
        )


class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny,)

    @action(
        detail=False,
        methods=["POST"],
        url_path="user_analytics",
        url_name="get_user_analytics",
    )
    def get_user_analytics(self, request):
        """
        Get Reports of a User
        """
        PERMISSION_ERROR = {
            "message": "You do not have enough permissions to access this view!"
        }
        emails = User.objects.all()
        emails_list = emails.values_list("email", flat=True)
        try:
            user_email = request.user.email
            if user_email not in emails_list:
                return Response(PERMISSION_ERROR, status=status.HTTP_400_BAD_REQUEST)
        except:
            if type(request) == dict:
                pass
            else:
                return Response(PERMISSION_ERROR, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = request.data.get("start_date")
            end_date = request.data.get("end_date")
            user_id = request.data.get("user_id")
            reports_type = request.data.get("reports_type")
            project_type = request.data.get("project_type")
        except:
            start_date = request["start_date"]
            end_date = request["end_date"]
            user_id = request["user_id"]
            reports_type = request["reports_type"]
            project_type = request["project_type"]

        review_reports = False
        supercheck_reports = False
        if reports_type == "review":
            review_reports = True
        elif reports_type == "supercheck":
            supercheck_reports = True
        start_date = start_date + " 00:00"
        end_date = end_date + " 23:59"

        cond, invalid_message = is_valid_date(start_date)
        if not cond:
            return Response(
                {"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST
            )

        cond, invalid_message = is_valid_date(end_date)
        if not cond:
            return Response(
                {"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST
            )

        start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
        end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M")

        if start_date > end_date:
            return Response(
                {"message": "'To' Date should be after 'From' Date"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project_type_lower = project_type.lower()
        is_textual_project = (
            False if project_type in get_audio_project_types() else True
        )  # flag for distinguishing between textual and audio projects

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if review_reports:
            if project_type == "all":
                project_objs = Project.objects.filter(  # Not using the project_type filter if it is set to "all"
                    annotation_reviewers=user_id,
                )
            else:
                project_objs = Project.objects.filter(
                    annotation_reviewers=user_id,
                    project_type=project_type,
                )
        elif supercheck_reports:
            if project_type == "all":
                project_objs = Project.objects.filter(  # Not using the project_type filter if it is set to "all"
                    review_supercheckers=user_id,
                )
            else:
                project_objs = Project.objects.filter(
                    review_supercheckers=user_id,
                    project_type=project_type,
                )
        else:
            if project_type == "all":
                project_objs = Project.objects.filter(
                    annotators=user_id,
                )
            else:
                project_objs = Project.objects.filter(
                    annotators=user_id,
                    project_type=project_type,
                )

        all_annotated_lead_time_list = []
        all_annotated_lead_time_count = 0
        total_annotated_tasks_count = 0
        all_tasks_word_count = 0
        all_projects_total_duration = 0
        project_wise_summary = []
        for proj in project_objs:
            project_name = proj.title
            project_type = proj.project_type
            is_textual_project = (
                False if project_type in get_audio_project_types() else True
            )
            annotated_labeled_tasks = []
            if review_reports:
                labeld_tasks_objs = Task.objects.filter(
                    Q(project_id=proj.id)
                    & Q(review_user=user_id)
                    & Q(
                        task_status__in=[
                            "reviewed",
                            "exported",
                            "super_checked",
                        ]
                    )
                )

                annotated_task_ids = list(
                    labeld_tasks_objs.values_list("id", flat=True)
                )
                annotated_labeled_tasks = Annotation.objects.filter(
                    task_id__in=annotated_task_ids,
                    annotation_type=REVIEWER_ANNOTATION,
                    updated_at__range=[start_date, end_date],
                    completed_by=user_id,
                ).exclude(annotation_status__in=["to_be_revised", "draft", "skipped"])
            elif supercheck_reports:
                labeld_tasks_objs = Task.objects.filter(
                    Q(project_id=proj.id)
                    & Q(super_check_user=user_id)
                    & Q(
                        task_status__in=[
                            "exported",
                            "super_checked",
                        ]
                    )
                )

                annotated_task_ids = list(
                    labeld_tasks_objs.values_list("id", flat=True)
                )
                annotated_labeled_tasks = Annotation.objects.filter(
                    task_id__in=annotated_task_ids,
                    annotation_type=SUPER_CHECKER_ANNOTATION,
                    updated_at__range=[start_date, end_date],
                    completed_by=user_id,
                )
            else:
                labeld_tasks_objs = Task.objects.filter(
                    Q(project_id=proj.id)
                    & Q(annotation_users=user_id)
                    & Q(
                        task_status__in=[
                            "annotated",
                            "reviewed",
                            "exported",
                            "super_checked",
                        ]
                    )
                )
                annotated_task_ids = list(
                    labeld_tasks_objs.values_list("id", flat=True)
                )
                annotated_labeled_tasks = Annotation.objects.filter(
                    task_id__in=annotated_task_ids,
                    annotation_type=ANNOTATOR_ANNOTATION,
                    updated_at__range=[start_date, end_date],
                    completed_by=user_id,
                )

            annotated_tasks_count = annotated_labeled_tasks.count()
            total_annotated_tasks_count += annotated_tasks_count

            avg_lead_time = 0
            lead_time_annotated_tasks = [
                eachtask.lead_time for eachtask in annotated_labeled_tasks
            ]
            all_annotated_lead_time_list.extend(lead_time_annotated_tasks)
            if len(lead_time_annotated_tasks) > 0:
                avg_lead_time = sum(lead_time_annotated_tasks) / len(
                    lead_time_annotated_tasks
                )
                avg_lead_time = round(avg_lead_time, 2)

            total_word_count = 0
            if "OCRTranscription" in project_type:
                for each_anno in annotated_labeled_tasks:
                    total_word_count += ocr_word_count(each_anno.result)
            elif is_textual_project:
                total_word_count_list = []
                for each_task in annotated_labeled_tasks:
                    try:
                        total_word_count_list.append(each_task.task.data["word_count"])
                    except:
                        pass

                total_word_count = sum(total_word_count_list)
            all_tasks_word_count += total_word_count

            total_duration = "00:00:00"
            if project_type in get_audio_project_types():
                total_duration_list = []
                for each_task in annotated_labeled_tasks:
                    try:
                        total_duration_list.append(
                            get_audio_transcription_duration(each_task.result)
                        )
                    except:
                        pass
                total_duration = convert_seconds_to_hours(sum(total_duration_list))
                all_projects_total_duration += sum(total_duration_list)

            result = {
                "Project Name": project_name,
                (
                    "Reviewed Tasks"
                    if review_reports
                    else (
                        "SuperChecked Tasks"
                        if supercheck_reports
                        else "Annotated Tasks"
                    )
                ): annotated_tasks_count,
                "Word Count": total_word_count,
                "Total Segments Duration": total_duration,
                (
                    "Avg Review Time (sec)"
                    if review_reports
                    else (
                        "Avg SuperCheck Time (sec)"
                        if supercheck_reports
                        else "Avg Annotation Time (sec)"
                    )
                ): avg_lead_time,
            }

            if project_type in get_audio_project_types():
                del result["Word Count"]
            elif is_textual_project:
                del result["Total Segments Duration"]
            else:
                del result["Word Count"]
                del result["Total Segments Duration"]

            if (
                result[
                    (
                        "Reviewed Tasks"
                        if review_reports
                        else (
                            "SuperChecked Tasks"
                            if supercheck_reports
                            else "Annotated Tasks"
                        )
                    )
                ]
                > 0
            ):
                project_wise_summary.append(result)

        project_wise_summary = sorted(
            project_wise_summary,
            key=lambda x: x[
                (
                    "Reviewed Tasks"
                    if review_reports
                    else (
                        "SuperChecked Tasks"
                        if supercheck_reports
                        else "Annotated Tasks"
                    )
                )
            ],
            reverse=True,
        )

        if total_annotated_tasks_count > 0:
            all_annotated_lead_time_count = (
                sum(all_annotated_lead_time_list) / total_annotated_tasks_count
            )
            all_annotated_lead_time_count = round(all_annotated_lead_time_count, 2)

        # total_summary = {}
        # if is_translation_project or project_type == "SemanticTextualSimilarity_Scale5":

        total_result = {
            (
                "Reviewed Tasks"
                if review_reports
                else ("SuperChecked Tasks" if supercheck_reports else "Annotated Tasks")
            ): total_annotated_tasks_count,
            "Word Count": all_tasks_word_count,
            "Total Segments Duration": convert_seconds_to_hours(
                all_projects_total_duration
            ),
            (
                "Avg Review Time (sec)"
                if review_reports
                else (
                    "Avg SuperCheck Time (sec)"
                    if supercheck_reports
                    else "Avg Annotation Time (sec)"
                )
            ): round(all_annotated_lead_time_count, 2),
        }
        if project_type_lower != "all" and project_type in get_audio_project_types():
            del total_result["Word Count"]
        elif project_type_lower != "all" and is_textual_project:
            del total_result["Total Segments Duration"]
        elif project_type_lower != "all":
            del total_result["Word Count"]
            del total_result["Total Segments Duration"]

        total_summary = [total_result]

        final_result = {
            "total_summary": total_summary,
            "project_summary": project_wise_summary,
        }
        return Response(final_result)

    @action(
        detail=True,
        methods=["POST"],
        name="Schedule payment reports (e-mail)",
        url_path="schedule_mail",
        url_name="schedule_mail",
    )
    def schedule_mail(self, request, pk=None):
        user = request.user
        if not (
            user.is_authenticated
            and (
                user.role == User.ORGANIZATION_OWNER
                or user.role == User.WORKSPACE_MANAGER
                or user.is_superuser
            )
        ):
            final_response = {
                "message": "You do not have enough permissions to access this view!"
            }
            return Response(final_response, status=status.HTTP_401_UNAUTHORIZED)

        report_level = request.data.get("report_level")
        id = request.data.get("id")
        if report_level == 1:
            try:
                organization = Organization.objects.get(pk=id)
            except Organization.DoesNotExist:
                return Response(
                    {"message": "Organization not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not (
                user.is_superuser
                or (
                    user.role == User.ORGANIZATION_OWNER
                    and user.organization == organization
                )
            ):
                return Response(
                    {"message": "Not Authorized"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif report_level == 2:
            try:
                workspace = Workspace.objects.get(pk=id)
            except Workspace.DoesNotExist:
                return Response(
                    {"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
                )
            if not (
                request.user.is_superuser
                or (
                    user.role == User.ORGANIZATION_OWNER
                    and workspace.organization == user.organization
                )
                or user in workspace.managers.all()
            ):
                return Response(
                    {"message": "Not Authorized"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            return Response(
                {"message": "Invalid report level"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project_type = request.data.get("project_type")
        schedule = request.data.get("schedule")
        schedule_day = request.data.get("schedule_day")

        if schedule == "Daily":
            try:
                crontab_schedule = CrontabSchedule.objects.get(
                    minute="0",
                    hour="6",
                    day_of_week="*",
                    day_of_month="*",
                    month_of_year="*",
                )
            except CrontabSchedule.DoesNotExist:
                crontab_schedule = CrontabSchedule.objects.create(
                    minute="0",
                    hour="6",
                    day_of_week="*",
                    day_of_month="*",
                    month_of_year="*",
                )
        elif schedule == "Weekly":
            try:
                crontab_schedule = CrontabSchedule.objects.get(
                    minute="0",
                    hour="6",
                    day_of_week=schedule_day,
                    day_of_month="*",
                    month_of_year="*",
                )
            except CrontabSchedule.DoesNotExist:
                crontab_schedule = CrontabSchedule.objects.create(
                    minute="0",
                    hour="6",
                    day_of_week=schedule_day,
                    day_of_month="*",
                    month_of_year="*",
                )
        elif schedule == "Monthly":
            try:
                crontab_schedule = CrontabSchedule.objects.get(
                    minute="0",
                    hour="6",
                    day_of_week="*",
                    day_of_month=schedule_day,
                    month_of_year="*",
                )
            except CrontabSchedule.DoesNotExist:
                crontab_schedule = CrontabSchedule.objects.create(
                    minute="0",
                    hour="6",
                    day_of_week="*",
                    day_of_month=schedule_day,
                    month_of_year="*",
                )
        else:
            return Response(
                {"message": "Invalid schedule"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task_obj = CustomPeriodicTask.objects.get(
                user__id=user.id,
                schedule=(
                    1 if schedule == "Daily" else 2 if schedule == "Weekly" else 3
                ),
                project_type=project_type,
                report_level=report_level,
                organization=organization if report_level == 1 else None,
                workspace=workspace if report_level == 2 else None,
            )
            return Response(
                {"message": "Schedule already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except CustomPeriodicTask.DoesNotExist:
            try:
                celery_task = PeriodicTask.objects.create(
                    crontab=crontab_schedule,
                    name=f"Payment Report {user.email} {schedule} {datetime.now()}",
                    task=(
                        "organizations.tasks.send_user_reports_mail_org"
                        if report_level == 1
                        else "workspaces.tasks.send_user_reports_mail_ws"
                    ),
                    kwargs={
                        f'{"org_id" if report_level == 1 else "ws_id"}': id,
                        "user_id": user.id,
                        "project_type": project_type,
                        "period": schedule,
                    },
                )
                task_obj = CustomPeriodicTask.objects.create(
                    celery_task=celery_task,
                    user=user,
                    schedule=(
                        1 if schedule == "Daily" else 2 if schedule == "Weekly" else 3
                    ),
                    project_type=project_type,
                    report_level=report_level,
                    organization=organization if report_level == 1 else None,
                    workspace=workspace if report_level == 2 else None,
                )
            except:
                return Response(
                    {"message": "Error in scheduling email"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"message": "Email scheduled successfully"}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["PATCH"],
        name="Enable/disable payment reports (e-mail)",
        url_name="update_scheduled_mail",
        url_path="update_scheduled_mail",
    )
    def update_scheduled_mail(self, request, pk=None):
        user = request.user
        if not (
            user.is_authenticated
            and (
                user.role == User.ORGANIZATION_OWNER
                or user.role == User.WORKSPACE_MANAGER
                or user.is_superuser
            )
        ):
            final_response = {
                "message": "You do not have enough permissions to access this view!"
            }
            return Response(final_response, status=status.HTTP_401_UNAUTHORIZED)

        task_id = request.data.get("task_id")

        try:
            task_obj = CustomPeriodicTask.objects.get(pk=task_id)
            if not user.is_superuser and task_obj.user != user:
                return Response(
                    {"message": "Not Authorized"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            celery_task = task_obj.celery_task
            celery_task.enabled = True if celery_task.enabled == False else False
            celery_task.save()
        except:
            return Response(
                {"message": "Error in modifying email schedule"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = (
            "Email schedule disabled"
            if celery_task.enabled == False
            else "Email schedule enabled"
        )
        return Response({"message": message}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["POST"],
        name="Delete payment reports schedule (e-mail)",
        url_name="delete_scheduled_mail",
        url_path="delete_scheduled_mail",
    )
    def delete_scheduled_mail(self, request, pk=None):
        user = request.user
        if not (
            user.is_authenticated
            and (
                user.role == User.ORGANIZATION_OWNER
                or user.role == User.WORKSPACE_MANAGER
                or user.is_superuser
            )
        ):
            final_response = {
                "message": "You do not have enough permissions to access this view!"
            }
            return Response(final_response, status=status.HTTP_401_UNAUTHORIZED)

        task_id = request.data.get("task_id")

        try:
            # task_obj is automatically deleted by models.CASCADE
            task_obj = CustomPeriodicTask.objects.get(pk=task_id)
            if not user.is_superuser and task_obj.user != user:
                return Response(
                    {"message": "Not Authorized"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            celery_task = task_obj.celery_task
            celery_task.delete()
        except:
            return Response(
                {"message": "Error in deleting email schedule"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Email schedule deleted"}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["GET"],
        name="Get currently scheduled payment reports for user",
        url_name="get_scheduled_mails",
        url_path="get_scheduled_mails",
    )
    def get_scheduled_mails(self, request, pk=None):
        user = request.user
        if not (
            user.is_authenticated
            and (
                user.role == User.ORGANIZATION_OWNER
                or user.role == User.WORKSPACE_MANAGER
                or user.is_superuser
            )
        ):
            final_response = {
                "message": "You do not have enough permissions to access this view!"
            }
            return Response(final_response, status=status.HTTP_401_UNAUTHORIZED)

        user_periodic_tasks = CustomPeriodicTask.objects.filter(
            user__id=pk,
        )
        result = []
        for task in user_periodic_tasks:
            report_level = "Organization" if task.report_level == 1 else "Workspace"
            organization = task.organization.title if task.organization else None
            workspace = task.workspace.workspace_name if task.workspace else None
            project_type = json.loads(task.celery_task.kwargs.replace("'", '"'))[
                "project_type"
            ]
            schedule = (
                "Daily"
                if task.schedule == 1
                else "Weekly"
                if task.schedule == 2
                else "Monthly"
            )
            scheduled_day = (
                calendar.day_name[int(task.celery_task.crontab.day_of_week) - 1]
                if task.schedule == 2
                else task.celery_task.crontab.day_of_month
                if task.schedule == 3
                else None
            )
            result.append(
                {
                    "id": task.id,
                    "Report Level": report_level,
                    "Organization": organization,
                    "Workspace": workspace,
                    "Project Type": project_type,
                    "Schedule": schedule,
                    "Scheduled Day": scheduled_day,
                    "Created At": task.created_at,
                    "Run Count": task.celery_task.total_run_count,
                    "Status": "Enabled"
                    if task.celery_task.enabled == True
                    else "Disabled",
                }
            )
        result = sorted(result, key=lambda x: x["Created At"], reverse=True)
        return Response(result, status=status.HTTP_200_OK)


class LanguageViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(responses={200: LanguageSerializer})
    @action(detail=False, methods=["get"], url_path="fetch")
    def fetch_language(self, request):
        """
        Fetches all language choices available to the user.
        """
        serialized = LanguageSerializer(
            data={"language": [lang[0] for lang in LANG_CHOICES]}
        )
        if serialized.is_valid():
            return Response(serialized.data, status=status.HTTP_200_OK)
        return Response(serialized.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
