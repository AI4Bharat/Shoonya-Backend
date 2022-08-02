from rest_framework import serializers

from .models import *
from users.serializers import UserProfileSerializer

class ProjectSerializer(serializers.ModelSerializer):
    users = UserProfileSerializer(read_only=True, many=True)
    annotation_reviewers = UserProfileSerializer(read_only=True, many=True)
    created_by = UserProfileSerializer(read_only=True)
    frozen_users = UserProfileSerializer(read_only=True, many=True)
    class Meta:
        model = Project

        # sampling_mode = serializers.ChoiceField(choices=SAMPLING_MODE_CHOICES, default='friendly')
        # project_type = serializers.ChoiceField(choices=PROJECT_TYPE_CHOICES, default='friendly')
        fields = [
            "id",
            "title",
            "description",
            "created_by",
            "is_archived",
            "is_published",
            "users",
            "annotation_reviewers",
            "frozen_users",
            "workspace_id",
            "organization_id",
            "filter_string",
            "sampling_mode",
            "sampling_parameters_json",
            "project_type",
            "dataset_id",
            "label_config",
            "variable_parameters",
            "project_mode",
            "required_annotators_per_task",
            "tasks_pull_count_per_batch",
            "max_pending_tasks_per_user",
            "src_language",
            "tgt_language",
            "created_at",
            "enable_task_reviews",
        ]


class ProjectUsersSerializer(serializers.ModelSerializer):
    users = UserProfileSerializer(required=True, many=True)
    annotation_reviewers = UserProfileSerializer(required=True, many=True)

    class Meta:
        model = Project
        fields = ["title", "description", "is_archived", "is_published", "users", "annotation_reviewers"]
