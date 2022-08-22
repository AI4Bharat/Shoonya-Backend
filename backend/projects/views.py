import re
from collections import OrderedDict
from datetime import datetime
from time import sleep

from django.core.files import File
from django.db.models import Count, Q
from django.forms.models import model_to_dict
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import LANG_CHOICES
from users.serializers import UserEmailSerializer
from dataset.serializers import TaskResultSerializer

from utils.search import process_search_query

from dataset import models as dataset_models
from django_celery_results.models import TaskResult
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from users.models import User

from projects.serializers import ProjectSerializer, ProjectUsersSerializer
from tasks.models import Annotation as Annotation_model
from tasks.models import *
from tasks.models import Task
from tasks.serializers import TaskSerializer
from .models import *
from .registry_helper import ProjectRegistry
from dataset.models import DatasetInstance

# Import celery tasks
from .tasks import (
    create_parameters_for_task_creation,
    add_new_data_items_into_project,
    export_project_in_place,
    export_project_new_record,
    filter_data_items,
)

from .decorators import (
    is_organization_owner_or_workspace_manager,
    is_project_editor,
    project_is_archived,
    project_is_published,
)
from .utils import is_valid_date, no_of_words

from workspaces.decorators import is_particular_workspace_manager

# Create your views here.

EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

PROJECT_IS_PUBLISHED_ERROR = {"message": "This project is already published!"}


def get_task_field(annotation_json, field):
    return annotation_json[field]


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx : min(ndx + n, l)]


