from rest_framework import serializers

from .models import *
from users.models import User
from users.serializers import UserProfileSerializer


class WorkspaceSerializer(serializers.ModelSerializer):
    managers = UserProfileSerializer(read_only=True,many=True)
    created_by = UserProfileSerializer(read_only=True)
    users = UserProfileSerializer(read_only=True, many=True)
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
        ]


class WorkspaceManagerSerializer(serializers.ModelSerializer):
    managers = UserProfileSerializer(required=True)

    class Meta:
        model = Workspace
        fields = ["id", "workspace_name", "managers"]

class UnAssignManagerSerializer(serializers.Serializer):
    usernames = serializers.ListField(child=serializers.CharField())

    def validate_emails(self, usernames):
        users = User.objects.filter(username__in=usernames).all()
        
        if len(users) != len(usernames):
            raise serializers.ValidationError("Enter existing user usernames")
        
        return usernames

    def update(self, workspace, validated_data):
        usernames = validated_data.pop('usernames')
        users = User.objects.filter(username__in=usernames).all()

        for user in users:
            workspace.managers.remove(user)
        workspace.save()
        
        return workspace

