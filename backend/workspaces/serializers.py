from rest_framework import serializers

from .models import *

class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ['organization', 'workspace_name', 'users', 'is_archived', 'created_by', 'id']