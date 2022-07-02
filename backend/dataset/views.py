import ast
from base64 import b64encode
from urllib.parse import parse_qsl

from django.apps import apps
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django_celery_results.models import TaskResult
from filters import filter
from projects.serializers import ProjectSerializer
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from . import resources
from .models import *
from .serializers import *
from .tasks import upload_data_to_data_instance
from users.serializers import UserFetchSerializer


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
    permission_classes = (IsAuthenticatedOrReadOnly,)

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
            dataset_instance_result
        ) = get_dataset_upload_status(pk)

        # Add the task status and time to the dataset instance response
        dataset_instance_response.data["last_upload_status"] = dataset_instance_status
        dataset_instance_response.data["last_upload_date"] = dataset_instance_date
        dataset_instance_response.data["last_upload_time"] = dataset_instance_time
        dataset_instance_response.data["last_upload_result"] = dataset_instance_result

        return dataset_instance_response

    def list(self, request, *args, **kwargs):
        if "dataset_type" in dict(request.query_params):
            queryset = DatasetInstance.objects.filter(
                dataset_type__exact=request.query_params["dataset_type"]
            )
        else:
            queryset = DatasetInstance.objects.all()
        serializer = DatasetInstanceSerializer(queryset, many=True)

        # Add status fields to the serializer data
        for dataset_instance in serializer.data:

            # Get the task statuses for the dataset instance
            (
                dataset_instance_status,
                dataset_instance_date,
                dataset_instance_time,
                dataset_instance_result
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
        try:
            # Get the dataset instance for the id
            dataset_instance = DatasetInstance.objects.get(instance_id=pk)
        except DatasetInstance.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        dataset_model = apps.get_model("dataset", dataset_instance.dataset_type)
        data_items = dataset_model.objects.filter(instance_id=pk)
        dataset_resource = getattr(
            resources, dataset_instance.dataset_type + "Resource"
        )
        exported_items = dataset_resource().export_as_generator(data_items)
        return StreamingHttpResponse(
            exported_items, status=status.HTTP_200_OK, content_type="text/csv"
        )

    @action(methods=["POST"], detail=True, name="Upload Dataset File")
    def upload(self, request, pk):
        """
        View to upload a dataset from a file
        URL: /data/instances/<instance-id>/upload/
        Accepted methods: POST
        """
        # Define list of accepted file formats
        ACCEPTED_FILETYPES = ['csv', 'tsv', 'json', 'yaml', 'xls', 'xlsx']

        # Get the dataset type using the instance ID
        dataset_type = get_object_or_404(DatasetInstance, pk=pk).dataset_type

        if 'dataset' not in request.FILES:
            return Response({
                "message": "Please provide a file with key 'dataset'.",
            }, status=status.HTTP_400_BAD_REQUEST)
        dataset = request.FILES['dataset']
        content_type = dataset.name.split('.')[-1]

        # Ensure that the content type is accepted, return error otherwise
        if content_type not in ACCEPTED_FILETYPES:
            return Response({
                "message": f"Invalid Dataset File. Only accepts the following file formats: {ACCEPTED_FILETYPES}",
            }, status=status.HTTP_400_BAD_REQUEST)

        # Read the dataset as a string from the dataset pointer
        try:
            if content_type in ['xls', 'xlsx']:
                # xls and xlsx files cannot be decoded as a string
                dataset_string = b64encode(dataset.read()).decode()
            else:
                dataset_string = dataset.read().decode()
        except Exception as e:
            return Response({
                "message": f"Error while reading file. Please check the file data and try again.",
                "exception": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Uplod the dataset to the dataset instance
        upload_data_to_data_instance.delay(
            pk=pk,
            dataset_type=dataset_type,
            dataset_string=dataset_string,
            content_type=content_type
        )

        # Get name of the dataset instance
        dataset_name = get_object_or_404(DatasetInstance, pk=pk).instance_name
        return Response(
            {
                "message": f"Uploading {dataset_type} data to Dataset Instance: {dataset_name}",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['GET'], detail=True, name="List all Projects using Dataset")
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

    @action(methods=['GET'], detail=True, name="List all Users using Dataset")
    def users(self, request, pk):
        users = User.objects.filter(dataset_users__instance_id=pk)
        serializer = UserFetchSerializer(many=True, data=users)
        serializer.is_valid()
        return Response(serializer.data)


class DatasetItemsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Dataset Items
    """

    queryset = DatasetBase.objects.all()
    serializer_class = DatasetItemsSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

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
