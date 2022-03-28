from rest_framework import serializers

from .models import *
from users.serializers import UserProfileSerializer


class WorkspaceSerializer(serializers.ModelSerializer):
    managers = UserProfileSerializer(read_only=True,many=True)
    created_by = UserProfileSerializer(read_only=True)
    class Meta:
        model = Workspace
        fields = [
            "organization",
            "workspace_name",
            "managers",
            "is_archived",
            "created_by",
            "id",
        ]


class WorkspaceManagerSerializer(serializers.ModelSerializer):
    managers = UserProfileSerializer(required=True)

    class Meta:
        model = Workspace
        fields = ["id", "workspace_name", "managers"]
