import resource
from tablib import Dataset
from django.apps import apps
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from django_celery_results.models import TaskResult

from urllib.parse import parse_qsl

from filters import filter
from projects.serializers import ProjectSerializer
from .models import *
from .serializers import *
from .resources import RESOURCE_MAP
from . import resources


## Utility functions used inside the view functions 
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
    task_queryset = TaskResult.objects.filter(
        task_name__in=[
            'projects.tasks.export_project_in_place', 
            'projects.tasks.export_project_new_record'
        ],
        # task_name = 'projects.tasks.export_project_in_place',
        task_kwargs__contains=project_id_keyword_arg,
    ) 

    # If the celery TaskResults table returns
    if task_queryset:

        # Sort the tasks by newest items first by date 
        task_queryset = task_queryset.order_by('-date_done')

        # Get the export task status and last update date
        task_status = task_queryset.first().as_dict()['status']
        task_date = task_queryset.first().as_dict()['date_done']
    
        return task_status, task_date
    
    return "Success", "Synchronously Completed. No Date."

# Create your views here.
class DatasetInstanceViewSet(viewsets.ModelViewSet):
    '''
    ViewSet for Dataset Instance
    '''
    queryset = DatasetInstance.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def get_serializer_class(self):
        if self.action == 'upload':
            return DatasetInstanceUploadSerializer
        return DatasetInstanceSerializer

    def list(self, request, *args, **kwargs):
        if "dataset_type" in dict(request.query_params):
            queryset = DatasetInstance.objects.filter(dataset_type__exact=request.query_params["dataset_type"])
        else:
            queryset = DatasetInstance.objects.all()
        serializer = DatasetInstanceSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['GET'], detail=True, name="Download Dataset in CSV format")
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

        dataset_model = apps.get_model('dataset', dataset_instance.dataset_type)
        data_items = dataset_model.objects.filter(instance_id=pk)
        dataset_resource = getattr(resources, dataset_instance.dataset_type+"Resource")
        exported_items = dataset_resource().export_as_generator(data_items)
        return StreamingHttpResponse(exported_items, status=status.HTTP_200_OK, content_type='text/csv')


    @action(methods=['POST'], detail=True, name="Upload CSV Dataset")
    def upload(self, request, pk):
        '''
        View to upload a dataset in CSV format
        URL: /data/instances/<instance-id>/upload/
        Accepted methods: POST
        '''
        # Get the dataset type using the instance ID
        dataset_type = get_object_or_404(DatasetInstance, pk=pk).dataset_type

        # Fetch the file from the POST request body (key is dataset)
        if 'dataset' not in request.FILES:
            return Response({
                "message": "Please provide a file with key 'dataset'.",
            }, status=status.HTTP_400_BAD_REQUEST)
        dataset = request.FILES['dataset']

        # Ensure that the content type is CSV, return error otherwise
        if dataset.content_type != 'text/csv':
            return Response({
                "message": "Invalid Dataset File. Only accepts .csv files.",
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create a new tablib Dataset and load the data into this dataset
        imported_data = Dataset().load(dataset.read().decode(), format='csv')

        # Add the instance_id column to all rows in the dataset
        imported_data.append_col([pk]*len(imported_data), header="instance_id")

        # Declare the appropriate resource map based on dataset type
        resource = RESOURCE_MAP[dataset_type]()

        # Import the data into the database
        try:
            resource.import_data(imported_data, raise_errors=True)
        # If validation checks fail, raise the Exception
        except Exception as e:
            return Response({
                "message": "Dataset validation failed.",
                "exception": e
            }, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the imported data from the model and return it to the frontend
        model = apps.get_model('dataset', dataset_type)
        data = model.objects.filter(instance_id=pk)
        serializer = SERIALIZER_MAP[dataset_type](data, many=True)
        return Response({
            "message": f"Uploaded {dataset_type} data to Dataset {pk}",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(methods=['GET'], detail=True, name="List all Projects using Dataset")
    def projects(self, request, pk):
        '''
        View to list all projects using a dataset
        URL: /data/instances/<instance-id>/projects/
        Accepted methods: GET
        '''
        # Get the projects using the instance ID
        projects = apps.get_model('projects', 'Project').objects.filter(dataset_id=pk)

        # Serialize the projects and return them to the frontend
        serializer = ProjectSerializer(projects, many=True)

        # Add new fields to the serializer data to show project exprot status and date 
        for project in serializer.data:

            # Get project export status details 
            project_export_status, last_project_export_date = get_project_export_status(project.get('id'))
            project["last_project_export_status"] = project_export_status 
            project["last_project_export_date"] = last_project_export_date

        return Response(serializer.data)


class DatasetItemsViewSet(viewsets.ModelViewSet):
    '''
    ViewSet for Dataset Items
    '''
    queryset = DatasetBase.objects.all()
    serializer_class = DatasetItemsSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )

    @action(detail=False, methods=['POST'], name='Get data Items')
    def get_data_items(self, request, *args, **kwargs):
        try:
            dataset_instance_ids = request.data.get('instance_ids')
            dataset_type = request.data.get('dataset_type',"")
            if type(dataset_instance_ids) != list:
                dataset_instance_ids = [dataset_instance_ids]
            filter_string = request.data.get('filter_string')
            #  Get dataset type from first dataset instance if dataset_type not passed in json data from frontend
            if dataset_type=="":
                dataset_type = DatasetInstance.objects.get(instance_id=dataset_instance_ids[0]).dataset_type
            dataset_model = apps.get_model('dataset', dataset_type)
            data_items = dataset_model.objects.filter(instance_id__in=dataset_instance_ids)
            query_params = dict(parse_qsl(filter_string))
            query_params = filter.fix_booleans_in_dict(query_params)
            filtered_set = filter.filter_using_dict_and_queryset(query_params, data_items)
            # filtered_data = filtered_set.values()
            # serializer = DatasetItemsSerializer(filtered_set, many=True)
            page = request.GET.get('page')
            try:
                page = self.paginate_queryset(filtered_set)
            except Exception as e:
                page = []
                data = page
                return Response({
                    "status": status.HTTP_200_OK,
                    "message": 'No more record.',
                    #TODO: should be results. Needs testing to be sure.
                    "data": data
                })

            if page is not None:
                datset_serializer=SERIALIZER_MAP[dataset_type]
                serializer=datset_serializer(page,many=True)
                data=serializer.data
                return self.get_paginated_response(data)

            return Response({
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "Error fetching data items!"
            })
        except:
            return Response({
                "status":status.HTTP_400_BAD_REQUEST,
                "message":"Error fetching data items!"
                })
        # return Response(filtered_data)


class DatasetTypeView(APIView):
    '''
    ViewSet for Dataset Type
    '''
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def get(self, request, dataset_type):
        model = apps.get_model('dataset', dataset_type)
        fields = model._meta.get_fields()
        dict = {}
        for field in fields:
            try:
                dict[field.name] = {'name':str(field.get_internal_type()),'choices':vars(field)['choices']}
            except:
                dict[field.name] = {'name':str(field.get_internal_type()),'choices':None}
        return Response(dict,status=status.HTTP_200_OK)


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
