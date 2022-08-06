from rest_framework import serializers


# Imported user model here coz circular import errors popped up when we tried defining UserReadSerializer in users.serializers and importing it here
from users.models import User
from .models import *


class InviteGenerationSerializer(serializers.Serializer):
    emails = serializers.ListField(child=serializers.EmailField())
    organization_id = serializers.IntegerField()
    role = serializers.IntegerField()


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "role"]
        read_only_fields = ["username", "email", "first_name", "last_name", "role"]


class OrganizationSerializer(serializers.ModelSerializer):
    created_by = UserReadSerializer(read_only=True)

    class Meta:
        model = Organization
        fields = ["id", "title", "email_domain_name", "created_by", "created_at"]
        read_only_fields = ["id", "created_by", "created_at"]
