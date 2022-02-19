from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from users.models import User

from .serializers import ProjectSerializer
from .models import Project
from .decorators import is_organization_owner_or_workspace_manager, project_is_archived, is_particular_workspace_manager, project_is_published

# Create your views here.

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

 