def get_review_reports(proj_id, userid, start_date, end_date):

    user = User.objects.get(id=userid)
    userName = user.username

    total_tasks = Task.objects.filter(project_id=proj_id, review_user=userid)

    total_task_count = total_tasks.count()

    accepted_tasks = Task.objects.filter(
        project_id=proj_id, review_user=userid, task_status="accepted"
    )

    accepted_tasks_objs_ids = list(accepted_tasks.values_list("id", flat=True))
    accepted_objs = Annotation_model.objects.filter(
        task_id__in=accepted_tasks_objs_ids,
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    accepted_objs_count = accepted_objs.count()

    acceptedwtchange_tasks = Task.objects.filter(
        project_id=proj_id, review_user=userid, task_status="accepted_with_changes"
    )

    acceptedwtchange_tasks_objs_ids = list(
        acceptedwtchange_tasks.values_list("id", flat=True)
    )
    acceptedwtchange_objs = Annotation_model.objects.filter(
        task_id__in=acceptedwtchange_tasks_objs_ids,
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    acceptedwtchange_objs_count = acceptedwtchange_objs.count()

    labeled_tasks = Task.objects.filter(
        project_id=proj_id, review_user=userid, task_status="labeled"
    )
    labeled_tasks_count = labeled_tasks.count()

    to_be_revised_tasks = Task.objects.filter(
        project_id=proj_id, review_user=userid, task_status="to_be_revised"
    )
    to_be_revised_tasks_count = to_be_revised_tasks.count()

    result = {
        "Reviewer Name": userName,
        "Assigned Tasks": total_task_count,
        "Accepted Tasks": accepted_objs_count,
        "Accepted With Changes Tasks": acceptedwtchange_objs_count,
        "Labeled Tasks": labeled_tasks_count,
        "To Be Revised Tasks": to_be_revised_tasks_count,
    }
    return result


def extract_latest_status_date_time_from_taskresult_queryset(taskresult_queryset):
    """Function to extract the latest status and date time from the celery task results.

    Args:
        taskresult_queryset (Django Queryset): Celery task results queryset

    Returns:
        str: Complettion state of the latest celery task
        str: Complettion date of the latest celery task
        str: Complettion time of the latest celery task
    """

    # Sort the tasks by newest items first by date
    taskresult_queryset = taskresult_queryset.order_by("-date_done")

    # Get the export task status and last update date
    task_status = taskresult_queryset.first().as_dict()["status"]
    task_datetime = taskresult_queryset.first().as_dict()["date_done"]

    # Extract date and time from the datetime object
    task_date = task_datetime.date()
    task_time = f"{str(task_datetime.time().replace(microsecond=0))} UTC"

    return task_status, task_date, task_time


def get_project_pull_status(pk):
    """Function to return status of the last pull data items task.

    Args:
        pk (int): Primary key of the project

    Returns:
        str: Status of the project export
        str: Date when the last time project was exported
    """

    # Create the keyword argument for project ID
    project_id_keyword_arg = "'project_id': " + "'" + str(pk) + "'"

    # Check the celery project export status
    taskresult_queryset = TaskResult.objects.filter(
        task_name="projects.tasks.add_new_data_items_into_project",
        task_kwargs__contains=project_id_keyword_arg,
    )

    # If the celery TaskResults table returns
    if taskresult_queryset:

        # Sort the tasks by newest items first by date
        taskresult_queryset = taskresult_queryset.order_by("-date_done")

        # Get the export task status and last update date
        task_status = taskresult_queryset.first().as_dict()["status"]
        task_datetime = taskresult_queryset.first().as_dict()["date_done"]
        task_result = taskresult_queryset.first().as_dict()["result"]

        if '"' in task_result:
            task_result = task_result.strip('"')

        # Extract date and time from the datetime object
        task_date = task_datetime.date()
        task_time = f"{str(task_datetime.time().replace(microsecond=0))} UTC"

        return task_status, task_date, task_time, task_result

    return (
        "Success",
        "Synchronously Completed. No Date.",
        "Synchronously Completed. No Time.",
        "No result.",
    )


def get_project_export_status(pk):
    """Function to return status of the project export background task.

    Args:
        pk (int): Primary key of the project

    Returns:
        str: Status of the project export
        str: Date when the last time project was exported
    """

    # Create the keyword argument for project ID
    project_id_keyword_arg = "'project_id': " + "'" + str(pk) + "'" + ","

    # Check the celery project export status
    taskresult_queryset = TaskResult.objects.filter(
        task_name__in=[
            "projects.tasks.export_project_in_place",
            "projects.tasks.export_project_new_record",
        ],
        task_kwargs__contains=project_id_keyword_arg,
    )

    # If the celery TaskResults table returns
    if taskresult_queryset:

        return extract_latest_status_date_time_from_taskresult_queryset(
            taskresult_queryset
        )
    return (
        "Success",
        "Synchronously Completed. No Date.",
        "Synchronously Completed. No Time.",
    )


def get_project_creation_status(pk) -> str:
    # sourcery skip: use-named-expression
    """Function to return the status of the project that is queried.

    Args:
        pk (int): The primary key of the project

    Returns:
        str: Project Status
    """

    # Get the project object
    project = Project.objects.get(pk=pk)

    # Create the keyword argument for project ID
    project_id_keyword_arg = "'project_id': " + str(pk) + "}"

    # Check the celery task creation status
    taskresult_queryset = TaskResult.objects.filter(
        task_name="projects.tasks.create_parameters_for_task_creation",
        task_kwargs__contains=project_id_keyword_arg,
    )

    # If the celery TaskResults table returns
    if taskresult_queryset:
        task_creation_status = taskresult_queryset.first().as_dict()["status"]

        # Check if the task has failed
        if task_creation_status == "FAILURE":
            return "Task Creation Process Failed!"

        if task_creation_status != "SUCCESS":
            return "Creating Annotation Tasks."

    # If the background task function has already run, check the status of the project
    if project.is_archived:
        return "Archived"
    elif project.is_published:
        return "Published"
    else:
        return "Draft"


def get_task_count(pk, status):
    project = Project.objects.get(pk=pk)
    tasks = (
        Task.objects.filter(project_id=pk)
        .filter(task_status=status)
        .annotate(annotator_count=Count("annotation_users"))
    )
    task_count = tasks.filter(
        annotator_count__lt=project.required_annotators_per_task
    ).count()
    return task_count


def get_tasks_count(pk, annotator, status, return_task_count=True):
    Task_objs = Task.objects.filter(
        project_id=pk, annotation_users=annotator, task_status=status
    )
    if return_task_count == True:
        Task_objs_count = Task_objs.count()
        return Task_objs_count
    else:
        return Task_objs


def get_annotated_tasks(pk, annotator, status, start_date, end_date):
    annotated_tasks_objs = get_tasks_count(
        pk, annotator, status, return_task_count=False
    )
    annotated_tasks_objs_ids = list(annotated_tasks_objs.values_list("id", flat=True))
    annotated_objs = Annotation_model.objects.filter(
        task_id__in=annotated_tasks_objs_ids,
        parent_annotation_id=None,
        created_at__range=[start_date, end_date],
        completed_by=annotator,
    )
    return annotated_objs


class ProjectViewSet(viewsets.ModelViewSet):
    """
    Project ViewSet
    """

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticated,)

    def retrieve(self, request, pk, *args, **kwargs):
        """
        Retrieves a project given its ID
        """
        project_response = super().retrieve(request, *args, **kwargs)

        datasets = (
            DatasetInstance.objects.only("instance_id", "instance_name")
            .filter(instance_id__in=project_response.data["dataset_id"])
            .values("instance_id", "instance_name")
        )
        project_response.data["datasets"] = datasets
        project_response.data.pop("dataset_id")

        # Add a new field to the project response to indicate project status
        project_response.data["status"] = get_project_creation_status(pk)

        # Add a new field to the project to indicate the async project export status and last export date
        (
            project_export_status,
            last_project_export_date,
            last_project_export_time,
        ) = get_project_export_status(pk)
        project_response.data["last_project_export_status"] = project_export_status
        project_response.data["last_project_export_date"] = last_project_export_date
        project_response.data["last_project_export_time"] = last_project_export_time

        # Add the details about the last data pull
        (
            last_pull_status,
            last_pull_date,
            last_project_export_time,
            last_project_export_result,
        ) = get_project_pull_status(pk)
        project_response.data["last_pull_status"] = last_pull_status
        project_response.data["last_pull_date"] = last_pull_date
        project_response.data["last_pull_time"] = last_project_export_time
        project_response.data["last_pull_result"] = last_project_export_result

        # Add a field to specify the no. of available tasks to be assigned
        project_response.data["unassigned_task_count"] = get_task_count(pk, UNLABELED)

        # Add a field to specify the no. of labeled tasks
        project_response.data["labeled_task_count"] = (
            Task.objects.filter(project_id=pk)
            .filter(task_status=LABELED)
            .filter(review_user__isnull=True)
            .exclude(annotation_users=request.user.id)
            .count()
        )

        return project_response

    def list(self, request, *args, **kwargs):
        """
        List all Projects
        """
        try:
            # projects = self.queryset.filter(annotators=request.user)

            if request.user.role == User.ORGANIZATION_OWNER:
                projects = self.queryset.filter(
                    organization_id=request.user.organization
                )
            else:
                projects = self.queryset.filter(
                    annotators=request.user
                ) | self.queryset.filter(annotation_reviewers=request.user)
                projects = projects.distinct()
            projects_json = self.serializer_class(projects, many=True)
            return Response(projects_json.data, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"message": "Please Login!"}, status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        method="post",
        request_body=UserEmailSerializer,
        responses={
            201: "User removed",
            404: "User does not exist",
            500: "Server error occured",
        },
    )
    @is_project_editor
    @action(detail=True, methods=["post"], url_name="remove")
    # TODO: Refactor code to handle better role access
    def remove_annotator(self, request, pk=None):
        user = User.objects.filter(email=request.data["email"]).first()
        if not user:
            return Response(
                {"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        project = Project.objects.filter(pk=pk).first()
        if not project:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        if project.frozen_users.filter(id=user.id).exists():
            return Response(
                {"message": "User is already frozen in this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tasks = Task.objects.filter(
            Q(project_id=project.id) & Q(annotation_users__in=[user])
        ).filter(Q(task_status="unlabeled") | Q(task_status="draft"))

        Annotation_model.objects.filter(
            Q(completed_by=user) & Q(task__task_status="draft")
        ).delete()  # delete all draft annotations by the user

        for task in tasks:
            task.annotation_users.remove(user)

        tasks.update(task_status="unlabeled")  # unassign user from tasks

        project.frozen_users.add(user)

        return Response({"message": "User removed"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_name="remove_reviewer")
    def remove_reviewer(self, request, pk=None):
        user_id = request.data.get("id")
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(
                {"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        project = Project.objects.filter(pk=pk).first()
        if not project:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        if project.frozen_users.filter(id=user.id).exists():
            return Response(
                {"message": "User is already frozen in this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tasks = (
            Task.objects.filter(project_id=project.id)
            .filter(review_user=user)
            .exclude(task_status__in=[ACCEPTED, TO_BE_REVISED])
        )
        for task in tasks:
            task.review_user = None
            task.save()

        project.frozen_users.add(user)
        project.save()
        return Response({"message": "User removed"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        manual_parameters=[
            openapi.Parameter(
                "task_status",
                openapi.IN_QUERY,
                description=("A string that denotes the status of task"),
                type=openapi.TYPE_STRING,
                enum=[task_status[0] for task_status in TASK_STATUS],
                required=False,
            ),
            openapi.Parameter(
                "current_task_id",
                openapi.IN_QUERY,
                description=("The unique id identifying the current task"),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={},
        ),
        responses={
            201: TaskSerializer,
            204: "No more tasks available! or No more unlabeled tasks!",
        },
    )
    @action(detail=True, methods=["post"], url_path="next")
    def next(self, request, pk):
        """
        Fetch the next task for the user(annotation or review)
        """
        project = Project.objects.get(pk=pk)
        user_role = request.user.role

        # Check if the endpoint is being accessed in review mode
        is_review_mode = (
            "mode" in dict(request.query_params)
            and request.query_params["mode"] == "review"
        )
        if is_review_mode:
            if not project.enable_task_reviews:
                resp_dict = {"message": "Task reviews are not enabled for this project"}
                return Response(resp_dict, status=status.HTTP_403_FORBIDDEN)

        # Check if task_status is passed
        if "task_status" in dict(request.query_params):

            if (
                request.user in project.annotation_reviewers.all()
                or request.user in project.users.all()
            ):
                # Filter Tasks based on whether the request is in review mode or not
                queryset = (
                    Task.objects.filter(
                        project_id__exact=project.id,
                        review_user=request.user.id,
                        task_status=request.query_params["task_status"],
                    )
                    if is_review_mode
                    else Task.objects.filter(
                        project_id__exact=project.id,
                        annotation_users=request.user.id,
                        task_status=request.query_params["task_status"],
                    )
                )
            else:
                # TODO : Refactor code to reduce DB calls
                queryset = Task.objects.filter(
                    task_status=request.query_params["task_status"]
                )

            queryset = queryset.filter(
                **process_search_query(
                    request.GET, "data", list(queryset.first().data.keys())
                )
            )

            queryset = queryset.order_by("id")

            if "current_task_id" in dict(request.query_params):
                current_task_id = request.query_params["current_task_id"]
                queryset = queryset.filter(id__gt=current_task_id)

            for task in queryset:
                if not task.is_locked(request.user):
                    task.set_lock(request.user)
                    task_dict = TaskSerializer(task, many=False).data
                    return Response(task_dict)

            ret_dict = {"message": "No more tasks available!"}
            ret_status = status.HTTP_204_NO_CONTENT
            return Response(ret_dict, status=ret_status)

        else:
            # Check if there are unattended tasks
            if user_role == 1 and not request.user.is_superuser:
                # Filter Tasks based on whether the request is in review mode or not
                unattended_tasks = (
                    Task.objects.filter(
                        project_id__exact=project.id,
                        review_user=request.user.id,
                        task_status__exact=LABELED,
                    )
                    if is_review_mode
                    else Task.objects.filter(
                        project_id__exact=project.id,
                        annotation_users=request.user.id,
                        task_status__exact=UNLABELED,
                    )
                )
            else:
                # TODO : Refactor code to reduce DB calls
                # Filter Tasks based on whether the request is in review mode or not
                unattended_tasks = (
                    Task.objects.filter(
                        project_id__exact=project.id,
                        task_status__exact=LABELED,
                    )
                    if is_review_mode
                    else Task.objects.filter(
                        project_id__exact=project.id,
                        task_status__exact=UNLABELED,
                    )
                )

            unattended_tasks = unattended_tasks.order_by("id")

            if "current_task_id" in dict(request.query_params):
                current_task_id = request.query_params["current_task_id"]
                unattended_tasks = unattended_tasks.filter(id__gt=current_task_id)

            for task in unattended_tasks:
                if not task.is_locked(request.user):
                    task.set_lock(request.user)
                    task_dict = TaskSerializer(task, many=False).data
                    return Response(task_dict)

            ret_dict = {"message": "No more unlabeled tasks!"}
            ret_status = status.HTTP_204_NO_CONTENT
            return Response(ret_dict, status=ret_status)

    @is_organization_owner_or_workspace_manager
    def create(self, request, *args, **kwargs):
        """
        Creates a project

        Authenticated only for organization owner or workspace manager
        """
        # Read project details from api request
        project_type = request.data.get("project_type")
        project_mode = request.data.get("project_mode")

        if project_mode == Collection:

            # Create project object
            project_response = super().create(request, *args, **kwargs)

        else:

            # Collect the POST request parameters
            dataset_instance_ids = request.data.get("dataset_id")
            if type(dataset_instance_ids) != list:
                dataset_instance_ids = [dataset_instance_ids]
            filter_string = request.data.get("filter_string")
            sampling_mode = request.data.get("sampling_mode")
            sampling_parameters = request.data.get("sampling_parameters_json")
            variable_parameters = request.data.get("variable_parameters")

            # Create project object
            project_response = super().create(request, *args, **kwargs)
            project_id = project_response.data["id"]

            # Function call to create the paramters for the sampling and filtering of sentences
            create_parameters_for_task_creation.delay(
                project_type=project_type,
                dataset_instance_ids=dataset_instance_ids,
                filter_string=filter_string,
                sampling_mode=sampling_mode,
                sampling_parameters=sampling_parameters,
                variable_parameters=variable_parameters,
                project_id=project_id,
            )

        # Return the project response
        return project_response

    @is_project_editor
    @project_is_archived
    def update(self, request, pk=None, *args, **kwargs):
        """
        Update project details
        """
        return super().update(request, *args, **kwargs)

    @is_project_editor
    @project_is_archived
    def partial_update(self, request, pk=None, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @is_project_editor
    @project_is_published
    def destroy(self, request, pk=None, *args, **kwargs):
        """
        Delete a project
        """
        return super().delete(request, *args, **kwargs)

    # TODO : add exceptions
    @action(detail=True, methods=["POST", "GET"], name="Archive Project")
    @is_project_editor
    def archive(self, request, pk=None, *args, **kwargs):
        """
        Archive a published project
        """
        project = Project.objects.get(pk=pk)
        project.is_archived = not project.is_archived
        project.save()
        return super().retrieve(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["GET"],
        name="Get Project Users",
        url_name="get_project_annotators",
    )
    def get_project_annotators(self, request, pk=None, *args, **kwargs):
        """
        Get the list of annotators in the project
        """
        ret_dict = {}
        ret_status = 0
        try:
            project = Project.objects.get(pk=pk)
            serializer = ProjectUsersSerializer(project, many=False)
            ret_dict = serializer.data
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(
        detail=True,
        methods=["GET"],
        name="Get Tasks of a Project",
        url_name="get_project_tasks",
    )
    @project_is_archived
    def get_project_tasks(self, request, pk=None, *args, **kwargs):
        """
        Get the list of tasks in the project
        """
        ret_dict = {}
        ret_status = 0
        try:
            # role check
            if (
                request.user.role == User.ORGANIZATION_OWNER
                or request.user.role == User.WORKSPACE_MANAGER
                or request.user.is_superuser
            ):
                tasks = Task.objects.filter(project_id=pk).order_by("id")
            elif request.user.role == User.ANNOTATOR:
                tasks = Task.objects.filter(
                    project_id=pk, annotation_users=request.user
                ).order_by("id")
            tasks = tasks.filter(
                **process_search_query(
                    request.GET, "data", list(tasks.first().data.keys())
                )
            )
            serializer = TaskSerializer(tasks, many=True)
            ret_dict = serializer.data
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(
        detail=True,
        methods=["POST"],
        name="Assign new tasks to user",
        url_name="assign_new_tasks",
    )
    def assign_new_tasks(self, request, pk, *args, **kwargs):
        """
        Pull a new batch of unassigned tasks for this project
        and assign to the user
        """
        cur_user = request.user
        project = Project.objects.get(pk=pk)
        if not project.is_published:
            return Response(
                {"message": "This project is not yet published"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProjectUsersSerializer(project, many=False)
        annotators = serializer.data["annotators"]
        user_ids = set()
        for annotator in annotators:
            user_ids.add(user["id"])
        # verify if user belongs in project annotators
        if not cur_user.id in user_ids:
            return Response(
                {"message": "You are not assigned to this project"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # check if user has pending tasks
        # the below logic will work only for required_annotators_per_task=1
        # TO-DO Modify and use the commented logic to cover all cases
        pending_tasks = (
            Task.objects.filter(project_id=pk)
            .filter(annotation_users=cur_user.id)
            .filter(task_status__exact=UNLABELED)
            .count()
        )
        # assigned_tasks_queryset = Task.objects.filter(project_id=pk).filter(annotation_users=cur_user.id)
        # assigned_tasks = assigned_tasks_queryset.count()
        # completed_tasks = Annotation_model.objects.filter(task__in=assigned_tasks_queryset).filter(completed_by__exact=cur_user.id).count()
        # pending_tasks = assigned_tasks - completed_tasks
        if pending_tasks >= project.max_pending_tasks_per_user:
            return Response(
                {"message": "Your pending task count is too high"},
                status=status.HTTP_403_FORBIDDEN,
            )
        tasks_to_be_assigned = project.max_pending_tasks_per_user - pending_tasks

        if "num_tasks" in dict(request.data):
            task_pull_count = request.data["num_tasks"]
        else:
            task_pull_count = project.tasks_pull_count_per_batch

        tasks_to_be_assigned = min(tasks_to_be_assigned, task_pull_count)

        lock_set = False
        while lock_set == False:
            if project.is_locked(ANNOTATION_LOCK):
                sleep(settings.PROJECT_LOCK_RETRY_INTERVAL)
                continue
            else:
                try:
                    project.set_lock(cur_user, ANNOTATION_LOCK)
                    lock_set = True
                except Exception as e:
                    continue

        # check if the project contains eligible tasks to pull
        tasks = Task.objects.filter(project_id=pk)
        tasks = tasks.order_by("id")
        tasks = (
            tasks.filter(task_status=UNLABELED)
            .exclude(annotation_users=cur_user.id)
            .annotate(annotator_count=Count("annotation_users"))
        )
        tasks = tasks.filter(annotator_count__lt=project.required_annotators_per_task)
        if not tasks:
            project.release_lock(ANNOTATION_LOCK)
            return Response(
                {"message": "No tasks left for assignment in this project"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # filter out tasks which meet the annotator count threshold
        # and assign the ones with least count to user, so as to maintain uniformity
        tasks = tasks.order_by("annotator_count")[:tasks_to_be_assigned]
        # tasks = tasks.order_by("id")
        for task in tasks:
            task.annotation_users.add(cur_user)
            task.save()

        project.release_lock(ANNOTATION_LOCK)
        return Response(
            {"message": "Tasks assigned successfully"}, status=status.HTTP_200_OK
        )

    @action(
        detail=True, methods=["get"], name="Unassign tasks", url_name="unassign_tasks"
    )
    def unassign_tasks(self, request, pk, *args, **kwargs):
        """
        Unassigns all unlabeled tasks from an annotator.
        """
        user = request.user
        userRole = user.role
        user_obj = User.objects.get(pk=user.id)
        project_id = pk

        if userRole == 1 and not user_obj.is_superuser:
            if project_id:
                tasks = (
                    Task.objects.filter(project_id__exact=project_id)
                    .filter(annotation_users=user.id)
                    .filter(task_status=UNLABELED)
                )
                if tasks.count() > 0:
                    for task in tasks:
                        task.unassign(user_obj)
                    return Response(
                        {"message": "Tasks unassigned"}, status=status.HTTP_200_OK
                    )
                return Response(
                    {"message": "No tasks to unassign"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"message": "Project id not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": "Only annotators can unassign tasks"},
            status=status.HTTP_403_FORBIDDEN,
        )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "from_date": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The start date",
                    format="date",
                ),
                "to_date": openapi.Schema(
                    type=openapi.TYPE_STRING, description="The end date", format="date"
                ),
            },
            required=["from_date", "to_date"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "username": openapi.Schema(type=openapi.TYPE_STRING),
                        "mail": openapi.Schema(
                            type=openapi.TYPE_STRING, format="email"
                        ),
                        "total_annoted_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        "avg_lead_time": openapi.Schema(
                            type=openapi.TYPE_NUMBER, format="float"
                        ),
                        "total_assigned_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        "skipped_tasks": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "total_pending_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                    },
                ),
            ),
            404: "Project does not exist!",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        name="Assign new tasks for review to user",
        url_name="assign_new_review_tasks",
    )
    def assign_new_review_tasks(self, request, pk, *args, **kwargs):
        """
        Pull a new batch of labeled tasks and assign to the reviewer
        """
        cur_user = request.user
        project = Project.objects.get(pk=pk)
        if not project.is_published:
            return Response(
                {"message": "This project is not yet published"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not project.enable_task_reviews:
            return Response(
                {"message": "Task reviews are disabled for this project"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProjectUsersSerializer(project, many=False)
        annotation_reviewers = serializer.data["annotation_reviewers"]
        reviewer_ids = set()
        for annotation_reviewer in annotation_reviewers:
            reviewer_ids.add(annotation_reviewer["id"])
        # verify if user belongs in annotation_reviewers for this project
        if not cur_user.id in reviewer_ids:
            return Response(
                {"message": "You are not assigned to review this project"},
                status=status.HTTP_403_FORBIDDEN,
            )

        lock_set = False
        while lock_set == False:
            if project.is_locked(REVIEW_LOCK):
                sleep(settings.PROJECT_LOCK_RETRY_INTERVAL)
                continue
            else:
                try:
                    project.set_lock(cur_user, REVIEW_LOCK)
                    lock_set = True
                except Exception as e:
                    continue

        # check if the project contains eligible tasks to pull
        tasks = (
            Task.objects.filter(project_id=pk)
            .filter(task_status=LABELED)
            .filter(review_user__isnull=True)
            .exclude(annotation_users=cur_user.id)
        )
        if not tasks:
            project.release_lock(REVIEW_LOCK)
            return Response(
                {"message": "No tasks available for review in this project"},
                status=status.HTTP_404_NOT_FOUND,
            )

        task_pull_count = project.tasks_pull_count_per_batch
        if "num_tasks" in dict(request.data):
            task_pull_count = request.data["num_tasks"]

        tasks = tasks.order_by("id")
        tasks = tasks[:task_pull_count]
        for task in tasks:
            task.review_user = cur_user
            task.save()

        project.release_lock(REVIEW_LOCK)
        return Response(
            {"message": "Tasks assigned successfully"}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["get"],
        name="Unassign review tasks",
        url_name="unassign_review_tasks",
    )
    def unassign_review_tasks(self, request, pk, *args, **kwargs):
        """
        Unassigns all labeled tasks from a reviewer.
        """
        user = request.user
        project_id = pk

        if project_id:
            project_obj = Project.objects.get(pk=project_id)
            if project_obj and user in project_obj.annotation_reviewers.all():
                tasks = (
                    Task.objects.filter(project_id__exact=project_id)
                    .filter(task_status=LABELED)
                    .filter(review_user=user.id)
                )
                if tasks.count() > 0:
                    tasks.update(review_user=None)
                    return Response(
                        {"message": "Tasks unassigned"}, status=status.HTTP_200_OK
                    )
                return Response(
                    {"message": "No tasks to unassign"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"message": "Only reviewers can unassign tasks"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {"message": "Project id not provided"}, status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "from_date": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The start date",
                    format="date",
                ),
                "to_date": openapi.Schema(
                    type=openapi.TYPE_STRING, description="The end date", format="date"
                ),
            },
            required=["from_date", "to_date"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "username": openapi.Schema(type=openapi.TYPE_STRING),
                        "mail": openapi.Schema(
                            type=openapi.TYPE_STRING, format="email"
                        ),
                        "total_annoted_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        "avg_lead_time": openapi.Schema(
                            type=openapi.TYPE_NUMBER, format="float"
                        ),
                        "total_assigned_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        "skipped_tasks": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "total_pending_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                    },
                ),
            ),
            404: "Project does not exist!",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        name="Get Reports  of a Project",
        url_name="get_analytics",
    )
    def get_analytics(self, request, pk=None, *args, **kwargs):
        """
        Get Reports of a Project
        """
        try:
            proj_obj = Project.objects.get(id=pk)
        except Project.DoesNotExist:
            final_result = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
            return Response(final_result, status=ret_status)
        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")
        from_date = from_date + " 00:00"
        to_date = to_date + " 23:59"
        cond, invalid_message = is_valid_date(from_date)
        if not cond:
            return Response(
                {"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST
            )
        cond, invalid_message = is_valid_date(to_date)
        if not cond:
            return Response(
                {"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST
            )

        start_date = datetime.strptime(from_date, "%Y-%m-%d %H:%M")
        end_date = datetime.strptime(to_date, "%Y-%m-%d %H:%M")

        if start_date > end_date:
            return Response(
                {"message": "'To' Date should be after 'From' Date"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project_type = proj_obj.project_type
        project_type = project_type.lower()
        is_translation_project = True if "translation" in project_type else False
        users_id = request.user.id

        reports_type = request.data.get("reports_type")

        if reports_type == "review_reports":
            if proj_obj.enable_task_reviews:
                reviewer_names_list = proj_obj.annotation_reviewers.all()
                reviewer_ids = [name.id for name in reviewer_names_list]
                final_reports = []
                if (
                        request.user.role == User.ORGANIZATION_OWNER
                        or request.user.role == User.WORKSPACE_MANAGER
                    ):

                    for id in reviewer_ids:
                        result = get_review_reports(pk, id, start_date, end_date)
                        final_reports.append(result)

                elif users_id in reviewer_ids:
                    result = get_review_reports(pk, users_id, start_date, end_date)
                    final_reports.append(result)
                else:
                    final_reports = {
                        "message": "You do not have enough permissions to access this view!"
                    }
                return Response(final_reports)
            else:
                result = {"message": "disabled task reviews for this project "}
                return Response(result)

        managers = [
            user1.get_username() for user1 in proj_obj.workspace_id.managers.all()
        ]

        final_result = []
        users_ids = []
        user_mails = []
        user_names = []
        if (
            request.user.role == User.ORGANIZATION_OWNER
            or request.user.role == User.WORKSPACE_MANAGER
            or request.user.is_superuser
        ):
            users_ids = [obj.id for obj in proj_obj.annotators.all()]
            user_mails = [user.get_username() for user in proj_obj.annotators.all()]
            user_names = [user.username for user in proj_obj.annotators.all()]

        elif request.user.role == User.ANNOTATOR:

            users_ids = [request.user.id]
            user_names = [request.user.username]
            user_mails = [request.user.email]

        for index, each_annotator in enumerate(users_ids):
            user_name = user_names[index]
            usermail = user_mails[index]
            if usermail in managers:
                continue
            items = []

            items.append(("Annotator", user_name))
            items.append(("Email", usermail))

            # get total tasks
            all_tasks_in_project = Task.objects.filter(
                Q(project_id=pk) & Q(annotation_users=each_annotator)
            )
            assigned_tasks = all_tasks_in_project.count()
            items.append(("Assigned Tasks", assigned_tasks))

            # get accepted tasks
            annotated_accept_tasks = get_annotated_tasks(
                pk, each_annotator, "accepted", start_date, end_date
            )
            items.append(("Accepted Tasks", annotated_accept_tasks.count()))

            proj = Project.objects.get(id=pk)
            if proj.enable_task_reviews:
                # get accepted with changes tasks count
                accepted_wt_tasks = get_annotated_tasks(
                    pk, each_annotator, "accepted_with_changes", start_date, end_date
                )
                items.append(
                    ("Accepted With Changes  Tasks", accepted_wt_tasks.count())
                )

                # get labeled task count
                labeled_tasks = get_annotated_tasks(
                    pk, each_annotator, "labeled", start_date, end_date
                )
                items.append(("Labeled Tasks", labeled_tasks.count()))

                # get to_be_revised count
                to_be_revised_tasks = get_annotated_tasks(
                    pk, each_annotator, "to_be_revised", start_date, end_date
                )
                items.append(("To Be Revised Tasks", to_be_revised_tasks.count()))

            # get unlabeled count
            total_unlabeled_tasks_count = get_tasks_count(
                pk, each_annotator, "unlabeled"
            )
            items.append(("Unlabeled Tasks", total_unlabeled_tasks_count))

            # get skipped tasks count
            total_skipped_tasks_count = get_tasks_count(pk, each_annotator, "skipped")
            items.append(("Skipped Tasks", total_skipped_tasks_count))

            # get draft tasks count
            total_draft_tasks_count = get_tasks_count(pk, each_annotator, "draft")
            items.append(("Draft Tasks", total_draft_tasks_count))

            if is_translation_project:
                if proj.enable_task_reviews:
                    all_annotated_tasks = (
                        list(annotated_accept_tasks)
                        + list(accepted_wt_tasks)
                        + list(labeled_tasks)
                        + list(to_be_revised_tasks)
                    )
                    total_word_count_list = [
                        no_of_words(each_task.task.data["input_text"])
                        for each_task in all_annotated_tasks
                    ]
                    total_word_count = sum(total_word_count_list)
                else:
                    total_word_count_list = [
                        no_of_words(each_task.task.data["input_text"])
                        for each_task in annotated_accept_tasks
                    ]
                    total_word_count = sum(total_word_count_list)
                items.append(("Word Count", total_word_count))

            if proj.enable_task_reviews:
                all_annotated_tasks = (
                    list(annotated_accept_tasks)
                    + list(accepted_wt_tasks)
                    + list(labeled_tasks)
                    + list(to_be_revised_tasks)
                )
                lead_time_annotated_tasks = [
                    annot.lead_time for annot in all_annotated_tasks
                ]
            else:
                lead_time_annotated_tasks = [
                    eachtask.lead_time for eachtask in annotated_accept_tasks
                ]

            avg_lead_time = 0
            if len(lead_time_annotated_tasks) > 0:
                avg_lead_time = sum(lead_time_annotated_tasks) / len(
                    lead_time_annotated_tasks
                )
            items.append(
                ("Average Annotation Time (In Seconds)", round(avg_lead_time, 2))
            )

            final_result.append(dict(items))
        ret_status = status.HTTP_200_OK
        return Response(final_result, status=ret_status)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "emails": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER, format="ids"),
                    description="List of ids of annotators to be added to project",
                )
            },
            required=["ids"],
        ),
        responses={
            200: "Users added",
            404: "Project does not exist or User does not exist",
            500: "Internal server error",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        name="Add Project Users",
        url_name="add_project_annotators",
    )
    @project_is_archived
    @is_project_editor
    def add_project_annotators(self, request, pk=None, *args, **kwargs):
        """
        Add annotators to the project
        """

        try:
            project = Project.objects.get(pk=pk)

            ids = request.data.get("ids")
            annotators = User.objects.filter(id__in=ids)

            if annotators.count() != len(ids):
                return Response(
                    {"message": "Enter all valid user ids"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for annotator in annotators:
                project.annotators.add(annotator)

            return Response({"message": "Added"}, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        except:
            return Response(
                {"message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["POST"],
        name="Add Project Reviewers",
        url_name="add_project_reviewers",
    )
    @project_is_archived
    @is_project_editor
    def add_project_reviewers(self, request, pk, *args, **kwargs):
        """
        Adds annotation reviewers to the project
        """
        ret_dict = {}
        ret_status = 0
        try:
            project = Project.objects.get(pk=pk)
            if not project.enable_task_reviews:
                return Response(
                    {"message": "Task reviews are disabled for this project"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            ids = request.data.get("ids")
            users = User.objects.filter(id__in=ids)
            if users.count() != len(ids):
                return Response(
                    {"message": "Enter all valid user ids"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            for user in users:
                project.annotation_reviewers.add(user)

            return Response({"message": "Reviewers added"}, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        except:
            return Response(
                {"message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["POST"],
        name="Enable Task Reviews",
        url_name="allow_task_reviews",
    )
    @is_project_editor
    def allow_task_reviews(self, request, pk):
        try:
            project = Project.objects.get(pk=pk)
            if project.enable_task_reviews:
                return Response(
                    {"message": "Task reviews are already enabled"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            tasks = Task.objects.filter(project_id=project.id).filter(
                task_status=ACCEPTED
            )
            tasks.update(task_status=LABELED)
            project.enable_task_reviews = True
            project.save()
            return Response(
                {"message": "Task reviews enabled"}, status=status.HTTP_200_OK
            )
        except Project.DoesNotExist:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        except:
            return Response(
                {"message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["POST"],
        name="Disable Task Reviews",
        url_name="disable_task_reviews",
    )
    @is_project_editor
    def disable_task_reviews(self, request, pk):
        try:
            project = Project.objects.get(pk=pk)
            if not project.enable_task_reviews:
                return Response(
                    {"message": "Task reviews are already disabled"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            tasks = Task.objects.filter(project_id=project.id)
            # delete review annotations for review tasks
            reviewed_tasks = tasks.filter(task_status__in=[ACCEPTED, TO_BE_REVISED])
            Annotation_model.objects.filter(task__in=reviewed_tasks).exclude(
                parent_annotation__isnull=True
            ).delete()
            # mark all unreviewed tasks accepted
            unreviewed_tasks = tasks.filter(task_status=LABELED)
            unreviewed_tasks.update(task_status=ACCEPTED)
            # unassign reviewers
            tasks.update(review_user=None)
            project.enable_task_reviews = False
            project.save()
            return Response(
                {"message": "Task reviews disabled"}, status=status.HTTP_200_OK
            )
        except Project.DoesNotExist:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        except:
            return Response(
                {"message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "project_type",
                openapi.IN_QUERY,
                description=("A string to pass the project tpye"),
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={200: "Return types of project and its details"},
    )
    @action(detail=False, methods=["GET"], name="Get Project Types", url_name="types")
    def types(self, request, *args, **kwargs):
        """
        Fetches project types
        """
        # project_registry = ProjectRegistry()
        try:
            if "project_type" in dict(request.query_params):
                return Response(
                    ProjectRegistry.get_instance().project_types[
                        request.query_params["project_type"]
                    ],
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    ProjectRegistry.get_instance().data, status=status.HTTP_200_OK
                )
        except Exception:
            print(Exception.args)
            return Response(
                {"message": "Error Occured"}, status=status.HTTP_400_BAD_REQUEST
            )

    def get_task_queryset(self, queryset):
        return queryset

    @action(detail=True, methods=["POST", "GET"], name="Pull new items")
    @project_is_archived
    @is_project_editor
    def pull_new_items(self, request, pk=None, *args, **kwargs):
        """
        Pull New Data Items to the Project
        """
        try:
            project = Project.objects.get(pk=pk)
            if project.sampling_mode != FULL:
                ret_dict = {"message": "Sampling Mode is not FULL!"}
                ret_status = status.HTTP_403_FORBIDDEN
            else:
                # Get serializer with the project user data
                try:
                    serializer = ProjectUsersSerializer(project, many=False)
                except User.DoesNotExist:
                    ret_dict = {"message": "User does not exist!"}
                    ret_status = status.HTTP_404_NOT_FOUND

                # Get project instance and check how many items to pull
                project_type = project.project_type
                ids_to_exclude = Task.objects.filter(project_id__exact=project)
                items = filter_data_items(
                    project_type,
                    list(project.dataset_id.all()),
                    project.filter_string,
                    ids_to_exclude,
                )

                if items:

                    # Pull new data items in to the project asynchronously
                    add_new_data_items_into_project.delay(project_id=pk, items=items)

                    ret_dict = {"message": "Adding new tasks to the project."}
                    ret_status = status.HTTP_200_OK

                else:
                    ret_dict = {"message": "No items to pull into the dataset."}
                    ret_status = status.HTTP_404_NOT_FOUND

        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(detail=True, methods=["POST", "GET"], name="Download a Project")
    @project_is_archived
    @is_project_editor
    def download(self, request, pk=None, *args, **kwargs):
        """
        Download a project
        """
        try:
            project = Project.objects.get(pk=pk)
            project_type = dict(PROJECT_TYPE_CHOICES)[project.project_type]
            if "export_type" in dict(request.query_params):
                export_type = request.query_params["export_type"]
            else:
                export_type = "CSV"
            tasks = Task.objects.filter(project_id__exact=project)
            if len(tasks) == 0:
                ret_dict = {"message": "No tasks in project!"}
                ret_status = status.HTTP_200_OK
                return Response(ret_dict, status=ret_status)

            tasks_list = []
            for task in tasks:
                task_dict = model_to_dict(task)
                if export_type != "JSON":
                    task_dict["data"]["task_status"] = task.task_status
                # Rename keys to match label studio converter
                # task_dict['id'] = task_dict['task_id']
                # del task_dict['task_id']
                if task.correct_annotation is not None:
                    annotation_dict = model_to_dict(task.correct_annotation)
                    print(task.correct_annotation)
                    print(task.correct_annotation.created_at)
                    print(task.correct_annotation.updated_at)
                    # annotation_dict['result'] = annotation_dict['result_json']
                    # del annotation_dict['result_json']
                    # print(annotation_dict)
                    annotation_dict["created_at"] = str(
                        task.correct_annotation.created_at
                    )
                    annotation_dict["updated_at"] = str(
                        task.correct_annotation.updated_at
                    )
                    task_dict["annotations"] = [OrderedDict(annotation_dict)]
                else:
                    task_dict["annotations"] = [OrderedDict({"result": {}})]
                del task_dict["annotation_users"]
                del task_dict["review_user"]
                tasks_list.append(OrderedDict(task_dict))
            download_resources = True
            export_stream, content_type, filename = DataExport.generate_export_file(
                project, tasks_list, export_type, download_resources, request.GET
            )

            response = HttpResponse(File(export_stream), content_type=content_type)
            response["Content-Disposition"] = 'attachment; filename="%s"' % filename
            response["filename"] = filename
            return response

        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @swagger_auto_schema(method="get", responses={200: "No tasks to export!"})
    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "export_dataset_instance_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="A unique integer identifying the dataset instance",
                ),
            },
            description="Optional Post request body for projects which have save_type == new_record",
        ),
        responses={
            200: "No tasks to export! or SUCCESS!",
            404: "Project does not exist! or User does not exist!",
        },
    )
    @action(detail=True, methods=["POST", "GET"], name="Export Project")
    @project_is_archived
    @is_project_editor
    def project_export(self, request, pk=None, *args, **kwargs):
        """
        Export a project
        """
        try:
            project = Project.objects.get(pk=pk)
            project_type = dict(PROJECT_TYPE_CHOICES)[project.project_type]

            # Read registry to get output dataset model, and output fields
            registry_helper = ProjectRegistry.get_instance()
            output_dataset_info = registry_helper.get_output_dataset_and_fields(
                project_type
            )

            dataset_model = getattr(dataset_models, output_dataset_info["dataset_type"])

            # If save_type is 'in_place'
            if output_dataset_info["save_type"] == "in_place":
                annotation_fields = output_dataset_info["fields"]["annotations"]

                data_items = []
                tasks = Task.objects.filter(
                    project_id__exact=project,
                    task_status__in=[ACCEPTED, ACCEPTED_WITH_CHANGES],
                )
                if len(tasks) == 0:
                    ret_dict = {"message": "No tasks to export!"}
                    ret_status = status.HTTP_200_OK
                    return Response(ret_dict, status=ret_status)

                # Perform task export function for inpalce functions
                export_project_in_place.delay(
                    annotation_fields=annotation_fields,
                    project_id=pk,
                    project_type=project_type,
                    get_request_data=dict(request.GET),
                )

            # If save_type is 'new_record'
            elif output_dataset_info["save_type"] == "new_record":
                export_dataset_instance_id = request.data["export_dataset_instance_id"]
                export_dataset_instance = dataset_models.DatasetInstance.objects.get(
                    instance_id__exact=export_dataset_instance_id
                )

                annotation_fields = output_dataset_info["fields"]["annotations"]
                task_annotation_fields = []
                if "variable_parameters" in output_dataset_info["fields"]:
                    task_annotation_fields += output_dataset_info["fields"][
                        "variable_parameters"
                    ]
                if "copy_from_input" in output_dataset_info["fields"]:
                    task_annotation_fields += list(
                        output_dataset_info["fields"]["copy_from_input"].values()
                    )

                data_items = []
                tasks = Task.objects.filter(
                    project_id__exact=project,
                    task_status__in=[ACCEPTED, ACCEPTED_WITH_CHANGES],
                )
                if len(tasks) == 0:
                    ret_dict = {"message": "No tasks to export!"}
                    ret_status = status.HTTP_200_OK
                    return Response(ret_dict, status=ret_status)

                export_project_new_record.delay(
                    annotation_fields=annotation_fields,
                    project_id=pk,
                    project_type=project_type,
                    export_dataset_instance_id=export_dataset_instance_id,
                    task_annotation_fields=task_annotation_fields,
                    get_request_data=dict(request.GET),
                )

                # data_items.append(data_item)

                # TODO: implement bulk create if possible (only if non-hacky)
                # dataset_model.objects.bulk_create(data_items)
                # Saving data items to dataset in a loop
                # for item in data_items:

            # FIXME: Allow export multiple times
            # project.is_archived=True
            # project.save()
            ret_dict = {"message": "SUCCESS!"}
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(detail=True, methods=["POST", "GET"], name="Publish Project")
    @project_is_archived
    @project_is_published
    @is_project_editor
    def project_publish(self, request, pk=None, *args, **kwargs):
        """
        Publish a project
        """
        try:
            project = Project.objects.get(pk=pk)

            if project.is_published:
                return Response(PROJECT_IS_PUBLISHED_ERROR, status=status.HTTP_200_OK)

            serializer = ProjectUsersSerializer(project, many=False)
            # ret_dict = serializer.data
            annotators = serializer.data["annotators"]

            if len(annotators) < project.required_annotators_per_task:
                ret_dict = {
                    "message": "Number of annotators is less than required annotators per task"
                }
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)

            # get all tasks of a project
            # tasks = Task.objects.filter(project_id=pk)

            # assign_users_to_tasks(tasks, annotators)

            # print("Here",task.annotation_users.all().count(), task.annotation_users.all())
            # for user in annotatorList:
            #     userEmail = user['email']

            #     send_mail("Annotation Tasks Assigned",
            #     f"Hello! You are assigned to tasks in the project {project.title}.",
            #     settings.DEFAULT_FROM_EMAIL, [userEmail],
            #     )

            # Task.objects.bulk_update(updated_tasks, ['annotation_users'])

            project.is_published = True
            project.save()

            ret_dict = {"message": "This project is published"}
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(detail=False, methods=["GET"], name="Get language choices")
    def language_choices(self, request):
        return Response(LANG_CHOICES)

    @action(methods=["GET"], detail=True, name="Get all past instances of celery tasks")
    def get_async_task_results(self, request, pk):
        """
        View to get all past instances of celery tasks
        URL: /projects/<project_id>/get_async_task_results?task_name=<task-name>
        Accepted methods: GET

        Returns:
            A list of all past instances of celery tasks for a specific task using the project ID
        """

        # Get the task name from the request
        task_name = request.query_params.get("task_name")

        # Check if task name is in allowed task names list
        if task_name not in ALLOWED_CELERY_TASKS:
            return Response(
                {
                    "message": "Invalid task name for this app.",
                    "allowed_tasks": ALLOWED_CELERY_TASKS,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Handle 'create_parameter' task separately
        if task_name == "projects.tasks.create_parameters_for_task_creation":

            # Create the keyword argument for dataset instance ID
            project_id_keyword_arg = "'project_id': " + str(pk) + "}"

        else:
            # Create the keyword argument for dataset instance ID
            project_id_keyword_arg = "'project_id': " + "'" + str(pk) + "'"

        # Check the celery project export status
        task_queryset = TaskResult.objects.filter(
            task_name=task_name,
            task_kwargs__contains=project_id_keyword_arg,
        )

        # Check if queryset is empty
        if not task_queryset:
            return Response(
                {"message": "No results found"}, status=status.HTTP_204_NO_CONTENT
            )

        # Sort the task queryset by date and time
        task_queryset = task_queryset.order_by("-date_done")

        # Serialize the task queryset and return it to the frontend
        serializer = TaskResultSerializer(task_queryset, many=True)

        # Get a list of all dates
        dates = task_queryset.values_list("date_done", flat=True)
        status_list = task_queryset.values_list("status", flat=True)

        # Remove quotes from all statuses
        status_list = [status.replace("'", "") for status in status_list]

        # Extract date and time from the datetime object
        all_dates = [date.strftime("%d-%m-%Y") for date in dates]
        all_times = [date.strftime("%H:%M:%S") for date in dates]

        # Add the date, time and status to the serializer data
        for i in range(len(serializer.data)):
            serializer.data[i]["date"] = all_dates[i]
            serializer.data[i]["time"] = all_times[i]
            serializer.data[i]["status"] = status_list[i]

        return Response(serializer.data)
