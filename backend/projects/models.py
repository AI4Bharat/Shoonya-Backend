from django.conf import settings
from django.db import models
from users.models import User
from organizations.models import Organization
from workspaces.models import Workspace
from dataset.models import DatasetInstance
from .registry_helper import ProjectRegistry
from django.utils.timezone import now
from datetime import datetime, timedelta
from users.models import LANG_CHOICES

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
# OCRTranscription = 3
# OCRTranscriptionEditing = 4
# MonolingualCollection = 5

PROJECT_TYPE_LIST = list(ProjectRegistry.get_instance().project_types.keys())
PROJECT_TYPE_CHOICES = tuple(zip(PROJECT_TYPE_LIST, PROJECT_TYPE_LIST))

Collection = "Collection"
Annotation = "Annotation"

PROJECT_MODE_CHOICES = ((Collection, "Collection"), (Annotation, "Annotation"))

ANNOTATION_STAGE = 1
REVIEW_STAGE = 2
SUPERCHECK_STAGE = 3

PROJECT_STAGE_CHOICES = (
    (ANNOTATION_STAGE, "Annotation Only"),
    (REVIEW_STAGE, "Review Enabled"),
    (SUPERCHECK_STAGE, "Supercheck Enabled"),
)

ANNOTATION_LOCK = "annotation_task_pull_lock"
REVIEW_LOCK = "review_task_pull_lock"
SUPERCHECK_LOCK = "supercheck_task_pull_lock"

LOCK_CONTEXT = (
    (ANNOTATION_LOCK, "annotation_lock"),
    (REVIEW_LOCK, "review_lock"),
    (SUPERCHECK_LOCK, "supercheck_lock"),
)

# List of async functions pertaining to the dataset models
ALLOWED_CELERY_TASKS = [
    "projects.tasks.add_new_data_items_into_project",
    "projects.tasks.create_parameters_for_task_creation",
    "projects.tasks.export_project_in_place",
    "projects.tasks.pull_new_data_items_into_project",
    "projects.tasks.export_project_new_record",
]


