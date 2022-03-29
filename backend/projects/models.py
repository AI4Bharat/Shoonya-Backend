from django.conf import settings
from django.db import models
from users.models import User
from organizations.models import Organization
from workspaces.models import Workspace
from dataset.models import DatasetInstance
#from dataset import LANG_CHOICES

RANDOM = "r"
BATCH = "b"
FULL = "f"

SAMPLING_MODE_CHOICES = (
    (RANDOM, "Random"),
    (BATCH, "Batch"),
    (FULL, "Full"),
)

# DEPRECIATED: Using numbers for project types
# MonolingualTranslation = 1
# TranslationEditing = 2
# OCRAnnotation = 3
# MonolingualCollection = 4

PROJECT_TYPE_CHOICES = (
    ("MonolingualTranslation", "MonolingualTranslation"),
    ("TranslationEditing", "TranslationEditing"),
    ("OCRAnnotation", "OCRAnnotation"),
    ("MonolingualCollection", "MonolingualCollection"),
    ("SentenceSplitting", "SentenceSplitting"),
)

Collection = "Collection"
Annotation = "Annotation"

PROJECT_MODE_CHOICES = (
    (Collection, "Collection"),
    (Annotation, "Annotation")
)


# Create your models here.
class Project(models.Model):
    """
    Model definition for Project Management
    """

    title = models.CharField(max_length=100)
    description = models.TextField(max_length=1000, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
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
        null=True, blank=True
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

    expert_instruction = models.TextField(max_length=500, null=True, blank=True)
    show_instruction = models.BooleanField(
        verbose_name="show_instruction_to_annotator", default=False
    )
    show_skip_button = models.BooleanField(
        verbose_name="annotator_can_skip_project", default=False
    )
    show_predictions_to_annotator = models.BooleanField(
        verbose_name="annotator_can_see_model_predictions", default=False
    )

    filter_string = models.CharField(max_length=1000, null=True, blank=True)
    label_config = models.CharField(
        verbose_name="XML Template Config", max_length=1000, null=True, blank=True
    )

    color = models.CharField(max_length=6, null=True, blank=True)

    sampling_mode = models.CharField(
        choices=SAMPLING_MODE_CHOICES,
        default=FULL,
        max_length=1,
    )

    sampling_parameters_json = models.JSONField(
        verbose_name="sampling parameters json", null=True, blank=True
    )

    data_type = models.JSONField(verbose_name="data type in project xml", null=True, blank=True)

    project_type = models.CharField(
        choices=PROJECT_TYPE_CHOICES, max_length=100,
    )

    project_mode = models.CharField(
        choices=PROJECT_MODE_CHOICES, max_length=100,
    )

    variable_parameters = models.JSONField(verbose_name="variable parameters for project", null=True, blank=True)

    metadata_json = models.JSONField(
        verbose_name="metadata json", null=True, blank=True
    )
    # maximum_annotators
    # total_annotations
    # lang_id = models.CharField(
    #     verbose_name="language_id", choices=LANG_CHOICES, max_length=3
    # )

    def __str__(self):
        return str(self.title)
