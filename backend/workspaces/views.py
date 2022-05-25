from ast import Is
import re
from urllib import response
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated
from projects.serializers import ProjectSerializer
from drf_yasg.utils import swagger_auto_schema
from projects.models import Project
from users.models import User
from users.serializers import UserProfileSerializer

from .serializers import WorkspaceManagerSerializer, WorkspaceSerializer
from .models import Workspace
from .decorators import (
    is_organization_owner_or_workspace_manager,
    is_workspace_member,
    workspace_is_archived,
    is_particular_workspace_manager,
)

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

    @is_organization_owner_or_workspace_manager
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
    @is_particular_workspace_manager
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
    @is_particular_workspace_manager
    def archive(self, request, pk=None, *args, **kwargs):
        workspace = Workspace.objects.get(pk=pk)
        workspace.is_archived = not workspace.is_archived
        workspace.save()
        return super().retrieve(request, *args, **kwargs)

    # TODO: Add serializer
    @action(detail=True, methods=["POST"], name="Assign Manager", url_name="assign_manager")
    @is_particular_workspace_manager
    def assign_manager(self, request, pk=None, *args, **kwargs):
        """
        API for assigning manager to a workspace
        """
        ret_dict = {}
        ret_status = 0
        email = str(request.data["email"])
        try:
            if re.fullmatch(EMAIL_VALIDATION_REGEX, email):
                user = User.objects.get(email=email)
                workspace = Workspace.objects.get(pk=pk)
                workspace.managers.add(user)
                workspace.users.add(user)
                workspace.save()
                serializer = WorkspaceManagerSerializer(workspace, many=False)
                ret_dict = serializer.data
                ret_status = status.HTTP_200_OK
            else:
                ret_dict = {"message": "Enter a valid Email!"}
                ret_status = status.HTTP_400_BAD_REQUEST
        except User.DoesNotExist:
            ret_dict = {"message": "User with such Email does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except Exception:
            ret_dict = {"message": "Email is required!"}
            ret_status = status.HTTP_400_BAD_REQUEST
        return Response(ret_dict, status=ret_status)

    @swagger_auto_schema(responses={200: ProjectSerializer})
    @action(detail=True, methods=["GET"], name="Get Projects", url_path="projects", url_name="projects")
    @is_workspace_member
    def get_projects(self, request, pk=None):
        """
        API for getting all projects of a workspace
        """
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role == User.ANNOTATOR:
            projects = Project.objects.filter(users=request.user, workspace_id=workspace)
        else:
            projects = Project.objects.filter(workspace_id=workspace)
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkspaceusersViewSet(viewsets.ViewSet):
    
    @is_organization_owner_or_workspace_manager
    @permission_classes((IsAuthenticated,))
    @action(detail=True, methods=['POST'], url_path='addusers', url_name='add_users')
    def add_users(self, request,pk=None):
        user_id = request.data.get('user_id',"")
        try:
            workspace = Workspace.objects.get(pk=pk)

            if(((request.user.role) == (User.ORGANIZAION_OWNER) and (request.user.organization)==(workspace.organization)) or ((request.user.role==User.WORKSPACE_MANAGER) and (request.user in workspace.managers.all()))) == False:
                return Response({"message": "Not authorized!"}, status=status.HTTP_403_FORBIDDEN)

            emails = user_id.split(',')
            invalid_emails = []
            for email in emails:
                try:
                    user = User.objects.get(email=email)
                    if((user.organization) == (workspace.organization)):
                        workspace.users.add(user)
                    else:
                        invalid_emails.append(email)
                except User.DoesNotExist:
                    invalid_emails.append(email)

            workspace.save()
            if len(invalid_emails) == 0:
                return Response({"message": "users added successfully"}, status=status.HTTP_200_OK)
            elif len(invalid_emails)==len(emails):
                return Response({"message": "No valid emails found"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": f"users added partially! Invalid emails: {','.join(invalid_emails)}"}, status=status.HTTP_200_OK)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"message": "Server Error occured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @is_organization_owner_or_workspace_manager
    @permission_classes((IsAuthenticated,))
    @action(detail=True, methods=['POST'], url_path='removeusers', url_name='remove_users')
    def remove_users(self, request,pk=None):
        user_id = request.data.get('user_id',"")
        try:
            workspace = Workspace.objects.get(pk=pk)

            if(((request.user.role) == (User.ORGANIZAION_OWNER) and (request.user.organization) == (workspace.organization)) or ((request.user.role == User.WORKSPACE_MANAGER) and (request.user in workspace.managers.all()))) == False:
                return Response({"message": "Not authorized!"}, status=status.HTTP_403_FORBIDDEN)

            try:
                user = User.objects.get(email=user_id)
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
