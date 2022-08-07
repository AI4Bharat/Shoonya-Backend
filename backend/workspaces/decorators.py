from functools import wraps
from workspaces.models import Workspace
from users.models import User
from organizations.models import Organization
from rest_framework.response import Response
from rest_framework import status

PERMISSION_ERROR = {
    "message": "You do not have enough permissions to access this view!"
}
WORKSPACE_IS_ARCHIVED_ERROR = {"message": "This Workspace is archived!"}
NOT_IN_WORKSPACE_ERROR = {"message": "You do not belong to this workspace!"}

# Only allow workspace managers and organization owners to create workspaces.
def is_organization_owner_or_workspace_manager(f):
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        if (
            request.user.role == User.ORGANIZAION_OWNER
            or request.user.role == User.WORKSPACE_MANAGER
            or request.user.is_superuser
        ):
            return f(self, request, *args, **kwargs)
        return Response(PERMISSION_ERROR, status=status.HTTP_403_FORBIDDEN)

    return wrapper


# Only allow organization CRUD if user only is a particular organization's Workspace Manager and Organization Owner.
def is_particular_workspace_manager(f):
    @wraps(f)
    def wrapper(self, request, pk=None, *args, **kwargs):
        if (
            (
                request.user.role == User.WORKSPACE_MANAGER
                and request.user in Workspace.objects.get(pk=pk).managers.all()
            )
            or (
                request.user.role == User.ORGANIZAION_OWNER
                and Organization.objects.get(
                    pk=Workspace.objects.get(pk=pk).organization.pk
                ).created_by
                == request.user
            )
            or request.user.is_superuser
        ):
            return f(self, request, pk, *args, **kwargs)
        return Response(NOT_IN_WORKSPACE_ERROR, status=status.HTTP_403_FORBIDDEN)

    return wrapper


# Allow only Read Only if workspace is archived.
def workspace_is_archived(f):
    @wraps(f)
    def wrapper(self, request, pk, *args, **kwargs):
        workspace = Workspace.objects.get(pk=pk)
        if workspace.is_archived:
            return Response(WORKSPACE_IS_ARCHIVED_ERROR, status=status.HTTP_200_OK)
        return f(self, request, pk, *args, **kwargs)

    return wrapper


def is_workspace_member(f):
    @wraps(f)
    def wrapper(self, request, pk=None, *args, **kwargs):
        workspace = Workspace.objects.get(pk=pk)
        if request.user in workspace.users.all():
            return f(self, request, pk, *args, **kwargs)
        else:
            return Response(NOT_IN_WORKSPACE_ERROR, status=status.HTTP_403_FORBIDDEN)

    return wrapper
