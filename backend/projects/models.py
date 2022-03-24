from django.conf import settings
from django.db import models
from users.models import User
from organizations.models import Organization
from workspaces.models import Workspace
from dataset.models import DatasetInstance

RANDOM = "r"
BATCH = "b"
FULL = "f"

SAMPLING_MODE_CHOICES = (
    (RANDOM, "Random"),
    (BATCH, "Batch"),
    (FULL, "Full"),
)

MonolingualTranslation = 1
TranslationEditing = 2
OCRAnnotation = 3

PROJECT_TYPE_CHOICES = (
    (MonolingualTranslation, "MonolingualTranslation"),
    (TranslationEditing, "TranslationEditing"),
    (OCRAnnotation, "OCRAnnotation")
)


# Create your models here.
class Project(models.Model):
    """
    Model definition for Project Management
    """

    title = models.CharField(max_length=100)
    description = models.TextField(max_length=250)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="project_creator",
        verbose_name="created_by",
    )

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="project_users"
    )
    organization_id = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True
    )
    workspace_id = models.ForeignKey(Workspace, on_delete=models.SET_NULL, null=True)
    dataset_id = models.ManyToManyField(
        DatasetInstance,
        related_name="project_dataset_instances",
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

    expert_instruction = models.TextField(max_length=500, null=True)
    show_instruction = models.BooleanField(
        verbose_name="show_instruction_to_annotator", default=False
    )
    show_skip_button = models.BooleanField(
        verbose_name="annotator_can_skip_project", default=False
    )
    show_predictions_to_annotator = models.BooleanField(
        verbose_name="annotator_can_see_model_predictions", default=False
    )
    maximum_annotators = models.IntegerField
    total_annotation = models.IntegerField
    filter_string = models.CharField(max_length=1000, null=True)
    label_config = models.CharField(
        verbose_name="XML Template Config", max_length=1000, null=True
    )

    color = models.CharField(max_length=6, null=True)

    sampling_mode = models.CharField(
        choices=SAMPLING_MODE_CHOICES,
        blank=False,
        null=False,
        default=FULL,
        max_length=1,
    )

    sampling_parameters_json = models.JSONField(
        verbose_name="sampling parameters json", null=True
    )

    data_type = models.JSONField(verbose_name="data type in project xml", null=True)

    project_type = models.PositiveSmallIntegerField(
        choices=PROJECT_TYPE_CHOICES, blank=False, null=False
    )

    def __str__(self):
        return str(self.title)
