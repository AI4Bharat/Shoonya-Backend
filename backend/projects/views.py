import email
import re
import random
import json
from collections import OrderedDict
from typing import Dict
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
from django.http import HttpResponse
from django.core.files import File
import pandas as pd
from datetime import datetime
from django.db.models import Q
from .word_count import no_of_words
from users.serializers import UserEmailSerializer

from utils.search import process_search_query

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
from django_celery_results.models import TaskResult
from tasks.serializers import TaskSerializer
from .registry_helper import ProjectRegistry

# Import celery tasks
from .tasks import create_parameters_for_task_creation, create_tasks_from_dataitems, export_project_in_place, export_project_new_record

from projects.serializers import ProjectSerializer, ProjectUsersSerializer
from tasks.serializers import TaskSerializer
from .models import *
from .decorators import (
    is_organization_owner_or_workspace_manager,
    project_is_archived,
    is_particular_workspace_manager,
    project_is_published,
)
from filters import filter
from utils.monolingual.sentence_splitter import split_sentences
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from .utils import is_valid_date



# Create your views here.

EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

PROJECT_IS_PUBLISHED_ERROR = {"message": "This project is already published!"}

def get_task_field(annotation_json, field):
    return annotation_json[field]


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx : min(ndx + n, l)]

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
        task_datetime = task_queryset.first().as_dict()['date_done']

        # Extract date and time from the datetime object 
        task_date = task_datetime.date()
        task_time = str(task_datetime.time().replace(microsecond=0)) + " UTC"
    
        return task_status, task_date, task_time
    
    return "Success", "Synchronously Completed. No Date.", "Synchronously Completed. No Time."

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
    task_queryset = TaskResult.objects.filter(
        task_name='projects.tasks.create_parameters_for_task_creation',
        task_kwargs__contains=project_id_keyword_arg,
    )

    # If the celery TaskResults table returns 
    if task_queryset: 
        task_creation_status = task_queryset.first().as_dict()['status']

        # Check if the task has failed 
        if task_creation_status == 'FAILURE': 
            return "Task Creation Process Failed!"

        if task_creation_status != 'SUCCESS':
            return "Creating Annotation Tasks."

    # If the background task function has already run, check the status of the project
    if project.is_archived:
        return "Archived"
    elif project.is_published:
        return "Published"
    else:
        return "Draft"

def assign_users_to_tasks(tasks, users):
    annotatorList = []
    for user in users:
        userRole = user["role"]
        user_obj = User.objects.get(pk=user["id"])
        if userRole == 1 and not user_obj.is_superuser:
            annotatorList.append(user)

    total_tasks = len(tasks)
    total_users = len(annotatorList)
    # print("Total Users: ",total_users)
    # print("Total Tasks: ",total_tasks)

    tasks_per_user = total_tasks // total_users
    chunk = tasks_per_user if total_tasks % total_users == 0 else tasks_per_user + 1
    # print(chunk)

    # updated_tasks = []
    for c in range(total_users):
        st_idx = c * chunk
        # if c == chunk - 1:
        #     en_idx = total_tasks
        # else:
        #     en_idx = (c+1) * chunk

        en_idx = total_tasks if (c + 1) * chunk > total_tasks else (c + 1) * chunk

        user_obj = User.objects.get(pk=annotatorList[c]["id"])
        for task in tasks[st_idx:en_idx]:
            task.annotation_users.add(user_obj)
            # updated_tasks.append(task)
            task.save()