# Create your models here.
class Project(models.Model):
    """
    Model definition for Project Management
    """

    title = models.CharField(max_length=100, help_text=("Project Title"))
    description = models.TextField(
        max_length=1000, null=True, blank=True, help_text=("Project Description")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="project_creator",
        verbose_name="created_by",
        help_text=("Project Created By"),
    )

    annotators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="project_users",
        help_text=("Project Users"),
    )
    annotation_reviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="review_projects",
        blank=True,
        help_text=("Project Annotation Reviewers"),
    )
    review_supercheckers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="supercheck_reviewed_projects",
        blank=True,
        help_text=("Project Review Super Checkers"),
    )
    frozen_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="frozen_project_users",
        blank=True,
        help_text=("Frozen Project Users"),
    )
    organization_id = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        help_text=("Organization to which the Project belongs"),
    )
    workspace_id = models.ForeignKey(
        Workspace,
        on_delete=models.SET_NULL,
        null=True,
        help_text=("Workspace to which the Project belongs"),
    )
    dataset_id = models.ManyToManyField(
        DatasetInstance,
        related_name="project_dataset_instances",
        blank=True,
        help_text=("Dataset Instances that are available for project creation"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text=("Project Created At")
    )
    published_at = models.DateTimeField(
        help_text=("Project published at"), null=True, blank=True
    )
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
    expert_instruction = models.TextField(
        max_length=500, null=True, blank=True, help_text=("Expert Instruction")
    )
    show_instruction = models.BooleanField(
        verbose_name="show_instruction_to_annotator",
        default=False,
        help_text=("Show Instruction to Annotator"),
    )
    show_skip_button = models.BooleanField(
        verbose_name="annotator_can_skip_project",
        default=False,
        help_text=("Button to Skip the Project"),
    )
    show_predictions_to_annotator = models.BooleanField(
        verbose_name="annotator_can_see_model_predictions",
        default=False,
        help_text=("Show Annotation predictions to annotator"),
    )

    filter_string = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text=("Filter string for filtering data for project"),
    )
    label_config = models.TextField(
        verbose_name="XML Template Config",
        null=True,
        blank=True,
        help_text=("Label Studio Config XML to be used to show annotation task UI"),
    )

    color = models.CharField(max_length=6, null=True, blank=True, help_text=("Colour"))

    sampling_mode = models.CharField(
        choices=SAMPLING_MODE_CHOICES,
        default=FULL,
        max_length=1,
        help_text=(
            "Sampling Mode of the dataset for the project - Random, Batch or Full"
        ),
    )

    sampling_parameters_json = models.JSONField(
        verbose_name="sampling parameters json",
        null=True,
        blank=True,
        help_text=(
            "Sampling parameters for the sampling mode - percentage for random and batch number and size for batch"
        ),
    )

    data_type = models.JSONField(
        verbose_name="data type in project xml",
        null=True,
        blank=True,
        help_text=("Data Type in the Project XML"),
    )

    project_type = models.CharField(
        choices=PROJECT_TYPE_CHOICES,
        max_length=100,
        help_text=("Project Type indicating the annotation task"),
    )

    project_mode = models.CharField(
        choices=PROJECT_MODE_CHOICES,
        max_length=100,
        help_text=("Mode of the Project - Annotation or Collection"),
    )

    variable_parameters = models.JSONField(
        verbose_name="variable parameters for project",
        null=True,
        blank=True,
        help_text=("Variable parameters specific for each project type"),
    )

    metadata_json = models.JSONField(
        verbose_name="metadata json",
        null=True,
        blank=True,
        help_text=("Metadata for project"),
    )
    # maximum_annotators
    # total_annotations
    required_annotators_per_task = models.IntegerField(
        verbose_name="required_annotators_per_task",
        default=1,
        help_text=("No. of annotators required for each task"),
    )
    # language = models.CharField(
    #     verbose_name="language", choices=LANG_CHOICES, max_length=3
    # )
    tasks_pull_count_per_batch = models.IntegerField(
        verbose_name="tasks_pull_count_per_batch",
        default=10,
        help_text=("Maximum no. of new tasks that can be assigned to a user at once"),
    )

    max_pending_tasks_per_user = models.IntegerField(
        verbose_name="max_pending_tasks_per_user",
        default=60,
        help_text=(
            "Maximum no. of tasks assigned to a user which are at unlabeled stage, as a threshold for pulling new tasks"
        ),
    )

    # enable_task_reviews = models.BooleanField(
    #     verbose_name="enable_task_reviews",
    #     default=False,
    #     help_text=("Indicates whether the annotations need to be reviewed"),
    # )

    project_stage = models.PositiveSmallIntegerField(
        choices=PROJECT_STAGE_CHOICES, blank=False, null=False, default=ANNOTATION_STAGE
    )

    k_value = models.IntegerField(
        verbose_name="Superchecking K% Value",
        default=100,
        help_text=(
            "This will be used to pull k percent of tasks in a project for super-check"
        ),
    )

    revision_loop_count = models.IntegerField(
        verbose_name="revision loop count",
        default=3,
        help_text=(
            "This will be used to keep track of the rejected/ reviewed-back loop count in Super check."
        ),
    )

    def clear_expired_lock(self):
        self.lock.filter(expires_at__lt=now()).delete()

    def release_lock(self, context):
        self.lock.filter(lock_context=context).delete()

    def is_locked(self, context):
        self.clear_expired_lock()
        return (
            self.lock.filter(lock_context=context).filter(expires_at__gt=now()).count()
        )

    def set_lock(self, annotator, context):
        """
        Locks the project for an annotator
        """
        if not self.is_locked(context):
            ProjectTaskRequestLock.objects.create(
                project=self,
                user=annotator,
                lock_context=context,
                expires_at=now() + timedelta(seconds=settings.PROJECT_LOCK_TTL),
            )
        else:
            raise Exception("Project already locked")

    src_language = models.CharField(
        choices=LANG_CHOICES,
        null=True,
        blank=True,
        max_length=50,
        help_text=("Source language of the project"),
        verbose_name="Source Language",
    )
    tgt_language = models.CharField(
        choices=LANG_CHOICES,
        null=True,
        blank=True,
        max_length=50,
        help_text=("Target language of the project"),
        verbose_name="Target Language",
    )

    def __str__(self):
        return str(self.title)


class ProjectTaskRequestLock(models.Model):
    """
    Basic database lock implementation to handle
    concurrency in tasks pull requests for same project
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="lock",
        help_text="Project locked for task pulling",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_lock",
        help_text="User locking this project to pull tasks",
    )
    lock_context = models.CharField(
        choices=LOCK_CONTEXT,
        max_length=50,
        default=ANNOTATION_LOCK,
        verbose_name="lock_context",
    )
    expires_at = models.DateTimeField("expires_at")
