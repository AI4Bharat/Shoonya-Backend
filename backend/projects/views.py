import re
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from users.models import User

from .serializers import ProjectSerializer, ProjectUsersSerializer
from .models import Project
from .decorators import is_organization_owner_or_workspace_manager, project_is_archived, is_particular_workspace_manager, project_is_published

# Create your views here.

EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def retrieve(self, request, pk=None, *args, **kwargs):
        print(pk)
        return super().retrieve(request, *args, **kwargs)

    @is_organization_owner_or_workspace_manager    
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @is_particular_workspace_manager
    @project_is_archived
    def update(self, request, pk=None, *args, **kwargs):
        return super().update(request, *args, **kwargs)        
    
    @is_particular_workspace_manager
    @project_is_archived
    def partial_update(self, request, pk=None, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @is_organization_owner_or_workspace_manager    
    @project_is_published
    def destroy(self, request, pk=None, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
    
    # TODO : add exceptions
    @action(detail=True, methods=['POST', 'GET'], name='Archive Project')
    @is_particular_workspace_manager
    def archive(self, request, pk=None, *args, **kwargs):
        print(pk)
        project = Project.objects.get(pk=pk)
        project.is_archived = not project.is_archived
        project.save()
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['GET'], name="Get Project Users", url_name='get_project_users')
    @project_is_archived
    def get_project_users(self, request, pk=None, *args, **kwargs):
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

 