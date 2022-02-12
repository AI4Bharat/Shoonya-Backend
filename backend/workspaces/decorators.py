from functools import wraps
from workspaces.models import Workspace
from users.models import User
from organizations.models import Organization
from rest_framework.response import Response

PERMISSION_ERROR = {
    'message': 'You do not have enough permissions to access this view!'
}
WORKSPACE_IS_ARCHIVED_ERROR = {
    'message': 'This Workspace is archived!'
}
NOT_WORKSPACE_MANAGER_ERROR = {
    'message': 'You do not belong to this workspace!'
}

# Only allow workspace managers and organization owners to create workspaces.
def is_organization_owner_or_workspace_manager(f):
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        if request.user.role == User.ORGANIZAION_OWNER or request.user.role == User.WORKSPACE_MANAGER or request.user.is_superuser:
            return f(self, request, *args, **kwargs)
        return Response(PERMISSION_ERROR, status=403)
    return wrapper


# Only allow organization CRUD if user only is a particular organization's Workspace Manager and Organization Owner.
def is_particular_workspace_manager(f):
    @wraps(f)
    def wrapper(self, request, pk=None, *args, **kwargs):
        if (request.user.role == User.WORKSPACE_MANAGER and Workspace.objects.get(pk=pk).created_by == request.user) or (request.user.role == User.ORGANIZAION_OWNER and Organization.objects.get(pk=Workspace.objects.get(pk=pk).organization.pk).created_by.pk == request.user.pk) or request.user.is_superuser:
            return f(self, request, pk, *args, **kwargs)
        return Response(NOT_WORKSPACE_MANAGER_ERROR, status=403)
    return wrapper

# Allow only Read Only if workspace is archived.
def workspace_is_archived(f):
    @wraps(f)
    def wrapper(self, request, pk, *args, **kwargs):
        workspace = Workspace.objects.get(pk=pk)
        if workspace.is_archived:
            return Response(WORKSPACE_IS_ARCHIVED_ERROR, status=200)
        return f(self, request, pk, *args, **kwargs)
    return wrapper