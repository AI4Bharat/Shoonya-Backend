import email
import re
import random
import json
from collections import OrderedDict
from urllib.parse import parse_qsl
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.core.mail import send_mail
from django.conf import settings
from django.forms.models import model_to_dict
import pandas as pd

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from users.models import User
from tasks.models import Task
from dataset import models as dataset_models
from tasks.models import *
from tasks.models import Annotation as Annotation_model
from tasks.serializers import TaskSerializer
from .registry_helper import ProjectRegistry

from projects.serializers import ProjectSerializer, ProjectUsersSerializer
from tasks.serializers import TaskSerializer
from .models import *
from .decorators import is_organization_owner_or_workspace_manager, project_is_archived, is_particular_workspace_manager, project_is_published
from filters import filter
from utils.monolingual.sentence_splitter import split_sentences


# Create your views here.

EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

PROJECT_IS_PUBLISHED_ERROR = {
    'message': 'This project is already published!'
}

def get_task_field(annotation_json, field):
    return annotation_json[field]

def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx : min(ndx + n, l)]


def create_tasks_from_dataitems(items, project):

    project_type = project.project_type
    registry_helper = ProjectRegistry.get_instance()
    input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)
    output_dataset_info = registry_helper.get_output_dataset_and_fields(project_type)
    variable_parameters = project.variable_parameters
    # Create task objects
    tasks = []
    for item in items:
        data_id = item['id']
        if "variable_parameters" in output_dataset_info['fields']:
            for var_param in output_dataset_info['fields']['variable_parameters']:
                item[var_param] = variable_parameters[var_param]
        if "copy_from_input" in output_dataset_info['fields']:
            for input_field, output_field in output_dataset_info['fields']['copy_from_input'].items():
                item[output_field] = item[input_field]
                del item[input_field]
        data = dataset_models.DatasetBase.objects.get(pk=data_id)
        # Remove data id because it's not needed in task.data
        del item['id']
        task = Task(
            data=item,
            project_id=project,
            input_data = data
        )
        tasks.append(task)
    
    # Bulk create the tasks
    Task.objects.bulk_create(tasks)

    if input_dataset_info['prediction'] is not None:
        user_object = User.objects.get(email="prediction@ai4bharat.org")

        predictions = []
        prediction_field = input_dataset_info['prediction']
        for task,item in zip(tasks,items):

            if project_type == "SentenceSplitting":
                item[prediction_field] = [{
                    "value": {
                        "text": [
                            "\n".join(split_sentences(item["text"], item["language"]))
                        ]
                    },
                    "id": "0",
                    "from_name": "splitted_text",
                    "to_name": "text",
                    "type": "textarea"
                }]
            prediction = Annotation_model(
                result=item[prediction_field],
                task=task,
                completed_by=user_object
            )
            predictions.append(prediction)
        # 
        # Prediction.objects.bulk_create(predictions)
        Annotation_model.objects.bulk_create(predictions)


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
        return super().retrieve(request, *args, **kwargs)
      
      
    def list(self, request, *args, **kwargs):
        """
        List all Projects
        """
        try:
            # projects = self.queryset.filter(users=request.user)
  
            if request.user.role == User.ORGANIZAION_OWNER:
                projects = self.queryset.filter(organization_id=request.user.organization)
            else:
                projects = self.queryset.filter(users=request.user)
            projects_json = self.serializer_class(projects, many=True)
            return Response(projects_json.data, status=status.HTTP_200_OK)
        except Exception:
            return Response({"message": "Please Login!"}, status=status.HTTP_400_BAD_REQUEST)

          
    @action(detail=True, methods=['post'], url_name='remove')
    def remove_user(self, request, pk=None):
        try:
            email = request.data['email']
            user = User.objects.get(email=email)
            project = Project.objects.get(pk=pk)
            project.user.remove(user)
            project.save()
            return Response({'message': "User removed"}, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except:
            return Response({"message": "Server Error occured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='next')
    def next(self, request, pk):
        project = Project.objects.get(pk=pk)

        # Check if there are unlabelled tasks
        unlabelled_tasks = Task.objects.filter(project_id__exact=project.id, task_status__exact=UNLABELED)
        unlabelled_tasks = unlabelled_tasks.order_by('id')
        for task in unlabelled_tasks:
            if not task.is_locked(request.user):
                task.set_lock(request.user)
                task_dict = TaskSerializer(task, many=False).data
                return Response(task_dict)
        
        # Check if there are skipped tasks
        skipped_tasks = Task.objects.filter(project_id__exact=project.id, task_status__exact=SKIPPED)
        skipped_tasks = skipped_tasks.order_by('id')
        for task in skipped_tasks:
            if not task.is_locked(request.user):
                task.set_lock(request.user)
                task_dict = TaskSerializer(task, many=False).data
                return Response(task_dict)

        ret_dict = {"message": "No more unlabeled tasks!"}
        ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)


    @is_organization_owner_or_workspace_manager    
    def create(self, request, *args, **kwargs):
        """
        Creates a project

        Authenticated only for organization owner or workspace manager
        """
        # Read project details from api request
        project_type = request.data.get('project_type')
        project_mode = request.data.get('project_mode')

        if project_mode == Collection:
            # Create project object
            project_response = super().create(request, *args, **kwargs)
        
        else:
            dataset_instance_ids = request.data.get('dataset_id')
            if type(dataset_instance_ids) != list:
                dataset_instance_ids = [dataset_instance_ids]
            filter_string = request.data.get('filter_string')
            sampling_mode = request.data.get('sampling_mode')
            sampling_parameters = request.data.get('sampling_parameters_json')
            variable_parameters = request.data.get('variable_parameters')
            
            # Load the dataset model from the instance id using the project registry
            registry_helper = ProjectRegistry.get_instance()
            input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)
            output_dataset_info = registry_helper.get_output_dataset_and_fields(project_type)

            dataset_model = getattr(dataset_models, input_dataset_info["dataset_type"])
            
            # Get items corresponding to the instance id
            data_items = dataset_model.objects.filter(instance_id__in=dataset_instance_ids)

            
            # Apply filtering
            query_params = dict(parse_qsl(filter_string))
            query_params = filter.fix_booleans_in_dict(query_params)
            filtered_items = filter.filter_using_dict_and_queryset(query_params, data_items)

            # Get the input dataset fields from the filtered items
            if input_dataset_info['prediction'] is not None:
                filtered_items = list(filtered_items.values('id', *input_dataset_info["fields"], input_dataset_info['prediction']))
            else:
                filtered_items = list(filtered_items.values('id', *input_dataset_info["fields"]))



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

            # Set the labelstudio label config
            label_config = registry_helper.get_label_studio_jsx_payload(project_type)

            project.label_config = label_config
            project.save()

            create_tasks_from_dataitems(sampled_items, project)

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

    @action(detail=True, methods=['GET'], name="Get Tasks of a Project", url_name='get_project_tasks')
    @project_is_archived
    def get_project_tasks(self, request, pk=None, *args, **kwargs):
        '''
        Get the list of tasks in the project
        '''
        ret_dict = {}
        ret_status = 0
        try:
            tasks = Task.objects.filter(project_id=pk)
            serializer = TaskSerializer(tasks, many=True)
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
            invalid_emails = []
            for email in emails:
                if re.fullmatch(EMAIL_REGEX, email):
                    user = User.objects.get(email=email)
                    project.users.add(user)
                    project.save()
                else:
                    invalid_emails.append(email)
            if len(invalid_emails) != 0:
                ret_dict = {"message": "Users added!"}
                ret_status = status.HTTP_201_CREATED
            else:
                ret_dict = {"message": f"Users partially added! Invalid emails: {','.join(invalid_emails)}"}
                ret_status = status.HTTP_201_CREATED
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)
    
    @action(detail=False, methods=['GET'], name="Get Project Types", url_name="types")
    @is_organization_owner_or_workspace_manager
    def types(self, request, *args, **kwargs):
        # project_registry = ProjectRegistry()
        try:
            return Response(ProjectRegistry.get_instance().data, status=status.HTTP_200_OK)
        except Exception:
            print(Exception.args)
            return Response({"message": "Error Occured"}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_task_queryset(self, queryset):
        return queryset
    
    @action(detail=True, methods=['POST'], name='Pull new items')
    @project_is_archived
    @is_organization_owner_or_workspace_manager
    def pull_new_items(self, request, pk=None, *args, **kwargs):
        try:
            project = Project.objects.get(pk=pk)
            if project.sampling_mode != FULL:
                ret_dict = {"message": "Sampling Mode is not FULL!"}         
                ret_status = status.HTTP_403_FORBIDDEN
            else:
                project_type = project.project_type
                registry_helper = ProjectRegistry.get_instance()
                input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)
                dataset_model = getattr(dataset_models, input_dataset_info["dataset_type"])
                tasks = Task.objects.filter(project_id__exact=project)
                all_items = dataset_model.objects.filter(instance_id__in=list(project.dataset_id.all()))
                items = all_items.exclude(id__in=tasks.values('input_data'))
                # Get the input dataset fields from the filtered items
                if input_dataset_info['prediction'] is not None:
                    items = list(items.values('id', *input_dataset_info["fields"], input_dataset_info['prediction']))
                else:
                    items = list(items.values('id', *input_dataset_info["fields"]))

                create_tasks_from_dataitems(items, project)
                ret_dict = {"message": "SUCCESS!"}         
                ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)
        

    @action(detail=True, methods=['POST'], name='Export Project')
    @project_is_archived
    @is_organization_owner_or_workspace_manager
    def project_export(self, request, pk=None, *args, **kwargs):
        '''
        Export a project
        '''
        try:
            project = Project.objects.get(pk=pk)
            project_type = dict(PROJECT_TYPE_CHOICES)[project.project_type]
            # Read registry to get output dataset model, and output fields
            registry_helper = ProjectRegistry.get_instance()
            output_dataset_info = registry_helper.get_output_dataset_and_fields(project_type)

            dataset_model = getattr(dataset_models, output_dataset_info["dataset_type"])

            # If save_type is 'in_place'
            if output_dataset_info['save_type'] == 'in_place':
                annotation_fields = output_dataset_info["fields"]["annotations"]
                data_items = []
                tasks = Task.objects.filter(project_id__exact=project)

                tasks_list = []
                annotated_tasks = []
                for task in tasks:
                    task_dict = model_to_dict(task)
                    # Rename keys to match label studio converter
                    # task_dict['id'] = task_dict['task_id']
                    # del task_dict['task_id']
                    if task.correct_annotation is not None:
                        annotated_tasks.append(task)
                        annotation_dict = model_to_dict(task.correct_annotation)
                        # annotation_dict['result'] = annotation_dict['result_json']
                        # del annotation_dict['result_json']
                        task_dict['annotations'] = [OrderedDict(annotation_dict)]
                    del task_dict['annotation_users']
                    del task_dict['review_user']
                    tasks_list.append(OrderedDict(task_dict))
                download_resources=True
                tasks_df = DataExport.export_csv_file(
                    project, tasks_list, download_resources, request.GET
                )
                tasks_annotations = json.loads(tasks_df.to_json(orient='records'))

                for (ta, tl, task) in zip(tasks_annotations, tasks_list, annotated_tasks):

                    task.output_data = task.input_data
                    task.save()
                    data_item = dataset_model.objects.get(id__exact=tl["input_data"])
                    for field in annotation_fields:
                        setattr(data_item, field, ta[field])
                    data_items.append(data_item)

                # Write json to dataset columns
                dataset_model.objects.bulk_update(data_items, annotation_fields)
            
            # If save_type is 'new_record'
            elif output_dataset_info['save_type'] == 'new_record':
                export_dataset_instance_id = request.data['export_dataset_instance_id']
                export_dataset_instance = dataset_models.DatasetInstance.objects.get(instance_id__exact=export_dataset_instance_id)

                annotation_fields = output_dataset_info["fields"]["annotations"]
                task_annotation_fields = []
                if "variable_parameters" in output_dataset_info["fields"]:
                    task_annotation_fields += output_dataset_info["fields"]["variable_parameters"]
                if "copy_from_input" in output_dataset_info["fields"]:
                    task_annotation_fields += list(output_dataset_info["fields"]["copy_from_input"].values())

                data_items = []
                tasks = Task.objects.filter(project_id__exact=project)

                tasks_list = []
                annotated_tasks = [] # 
                for task in tasks:
                    task_dict = model_to_dict(task)
                    # Rename keys to match label studio converter
                    # task_dict['id'] = task_dict['task_id']
                    # del task_dict['task_id']
                    if project.project_mode == Annotation:
                        if task.correct_annotation is not None:
                            annotated_tasks.append(task)
                            annotation_dict = model_to_dict(task.correct_annotation)
                            # annotation_dict['result'] = annotation_dict['result_json']
                            # del annotation_dict['result_json']
                            task_dict['annotations'] = [OrderedDict(annotation_dict)]
                    elif project.project_mode == Collection:
                        annotated_tasks.append(task)

                    del task_dict['annotation_users']
                    del task_dict['review_user']
                    tasks_list.append(OrderedDict(task_dict))

                if project.project_mode == Collection:
                    for (tl,task) in zip(tasks_list, annotated_tasks):
                        if task.output_data is not None:
                            data_item = dataset_model.objects.get(id__exact=task.output_data.id)
                        else:
                            data_item = dataset_model()
                            data_item.instance_id = export_dataset_instance

                        for field in annotation_fields:
                            setattr(data_item, field, tl["data"][field])
                        for field in task_annotation_fields:
                            setattr(data_item, field, tl["data"][field])

                        data_item.save()
                        task.output_data = data_item
                        task.save()
                
                elif project.project_mode == Annotation:

                    download_resources=True
                    # export_stream, content_type, filename = DataExport.generate_export_file(
                    #     project, tasks_list, 'CSV', download_resources, request.GET
                    # )
                    tasks_df = DataExport.export_csv_file(
                        project, tasks_list, download_resources, request.GET
                    )
                    tasks_annotations = json.loads(tasks_df.to_json(orient='records'))
                    

                    for (ta,task) in zip(tasks_annotations, annotated_tasks):
                        # data_item = dataset_model.objects.get(id__exact=task.id.id)
                        if task.output_data is not None:
                            data_item = dataset_model.objects.get(id__exact=task.output_data.id)
                        else:
                            data_item = dataset_model()
                            data_item.instance_id = export_dataset_instance
                            data_item.parent_data = task.input_data

                        for field in annotation_fields:
                            setattr(data_item, field, ta[field])
                        for field in task_annotation_fields:
                            setattr(data_item, field, ta[field])

                        data_item.save()
                        task.output_data = data_item
                        task.save()

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

    @action(detail=True, methods=['POST', 'GET'], name='Publish Project')
    @project_is_archived
    @is_organization_owner_or_workspace_manager
    def project_publish(self, request, pk=None, *args, **kwargs):
        '''
        Publish a project
        '''
        try:
            project = Project.objects.get(pk=pk)

            if project.is_published:
                return Response(PROJECT_IS_PUBLISHED_ERROR, status=status.HTTP_200_OK)

            serializer = ProjectUsersSerializer(project, many=False)
            #ret_dict = serializer.data
            users = serializer.data['users']
           
            project.is_published = True
            project.save()

            for user in users:
                userEmail = user['email']
                
                send_mail("Annotation Tasks Assigned",
                f"Hello! You are assigned to tasks in the project {project.title}.",
                settings.DEFAULT_FROM_EMAIL, [userEmail],
                )

            ret_dict = {"message": "This project is published"}
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)
        

    

 