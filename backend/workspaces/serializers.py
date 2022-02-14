from rest_framework import serializers

from .models import *
from users.serializers import UserProfileSerializer


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = [
            "organization",
            "workspace_name",
            "users",
            "is_archived",
            "created_by",
            "id",
        ]

class WorkspaceManagerSerializer(serializers.ModelSerializer):
    manager = UserProfileSerializer(required=True)
    class Meta:
        model = Workspace
        fields = ["id", "workspace_name", "manager"]