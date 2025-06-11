from users.models import User
from rest_framework.response import Response
from .models import Organization
from functools import wraps
from django.http import HttpResponse
from workspaces.models import Workspace


PERMISSION_ERROR = {
    "message": "You do not have enough permissions to access this view!"
}
NO_ORGANIZATION_FOUND = {"message": "No matching organization found."}
NO_ORGANIZATION_OWNER_ERROR = {"message": "You do not belong to this organization!"}


# Allow view only if is a organization owner.
def is_organization_owner(f):
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.role == User.ORGANIZATION_OWNER or request.user.is_superuser
        ):
            return f(self, request, *args, **kwargs)
        return Response(PERMISSION_ERROR, status=403)

    return wrapper


# Allow detail view only if user is a particular organization's owner.
def is_particular_organization_owner(f):
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


def is_admin(f):
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.role == User.ADMIN or request.user.is_superuser
        ):
            return f(self, request, *args, **kwargs)
        return Response("Permission Denied", status=403)

    return wrapper


def is_permitted(f):
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        if "organization" not in request.data or "workspace" not in request.data:
            return Response(
                {
                    "message": "Please send the complete request data for organization and workspace"
                },
                status=403,
            )
        organization = Organization.objects.get(id=request.data["organization"])
        workspace = Workspace.objects.get(id=request.data["workspace"])
        if Organization.objects.filter(
            id=request.user.organization.id
        ) != Organization.objects.filter(id=int(organization)):
            return Response(NO_ORGANIZATION_OWNER_ERROR, status=403)
        if workspace.organization != request.user.organization:
            Response(NO_ORGANIZATION_OWNER_ERROR, status=403)
        org_permissions = Organization.objects.filter(
            id=request.user.organization.id
        ).permission_json
        requested_permission = request.data.get("requested_permission")
        allowed_roles = org_permissions.get(requested_permission, 0)
        if not allowed_roles:
            return Response({"message": "Requested Permission is invalid"}, status=403)
        for a in allowed_roles:
            if (a == "org_owner" and request.user.role != User.ORGANIZATION_OWNER) or (
                a == "workspace_manager" and request.user not in workspace.managers
            ):
                return Response({"message": "Access Denied"}, status=403)
            return f(self, request, *args, **kwargs)
        return Response(PERMISSION_ERROR, status=403)

    return wrapper
