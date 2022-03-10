import re
import random
from urllib.parse import parse_qsl
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from users.models import User
from dataset import models as dataset_models
from tasks.models import Task
from .registry_helper import ProjectRegistry

from .serializers import ProjectSerializer, ProjectUsersSerializer
from .models import *
from .decorators import is_organization_owner_or_workspace_manager, project_is_archived, is_particular_workspace_manager, project_is_published
from filters import filter

# Create your views here.

EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

class ProjectViewSet(viewsets.ModelViewSet):
    """
    Project ViewSet
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def retrieve(self, request, pk, *args, **kwargs):
        """
        Retrieves a project given its ID
        """
        print(pk)
        return super().retrieve(request, *args, **kwargs)

    @is_organization_owner_or_workspace_manager    
    def create(self, request, *args, **kwargs):
        """
        Creates a project

        Authenticated only for organization owner or workspace manager
        """
        # Read project details from api request
        project_type_key = request.data.get('project_type')
        project_type = dict(PROJECT_TYPE_CHOICES)[project_type_key]
        dataset_instance_ids = request.data.get('dataset_id')
        filter_string = request.data.get('filter_string')
        sampling_mode = request.data.get('sampling_mode')
        sampling_parameters = request.data.get('sampling_parameters_json')
        
        # Load the dataset model from the instance id using the project registry
        registry_helper = ProjectRegistry.get_instance()
        input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)
        dataset_model = getattr(dataset_models, input_dataset_info["dataset_type"])
        
        # Get items corresponding to the instance id
        data_items = dataset_model.objects.filter(instance_id__in=dataset_instance_ids)
        
        # Apply filtering
        query_params = dict(parse_qsl(filter_string))
        query_params = filter.fix_booleans_in_dict(query_params)
        filtered_items = filter.filter_using_dict_and_queryset(query_params, data_items)

        # Get the input dataset fields from the filtered items
        filtered_items = list(filtered_items.values('data_id', *input_dataset_info["fields"]))

        # Apply sampling
        if sampling_mode == RANDOM:
            try:
                sampling_count = sampling_parameters['count']
            except KeyError:
                sampling_fraction = sampling_parameters['fraction']
                sampling_count = int(sampling_fraction * len(filtered_items))
            
            sampled_items = random.sample(filtered_items, k=sampling_count)
        elif sampling_mode == BATCH:
            batch_size = sampling_parameters['batch_size']
            try:
                batch_number = sampling_parameters['batch_number']
            except KeyError:
                batch_number = 1
            sampled_items = filtered_items[batch_size*(batch_number-1):batch_size*(batch_number)]
        else:
            sampled_items = filtered_items
        
        # Create project object
        project_response = super().create(request, *args, **kwargs)
        project_id = project_response.data["id"]
        project = Project.objects.get(pk=project_id)

        # Create task objects
        tasks = []
        for item in sampled_items:
            data_id = item['data_id']
            data = dataset_models.DatasetBase.objects.get(pk=data_id)
            del item['data_id']
            task = Task(
                data=item,
                project_id=project,
                data_id = data
            )
            tasks.append(task)
        
        # Bulk create the tasks
        Task.objects.bulk_create(tasks)

        # Return the project response
        return project_response


    @is_particular_workspace_manager
    @project_is_archived
    def update(self, request, pk=None, *args, **kwargs):
        '''
        Update project details
        '''
        return super().update(request, *args, **kwargs)        
    
    @is_particular_workspace_manager
    @project_is_archived
    def partial_update(self, request, pk=None, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @is_organization_owner_or_workspace_manager    
    @project_is_published
    def destroy(self, request, pk=None, *args, **kwargs):
        '''
        Delete a project
        '''
        return super().delete(request, *args, **kwargs)
    
    # TODO : add exceptions
    @action(detail=True, methods=['POST', 'GET'], name='Archive Project')
    @is_particular_workspace_manager
    def archive(self, request, pk=None, *args, **kwargs):
        '''
        Archive a published project
        '''
        print(pk)
        project = Project.objects.get(pk=pk)
        project.is_archived = not project.is_archived
        project.save()
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['GET'], name="Get Project Users", url_name='get_project_users')
    @project_is_archived
    def get_project_users(self, request, pk=None, *args, **kwargs):
        '''
        Get the list of annotators in the project
        '''
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
    
    @action(detail=True, methods=['POST'], name="Add Project Users", url_name="add_project_users")
    @project_is_archived
    @is_particular_workspace_manager
    def add_project_users(self, request, pk=None, *args, **kwargs):
        '''
        Add annotators to the project
        '''
        ret_dict = {}
        ret_status = 0
        try:
            project = Project.objects.get(pk=pk)
            emails = request.data.get('emails')
            for email in emails:
                if re.fullmatch(EMAIL_REGEX, email):
                    user = User.objects.get(email=email)
                    project.users.add(user)
                    project.save()
                else:
                    print("Invalid Email")
            ret_dict = {"message": "Users added!"}
            ret_status = status.HTTP_201_CREATED
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)
    
    @action(detail=False, methods=['GET'], name="Get Project Types", url_name="get_project_types")
    @project_is_archived
    @is_organization_owner_or_workspace_manager
    def get_project_types(self, request, *args, **kwargs):
        project_registry = ProjectRegistry()
        try:
            return Response(project_registry.data, status=status.HTTP_200_OK)
        except Exception:
            print(Exception.args)
            return Response({"message": "Error Occured"}, status=status.HTTP_400_BAD_REQUEST)

 