from django.conf import settings
from django.db import models
from users.models import User
from organizations.models import Organization
from workspaces.models import Workspace
from dataset.models import DatasetInstance

# from dataset import LANG_CHOICES

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
    ("ContextualTranslationEditing", "ContextualTranslationEditing"),
    ("OCRAnnotation", "OCRAnnotation"),
    ("MonolingualCollection", "MonolingualCollection"),
    ("SentenceSplitting", "SentenceSplitting"),
)

Collection = "Collection"
Annotation = "Annotation"

PROJECT_MODE_CHOICES = ((Collection, "Collection"), (Annotation, "Annotation"))


# Create your models here.
class Project(models.Model):
    """
    Model definition for Project Management
    """

    title = models.CharField(max_length=100, help_text=("Project Title"))
    description = models.TextField(max_length=1000, null=True, blank=True, help_text=("Project Description"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="project_creator",
        verbose_name="created_by",
        help_text=("Project Created By")
    )

    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="project_users", help_text=("Project Users"))
    organization_id = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, help_text=("Organization to which the Project belongs"))
    workspace_id = models.ForeignKey(Workspace, on_delete=models.SET_NULL, null=True, help_text=("Workspace to which the Project belongs"))
    dataset_id = models.ManyToManyField(DatasetInstance, related_name="project_dataset_instances", blank=True, help_text=("Dataset Instances that are available for project creation"))

    is_archived = models.BooleanField(
        verbose_name="project_is_archived",
        default=False,
        help_text=("Indicates whether a project is archieved or not."),
    )
    is_published = models.BooleanField(
        verbose_name="project_is_published",
        default=False,
        help_text=("Indicates whether a project is published or not."),
    )

    expert_instruction = models.TextField(max_length=500, null=True, blank=True, help_text=("Expert Instruction"))
    show_instruction = models.BooleanField(verbose_name="show_instruction_to_annotator", 
        default=False, help_text=("Show Instruction to Annotator"))
    show_skip_button = models.BooleanField(verbose_name="annotator_can_skip_project", 
        default=False, help_text=("Button to Skip the Project"))
    show_predictions_to_annotator = models.BooleanField(
        verbose_name="annotator_can_see_model_predictions", default=False,
        help_text=("Show Annotation predictions to annotator")
    )

    filter_string = models.CharField(max_length=1000, null=True, blank=True, 
        help_text=("Filter string for filtering data for project"))
    label_config = models.CharField(verbose_name="XML Template Config", max_length=1000, null=True, blank=True, 
        help_text=("Label Studio Config XML to be used to show annotation task UI"))

    color = models.CharField(max_length=6, null=True, blank=True, help_text=("Colour"))

    sampling_mode = models.CharField(choices=SAMPLING_MODE_CHOICES, default=FULL, max_length=1,
        help_text=("Sampling Mode of the dataset for the project - Random, Batch or Full"))

    sampling_parameters_json = models.JSONField(verbose_name="sampling parameters json", null=True, blank=True,
        help_text=("Sampling parameters for the sampling mode - percentage for random and batch number and size for batch"))

    data_type = models.JSONField(verbose_name="data type in project xml", null=True, blank=True,
        help_text=("Data Type in the Project XML"))

    project_type = models.CharField(choices=PROJECT_TYPE_CHOICES, max_length=100,
        help_text=("Project Type indicating the annotation task"))

    project_mode = models.CharField(choices=PROJECT_MODE_CHOICES, max_length=100,
        help_text=("Mode of the Project - Annotation or Collection"))

    variable_parameters = models.JSONField(verbose_name="variable parameters for project", null=True, blank=True,
        help_text=("Variable parameters specific for each project type")) 

    metadata_json = models.JSONField(verbose_name="metadata json", null=True, blank=True,
        help_text=("Metadata for project"))
    # maximum_annotators
    # total_annotations
    required_annotators_per_task = models.IntegerField(verbose_name="required_annotators_per_task", default=1,
        help_text=("No. of annotators required for each task"))
    # language = models.CharField(
    #     verbose_name="language", choices=LANG_CHOICES, max_length=3
    # )

    def __str__(self):
        return str(self.title)
