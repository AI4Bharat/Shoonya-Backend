from functools import wraps
from workspaces.models import Workspace
from users.models import User
from organizations.models import Organization
from rest_framework.response import Response
from rest_framework import status

PERMISSION_ERROR = {
    "message": "You do not have enough permissions to access this view!"
}
WORKSPACE_ERROR = {"message": "Workspace does not exist"}
WORKSPACE_IS_ARCHIVED_ERROR = {"message": "This Workspace is archived!"}
NOT_IN_WORKSPACE_ERROR = {"message": "You do not belong to this workspace!"}


# Only allow workspace managers and organization owners to create workspaces.
def is_organization_owner_or_workspace_manager(f):
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        if (
            request.user.role == User.ORGANIZATION_OWNER
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
                request.user.role == User.ORGANIZATION_OWNER
                and Workspace.objects.get(pk=pk).organization
                == request.user.organization
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
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response(WORKSPACE_ERROR, status=status.HTTP_404_NOT_FOUND)
        if workspace.is_archived:
            return Response(WORKSPACE_IS_ARCHIVED_ERROR, status=status.HTTP_200_OK)
        return f(self, request, pk, *args, **kwargs)

    return wrapper


# Check if user is a workspace member
def belongs_to_workspace(f):
    @wraps(f)
    def wrapper(self, request, pk=None, *args, **kwargs):
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response(WORKSPACE_ERROR, status=status.HTTP_404_NOT_FOUND)
        if request.user in workspace.users.all() or (
            request.user in workspace.managers.all()
            and request.user.role == User.WORKSPACE_MANAGER
        ):
            return f(self, request, pk, *args, **kwargs)
        else:
            return Response(NOT_IN_WORKSPACE_ERROR, status=status.HTTP_403_FORBIDDEN)

    return wrapper


# Check if user is the organization owner in which the workspace is present in.
def is_particular_organization_owner(f):
    @wraps(f)
    def wrapper(self, request, pk=None, *args, **kwargs):
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response(WORKSPACE_ERROR, status=status.HTTP_404_NOT_FOUND)
        if (
            request.user.organization == workspace.organization
            and request.user.role == User.ORGANIZATION_OWNER
        ) or (request.user.is_superuser):
            return f(self, request, pk, *args, **kwargs)
        else:
            return Response(PERMISSION_ERROR, status=status.HTTP_403_FORBIDDEN)

    return wrapper


# Allow detail view only if user is a particular organization's owner.
def is_workspace_creator(f):
    @wraps(f)
    def wrapper(self, request, pk=None, *args, **kwargs):
        if request.user.role == User.ORGANIZATION_OWNER or request.user.is_superuser:
            if "organization" in request.data:
                organization = Organization.objects.filter(
                    pk=request.data["organization"]
                ).first()
            else:
                organization = Organization.objects.filter(pk=pk).first()

            if not organization:
                return Response(NO_ORGANIZATION_FOUND, status=404)
            elif request.user.organization != organization:
                return Response(NO_ORGANIZATION_OWNER_ERROR, status=403)
            return f(self, request, pk, *args, **kwargs)
        else:
            return Response(PERMISSION_ERROR, status=403)

    return wrapper
