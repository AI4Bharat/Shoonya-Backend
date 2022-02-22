from rest_framework import serializers

from .models import *
from users.serializers import UserProfileSerializer

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['title', 'description', 'created_by', 'is_archived', 'is_published', 'users']

class ProjectUsersSerializer(serializers.ModelSerializer):
    users = UserProfileSerializer(required=True, many=True)
    class Meta:
        model = Project
        fields = ['title', 'description', 'is_archived', 'is_published', 'users']