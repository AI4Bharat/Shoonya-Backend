from typing_extensions import Required
from rest_framework import serializers
from .models import *
from users.models import User
from users.serializers import UserProfileSerializer
from django.contrib.auth.models import User
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password


class WorkspaceSerializer(serializers.ModelSerializer):
    managers = UserProfileSerializer(read_only=True, many=True)
    created_by = UserProfileSerializer(read_only=True)
    users = UserProfileSerializer(read_only=True, many=True)
    frozen_users = UserProfileSerializer(read_only=True, many=True)
    guest_workspace_display = serializers.SerializerMethodField()
    # workspace_password = UserProfileSerializer(read_only=True, many=True)

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

    # Custome creation for guest workspace
    # def create(self, validated_data):
    #     guest_workspace = validated_data.get("guest_workspace")
    #     workspace_password = validated_data.get("workspace_password")
    #     if guest_workspace and workspace_password is None:
    #         raise serializers.ValidationError({"workspace_password": "Password is required for guest workspaces."})
    #     workspace = super().create(validated_data)
    #     if guest_workspace:
    #         workspace.set_password(workspace_password)
    #         workspace.save()
    #     return workspace


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
    # workspace_password = serializers.CharField(write_only=True, required=True)
    # class Meta:
    #     model = Workspace
    #     fields = ["workspace_password"]
    # def validate_workspace_password(self, value):
    #     password_validation.validate_password(value)
    #     return value

    # def validate(self, data):
    #     '''
    #       Validate workspace_password during guest user entry
    #     '''

    #     entered_password = data.get("workspace_password")
    #     if self.instance and entered_password != self.instance.workspace_password:
    #         raise serializers.ValidationError("Invalid workspace password.")
    #     return data
    enter_password = serializers.CharField(write_only=True, required=True)

    def match_workspace_password(self, instance, value):
        if not instance.check_password(value["enter_password"]):
            return False
        return True
