from rest_framework import serializers

from organizations.serializers import OrganizationSerializer
from .models import User


class UserSignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "password", "email"]
        read_only_fields = ["email"]

    def update(self, instance, validated_data):
        instance.username = validated_data.get("username")
        instance.has_accepted_invite = True
        instance.set_password(validated_data.get("password"))
        instance.save()
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    is_annotator = serializers.SerializerMethodField()
    is_workspace_manager = serializers.SerializerMethodField()
    is_organization_owner = serializers.SerializerMethodField()
    organization = OrganizationSerializer(read_only=True)
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_annotator",
            "is_workspace_manager",
            "is_organization_owner",
            'organization'
        ]
        read_only_fields = [
            "email",
            "role",
            "is_annotator",
            "is_workspace_manager",
            "is_organization_owner",
            'organization'
        ]

    def get_is_annotator(self, obj):
        return obj.is_annotator()

    def get_is_workspace_manager(self, obj):
        return obj.is_workspace_manager()

    def get_is_organization_owner(self, obj):
        return obj.is_organization_owner()
