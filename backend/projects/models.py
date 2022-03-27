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

MonolingualTranslation = 1
TranslationEditing = 2
OCRAnnotation = 3

PROJECT_TYPE_CHOICES = (
    (MonolingualTranslation, "MonolingualTranslation"),
    (TranslationEditing, "TranslationEditing"),
    (OCRAnnotation, "OCRAnnotation")
)

TAB_CHOICES = (
    ("grid", "Grid"),
    ("list", "List")
)

FILTER_CHOICES = (
    ("and", "and"),
    ("or", "or")
)

COLUMN_CHOICES = (
    ("tasks", "tasks"),
    ("annotations", "annotations")
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

    project_type = models.PositiveSmallIntegerField(
        choices=PROJECT_TYPE_CHOICES,
    )

    variable_parameters = models.JSONField(verbose_name="variable parameters for project", null=True, blank=True)

    # maximum_annotators
    # total_annotations
    # lang_id = models.CharField(
    #     verbose_name="language_id", choices=LANG_CHOICES, max_length=3
    # )

    def __str__(self):
        return str(self.title)

class Tab(models.Model):
    """
    Model for tab view in datamanager
    """
    type = models.CharField(
        verbose_name="type_of_view", choices = TAB_CHOICES, max_length=4
    )
    title = models.CharField(max_length=100)
    target = models.CharField(verbose_name="entity_type", choices=TARGET_CHOICES, max_length=15)
    filters = models.ForeignKey(Filter, on_delete=models.CASCADE)
    # ordering = models.ForeignKey(ColumnAlias, on_delete = mmodels.CASCADE)
    selectedItems = models.ForeignKey()
    #columnsDisplayType =
    #columnsWidth =
    #hiddenColumns =

class Filter(models.Model):
    conjunction = models.CharField(
        verbose_name = "joining_two_filters", choices = FILTER_CHOICES, max_length=3
    )
    items = models.ForeignKey(FilterItem, on_delete=models.CASCADE)

class FilterItem(models.Model):
    #filter = 
    type = models.ForeignKey(ColumnType, on_delete=models.CASCADE)
    operator = models.ForeignKey(FilterOperator, on_delete=models.CASCADE)
    value = models.CharField(max_length=50)

class FilterOperator(models.Model):
    equal = models.CharField(max_length=50)
    not_equal = models.CharField(max_length=50)
    contains = models.CharField(max_length=50)
    not_contains = models.CharField(max_length=50)
    less = models.FloatField()
    greater = models.FloatField()
    less_or_equal = models.FloatField()
    greater_or_equal = models.FloatField()
    in = models.CharField(max_length=50)
    not_in = models.CharField(max_length=50)
    empty = models.BooleanField()

class Column(models.Model):
    parent = models.CharField(max_length=50, null=True)
    target = models.CharField(choices = COLUMN_CHOICES, max_length=50)
    title = models.CharField(max_length=50)
    type = models.ForeignKey(ColumnType, on_delete=models.CASCADE)
    children = models.CharField(max_length=50, null=True)
    #visibility_defaults = 

class ColumnType(models.Model):
    string = models.CharField(max_length=50)
    boolean = models.BooleanField()
    number = models.FloatField()
    datetime = models.datetime()
    #list
    image = models.CharField(max_length=200)
    audio = models.CharField(max_length=200)
    audioplus = models.CharField(max_length=200)
    text = models.TextField()
    hypertext = models.TextField()
    timeseries = models.CharField(max_length=200)
    unknown = models.CharField(max_length=200)