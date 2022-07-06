from functools import wraps
from workspaces.models import Workspace
from users.models import User
from organizations.models import Organization
from rest_framework.response import Response
from rest_framework import status
from .models import Project

PERMISSION_ERROR = {
    'message': 'You do not have enough permissions to access this view!'
}
PROJECT_IS_ARCHIVED_ERROR = {
    'message': 'This Project is archived!'
}
NOT_WORKSPACE_MANAGER_ERROR = {
    'message': 'You do not belong to this workspace!'
}
PROJECT_IS_PUBLISHED_ERROR = {
    'message': 'This Project is already published and cannot be deleted!'
}


# Only allow workspace managers and organization owners to create projects.
def is_organization_owner_or_workspace_manager(f):
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        if request.user.role == User.ORGANIZAION_OWNER or request.user.role == User.WORKSPACE_MANAGER or request.user.is_superuser:
            return f(self, request, *args, **kwargs)
        return Response(PERMISSION_ERROR, status=status.HTTP_403_FORBIDDEN)
    return wrapper

# Allow only Read Only if project is archived.
def project_is_archived(f):
    @wraps(f)
    def wrapper(self, request, pk, *args, **kwargs):
        try: 
            project = Project.objects.get(pk=pk)
            if project.is_archived:
                return Response(PROJECT_IS_ARCHIVED_ERROR, status=status.HTTP_403_FORBIDDEN)
            return f(self, request, pk, *args, **kwargs)
        except Project.DoesNotExist: 
            return f(self, request, pk, *args, **kwargs)
    return wrapper

# Allow delete only if project is in draft mode and is not in published mode.
def project_is_published(f):
    @wraps(f)
    def wrapper(self, request, pk, *args, **kwargs):
        project = Project.objects.get(pk=pk)
        if project.is_published:
            return Response(PROJECT_IS_PUBLISHED_ERROR, status=status.HTTP_403_FORBIDDEN)
        return f(self, request, pk, *args, **kwargs)
    return wrapper

# Check whether the user is allowed to edit the project (Checks the workspace of the manager and the organization of the organization owner)
def is_project_editor(f):
    @wraps(f)
    def wrapper(self, request, pk, *args, **kwargs):
        if (
            (
                request.user.role == User.WORKSPACE_MANAGER
                and request.user in Project.objects.get(pk=pk).workspace_id.managers.all()
            )
            or (
                request.user.role == User.ORGANIZAION_OWNER
                and request.user.organization ==  Project.objects.get(pk=pk).workspace_id.organization
            )
            or request.user.is_superuser
        ):
            return f(self, request, pk, *args, **kwargs)
        return Response(NOT_WORKSPACE_MANAGER_ERROR, status=status.HTTP_403_FORBIDDEN)
    return wrapper
