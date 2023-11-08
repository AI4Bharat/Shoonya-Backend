import ast
import json
import re
from base64 import b64encode
from urllib.parse import parse_qsl

from django.apps import apps
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django_celery_results.models import TaskResult
from users.serializers import UserFetchSerializer
from filters import filter
from projects.serializers import ProjectSerializer
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .permissions import DatasetInstancePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from organizations.decorators import (
    is_particular_organization_owner,
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import IsAuthenticated
from users.models import User
from projects.models import ANNOTATION_STAGE, REVIEW_STAGE
from projects.utils import (
    convert_seconds_to_hours,
    get_audio_project_types,
    get_audio_transcription_duration,
    calculate_word_error_rate_between_two_audio_transcription_annotation,
    ocr_word_count,
)

from . import resources
from .models import *
from .serializers import *
from .tasks import upload_data_to_data_instance, deduplicate_dataset_instance_items
import dataset
from tasks.models import (
    Task,
    Annotation,
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
)


## Utility functions used inside the view functions
def extract_status_date_time_from_task_queryset(task_queryset):
    # Sort the tasks by newest items first by date
    task_queryset = task_queryset.order_by("-date_done")

    # Get the export task status and last update date
    task_status = task_queryset.first().as_dict()["status"]
    task_datetime = task_queryset.first().as_dict()["date_done"]

    # Remove quotes from the status if it is present in the string
    if '"' in task_status:
        task_status = task_status.strip('"')

    # Extract date and time from the datetime object
    task_date = task_datetime.date()
    task_time = f"{str(task_datetime.time().replace(microsecond=0))} UTC"

    return task_status, task_date, task_time


def get_project_export_status(pk):
    """Function to return status of the project export background task.

    Args:
        pk (int): Primary key of the project

    Returns:
        str: Status of the project export
        str: Date when the last time project was exported
        str: Time when the last time project was exported
    """

    # Create the keyword argument for project ID
    project_id_keyword_arg = "'project_id': " + "'" + str(pk) + "'" + ","

    # Check the celery project export status
    task_queryset = TaskResult.objects.filter(
        task_name__in=[
            "projects.tasks.export_project_in_place",
            "projects.tasks.export_project_new_record",
        ],
        # task_name = 'projects.tasks.export_project_in_place',
        task_kwargs__contains=project_id_keyword_arg,
    )

    # If the celery TaskResults table returns
    if task_queryset:
        (
            task_status,
            task_date,
            task_time,
        ) = extract_status_date_time_from_task_queryset(task_queryset)

        return task_status, task_date, task_time

    return (
        "Success",
        "Synchronously Completed. No Date.",
        "Synchronously Completed. No Time.",
    )


def get_dataset_upload_status(dataset_instance_pk):
    """Function to return status of the dataset upload background task.

    Args:
        dataset_instance_pk (int): Primary key of the dataset instance

    Returns:
        str: Status of the dataset upload
        str: Date when the last time dataset was uploaded
        str: Time when the last time dataset was uploaded
    """

    # Create the keyword argument for dataset instance ID
    instance_id_keyword_arg = "{'pk': " + "'" + str(dataset_instance_pk) + "'" + ","

    # Check the celery project export status
    task_queryset = TaskResult.objects.filter(
        task_name="dataset.tasks.upload_data_to_data_instance",
        task_kwargs__contains=instance_id_keyword_arg,
    )

    # If the celery TaskResults table returns data
    if task_queryset:
        (
            task_status,
            task_date,
            task_time,
        ) = extract_status_date_time_from_task_queryset(task_queryset)

        # Sort the tasks by newest items first by date
        task_queryset = task_queryset.order_by("-date_done")

        # Get the export task status and last update date
        task_status = task_queryset.first().as_dict()["status"]
        task_datetime = task_queryset.first().as_dict()["date_done"]
        task_result = task_queryset.first().as_dict()["result"]

        # Convert task result
        if "exc_message" in task_result:
            task_result = ast.literal_eval(task_result)["exc_message"]

        # Remove quotes from the status if it is present in the string
        if '"' in task_status:
            task_status = task_status.strip('"')

        if '"' in task_result:
            task_result = task_result.strip('"')

        # Extract date and time from the datetime object
        task_date = task_datetime.date()
        task_time = f"{str(task_datetime.time().replace(microsecond=0))} UTC"

        # Get the error messages if the task is a failure
        if task_status == "FAILURE":
            task_status = "Ingestion Failed!"

        # If the task is in progress
        elif task_status != "SUCCESS":
            task_status = "Ingestion in progress."

        # If the task is a success
        else:
            task_status = "Ingestion Successful!"

    # If no entry is found for the celery task
    else:
        task_date = "Synchronously Completed. No Date."
        task_time = "Synchronously Completed. No Time."
        task_status = "None"
        task_result = "None"

    return task_status, task_date, task_time, task_result


# Create your views here.
class DatasetInstanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Dataset Instance
    """

    queryset = DatasetInstance.objects.all()
    permission_classes = (DatasetInstancePermission,)

    # Define list of accepted file formats for file upload
    ACCEPTED_FILETYPES = ["csv", "tsv", "json", "yaml", "xls", "xlsx"]

    def get_serializer_class(self):
        if self.action == "upload":
            return DatasetInstanceUploadSerializer
        return DatasetInstanceSerializer

    def retrieve(self, request, pk, *args, **kwargs):
        """Retrieves a DatasetInstance given its ID"""

        dataset_instance_response = super().retrieve(request, *args, **kwargs)

        # Get the task statuses for the dataset instance
        (
            dataset_instance_status,
            dataset_instance_date,
            dataset_instance_time,
            dataset_instance_result,
        ) = get_dataset_upload_status(pk)

        # Add the task status and time to the dataset instance response
        dataset_instance_response.data["last_upload_status"] = dataset_instance_status
        dataset_instance_response.data["last_upload_date"] = dataset_instance_date
        dataset_instance_response.data["last_upload_time"] = dataset_instance_time
        dataset_instance_response.data["last_upload_result"] = dataset_instance_result

        return dataset_instance_response

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "dataset_visibility",
                openapi.IN_QUERY,
                description=("A string that denotes the visibility of dataset"),
                type=openapi.TYPE_STRING,
                enum=["all_public_datasets", "my_datasets"],
                required=False,
            ),
            openapi.Parameter(
                "dataset_type",
                openapi.IN_QUERY,
                description=("A string that denotes the type of dataset"),
                enum=[dataset_type[0] for dataset_type in DATASET_TYPE_CHOICES],
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        # Org Owners and superusers see all datasets
        if request.user.is_superuser:
            queryset = DatasetInstance.objects.all()
        elif request.user.role == User.ORGANIZATION_OWNER:
            queryset = DatasetInstance.objects.filter(
                organisation_id=request.user.organization
            )
        # Managers only see datasets that they are added to and public datasets
        else:
            queryset = DatasetInstance.objects.filter(
                organisation_id=request.user.organization
            ).filter(Q(public_to_managers=True) | Q(users__id=request.user.id))

        if "dataset_visibility" in request.query_params:
            dataset_visibility = request.query_params["dataset_visibility"]
            if dataset_visibility == "all_public_datasets":
                if (request.user.role == User.WORKSPACE_MANAGER) and (
                    request.user.is_superuser == False
                ):
                    queryset = queryset.filter(public_to_managers=True)
            elif dataset_visibility == "my_datasets":
                queryset = queryset.filter(users__id=request.user.id)

        # Filter the queryset based on the query params
        if "dataset_type" in dict(request.query_params):
            queryset = queryset.filter(
                dataset_type__exact=request.query_params["dataset_type"]
            )

        # Serialize the distinct items and sort by instance ID
        serializer = DatasetInstanceSerializer(
            queryset.distinct().order_by("instance_id"), many=True
        )

        # Add status fields to the serializer data
        for dataset_instance in serializer.data:
            # Get the task statuses for the dataset instance
            (
                dataset_instance_status,
                dataset_instance_date,
                dataset_instance_time,
                dataset_instance_result,
            ) = get_dataset_upload_status(dataset_instance["instance_id"])

            # Add the task status and time to the dataset instance response
            dataset_instance["last_upload_status"] = dataset_instance_status
            dataset_instance["last_upload_date"] = dataset_instance_date
            dataset_instance["last_upload_time"] = dataset_instance_time
            dataset_instance["last_upload_result"] = dataset_instance_result

        return Response(serializer.data)

    @action(methods=["GET"], detail=True, name="Download Dataset in CSV format")
    def download(self, request, pk):
        """
        View to download a dataset in CSV format
        URL: /data/instances/<instance-id>/download/
        Accepted methods: GET
        """
        export_type = request.GET.get("type", "csv")
        try:
            # Get the dataset instance for the id
            dataset_instance = DatasetInstance.objects.get(instance_id=pk)
        except DatasetInstance.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        dataset_model = apps.get_model("dataset", dataset_instance.dataset_type)
        data_items = dataset_model.objects.filter(instance_id=pk)
        dataset_resource = resources.RESOURCE_MAP[dataset_instance.dataset_type]
        exported_items = dataset_resource().export_as_generator(export_type, data_items)
        if export_type == "tsv":
            content_type = "text/tsv"
        else:
            content_type = "text/csv"
        return StreamingHttpResponse(
            exported_items, status=status.HTTP_200_OK, content_type=content_type
        )

    @action(methods=["POST"], detail=True, name="Upload Dataset File")
    def upload(self, request, pk):
        """
        View to upload a dataset from a file
        URL: /data/instances/<instance-id>/upload/
        Accepted methods: POST
        """

        # Get the dataset type using the instance ID
        dataset_type = get_object_or_404(DatasetInstance, pk=pk).dataset_type

        if "dataset" not in request.FILES:
            return Response(
                {
                    "message": "Please provide a file with key 'dataset'.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        dataset = request.FILES["dataset"]
        content_type = dataset.name.split(".")[-1]

        # Get the deduplicate option and convert to bool
        deduplicate = request.POST.get("deduplicate", "false")
        if_deduplicate = deduplicate.lower() == "true"

        # Ensure that the content type is accepted, return error otherwise
        if content_type not in DatasetInstanceViewSet.ACCEPTED_FILETYPES:
            return Response(
                {
                    "message": f"Invalid Dataset File. Only accepts the following file formats: {DatasetInstanceViewSet.ACCEPTED_FILETYPES}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Read the dataset as a string from the dataset pointer
        try:
            if content_type in ["xls", "xlsx"]:
                # xls and xlsx files cannot be decoded as a string
                dataset_string = b64encode(dataset.read()).decode()
            else:
                dataset_string = dataset.read().decode()
        except Exception as e:
            return Response(
                {
                    "message": f"Error while reading file. Please check the file data and try again.",
                    "exception": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Uplod the dataset to the dataset instance
        upload_data_to_data_instance.delay(
            pk=pk,
            dataset_type=dataset_type,
            dataset_string=dataset_string,
            content_type=content_type,
            deduplicate=if_deduplicate,
        )

        # Get name of the dataset instance
        dataset_name = get_object_or_404(DatasetInstance, pk=pk).instance_name
        return Response(
            {
                "message": f"Uploading {dataset_type} data to Dataset Instance: {dataset_name}",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(methods=["GET"], detail=True, name="List all Projects using Dataset")
    def projects(self, request, pk):
        """
        View to list all projects using a dataset
        URL: /data/instances/<instance-id>/projects/
        Accepted methods: GET
        """
        # Get the projects using the instance ID
        projects = apps.get_model("projects", "Project").objects.filter(dataset_id=pk)

        # Serialize the projects and return them to the frontend
        serializer = ProjectSerializer(projects, many=True)

        # Add new fields to the serializer data to show project exprot status and date
        for project in serializer.data:
            # Get project export status details
            (
                project_export_status,
                last_project_export_date,
                last_project_export_time,
            ) = get_project_export_status(project.get("id"))

            # Add the export status and date to the project instance serializer
            project["last_project_export_status"] = project_export_status
            project["last_project_export_date"] = last_project_export_date
            project["last_project_export_time"] = last_project_export_time

        return Response(serializer.data)

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "task_name",
                openapi.IN_QUERY,
                description=(
                    f"A task name to filter the tasks by. Allowed Tasks: {ALLOWED_CELERY_TASKS}"
                ),
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: "Returns the past task run history for a particular dataset instance and task name"
        },
    )
    @action(methods=["GET"], detail=True, name="Get all past instances of celery tasks")
    def get_async_task_results(self, request, pk):
        # sourcery skip: do-not-use-bare-except
        """
        View to get all past instances of celery tasks
        URL: /data/instances/<instance-id>/get_async_task_results?task_name=<task-name>
        Accepted methods: GET

        Returns:
            A list of all past instances of celery tasks for a specific task
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

        # Check if the task name has the word projects in it
        if "projects" in task_name:
            # Get the IDs of the projects associated with the dataset instance
            project_ids = (
                apps.get_model("projects", "Project")
                .objects.filter(dataset_id=pk)
                .values_list("id", flat=True)
            )

            # Create the project keywords list
            project_id_keyword_args = [
                "'project_id': " + "'" + str(pk) + "'" for pk in project_ids
            ]

            # Turn list of project ID keywords into list of Q objects
            queries = [
                Q(task_kwargs__contains=project_keyword)
                for project_keyword in project_id_keyword_args
            ]

            # Handle exception when queries is empty
            try:
                query = queries.pop()

            except IndexError:
                return Response(
                    {
                        "message": "No projects associated with this task.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Convert the list of Q objects into a single query
            for item in queries:
                query |= item

            # Get the task queryset for the task name and all the corresponding projects for this dataset
            task_queryset = TaskResult.objects.filter(
                query,
                task_name=task_name,
            )

        else:
            # Create the keyword argument for dataset instance ID
            instance_id_keyword_arg = "{'pk': " + "'" + str(pk) + "'" + ","

            # Check the celery project export status
            task_queryset = TaskResult.objects.filter(
                task_name=task_name,
                task_kwargs__contains=instance_id_keyword_arg,
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

            # displaying user friendly error messages
            result_data = json.loads(serializer.data[i]["result"])
            error_msg_list = result_data.get("exc_message", [])
            error_type = result_data.get("exc_type")

            if error_type == "InvalidDimensions":
                serializer.data[i][
                    "result"
                ] = "The data type of some value does not match the required data type or the dimensions of the dataset that you have uploaded are incorrect"
            elif (
                error_type == "EncodeError"
                and error_msg_list[0]
                == "TypeError('Object of type set is not JSON serializable')"
            ):
                serializer.data[i][
                    "result"
                ] = "The dataset that you have uploaded is empty"
            else:
                serializer.data[i]["result"] = "Type of error : " + error_type + "\n"
                if len(error_msg_list) > 0:
                    serializer.data[i]["result"] += (
                        "Error message : " + error_msg_list[0]
                    )

        # Add the project ID from the task kwargs to the serializer data
        if "projects" in task_name:
            for i in range(len(serializer.data)):
                try:
                    # Apply regex query to task kwargs and get the project ID string
                    project_id_list = re.findall(
                        r"('project_id': '[0-9]+')", serializer.data[i]["task_kwargs"]
                    )
                    project_id = int(project_id_list[0].split("'")[-2])

                    # Add to serializer data
                    serializer.data[i]["project_id"] = project_id

                except:
                    # Handle the project ID exception
                    serializer.data[i]["project_id"] = "Not ID found"

        return Response(serializer.data)

    @action(methods=["GET"], detail=True, name="List all Users using Dataset")
    def users(self, request, pk):
        users = User.objects.filter(dataset_users__instance_id=pk)
        # print(users)
        serializer = UserFetchSerializer(many=True, data=users)
        # print(serializer)
        serializer.is_valid()
        return Response(serializer.data)

    # creating endpoint for adding workspacemanagers

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="String containing emails separated by commas",
                )
            },
            required=["ids"],
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "Workspace manager added Successfully",
            403: "Not authorized",
            400: "No valid user_ids found",
            404: "dataset not found",
            500: "Server error occured",
        },
    )
    @is_particular_organization_owner
    @action(
        detail=True,
        methods=["POST"],
        url_path="addworkspacemanagers",
        url_name="add_managers",
    )
    def add_managers(self, request, pk=None):
        if "ids" in dict(request.data):
            ids = request.data.get("ids", "")
        else:
            return Response(
                {"message": "key doesnot match"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dataset = DatasetInstance.objects.get(pk=pk)
            for user_id in ids:
                user = User.objects.get(id=user_id)
                if user.role == 2:
                    if user in dataset.users.all():
                        return Response(
                            {"message": "user already exists"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    else:
                        dataset.users.add(user)
                        dataset.save()
                else:
                    return Response(
                        {"message": "user is not a manager"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            return Response(
                {"message": "managers added successfully"}, status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except DatasetInstance.DoesNotExist:
            return Response(
                {"message": "Dataset not found"}, status=status.HTTP_404_NOT_FOUND
            )

    # removing managers from the dataset

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "ids": openapi.Schema(type=openapi.TYPE_STRING, format="email")
            },
            required=["ids"],
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "manager removed Successfully",
            403: "Not authorized",
            404: "User not in the organization/User not found",
            500: "Server error occured",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="removemanagers",
        url_name="remove_managers",
    )
    @is_particular_organization_owner
    def remove_managers(self, request, pk=None):
        if "ids" in dict(request.data):
            ids = request.data.get("ids", "")
        else:
            return Response(
                {"message": "key doesnot match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            dataset = DatasetInstance.objects.get(pk=pk)

            for user_id in ids:
                user = User.objects.get(id=user_id)
                if user.role == 2:
                    if user not in dataset.users.all():
                        return Response(
                            {"message": "user doesnot exists"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    else:
                        dataset.users.remove(user)

                else:
                    return Response(
                        {"message": "user is not a manager"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            return Response(
                {"message": "manager removed successfully"},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except DatasetInstance.DoesNotExist:
            return Response(
                {"message": "Dataset not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except ValueError:
            return Response(
                {"message": "Server Error occured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(methods=["GET"], detail=False, name="List all Dataset Instance Types")
    def dataset_types(self, request):
        dataset_types = [dataset[0] for dataset in DATASET_TYPE_CHOICES]
        return Response(dataset_types)

    @action(methods=["GET"], detail=False, name="List all Accepted Upload Filetypes")
    def accepted_filetypes(self, request):
        return Response(DatasetInstanceViewSet.ACCEPTED_FILETYPES)

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "deduplicate_fields_list",
                openapi.IN_QUERY,
                description=(
                    "A list of fields based on which dataset items need to be deduplicated"
                ),
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_STRING),
                required=True,
            )
        ],
        responses={200: "Duplicate removal started"},
    )
    @action(
        methods=["GET"],
        detail=True,
        url_path="remove_duplicates_from_dataset_instance",
        url_name="remove_duplicates_from_dataset_instance",
    )
    def remove_duplicates(self, request, pk=None):
        try:
            deduplicate_fields_list = request.query_params["deduplicate_fields_list"]
        except:
            return Response(
                {"message": "deduplicate_fields_list is a required query parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deduplicate_fields_list = deduplicate_fields_list.split(",")
        if len(deduplicate_fields_list) == 0:
            return Response(
                {"message": "Fields list cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deduplicate_dataset_instance_items.delay(pk, deduplicate_fields_list)
        ret_dict = {"message": "Duplicate removal started"}
        ret_status = status.HTTP_200_OK
        return Response(ret_dict, status=ret_status)

    @action(
        detail=True,
        methods=["POST"],
        name="Dataset Instance Project Details",
        url_path="project_analytics",
        url_name="project_analytics",
    )
    def project_analytics(self, request, pk=None):
        """
        API for getting project_analytics of a dataset instance
        """
        try:
            DatasetInstance.objects.get(pk=pk)
        except DatasetInstance.DoesNotExist:
            return Response(
                {"message": "Dataset Instance not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        tgt_language = request.data.get("tgt_language")
        project_type = request.data.get("project_type")
        selected_language = "-"

        if tgt_language == None:
            projects_objs = apps.get_model("projects", "Project").objects.filter(
                dataset_id=pk, project_type=project_type
            )
        else:
            selected_language = tgt_language
            projects_objs = apps.get_model("projects", "Project").objects.filter(
                dataset_id=pk, project_type=project_type, tgt_language=tgt_language
            )
        final_result = []
        if projects_objs.count() != 0:
            for proj in projects_objs:
                proj_manager = [
                    manager.get_username()
                    for manager in proj.workspace_id.managers.all()
                ]
                try:
                    org_owner = proj.organization_id.created_by.get_username()
                    proj_manager.append(org_owner)
                except:
                    pass
                project_id = proj.id
                project_name = proj.title
                project_type = proj.project_type

                project_type_lower = project_type.lower()
                is_translation_project = (
                    True if "translation" in project_type_lower else False
                )

                all_tasks = Task.objects.filter(project_id=proj.id)
                total_tasks = all_tasks.count()
                annotators_list = [
                    annotator.get_username() for annotator in proj.annotators.all()
                ]
                no_of_annotators_assigned = len(
                    [
                        annotator
                        for annotator in annotators_list
                        if annotator not in proj_manager
                    ]
                )

                incomplete_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="incomplete"
                )
                incomplete_count = incomplete_tasks.count()

                labeled_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="annotated"
                )
                labeled_count = labeled_tasks.count()

                reviewed_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="reviewed"
                )

                reviewed_count = reviewed_tasks.count()

                exported_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="exported"
                )
                exported_count = exported_tasks.count()

                superchecked_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="super_checked"
                )
                superchecked_count = superchecked_tasks.count()

                total_word_annotated_count_list = []
                total_word_reviewed_count_list = []
                total_word_exported_count_list = []
                total_word_superchecked_count_list = []
                if (
                    is_translation_project
                    or project_type == "SemanticTextualSimilarity_Scale5"
                ):
                    for each_task in labeled_tasks:
                        try:
                            total_word_annotated_count_list.append(
                                each_task.data["word_count"]
                            )
                        except:
                            pass

                    for each_task in reviewed_tasks:
                        try:
                            total_word_reviewed_count_list.append(
                                each_task.data["word_count"]
                            )
                        except:
                            pass
                    for each_task in exported_tasks:
                        try:
                            total_word_exported_count_list.append(
                                each_task.data["word_count"]
                            )
                        except:
                            pass
                    for each_task in superchecked_tasks:
                        try:
                            total_word_superchecked_count_list.append(
                                each_task.data["word_count"]
                            )
                        except:
                            pass
                elif "OCRTranscription" in project_type:
                    for each_task in labeled_tasks:
                        try:
                            annotate_annotation = Annotation.objects.filter(
                                task=each_task, annotation_type=ANNOTATOR_ANNOTATION
                            )[0]
                            total_word_annotated_count_list.append(
                                ocr_word_count(annotate_annotation.result)
                            )
                        except:
                            pass

                    for each_task in reviewed_tasks:
                        try:
                            review_annotation = Annotation.objects.filter(
                                task=each_task, annotation_type=REVIEWER_ANNOTATION
                            )[0]
                            total_word_reviewed_count_list.append(
                                ocr_word_count(review_annotation.result)
                            )
                        except:
                            pass

                    for each_task in exported_tasks:
                        try:
                            total_word_exported_count_list.append(
                                ocr_word_count(each_task.correct_annotation.result)
                            )
                        except:
                            pass

                    for each_task in superchecked_tasks:
                        try:
                            supercheck_annotation = Annotation.objects.filter(
                                task=each_task, annotation_type=SUPER_CHECKER_ANNOTATION
                            )[0]
                            total_word_superchecked_count_list.append(
                                ocr_word_count(supercheck_annotation.result)
                            )
                        except:
                            pass

                total_word_annotated_count = sum(total_word_annotated_count_list)
                total_word_reviewed_count = sum(total_word_reviewed_count_list)
                total_word_exported_count = sum(total_word_exported_count_list)
                total_word_superchecked_count = sum(total_word_superchecked_count_list)

                total_duration_annotated_count_list = []
                total_duration_reviewed_count_list = []
                total_duration_exported_count_list = []
                total_duration_superchecked_count_list = []
                total_word_error_rate_rs_list = []
                total_word_error_rate_ar_list = []
                total_raw_duration_list = []
                if project_type in get_audio_project_types():
                    for each_task in labeled_tasks:
                        try:
                            annotate_annotation = Annotation.objects.filter(
                                task=each_task, annotation_type=ANNOTATOR_ANNOTATION
                            )[0]
                            total_duration_annotated_count_list.append(
                                get_audio_transcription_duration(
                                    annotate_annotation.result
                                )
                            )
                        except:
                            pass

                    for each_task in reviewed_tasks:
                        try:
                            review_annotation = Annotation.objects.filter(
                                task=each_task, annotation_type=REVIEWER_ANNOTATION
                            )[0]
                            total_duration_reviewed_count_list.append(
                                get_audio_transcription_duration(
                                    review_annotation.result
                                )
                            )
                            total_word_error_rate_ar_list.append(
                                calculate_word_error_rate_between_two_audio_transcription_annotation(
                                    review_annotation.result,
                                    review_annotation.parent_annotation.result,
                                )
                            )
                        except:
                            pass

                    for each_task in exported_tasks:
                        try:
                            total_duration_exported_count_list.append(
                                get_audio_transcription_duration(
                                    each_task.correct_annotation.result
                                )
                            )
                        except:
                            pass

                    for each_task in superchecked_tasks:
                        try:
                            supercheck_annotation = Annotation.objects.filter(
                                task=each_task, annotation_type=SUPER_CHECKER_ANNOTATION
                            )[0]
                            total_duration_superchecked_count_list.append(
                                get_audio_transcription_duration(
                                    supercheck_annotation.result
                                )
                            )
                            total_word_error_rate_rs_list.append(
                                calculate_word_error_rate_between_two_audio_transcription_annotation(
                                    supercheck_annotation.result,
                                    supercheck_annotation.parent_annotation.result,
                                )
                            )
                        except:
                            pass

                    for each_task in all_tasks:
                        try:
                            total_raw_duration_list.append(
                                each_task.data["audio_duration"]
                            )
                        except:
                            pass

                total_duration_annotated_count = convert_seconds_to_hours(
                    sum(total_duration_annotated_count_list)
                )
                total_duration_reviewed_count = convert_seconds_to_hours(
                    sum(total_duration_reviewed_count_list)
                )
                total_duration_exported_count = convert_seconds_to_hours(
                    sum(total_duration_exported_count_list)
                )
                total_duration_superchecked_count = convert_seconds_to_hours(
                    sum(total_duration_superchecked_count_list)
                )
                total_raw_duration = convert_seconds_to_hours(
                    sum(total_raw_duration_list)
                )

                if len(total_word_error_rate_rs_list) > 0:
                    avg_word_error_rate_rs = sum(total_word_error_rate_rs_list) / len(
                        total_word_error_rate_rs_list
                    )
                else:
                    avg_word_error_rate_rs = 0
                if len(total_word_error_rate_ar_list) > 0:
                    avg_word_error_rate_ar = sum(total_word_error_rate_ar_list) / len(
                        total_word_error_rate_ar_list
                    )
                else:
                    avg_word_error_rate_ar = 0

                if total_tasks == 0:
                    project_progress = 0.0
                else:
                    if proj.project_stage == ANNOTATION_STAGE:
                        project_progress = (
                            (labeled_count + exported_count) / total_tasks
                        ) * 100
                    elif proj.project_stage == REVIEW_STAGE:
                        project_progress = (
                            (reviewed_count + exported_count) / total_tasks
                        ) * 100
                    else:
                        project_progress = (
                            (superchecked_count + exported_count) / total_tasks
                        ) * 100
                result = {
                    "Project Id": project_id,
                    "Project Name": project_name,
                    "Language": selected_language,
                    "Project Type": project_type,
                    "No .of Annotators Assigned": no_of_annotators_assigned,
                    "Total": total_tasks,
                    "Annotated": labeled_count,
                    "Incomplete": incomplete_count,
                    "Reviewed": reviewed_count,
                    "Exported": exported_count,
                    "SuperChecked": superchecked_count,
                    "Annotated Tasks Segments Duration": total_duration_annotated_count,
                    "Reviewed Tasks Segments Duration": total_duration_reviewed_count,
                    "Exported Tasks Segments Duration": total_duration_exported_count,
                    "SuperChecked Tasks Segments Duration": total_duration_superchecked_count,
                    "Total Raw Audio Duration": total_raw_duration,
                    "Average Word Error Rate A/R": round(avg_word_error_rate_ar, 2),
                    "Average Word Error Rate R/S": round(avg_word_error_rate_rs, 2),
                    "Annotated Tasks Word Count": total_word_annotated_count,
                    "Reviewed Tasks Word Count": total_word_reviewed_count,
                    "Exported Tasks Word Count": total_word_exported_count,
                    "SuperChecked Tasks Word Count": total_word_superchecked_count,
                    "Project Progress": round(project_progress, 3),
                }

                if project_type in get_audio_project_types():
                    del result["Annotated Tasks Word Count"]
                    del result["Reviewed Tasks Word Count"]
                    del result["Exported Tasks Word Count"]
                    del result["SuperChecked Tasks Word Count"]

                elif is_translation_project or project_type in [
                    "SemanticTextualSimilarity_Scale5",
                    "OCRTranscriptionEditing",
                    "OCRTranscription",
                ]:
                    del result["Annotated Tasks Segments Duration"]
                    del result["Reviewed Tasks Segments Duration"]
                    del result["Exported Tasks Segments Duration"]
                    del result["SuperChecked Tasks Segments Duration"]
                    del result["Total Raw Audio Duration"]
                    del result["Average Word Error Rate A/R"]
                    del result["Average Word Error Rate R/S"]
                else:
                    del result["Annotated Tasks Word Count"]
                    del result["Reviewed Tasks Word Count"]
                    del result["Exported Tasks Word Count"]
                    del result["SuperChecked Tasks Word Count"]
                    del result["Annotated Tasks Segments Duration"]
                    del result["Reviewed Tasks Segments Duration"]
                    del result["Exported Tasks Segments Duration"]
                    del result["SuperChecked Tasks Segments Duration"]
                    del result["Total Raw Audio Duration"]
                    del result["Average Word Error Rate A/R"]
                    del result["Average Word Error Rate R/S"]

                final_result.append(result)
        ret_status = status.HTTP_200_OK
        return Response(final_result, status=ret_status)


class DatasetItemsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Dataset Items
    """

    queryset = DatasetBase.objects.all()
    serializer_class = DatasetItemsSerializer
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        DatasetInstancePermission,
    )

    def list(self, request):
        dataset_instances = DatasetInstance.objects.filter(
            instance_id__in=self.queryset.distinct("instance_id").values_list(
                "instance_id"
            )
        ).values("instance_id", "dataset_type")
        return Response(data=dataset_instances, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], name="Get data Items")
    def get_data_items(self, request, *args, **kwargs):
        try:
            dataset_instance_ids = request.data.get("instance_ids")
            dataset_type = request.data.get("dataset_type", "")
            if type(dataset_instance_ids) != list:
                dataset_instance_ids = [dataset_instance_ids]
            filter_string = request.data.get("filter_string")
            #  Get dataset type from first dataset instance if dataset_type not passed in json data from frontend
            if dataset_type == "":
                dataset_type = DatasetInstance.objects.get(
                    instance_id=dataset_instance_ids[0]
                ).dataset_type
            dataset_model = apps.get_model("dataset", dataset_type)
            data_items = dataset_model.objects.filter(
                instance_id__in=dataset_instance_ids
            )

            if "search_keys" in request.data:
                search_dict = {}
                for key, value in request.data["search_keys"].items():
                    field_type = str(
                        dataset_model._meta.get_field(key).get_internal_type()
                    )
                    # print(field_type)
                    if value is not None:
                        if field_type == "TextField":
                            search_dict["%s__search" % key] = value
                        else:
                            search_dict["%s__icontains" % key] = value
                    else:
                        search_dict[key] = value

                data_items = data_items.filter(**search_dict)

            query_params = dict(parse_qsl(filter_string))
            query_params = filter.fix_booleans_in_dict(query_params)
            filtered_set = filter.filter_using_dict_and_queryset(
                query_params, data_items
            )
            # filtered_data = filtered_set.values()
            # serializer = DatasetItemsSerializer(filtered_set, many=True)
            page = request.GET.get("page")
            try:
                page = self.paginate_queryset(filtered_set)
            except Exception as e:
                page = []
                data = page
                return Response(
                    {
                        "status": status.HTTP_200_OK,
                        "message": "No more record.",
                        # TODO: should be results. Needs testing to be sure.
                        "data": data,
                    }
                )

            if page is not None:
                datset_serializer = SERIALIZER_MAP[dataset_type]
                serializer = datset_serializer(page, many=True)
                data = serializer.data
                return self.get_paginated_response(data)

            return Response(
                {
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Error fetching data items!",
                }
            )
        except:
            return Response(
                {
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Error fetching data items!",
                }
            )

    # return Response(filtered_data)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "data_item_start_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "data_item_end_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "data_item_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                ),
            },
            description="Either pass the data_item_start_id and data_item_end_id or the data_item_ids in request body",
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the dataset instance"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "Deleted successfully! or No rows to delete",
            403: "Not authorized!",
            400: "Invalid parameters in the request body!",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="delete_data_items",
        url_name="delete_data_items",
    )
    def delete_data_items(self, request, pk=None):
        try:
            dataset_instance = DatasetInstance.objects.get(pk=pk)

            if (
                (
                    request.user.role == User.ORGANIZATION_OWNER
                    or request.user.is_superuser
                )
                and (request.user.organization == dataset_instance.organisation_id)
            ) == False:
                return Response(
                    {
                        "status": status.HTTP_403_FORBIDDEN,
                        "message": "You are not authorized to access the endpoint.",
                    }
                )
            dataset_type = dataset_instance.dataset_type
            dataset_model = apps.get_model("dataset", dataset_type)

            if "data_item_ids" in request.data:
                data_item_ids = request.data.get("data_item_ids")
                if len(data_item_ids) == 0:
                    return Response(
                        {
                            "status": status.HTTP_400_BAD_REQUEST,
                            "message": "Please enter valid values",
                        }
                    )
            else:
                data_item_start_id = request.data.get("data_item_start_id")
                data_item_end_id = request.data.get("data_item_end_id")
                if (
                    data_item_start_id == ""
                    or data_item_end_id == ""
                    or data_item_start_id == None
                    or data_item_end_id == None
                ):
                    return Response(
                        {
                            "status": status.HTTP_400_BAD_REQUEST,
                            "message": "Please enter valid values",
                        }
                    )

                data_item_ids = [
                    id for id in range(data_item_start_id, data_item_end_id + 1)
                ]

            data_items = dataset_model.objects.filter(
                instance_id=dataset_instance
            ).filter(id__in=data_item_ids)
            num_data_items = len(data_items)

            related_tasks_input_data_ids = [data_item.id for data_item in data_items]

            related_tasks = Task.objects.filter(
                input_data__id__in=related_tasks_input_data_ids
            )

            related_annotations_task_ids = [
                related_task.id for related_task in related_tasks
            ]
            related_annotations = Annotation.objects.filter(
                task__id__in=related_annotations_task_ids
            ).order_by("-id")

            num_related_tasks = len(related_tasks)
            num_related_annotations = len(related_annotations)
            if num_data_items == 0:
                return Response(
                    {
                        "status": status.HTTP_200_OK,
                        "message": "No rows to delete",
                    }
                )

            for related_annotation in related_annotations:
                related_annotation.delete()
            data_items.delete()

            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "message": f"Deleted {num_data_items} data items and {num_related_tasks} related tasks and {num_related_annotations} related annotations successfully!",
                }
            )
        except Exception as error:
            return Response(
                {
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": str(error),
                }
            )


class DatasetTypeView(APIView):
    """
    ViewSet for Dataset Type
    """

    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, dataset_type):
        model = apps.get_model("dataset", dataset_type)
        fields = model._meta.get_fields()
        dict = {}
        for field in fields:
            try:
                dict[field.name] = {
                    "name": str(field.get_internal_type()),
                    "choices": vars(field)["choices"],
                }
            except:
                dict[field.name] = {
                    "name": str(field.get_internal_type()),
                    "choices": None,
                }
        return Response(dict, status=status.HTTP_200_OK)


# class SentenceTextViewSet(viewsets.ModelViewSet):
#     queryset = SentenceText.objects.all()
#     serializer_class = SentenceTextSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class SpeechCollectionViewset(viewsets.ModelViewSet):
#     queryset = SpeechCollection.objects.all()
#     serializer_class = SpeechCollectionSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class SpeechRecognitionViewSet(viewsets.ModelViewSet):
#     queryset = SpeechRecognition.objects.all()
#     serializer_class = SpeechRecognitionSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )


# class MonolingualViewSet(viewsets.ModelViewSet):
#     queryset = Monolingual.objects.all()
#     serializer_class = MonolingualSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class TranslationViewSet(viewsets.ModelViewSet):
#     queryset = Translation.objects.all()
#     serializer_class = TranslationSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class OCRViewSet(viewsets.ModelViewSet):
#     queryset = OCR.objects.all()
#     serializer_class = OCRSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class VideoViewSet(viewsets.ModelViewSet):
#     queryset = Video.objects.all()
#     serializer_class = VideoSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class VideoChunkViewSet(viewsets.ModelViewSet):
#     queryset = VideoChunk.objects.all()
#     serializer_class = VideoChunkSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )
