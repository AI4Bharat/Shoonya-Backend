from users.models import User
from rest_framework.response import Response

PERMISSION_ERROR = {
    'message': 'You do not have enough permissions to access this view!'
}

def is_organization_owner(f):
    def wrapper(self, request, *args, **kwargs):
        if request.user.role == User.ORGANIZAION_OWNER or request.user.is_superuser:
            f(self, request, *args, **kwargs)
        return Response(PermissionError, status=403)
    return wrapper