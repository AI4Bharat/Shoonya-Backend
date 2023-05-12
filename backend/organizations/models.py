import string
from django.db import models, transaction
from users.models import *
from shoonya_backend.settings import AUTH_USER_MODEL
from shoonya_backend.mixins import DummyModelMixin
import secrets
from django.core.mail import send_mail
import os
from dotenv import load_dotenv

load_dotenv()

from django.conf import settings

# Create your models here.


class Organization(models.Model):
    """
    Organization Model
    """

    title = models.CharField(
        verbose_name="organization_title", max_length=1024, null=False
    )

    email_domain_name = models.CharField(
        verbose_name="organization_email_domain", max_length=4096, null=True
    )

    # users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='organizations')

    is_active = models.BooleanField(
        verbose_name="organization_is_active",
        default=True,
        help_text=("Designates weather an organization is active or not."),
    )

    created_by = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="organization_creator",
        verbose_name="created_by",
    )

    created_at = models.DateTimeField(verbose_name="created_at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="updated_at", auto_now=True)

    def __str__(self):
        return self.title + ", id=" + str(self.pk)

    @classmethod
    def create_organization(
        cls,
        created_by=None,
        title="Organization",
        email_domain_name="organization@shoonya.org",
    ):
        with transaction.atomic():
            org = Organization.objects.create(
                created_by=created_by, title=title, email_domain_name=email_domain_name
            )
            user = User.objects.get(pk=created_by.pk)
            user.organization_id = org
            user.save()
            return org

    # def add_user(self, user):
    #     if self.users.filter(pk=user.pk).exists():
    #         print('User exists!')
    #         return

    #     with transaction.atomic():
    #         self.users.add(user)
    #         return

    def has_user(self, user):
        return self.users.filter(pk=user.pk)

    @property
    def get_owner(self):
        return self.created_by

    # def has_object_permission(self, user):
    #     if user.organization_id == self.pk:
    #         return True
    #     return False


class Invite(models.Model):
    """
    Invites to invite users to organizations.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="invite_users",
        on_delete=models.CASCADE,
        null=True,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        related_name="invite_oganization",
        verbose_name="organization",
    )

    invite_code = models.CharField(
        verbose_name="invite_code", max_length=256, null=True, unique=True
    )

    def __str__(self):
        return (
            str(self.user.email)
            + " for "
            + str(self.organization.title)
            + " organization"
        )

    @classmethod
    def create_invite(cls, organization=None, users=None):
        with transaction.atomic():
            for user in users:
                try:
                    invite = Invite.objects.get(user=user)
                except:
                    invite = Invite.objects.create(organization=organization, user=user)
                    invite.invite_code = cls.generate_invite_code()
                    invite.save()
                send_mail(
                    "Invitation to join Organization",
                    f"Hello! You are invited to {organization.title}. Your Invite link is: https://shoonya.ai4bharat.org/#/invite/{invite.invite_code}",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )

    # def has_permission(self, user):
    #     if self.organization.created_by.pk == user.pk or user.is_superuser:
    #         return True
    #     return False

    @classmethod
    def re_invite(cls, users=None):
        with transaction.atomic():
            for user in users:
                invite = Invite.objects.get(user=user)
                send_mail(
                    "Invitation to join Organization",
                    f"Hello! You are invited to {invite.organization.title}. Your Invite link is: https://shoonya.ai4bharat.org/#/invite/{invite.invite_code}",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )

    @classmethod
    def generate_invite_code(cls):
        return "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for i in range(10)
        )
