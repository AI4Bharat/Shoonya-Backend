import string
from django.db import models, transaction
from users.models import *
from shoonya_backend.settings import AUTH_USER_MODEL
from shoonya_backend.mixins import DummyModelMixin
import secrets
from django.core.mail import EmailMultiAlternatives
import os
from dotenv import load_dotenv

load_dotenv()

from django.conf import settings


# Create your models here.
def default_permissions():
    from users.models import User

    return {
        "PROJECT_PERMISSIONS": {
            "can_view_add_annotators_to_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_add_annotators_to_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_add_reviewers_to_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_add_reviewers_to_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_add_superchecker_to_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_add_superchecker_to_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_basic_project_settings": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_basic_project_settings": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_publish_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_publish_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_archive_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_archive_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_export_project_into_dataset": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_export_project_into_dataset": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_pull_new_data_items_from_source_dataset": [
                "org_owner",
                "workspace_manager",
            ],
            "can_use_pull_new_data_items_from_source_dataset": [
                "org_owner",
                "workspace_manager",
            ],
            "can_view_download_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_download_project": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_delete_project_tasks": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_delete_project_tasks": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_deallocate_user_tasks": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_deallocate_user_tasks": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_project_stage": [User.ORGANIZATION_OWNER, User.WORKSPACE_MANAGER],
            "can_use_project_stage": [User.ORGANIZATION_OWNER, User.WORKSPACE_MANAGER],
            "can_view_supercheck_settings": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_supercheck_settings": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_user_profile_details_of_other_users": [
                "org_owner",
                "workspace_manager",
            ],
            "can_access_user_profile_details_of_other_users": [
                "org_owner",
                "workspace_manager",
            ],
        },
        "DATASET_PERMISSIONS": {
            "can_view_basic_dataset_settings": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_basic_dataset_settings": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_download_dataset": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_download_dataset": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_upload_dataset": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_upload_dataset": [User.ORGANIZATION_OWNER, User.WORKSPACE_MANAGER],
            "can_view_delete_data_item": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_delete_data_item": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_view_deduplicate_data_items": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
            "can_use_deduplicate_data_items": [
                User.ORGANIZATION_OWNER,
                User.WORKSPACE_MANAGER,
            ],
        },
    }


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
    permission_json = models.JSONField(
        verbose_name="permission json",
        null=True,
        blank=True,
        default=default_permissions,
        help_text=("Permissions for user role"),
    )

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
    def send_invite_email(cls, invite, user):
        current_environment = os.getenv("ENV")
        base_url = (
            "dev.shoonya.ai4bharat.org"
            if current_environment == "dev"
            else "shoonya.ai4bharat.org"
        )
        subject = "Invitation to join Organization"
        invite_link = f"https://{base_url}/#/invite/{invite.invite_code}"
        text_content = f"Hello! You are invited to Shoonya. Your Invite link is: "
        style_string = """
        *{ margin: 0; 
        padding: 0;
        }
        body {
        font-family: "Arial", sans-serif;
        background-color: #f2f8f8;
        margin: 0;
        padding: 0;
        padding-top: 2rem;
        }
        .container {
        background-color: #fff;
        border: solid 1px #e1e1e1;
        border-radius: 2px;
        padding: 1.4rem;
        max-width: 380px;
        margin: auto;
        }
        .header {
        width: fit-content;
        margin: auto;
        }
        h1 {
        font-size: 1.2rem;
        font-weight: 300;
        margin: 1rem 0;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        }
        p {
        font-size: 0.9rem;
        color: #222;
        margin: 0.8rem 0;
        }
        .primary {
        color: #18621f;
        }
        .footer {
        margin-top: 1rem;
        font-size: 0.9rem;
        }
        .footer > * {
        font-size: inherit;
        }"""

        html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Invitation to join Shoonya Organisation</title>
            <style>
            {style_string}
            </style>
            </head>
            <body>
            <div class="container">
            <header class="header">
            <h3>Invitaiton to join Shoonya</h3>
            </header>
            <main>
            <div style="margin: 1rem auto; width: fit-content">
            <table
            width="180"
            border="0"
            align="center"
            cellpadding="0"
            cellspacing="0"
            >
            <tbody>
            <tr>

            <td
            style="
            font-size: 12px;
            font-family: 'Zurich BT', Tahoma, Helvetica, Arial;
            text-align: center;
            color: white;
            border-radius: 1rem;
            border-width: 1px;
            background-color: rgb(44, 39, 153);

            ">
            <a target="_blank" style="text-decoration: none; color:white; font-size: 14px; display: block; padding: 0.2rem 0.5rem; " href="{invite_link}">
            Join Shoonya Now
            </a>
            </td>
            </tr>
            </tbody>
            </table>
            </div>
            <div>
            <p>
            Please use the above link to verify your email address and complete your registration.
            </p>
            <p style="font-style: italic">
            For security purposes, please do not share the this link with
            anyone.
            </p>
            <p style="font-size: 10px; color:grey">
                If clicking the link doesn't work, you can copy and paste the link into your browser's address window, or retype it there.
                <a href="{invite_link}">{invite_link}</a>
            </p>
            </div>
            </main>
            <footer class="footer">
            <p>
            Best Regards,<br />
            Shoonya Team
            </p>
            </footer>
            </div>
            </body>
            </html>
        """
        msg = EmailMultiAlternatives(
            subject, text_content, settings.DEFAULT_FROM_EMAIL, [user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

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
                cls.send_invite_email(invite, user)

    # def has_permission(self, user):
    #     if self.organization.created_by.pk == user.pk or user.is_superuser:
    #         return True
    #     return False

    @classmethod
    def re_invite(cls, users=None):
        with transaction.atomic():
            for user in users:
                invite = Invite.objects.get(user=user)
                cls.send_invite_email(invite, user)

    @classmethod
    def generate_invite_code(cls):
        return "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for i in range(10)
        )
