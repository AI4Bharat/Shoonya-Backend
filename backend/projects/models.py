from django.conf import settings
from django.db import models

# Create your models here.
class Project(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=250)
    created_by = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="project_creator",
        verbose_name="created_by",
    )
    is_archived = models.BooleanField(
        verbose_name="project_is_archived",
        default=False,
        help_text=("Designates wheather a project is archieved or not."),
    )
    is_published = models.BooleanField(
        verbose_name="project_is_published",
        default=False,
        help_text=("Designates wheather a project is published or not."),
    )
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="project_users")

    def __str__(self):
        return self.title
