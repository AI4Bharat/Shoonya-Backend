from typing_extensions import Required
from rest_framework import serializers
from .models import *
from users.models import User
from users.serializers import UserProfileSerializer


class WorkspaceSerializer(serializers.ModelSerializer):
    managers = UserProfileSerializer(read_only=True, many=True)
    created_by = UserProfileSerializer(read_only=True)
    users = UserProfileSerializer(read_only=True, many=True)
    frozen_users = UserProfileSerializer(read_only=True, many=True)
    guest_workspace_display = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "organization",
            "workspace_name",
            "managers",
            "users",
            "is_archived",
            "created_by",
            "id",
            "created_at",
            "guest_workspace_display",
            "frozen_users",
            "public_analytics",
        ]

    """Return 'Yes' if guest_workspace is True, otherwise 'No'."""

    def get_guest_workspace_display(self, obj):
        if obj.guest_workspace:
            return "Yes"
        else:
            return "No"


class WorkspaceManagerSerializer(serializers.ModelSerializer):
    managers = UserProfileSerializer(required=True)

    class Meta:
        model = Workspace
        fields = ["id", "workspace_name", "managers"]


class UnAssignManagerSerializer(serializers.Serializer):
    ids = serializers.IntegerField(required=True)

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        return user

    def update(self, workspace, validated_data):
        users = validated_data.get("ids")
        workspace.managers.remove(users)
        workspace.save()
        return workspace


class WorkspaceNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ["id", "workspace_name"]


class WorkspacePasswordSerializer(serializers.Serializer):
    workspace_password = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        Workspace_password = data.get("workspace_password")
        workspace = self.context.get("workspace")
        if workspace and workspace.guest_workspace:
            if workspace.match_workspace_password(Workspace_password):
                return True
        return False