class ProjectViewSet(viewsets.ModelViewSet):
    """
    Project ViewSet
    """

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def retrieve(self, request, pk, *args, **kwargs):
        """
        Retrieves a project given its ID
        """
        project_response = super().retrieve(request, *args, **kwargs)
 
        # Add a new field to the project response to indicate project status
        project_response.data["status"] = get_project_creation_status(pk)
        
        # Add a new field to the project to indicate the async project export status and last export date
        project_export_status, last_project_export_date, last_project_export_time = get_project_export_status(pk)
        project_response.data["last_project_export_status"] = project_export_status
        project_response.data["last_project_export_date"] = last_project_export_date
        project_response.data["last_project_export_time"] = last_project_export_time

        return project_response

    def list(self, request, *args, **kwargs):
        """
        List all Projects
        """
        try:
            # projects = self.queryset.filter(users=request.user)

            if request.user.role == User.ORGANIZAION_OWNER:
                projects = self.queryset.filter(
                    organization_id=request.user.organization
                )
            else:
                projects = self.queryset.filter(users=request.user)
            projects_json = self.serializer_class(projects, many=True)
            return Response(projects_json.data, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"message": "Please Login!"}, status=status.HTTP_400_BAD_REQUEST
            )
    
    @swagger_auto_schema(
        method='post',
        request_body=UserEmailSerializer,
        responses={
            201:"User removed",
            404:"User does not exist",
            500:"Server error occured"
        }
    )
    @action(detail=True, methods=["post"], url_name="remove")
    def remove_user(self, request, pk=None):
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
    
    @swagger_auto_schema(
        method="post",
        manual_parameters=[
            openapi.Parameter(
                "task_status",openapi.IN_QUERY,
                description=("A string that denotes the status of task"),
                type=openapi.TYPE_STRING,
                enum=[task_status[0] for task_status in TASK_STATUS],
                required=False
            ),
            openapi.Parameter(
                "current_task_id",openapi.IN_QUERY,
                description=("The unique id identifying the current task"),
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={},
        ),
        responses={
            201:TaskSerializer,
            204:"No more tasks available! or No more unlabeled tasks!"
            }
    )
    @action(detail=True, methods=["post"], url_path="next")
    def next(self, request, pk):
        project = Project.objects.get(pk=pk)
        user_role = request.user.role

        # Check if task_status is passed
        if "task_status" in dict(request.query_params):

            if user_role == 1 and not request.user.is_superuser:
                queryset = Task.objects.filter(
                    project_id__exact=project.id,
                    annotation_users=request.user.id,
                    task_status=request.query_params["task_status"],
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
            # Check if there are unlabelled tasks
            if user_role == 1 and not request.user.is_superuser:
                unlabelled_tasks = Task.objects.filter(
                    project_id__exact=project.id,
                    annotation_users=request.user.id,
                    task_status__exact=UNLABELED,
                )
            else:
                # TODO : Refactor code to reduce DB calls
                unlabelled_tasks = Task.objects.filter(
                    project_id__exact=project.id, task_status__exact=UNLABELED
                )

            unlabelled_tasks = unlabelled_tasks.order_by("id")

            if "current_task_id" in dict(request.query_params):
                current_task_id = request.query_params["current_task_id"]
                unlabelled_tasks = unlabelled_tasks.filter(id__gt=current_task_id)

            for task in unlabelled_tasks:
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

    @is_particular_workspace_manager
    @project_is_archived
    def update(self, request, pk=None, *args, **kwargs):
        """
        Update project details
        """
        return super().update(request, *args, **kwargs)

    @is_particular_workspace_manager
    @project_is_archived
    def partial_update(self, request, pk=None, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @is_organization_owner_or_workspace_manager
    @project_is_published
    def destroy(self, request, pk=None, *args, **kwargs):
        """
        Delete a project
        """
        return super().delete(request, *args, **kwargs)

    # TODO : add exceptions
    @action(detail=True, methods=["POST", "GET"], name="Archive Project")
    @is_particular_workspace_manager
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
        url_name="get_project_users",
    )
    @project_is_archived
    def get_project_users(self, request, pk=None, *args, **kwargs):
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
                request.user.role == User.ORGANIZAION_OWNER
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
    
    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "from_date":openapi.Schema(type=openapi.TYPE_STRING,description="The start date",format="date"),
                "to_date":openapi.Schema(type=openapi.TYPE_STRING,description="The end date",format="date")
            },
            required=["from_date","to_date"]
        ),
        responses={
            200:openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "username":openapi.Schema(type=openapi.TYPE_STRING),
                        "mail":openapi.Schema(type=openapi.TYPE_STRING,format="email"),
                        "total_annoted_tasks":openapi.Schema(type=openapi.TYPE_INTEGER),
                        "avg_lead_time":openapi.Schema(type=openapi.TYPE_NUMBER,format="float"),
                        "total_assigned_tasks":openapi.Schema(type=openapi.TYPE_INTEGER),
                        "skipped_tasks":openapi.Schema(type=openapi.TYPE_INTEGER),
                        "total_pending_tasks":openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                    )
            ),
            404:"Project does not exist!"
        }
    )
    @action(
    detail=True,
    methods=["POST"],
    name="Get Reports  of a Project",
    url_name="get_analytics"
    )
    @project_is_archived
    def get_analytics(self, request, pk=None, *args, **kwargs):
        """
        Get Reports of a Project
        """
        ret_dict = {}
        count=0
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        from_date = from_date + ' 00:00'
        to_date = to_date + ' 23:59'

        cond, invalid_message = is_valid_date(from_date)
        if not cond:
            return Response({"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST)
        
        cond, invalid_message = is_valid_date(to_date)
        if not cond:
            return Response({"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST)

        start_date = datetime.strptime(from_date, '%Y-%m-%d %H:%M')
        end_date = datetime.strptime(to_date, '%Y-%m-%d %H:%M')

        if start_date > end_date:
            return Response({"message": "'To' Date should be after 'From' Date"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if (
                request.user.role == User.ORGANIZAION_OWNER
                or request.user.role == User.WORKSPACE_MANAGER
                or request.user.is_superuser
            ):
                project_details = Project.objects.filter(id=pk)
                project_type =  project_details[0].project_type
                project_type =  project_type.lower()
                is_translation_project = True if  "translation" in  project_type else False

                project_users = project_details.values('users')
                final_result = []
                for each_user in project_users:
                    userid = each_user['users']
                    this_project_task_id = Task.objects.filter(project_id=pk).order_by(
                        'id'
                    )
                    all_ids_related_to_project = this_project_task_id.values("id")
                    annoted_tasks = Annotation_model.objects.filter(Q(completed_by = userid)& Q(created_at__range = [start_date, end_date]) & Q(task__task_status="accepted")).order_by('id')
                    annoted_tasks_ids = annoted_tasks.values('task_id')
                    project_related_ids = []
                    all_task_ids = []
                    for i in all_ids_related_to_project:
                        project_related_ids.append(i['id'])
                    for j in annoted_tasks_ids:
                        all_task_ids.append(j['task_id'])

                    set1 = set(project_related_ids)
                    set2 = set(all_task_ids)
                    count = len(set1.intersection(set2))
                    if count == 0:
                        avg_leadtime = 0
                        word_count1 = 0
                    else :
                        project_user_tasks_ids =  list(set1.intersection(set2))
                        lead_time = 0
                        word_count1 = 0
                        for each_id in project_user_tasks_ids:
                            annot_object1 = Annotation_model.objects.get(
                                task_id=each_id
                            )
                            lead_time += annot_object1.lead_time
                            task_object = Task.objects.get(id = each_id)
                            if is_translation_project :
                                word_count1 = (
                                    no_of_words(task_object.data['input_text'])
                                ) + word_count1
                        avg_leadtime = lead_time / count 
                        avg_leadtime = round(avg_leadtime,2)
                    user_details = User.objects.get(id=userid)
                    each_usermail = user_details.email
                    user_name = user_details.username
                    user_id = user_details.id

                    all_tasks_in_project = Task.objects.filter(
                        Q(project_id=pk) & Q(annotation_users=user_id)
                    ).order_by("id")
                    total_tasks = len(all_tasks_in_project.values())

                    all_skipped_tasks_in_project = Task.objects.filter(
                        Q(project_id=pk)
                        & Q(task_status="skipped")
                        & Q(annotation_users=user_id)
                    ).order_by("id")
                    total_skipped_tasks = len(all_skipped_tasks_in_project.values())

                    all_pending_tasks_in_project =  Task.objects.filter(Q(project_id = pk) & Q(task_status = "unlabeled") & Q(annotation_users = user_id) ).order_by('id')
                    total_unlabeled_tasks = len(all_pending_tasks_in_project.values())

                    all_draft_tasks_in_project =  Task.objects.filter(Q(project_id = pk) & Q(task_status = "draft") & Q(annotation_users = user_id)).order_by('id')
                    total_draft_tasks = len(all_draft_tasks_in_project.values())
                    #pending_tasks = total_tasks -( count + total_skipped_tasks )
                    if is_translation_project :
                        final_result.append({"Username":user_name,"Email":each_usermail , "Annotated Tasks" : count ,"Average Annotation Time (In Seconds)" : round(avg_leadtime, 2), "Assigned Tasks" : total_tasks,"Skipped Tasks" : total_skipped_tasks , "Unlabeled Tasks" : total_unlabeled_tasks, "Draft Tasks": total_draft_tasks , "Word Count" : word_count1})
                    else:
                        final_result.append({"Username":user_name,"Email":each_usermail , "Annotated Tasks" : count ,"Average Annotation Time (In Seconds)" : round(avg_leadtime, 2), "Assigned Tasks" : total_tasks,"Skipped Tasks" : total_skipped_tasks , "Unlabeled Tasks" : total_unlabeled_tasks, "Draft Tasks": total_draft_tasks })

                ret_status = status.HTTP_200_OK



            elif request.user.role == User.ANNOTATOR:
                project_details = Project.objects.filter(id=pk)
                project_type =  project_details[0].project_type
                project_type =  project_type.lower()
                is_translation_project = True if  "translation" in  project_type else False

                user_details = User.objects.get(email = request.user.email)
                userid = user_details.id
                this_project_task_id = Task.objects.filter(project_id = pk).order_by(
                    'id'
                )
                all_ids_related_to_project = this_project_task_id.values("id")
                annoted_tasks = Annotation_model.objects.filter(
                    Q(completed_by=userid) & Q(created_at__range=[start_date, end_date]) & Q(task__task_status="accepted")
                ).order_by("id")
                annoted_tasks_ids = annoted_tasks.values("task_id")
                project_related_ids = []
                all_task_ids = []
                for i in all_ids_related_to_project:
                    project_related_ids.append(i['id'])
                for j in annoted_tasks_ids:
                    all_task_ids.append(j['task_id'])

                set1 = set(project_related_ids)
                set2 = set(all_task_ids)
                count = len(set1.intersection(set2))

                if count == 0:
                    avg_leadtime = 0
                    word_count1 = 0
                else :
                    project_user_tasks_ids =  list(set1.intersection(set2))
                    lead_time = 0
                    word_count1 = 0
                    for each_id in project_user_tasks_ids:
                        annot_object1 = Annotation_model.objects.get(task_id=each_id)
                        lead_time += annot_object1.lead_time
                        task_object = Task.objects.get(id = each_id)
                        if is_translation_project :
                            word_count1 = (
                                no_of_words(task_object.data['input_text'])
                            ) + word_count1
                    avg_leadtime = lead_time / count 
                    avg_leadtime = round(avg_leadtime,2)

                user_name = user_details.username
                each_usermail = user_details.email
                user_id = user_details.id

                all_tasks_in_project =  Task.objects.filter(
                    Q(project_id = pk)
                    & Q(annotation_users = user_id)
                    ).order_by('id')
                total_tasks = all_tasks_in_project.count()

                all_skipped_tasks_in_project =  Task.objects.filter(
                    Q(project_id = pk)
                    & Q(task_status = "skipped")
                    & Q(annotation_users = user_id)
                    ).order_by('id')
                total_skipped_tasks = all_skipped_tasks_in_project.count()

                all_pending_tasks_in_project =  Task.objects.filter(
                    Q(project_id = pk)
                    & Q(task_status = "unlabeled")
                    & Q(annotation_users = user_id)
                    ).order_by('id')
                total_unlabeled_tasks = all_pending_tasks_in_project.count()

                all_draft_tasks_in_project =  Task.objects.filter(Q(project_id = pk) & Q(task_status = "draft") & Q(annotation_users = user_id)).order_by('id')
                total_draft_tasks = len(all_draft_tasks_in_project.values())

                #pending_tasks = total_tasks -( count + total_skipped_tasks )
                if  is_translation_project :
                    final_result = [{"Username":user_name,"Email":each_usermail , "Annotated Tasks" : count ,"Average Annotation Time (In Seconds)": round(avg_leadtime, 2) , "Assigned Tasks" : total_tasks , "Skipped Tasks":total_skipped_tasks , "Unlabeled Tasks" : total_unlabeled_tasks, "Draft Tasks": total_draft_tasks,"Word Count" : word_count1}]
                else:
                    final_result = [{"Username":user_name,"Email":each_usermail , "Annotated Tasks" : count ,"Average Annotation Time (In Seconds)": round(avg_leadtime, 2) , "Assigned Tasks" : total_tasks , "Skipped Tasks":total_skipped_tasks , "Unlabeled Tasks" : total_unlabeled_tasks, "Draft Tasks": total_draft_tasks}]
                ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            final_result = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(final_result, status=ret_status)
    
    @swagger_auto_schema(
        method='post',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "emails":openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING,format="email"),
                    description="List of email addresses of users to be added to project"
                )
            },
            required=["emails"]
        ),
        responses={
            201:"Users added",
            404:"Project does not exist or User does not exist",
            200:"Project is published error"
        }
    )
    @action(
        detail=True,
        methods=["POST"],
        name="Add Project Users",
        url_name="add_project_users",
    )
    @project_is_archived
    @is_particular_workspace_manager
    def add_project_users(self, request, pk=None, *args, **kwargs):
        """
        Add annotators to the project
        """
        ret_dict = {}
        ret_status = 0
        try:
            project = Project.objects.get(pk=pk)

            if project.is_published:
                return Response(PROJECT_IS_PUBLISHED_ERROR, status=status.HTTP_200_OK)

            emails = request.data.get("emails")
            invalid_emails = []
            for email in emails:
                if re.fullmatch(EMAIL_REGEX, email):
                    user = User.objects.get(email=email)

                    ### TODO: Check if user is an annotator
                    # if user.role != User.ANNOTATOR:
                    #     ret_dict = {"message": f"User {user.email} is not an annotator!"}
                    #     ret_status = status.HTTP_201_CREATED
                    project.users.add(user)
                    project.save()
                else:
                    invalid_emails.append(email)
            if len(invalid_emails) != 0:
                ret_dict = {"message": "Users added!"}
                ret_status = status.HTTP_201_CREATED
            else:
                ret_dict = {
                    "message": f"Users partially added! Invalid emails: {','.join(invalid_emails)}"
                }
                ret_status = status.HTTP_201_CREATED
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "project_type",openapi.IN_QUERY,
                description=("A string to pass the project tpye"),
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200:"Return types of project and its details"
        }
    )
    @action(detail=False, methods=["GET"], name="Get Project Types", url_name="types")
    @is_organization_owner_or_workspace_manager
    def types(self, request, *args, **kwargs):
        """
        Fetches project types
        """
        # project_registry = ProjectRegistry()
        try:
            if "project_type" in dict(request.query_params):
                return Response(
                    ProjectRegistry.get_instance().project_types[request.query_params["project_type"]], status=status.HTTP_200_OK
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
    @is_organization_owner_or_workspace_manager
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
                project_type = project.project_type
                registry_helper = ProjectRegistry.get_instance()
                input_dataset_info = registry_helper.get_input_dataset_and_fields(
                    project_type
                )
                dataset_model = getattr(
                    dataset_models, input_dataset_info["dataset_type"]
                )
                tasks = Task.objects.filter(project_id__exact=project)
                all_items = dataset_model.objects.filter(
                    instance_id__in=list(project.dataset_id.all())
                )
                items = all_items.exclude(id__in=tasks.values("input_data"))
                # Get the input dataset fields from the filtered items
                if input_dataset_info["prediction"] is not None:
                    items = list(
                        items.values(
                            "id",
                            *input_dataset_info["fields"],
                            input_dataset_info["prediction"],
                        )
                    )
                else:
                    items = list(items.values("id", *input_dataset_info["fields"]))

                new_tasks = create_tasks_from_dataitems(items, project)
                serializer = ProjectUsersSerializer(project, many=False)
                # ret_dict = serializer.data
                users = serializer.data["users"]
                assign_users_to_tasks(new_tasks, users)
                ret_dict = {"message": f"{len(new_tasks)} new tasks added."}
                ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(detail=True, methods=["POST", "GET"], name="Download a Project")
    @project_is_archived
    @is_organization_owner_or_workspace_manager
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
    
    @swagger_auto_schema(
        method="get",
        responses={
            200:"No tasks to export!"
        }
    )
    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "export_dataset_instance_id":openapi.Schema(type=openapi.TYPE_INTEGER,
                description="A unique integer identifying the dataset instance"),
            },
            description="Optional Post request body for projects which have save_type == new_record"
        ),
        responses={
            200:"No tasks to export! or SUCCESS!",
            404:"Project does not exist! or User does not exist!"
        }
    )
    @action(detail=True, methods=["POST", "GET"], name="Export Project")
    @project_is_archived
    @is_organization_owner_or_workspace_manager
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
                    project_id__exact=project, task_status__exact=ACCEPTED
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
                    get_request_data=dict(request.GET)
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
                    project_id__exact=project, task_status__exact=ACCEPTED
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
                    get_request_data=dict(request.GET)
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
    @is_organization_owner_or_workspace_manager
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
            users = serializer.data["users"]

            if len(users) < project.required_annotators_per_task:
                ret_dict = {
                    "message": "Number of annotators is less than required annotators per task"
                }
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)

            # get all tasks of a project
            tasks = Task.objects.filter(project_id=pk)

            assign_users_to_tasks(tasks, users)

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
