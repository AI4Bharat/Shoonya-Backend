import os
from smtplib import (
    SMTPAuthenticationError,
    SMTPException,
    SMTPRecipientsRefused,
    SMTPServerDisconnected,
)
import socket
import jwt
from datetime import datetime, timedelta

from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from organizations.models import Organization
from workspaces.models import Workspace
from shoonya_backend import settings
from dotenv import load_dotenv

from .utils import hash_upload
from .managers import UserManager

# List of Indic languages
LANG_CHOICES = (
    ("English", "English"),
    ("Assamese", "Assamese"),
    ("Bengali", "Bengali"),
    ("Bodo", "Bodo"),
    ("Dogri", "Dogri"),
    ("Gujarati", "Gujarati"),
    ("Hindi", "Hindi"),
    ("Kannada", "Kannada"),
    ("Kashmiri", "Kashmiri"),
    ("Konkani", "Konkani"),
    ("Maithili", "Maithili"),
    ("Malayalam", "Malayalam"),
    ("Manipuri", "Manipuri"),
    ("Marathi", "Marathi"),
    ("Nepali", "Nepali"),
    ("Odia", "Odia"),
    ("Punjabi", "Punjabi"),
    ("Sanskrit", "Sanskrit"),
    ("Santali", "Santali"),
    ("Sindhi", "Sindhi"),
    ("Sinhala", "Sinhala"),
    ("Tamil", "Tamil"),
    ("Telugu", "Telugu"),
    ("Urdu", "Urdu"),
)
load_dotenv()
# Create your models here.
# class Language(models.Model):
#     language = models.CharField(
#         verbose_name="language",
#         choices=LANG_CHOICES,
#         blank=False,
#         null=False,
#         default="English",
#         max_length=15,
#     )

