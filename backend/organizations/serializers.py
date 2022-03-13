from rest_framework import serializers
from .models import *


class InviteGenerationSerializer(serializers.Serializer):
    emails = serializers.ListField(child=serializers.EmailField())
    organization_id = serializers.IntegerField()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "title", "email_domain_name", "created_by"]
        read_only_fields = ["id", "created_by"]
