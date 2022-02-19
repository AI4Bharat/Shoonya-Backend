from rest_framework import serializers

from .models import *

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['title', 'description', 'created_by', 'is_archived', 'is_published', 'users']