#     def __str__(self):
#         return str(self.language)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for storing userdata, also imlements different roles like organization_owner, workspace_manager
    and annotator.

    Email and Password are required other are optional.
    """

    ANNOTATOR = 1
    REVIEWER = 2
    SUPER_CHECKER = 3
    WORKSPACE_MANAGER = 4
    ORGANIZATION_OWNER = 5
    ADMIN = 6

    ROLE_CHOICES = (
        (ANNOTATOR, "Annotator"),
        (REVIEWER, "Reviewer"),
        (SUPER_CHECKER, "Super Checker"),
        (WORKSPACE_MANAGER, "Workspace Manager"),
        (ORGANIZATION_OWNER, "Organization Owner"),
        (ADMIN, "Admin"),
    )

    username = models.CharField(verbose_name="username", max_length=265)
    email = models.EmailField(verbose_name="email_address", unique=True, blank=False)

    first_name = models.CharField(verbose_name="first_name", max_length=265, blank=True)
    last_name = models.CharField(verbose_name="last_name", max_length=265, blank=True)
    phone = models.CharField(verbose_name="phone", max_length=256, blank=True)
    profile_photo = models.CharField(
        verbose_name="profile_photo", max_length=256, blank=True
    )

    role = models.PositiveSmallIntegerField(
        choices=ROLE_CHOICES, blank=False, null=False, default=ANNOTATOR
    )

    is_staff = models.BooleanField(
        verbose_name="staff status",
        default=False,
        help_text=("Designates whether the user can log into this admin site."),
    )
    has_accepted_invite = models.BooleanField(
        verbose_name="invite status",
        default=False,
        help_text=("Designates whether the user has accepted the invite."),
    )

    is_active = models.BooleanField(
        verbose_name="active",
        default=True,
        help_text=(
            "Designates whether to treat this user as active. Unselect this instead of deleting accounts."
        ),
    )
    enable_mail = models.BooleanField(
        verbose_name="enable_mail",
        default=False,
        help_text=("Indicates whether mailing is enable or not."),
    )

    date_joined = models.DateTimeField(verbose_name="date joined", default=timezone.now)

    activity_at = models.DateTimeField(
        verbose_name="last annotation activity by the user", auto_now=True
    )

    languages = ArrayField(
        models.CharField(verbose_name="language", choices=LANG_CHOICES, max_length=15),
        blank=True,
        null=True,
        default=list,
    )
    # languages = models.ManyToManyField(Language, related_name="user_languages", blank=True, help_text=("Languages known by the user."))

    # maximum_annotations_per_day = models.IntegerField(
    #     verbose_name="maximum annotations per day", null=True
    # )

    AVAILABLE = 1
    ON_LEAVE = 2

    AVAILABILITY_STATUS_CHOICES = (
        (AVAILABLE, "Available"),
        (ON_LEAVE, "On Leave"),
    )

    availability_status = models.PositiveSmallIntegerField(
        choices=AVAILABILITY_STATUS_CHOICES,
        blank=False,
        null=False,
        default=AVAILABLE,
        help_text=(
            "Indicates whether a user is available for doing annotation or not."
        ),
    )

    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)

    FULL_TIME = 1
    PART_TIME = 2
    NA = 3
    CONTRACT_BASIS = 4

    PARTICIPATION_TYPE_CHOICES = (
        (FULL_TIME, "Full-Time"),
        (PART_TIME, "Part-Time"),
        (NA, "N/A"),
        (CONTRACT_BASIS, "Contract Basis"),
    )

    participation_type = models.PositiveSmallIntegerField(
        choices=PARTICIPATION_TYPE_CHOICES,
        blank=False,
        null=False,
        default=FULL_TIME,
        help_text=("Indicates the type of participation of user."),
    )

    unverified_email = models.EmailField(blank=True)
    old_email_update_code = models.CharField(max_length=256, blank=True)
    new_email_verification_code = models.CharField(max_length=256, blank=True)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELD = ()

    prefer_cl_ui = models.BooleanField(
        verbose_name="prefer_cl_ui",
        default=False,
        help_text=(
            "Indicates whether user prefers Chitralekha UI for audio transcription tasks or not."
        ),
    )

    class Meta:
        db_table = "user"
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["email"]),
        ]

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def name_or_email(self):
        name = self.get_full_name()
        if len(name) == 0:
            name = self.email
        return name

    def get_full_name(self):
        """
        Return the first_name and the last_name for a given user with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    """
    Functions to check type of user.
    """

    def is_annotator(self):
        return self.role == User.ANNOTATOR

    def is_reviewer(self):
        return self.role == User.REVIEWER

    def is_workspace_manager(self):
        return self.role == User.WORKSPACE_MANAGER

    def is_organization_owner(self):
        return self.role == User.ORGANIZATION_OWNER

    def is_admin(self):
        return self.role == User.ADMIN

    def send_mail_to_change_password(self, email, key):
        sent_token = self.generate_reset_token(key)
        prefix = os.getenv("FRONTEND_URL_FOR_RESET_PASSWORD")
        link = f"{prefix}/#/forget-password/confirm/{key}/{sent_token}"
        try:
            send_mail(
                "Reset password link for shoonya",
                f"Hello! Please click on the following link to reset your password - {link}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )
        except SMTPAuthenticationError:
            raise Exception(
                "Failed to authenticate with the SMTP server. Check your email settings."
            )
        except (
            SMTPException,
            socket.gaierror,
            SMTPRecipientsRefused,
            SMTPServerDisconnected,
        ) as e:
            raise Exception("Failed to send the email. Please try again later.")

    def generate_reset_token(self, user_id):
        # Setting token expiration time (2 hours)
        expiration_time = datetime.utcnow() + timedelta(hours=2)
        secret_key = os.getenv("SECRET_KEY")

        # Creating the payload containing user ID and expiration time
        payload = {
            "user_id": user_id,
            "exp": expiration_time,
        }

        # Signing the payload with a secret key
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        return token


class CustomPeriodicTask(models.Model):
    """
    Celery Beat Tasks for Users.
    """

    celery_task = models.OneToOneField(
        PeriodicTask,
        on_delete=models.CASCADE,
        null=False,
        help_text=("Celery Beat Task for the user."),
    )

    created_at = models.DateTimeField(verbose_name="created_at", auto_now_add=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="user",
        help_text=("User for which the task is created."),
    )

    DAILY = 1
    WEEKLY = 2
    MONTHLY = 3

    SCHEDULE_CHOICES = (
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
        (MONTHLY, "Monthly"),
    )

    schedule = models.PositiveSmallIntegerField(
        choices=SCHEDULE_CHOICES,
        verbose_name="schedule",
        blank=False,
        null=False,
        help_text=("Schedule of the task."),
    )

    project_type = models.CharField(
        verbose_name="project_type",
        max_length=256,
        blank=False,
        null=False,
        help_text=("Project type of the task."),
    )

    ORGANIZATION_LEVEL = 1
    WORKSPACE_LEVEL = 2

    REPORT_LEVEL_CHOICES = (
        (ORGANIZATION_LEVEL, "Organization Level"),
        (WORKSPACE_LEVEL, "Workspace Level"),
    )

    report_level = models.PositiveSmallIntegerField(
        choices=REPORT_LEVEL_CHOICES,
        verbose_name="report_level",
        blank=False,
        null=False,
        help_text=("Report level of the task."),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        verbose_name="organization",
        help_text=("Organization for which the reports will be generated."),
        blank=True,
        null=True,
    )

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        verbose_name="workspace",
        help_text=("Workspace for which the reports will be generated."),
        blank=True,
        null=True,
    )


@receiver(post_delete, sender=CustomPeriodicTask)
def delete_celery_task(sender, instance, **kwargs):
    instance.celery_task.delete()
