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
        ]


class WorkspaceManagerSerializer(serializers.ModelSerializer):
    managers = UserProfileSerializer(required=True)

    class Meta:
        model = Workspace
        fields = ["id", "workspace_name", "managers"]

class UnAssignManagerSerializer(serializers.Serializer):
    emails = serializers.ListField(child=serializers.EmailField())

    def validate_emails(self, emails):
        users = User.objects.filter(email__in=emails).all()
        
        if len(users) != len(emails):
            raise serializers.ValidationError("Enter existing user emails")
        
        return emails

    def update(self, workspace, validated_data):
        emails = validated_data.pop('emails')
        users = User.objects.filter(email__in=emails).all()

        for user in users:
            workspace.managers.remove(user)
        workspace.save()
        
        return workspace

