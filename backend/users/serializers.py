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


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "lang_id",
            "availability_status",
            "phone",
        ]
        read_only_fields = ["email"]


class UserProfileSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "lang_id",
            "availability_status",
            "first_name",
            "last_name",
            "phone",
            "role",
            "organization",
        ]
        read_only_fields = ["id", "email", "role", "organization"]


class UserFetchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "has_accepted_invite"]
        read_only_fields = [
            "id",
            "email",
            "role",
            "has_accepted_invite",
        ]
