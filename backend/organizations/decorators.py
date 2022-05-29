from users.models import User
from rest_framework.response import Response
from .models import Organization
from functools import wraps

PERMISSION_ERROR = {
    "message": "You do not have enough permissions to access this view!"
}
NO_ORGANIZATION_OWNER_ERROR = {"message": "You do not belong to this organization!"}

# Allow view only if is a organization owner.
def is_organization_owner(f):
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        if request.user.role == User.ORGANIZATION_OWNER or request.user.is_superuser:
            return f(self, request, *args, **kwargs)
        return Response(PERMISSION_ERROR, status=403)

    return wrapper


# Allow detail view only if user is a particular organization's owner.
def is_particular_organization_owner(f):
    @wraps(f)
    def wrapper(self, request, pk=None, *args, **kwargs):
        if (
            request.user.role == User.ORGANIZATION_OWNER
            and Organization.objects.get(pk=pk).created_by == request.user
        ) or request.user.is_superuser:
            return f(self, request, pk, *args, **kwargs)
        return Response(NO_ORGANIZATION_OWNER_ERROR, status=403)

    return wrapper
