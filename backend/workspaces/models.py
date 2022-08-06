from django.db import models
from organizations.models import Organization
from shoonya_backend.mixins import DummyModelMixin

from shoonya_backend import settings

# Create your models here.


class Workspace(models.Model, DummyModelMixin):
    """
    Workspace model.
    """

    organization = models.ForeignKey(
        Organization, related_name="organization_workspace", on_delete=models.CASCADE
    )

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="organization_users"
    )

    workspace_name = models.CharField(
        verbose_name="workspace_name", max_length=256, null=False
    )

    is_archived = models.BooleanField(verbose_name="is_archived", default=False)

    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="managers",
        related_name="workspace_managers",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="created_by",
        related_name="workspace_created_by",
        on_delete=models.SET_NULL,
        null=True,
    )

    created_at = models.DateTimeField(verbose_name="created_at", auto_now_add=True)

    def __str__(self):
        return str(self.workspace_name) 

    def has_user(self, user):
        if self.user.filter(pk=user.pk).exists():
            return True
        return False

    # def has_object_permission(self, user):
    #     if self.users.filter(pk=user.pk).exists():
    #         return True
    #     return False

    class Meta:
        ordering = ["pk"]
