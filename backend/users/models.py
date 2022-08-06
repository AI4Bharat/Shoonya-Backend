from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone

from organizations.models import Organization

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
    WORKSPACE_MANAGER = 2
    ORGANIZAION_OWNER = 3

    ROLE_CHOICES = (
        (ANNOTATOR, "Annotator"),
        (WORKSPACE_MANAGER, "Workspace Manager"),
        (ORGANIZAION_OWNER, "Organization Owner"),
    )

    username = models.CharField(verbose_name="username", max_length=265)
    email = models.EmailField(verbose_name="email_address", unique=True, blank=False)

    first_name = models.CharField(verbose_name="first_name", max_length=265, blank=True)
    last_name = models.CharField(verbose_name="last_name", max_length=265, blank=True)
    phone = models.CharField(verbose_name="phone", max_length=256, blank=True)
    profile_photo = models.ImageField(upload_to=hash_upload, blank=True)

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

    unverified_email = models.EmailField(blank=True)
    old_email_update_code = models.CharField(max_length=256, blank=True)
    new_email_verification_code = models.CharField(max_length=256, blank=True)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELD = ()

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

    def is_workspace_manager(self):
        return self.role == User.WORKSPACE_MANAGER

    def is_organization_owner(self):
        return self.role == User.ORGANIZAION_OWNER
