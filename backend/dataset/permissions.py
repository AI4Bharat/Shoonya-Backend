from rest_framework import permissions
from users.models import User


class DatasetInstancePermission(permissions.BasePermission):
    """
    Permission Class for the Dataset Instance Viewset
    """

    # Permissions for the list() and create() views
    def has_permission(self, request, view):
        # Allow any methods for managers, org owners and superusers. The filtering logic is handled in the views itself
        return request.user.is_authenticated and (
            request.user.role == User.WORKSPACE_MANAGER
            or request.user.role == User.ORGANIZATION_OWNER
            or request.user.is_superuser
        )

    # Permissions for the retrieve(), update(), partial_update(), destroy(), download(), upload() and projects() views
    def has_object_permission(self, request, view, obj):
        # Check if user is present in list of instance users, if user is org owner or superuser

        bool_check = request.user.is_authenticated and (
            request.user in obj.users.all()
            or (
                request.user.role == User.ORGANIZATION_OWNER
                and request.user.organization == obj.organisation_id
            )
            or request.user.is_superuser
        )

        # Read-Only access is given to all datasets that are public to managers as well as prev condition
        if request.method in permissions.SAFE_METHODS:
            return bool_check or (
                request.user.role == User.WORKSPACE_MANAGER
                and obj.public_to_managers
                and request.user.organization == obj.organisation_id
            )
        # Write access is given only for users satisfying bool_check
        return bool_check
