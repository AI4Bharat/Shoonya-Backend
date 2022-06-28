from ast import Is
import re
from urllib import response
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated
from yaml import serialize
from projects.serializers import ProjectSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from projects.models import Project
from users.models import User
from users.serializers import UserProfileSerializer
from tasks.models import Task
from organizations.models import Organization
from django.db.models import Q
from projects.utils import  no_of_words
from tasks.models import Annotation
from projects.utils import is_valid_date
from datetime import datetime

from .serializers import UnAssignManagerSerializer, WorkspaceManagerSerializer, WorkspaceSerializer
from .models import Workspace
from .decorators import (
    is_workspace_member,
    workspace_is_archived,
    is_particular_workspace_manager,
    is_organization_owner_or_workspace_manager
)
from organizations.decorators import is_particular_organization_owner

# Create your views here.

EMAIL_VALIDATION_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"


class WorkspaceViewSet(viewsets.ModelViewSet):
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        if int(request.user.role) == User.ANNOTATOR or int(request.user.role) == User.WORKSPACE_MANAGER:
            data = self.queryset.filter(users=request.user, is_archived=False, organization=request.user.organization)
            try:
                data = self.paginate_queryset(data)
            except:
                page = []
                data = page
                return Response({"status": status.HTTP_200_OK, "message": "No more record.", "results": data})
            serializer = WorkspaceSerializer(data, many=True)
            return self.get_paginated_response(serializer.data)
        elif int(request.user.role) == User.ORGANIZAION_OWNER:
            data = self.queryset.filter(organization=request.user.organization)
            try:
                data = self.paginate_queryset(data)
            except:
                page = []
                data = page
                return Response({"status": status.HTTP_200_OK, "message": "No more record.", "results": data})
            serializer = WorkspaceSerializer(data, many=True)
            return self.get_paginated_response(serializer.data)
        else:
            return Response({"message": "Not authorized!"}, status=status.HTTP_403_FORBIDDEN)

    def retrieve(self, request, pk=None, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @is_particular_organization_owner
    def create(self, request, *args, **kwargs):
        # TODO: Make sure to add the user to the workspace and created_by
        # return super().create(request, *args, **kwargs)
        try:
            data = self.serializer_class(data=request.data)
            if data.is_valid():
                obj = data.save()
                obj.users.add(request.user)
                obj.created_by = request.user
                obj.save()
                return Response({"message": "Workspace created!"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({"message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)

    @is_particular_workspace_manager
    @workspace_is_archived
    def update(self, request, pk=None, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @is_particular_workspace_manager
    @workspace_is_archived
    def partial_update(self, request, pk=None, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        return Response({"message": "Deleting of Workspaces is not supported!"}, status=status.HTTP_403_FORBIDDEN,)


class WorkspaceCustomViewSet(viewsets.ViewSet):
    @swagger_auto_schema(responses={200: UserProfileSerializer})
    @is_organization_owner_or_workspace_manager
    @action(detail=True, methods=["GET"], name="Get Workspace users", url_name="users")
    def users(self, request, pk=None):
        """
        Get all users of a workspace
        """
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        users = workspace.users.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data)

    # TODO : add exceptions
    @action(
        detail=True, methods=["POST"], name="Archive Workspace", url_name="archive",
    )
    @is_particular_organization_owner
    def archive(self, request, pk=None, *args, **kwargs):
        workspace = Workspace.objects.get(pk=pk)
        workspace.is_archived = not workspace.is_archived
        workspace.save()
        return Response({"done":True}, status=status.HTTP_200_OK)

    # TODO: Add serializer
    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING,format="email")
            },
            required=["username"]
        ),
        responses={
            200:"Done",
            404:"User with such Username does not exist!",
            400:"Bad request,Some exception occured"
        },
        manual_parameters=[
            openapi.Parameter(
                "id",openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ]

    )
    @action(detail=True, methods=["POST"], name="Assign Manager", url_name="assign_manager")
    @is_particular_organization_owner
    def assign_manager(self, request, pk=None, *args, **kwargs):
        """
        API for assigning manager to a workspace
        """
        ret_dict = {}
        ret_status = 0
        username = str(request.data["username"])
        try:
            user = User.objects.get(username=username)
            workspace = Workspace.objects.get(pk=pk)
            workspace.managers.add(user)
            workspace.users.add(user)
            workspace.save()
            serializer = WorkspaceManagerSerializer(workspace, many=False)
            ret_dict = {"done":True}
            ret_status = status.HTTP_200_OK
        except User.DoesNotExist:
            ret_dict = {"message": "User with such Username does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except Exception as e:
            ret_dict = {"message": str(e)}
            ret_status = status.HTTP_400_BAD_REQUEST
        return Response(ret_dict, status=ret_status)

    @action(detail=True, methods=["POST"], name="Unassign Manager", url_name="unassign_manager")
    @is_particular_organization_owner
    def unassign_manager(self, request, pk=None, *args, **kwargs):
        """
        API Endpoint for unassigning an workspace manager
        """
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UnAssignManagerSerializer(workspace, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"done":True}, status=status.HTTP_200_OK)
        

    @swagger_auto_schema(
        method="get",
        responses={200: ProjectSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                "only_active",openapi.IN_QUERY,
                description=("It is passed as true to get all the projects which are not archived,to get all it is passed as false"),
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
            openapi.Parameter(
                "id", openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ]
    )
    @action(detail=True, methods=["GET"], name="Get Projects", url_path="projects", url_name="projects")
    @is_organization_owner_or_workspace_manager
    def get_projects(self, request, pk=None):
        """
        API for getting all projects of a workspace
        """
        only_active=str(request.GET.get('only_active','false'))
        only_active=True if only_active=='true' else False
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role == User.ANNOTATOR:
            projects = Project.objects.filter(users=request.user, workspace_id=workspace)
        else:
            projects = Project.objects.filter(workspace_id=workspace)
        
        if only_active==True:
            projects=projects.filter(is_archived=False)
        
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=True, methods=["POST"], name="Workspace Project Details", url_path="project_analytics", url_name="project_analytics")
    @is_organization_owner_or_workspace_manager
    def project_analytics(self, request, pk=None):
        """
        API for getting project_analytics of a workspace
        """
        try:
            ws = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            ws_owner = ws.created_by.get_username()
        except :
            ws_owner = ""
        try : 
            org_id =  ws.organization.id
            org_obj= Organization.objects.get(id=org_id)
            org_owner = org_obj.created_by.get_username()
        except :
            org_owner = ""
        
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        from_date = from_date + ' 00:00'
        to_date = to_date + ' 23:59'
        tgt_language = request.data.get('tgt_language')
        project_type = request.data.get("project_type")

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

        selected_language = "No Language Selected"
        if tgt_language == None :
            projects_objs = Project.objects.filter(workspace_id=pk, project_type = project_type)
        else :
            selected_language = tgt_language
            projects_objs = Project.objects.filter(workspace_id=pk, project_type = project_type,tgt_language = tgt_language)
        final_result=[]
        if projects_objs.count() !=0:
            for proj in projects_objs:
                owners = [org_owner , ws_owner ]
                project_id = proj.id
                project_name = proj.title
                project_type = proj.project_type
                all_tasks = Task.objects.filter(project_id = proj.id)
                total_tasks = all_tasks.count()
                annotators_list = [ user_.get_username()  for user_ in   proj.users.all()]
                try :
                    proj_owner =  proj.created_by.get_username()
                    owners.append(proj_owner)
                except :
                    pass
                no_of_annotators_assigned = len( [annotator for annotator in annotators_list if annotator not in owners ])
                un_labeled_count = Task.objects.filter(project_id = proj.id,task_status = 'unlabeled').count()
                labeled_count = Task.objects.filter(Q (project_id = proj.id) & Q(task_status = 'accepted') & Q (correct_annotation__created_at__range = [start_date, end_date])).count()
                skipped_count = Task.objects.filter(project_id = proj.id,task_status = 'skipped').count()
                dropped_tasks = Task.objects.filter(project_id = proj.id,task_status = 'draft').count()
                if total_tasks == 0:
                    project_progress = 0.0
                else :
                    project_progress = (labeled_count / total_tasks) * 100
                result = {
                    "Project Id" : project_id,
                    "Project Name" : project_name,
                    "Language" : selected_language,
                    "Project Type" : project_type,
                    "Total No.Of Tasks" : total_tasks,
                    "Total No.Of Annotators Assigned" : no_of_annotators_assigned,
                    "Total No.Of Labeled Tasks" : labeled_count,
                    "Total No.Of Unlabeled Tasks" : un_labeled_count,
                    "Total No.Of Skipped Tasks": skipped_count,
                    "Total No.Of Draft Tasks" : dropped_tasks,
                    "Project Progress" : round(project_progress,3)
                    }
                final_result.append(result)
        ret_status = status.HTTP_200_OK
        return Response(final_result , status = ret_status )


    @action(detail=True, methods=["POST"], name="Workspace annotator Details", url_path="user_analytics", url_name="user_analytics")
    @is_organization_owner_or_workspace_manager
    def user_analytics(self, request, pk=None):
        """
        API for getting user_analytics of a workspace
        """
        try:
            ws = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            ws_owner = ws.created_by.get_username()
        except :
            ws_owner = ""
        try : 
            org_id =  ws.organization.id
            org_obj= Organization.objects.get(id=org_id)
            org_owner = org_obj.created_by.get_username()
        except :
            org_owner = ""

        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        from_date = from_date + ' 00:00'
        to_date = to_date + ' 23:59'
        tgt_language = request.data.get('tgt_language')


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


        user_mail =[user.get_username() for user in ws.users.all()]
        user_name =[user.username for user in ws.users.all()]
        users_id = [user.id for user in ws.users.all()]

        project_type = request.data.get("project_type")
        project_type_lower =  project_type.lower()
        is_translation_project = True if  "translation" in  project_type_lower  else False
        selected_language = "No Language Selected"
        final_result =[]
        for index,each_user in enumerate(users_id):
            if tgt_language == None :
                projects_objs = Project.objects.filter(workspace_id=pk, users = each_user,project_type = project_type)
            else :
                selected_language = tgt_language
                projects_objs = Project.objects.filter(workspace_id=pk, users = each_user,project_type = project_type,tgt_language = tgt_language)
            project_count = projects_objs.count()
            proj_ids = [eachid['id'] for eachid in projects_objs.values('id')]
            
            name = user_name[index]
            email = user_mail[index]
            assigned_tasks = 0
            annotated_tasks = 0
            total_word_count = 0
            avg_lead_time = 0
            total_skipped_tasks =0
            all_pending_tasks_in_project = 0 
            all_draft_tasks_in_project = 0
 	
            for each_project in proj_ids :
 	
                all_tasks_in_project = Task.objects.filter(Q(project_id=each_project) & Q(annotation_users= each_user )).order_by("id")
                assigned_tasks += all_tasks_in_project.count()
                
                annotated_tasks_objs =Task.objects.filter(Q(project_id=each_project) & Q(annotation_users= each_user ) & Q(task_status='accepted')
                & Q (correct_annotation__created_at__range = [start_date, end_date]))
                annotated_tasks += annotated_tasks_objs.count()
                                
                annotated_task_ids  = [task.id for task in annotated_tasks_objs]
                annotated_table_objs = Annotation.objects.filter(task_id__in =annotated_task_ids)
                lead_time_list = [obj.lead_time for obj in annotated_table_objs]
                if len(lead_time_list) > 0 :
                    avg_lead_time +=sum(lead_time_list) / len(lead_time_list)
                else :
                    pass
                if is_translation_project:
                    total_count_list = [no_of_words(Task.objects.get(id = id1).data['input_text']) for  id1 in annotated_task_ids]
                    total_word_count += sum(total_count_list)
                
                
                all_skipped_tasks_in_project = Task.objects.filter(
                        Q(project_id=each_project)
                        & Q(task_status="skipped")
                        & Q(annotation_users=each_user)
                    ).order_by("id")
                total_skipped_tasks += all_skipped_tasks_in_project.count()
 
                all_pending_tasks_in_project_objs =  Task.objects.filter(Q(project_id = each_project) & Q(task_status = "unlabeled") & Q(annotation_users = each_user) ).order_by('id')
                all_pending_tasks_in_project += all_pending_tasks_in_project_objs.count()

                all_draft_tasks_in_project_objs =  Task.objects.filter(Q(project_id = each_project) & Q(task_status = "draft") & Q(annotation_users = each_user)).order_by('id')
                all_draft_tasks_in_project += all_draft_tasks_in_project_objs.count()
            if is_translation_project :
                result = {
                    "Username":name,
                    "Email":email,
                    "Language" : selected_language,
                    "No.of Projects":project_count,
                    "Annotated Tasks" : annotated_tasks ,
                    "Average Annotation Time (In Seconds)" : round(avg_lead_time, 2),
                    "Assigned Tasks" : assigned_tasks,
                    "Skipped Tasks" : total_skipped_tasks,
                    "Unlabeled Tasks" : all_pending_tasks_in_project,
                    "Draft Tasks": all_draft_tasks_in_project,
                    "Word Count" : total_word_count
                    }
            else:
                result = {
                    "Username":name,
                    "Email":email,
                    "Language" : selected_language,
                    "No.of Projects":project_count,
                    "Annotated Tasks" : annotated_tasks ,
                    "Average Annotation Time (In Seconds)" : round(avg_lead_time, 2),
                    "Assigned Tasks" : assigned_tasks,
                    "Skipped Tasks" : total_skipped_tasks,
                    "Unlabeled Tasks" : all_pending_tasks_in_project,
                    "Draft Tasks": all_draft_tasks_in_project,
                    }

            if email == ws_owner or email == org_owner :
                pass
            else:
                final_result.append(result)
            
        return Response(final_result)




class WorkspaceusersViewSet(viewsets.ViewSet):
    
    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="String containing emails separated by commas")
            },
            required=["user_id"]
        ),
        manual_parameters=[
            openapi.Parameter(
                "id", openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200:"Users added Successfully",
            403:"Not authorized",
            400:"No valid user_ids found",
            404:"Workspace not found",
            500:"Server error occured"
        }

    )
    @is_organization_owner_or_workspace_manager
    @permission_classes((IsAuthenticated,))
    @action(detail=True, methods=['POST'], url_path='addannotators', url_name='add_annotators')
    def add_annotators(self, request,pk=None):
        user_id = request.data.get('user_id',"")
        try:
            workspace = Workspace.objects.get(pk=pk)

            if(((request.user.role) == (User.ORGANIZAION_OWNER) and (request.user.organization)==(workspace.organization)) or ((request.user.role==User.WORKSPACE_MANAGER) and (request.user in workspace.managers.all()))) == False:
                return Response({"message": "Not authorized!"}, status=status.HTTP_403_FORBIDDEN)

            user_ids = user_id.split(',')
            invalid_user_ids = []
            for user_id in user_ids:
                try:
                    user = User.objects.get(pk=user_id)
                    if((user.organization) == (workspace.organization)):
                        workspace.users.add(user)
                    else:
                        invalid_user_ids.append(user_id)
                except User.DoesNotExist:
                    invalid_user_ids.append(user_id)

            workspace.save()
            if len(invalid_user_ids) == 0:
                return Response({"message": "users added successfully"}, status=status.HTTP_200_OK)
            elif len(invalid_user_ids)==len(user_ids):
                return Response({"message": "No valid user_ids found"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": f"users added partially! Invalid user_ids: {','.join(invalid_user_ids)}"}, status=status.HTTP_200_OK)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"message": "Server Error occured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, format="email")
            },
            required=["user_id"]
        ),
        manual_parameters=[
            openapi.Parameter(
                "id", openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: "User removed Successfully",
            403: "Not authorized",
            404: "Workspace not found/User not in the workspace/User not found",
            500: "Server error occured"
        }
    )
    @is_organization_owner_or_workspace_manager
    @permission_classes((IsAuthenticated,))
    @action(detail=True, methods=['POST'], url_path='removeannotators', url_name='remove_annotators')
    def remove_annotators(self, request,pk=None):
        user_id = request.data.get('user_id',"")
        try:
            workspace = Workspace.objects.get(pk=pk)

            if(((request.user.role) == (User.ORGANIZAION_OWNER) and (request.user.organization) == (workspace.organization)) or ((request.user.role == User.WORKSPACE_MANAGER) and (request.user in workspace.managers.all()))) == False:
                return Response({"message": "Not authorized!"}, status=status.HTTP_403_FORBIDDEN)

            try:
                user = User.objects.get(pk=user_id)
                if user in workspace.users.all():
                    workspace.users.remove(user)
                    return Response({"message": "User removed successfully"}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "User not in workspace"}, status=status.HTTP_404_NOT_FOUND)

            except User.DoesNotExist:
                return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"message": "Server Error occured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
