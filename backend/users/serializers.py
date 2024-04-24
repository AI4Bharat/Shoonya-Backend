from rest_framework import serializers

from organizations.serializers import OrganizationSerializer
from .models import User
from django.contrib.auth import authenticate, password_validation


class UserLoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()

    def validate_login(self, data):
        user = authenticate(username=data["email"], password=data["password"])
        if not user:
            return "Incorrect password."
        return "Correct password"


class UserSignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def update(self, instance, validated_data):
        instance.username = validated_data.get("username")
        instance.has_accepted_invite = True
        instance.guest_user = False
        instance.set_password(validated_data.get("password"))
        instance.save()
        return instance


class UsersPendingSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "invited_by",
            "has_accepted_invite",
        ]

    def update(self, instance, validated_data):
        instance.id = validated_data.get("id", instance.id)
        instance.username = validated_data.get("username", instance.username)
        instance.first_name(validated_data.get("first_name", instance.first_name))
        instance.last_name(validated_data.get("last_name", instance.last_name))
        instance.email(validated_data.get("email", instance.email))
        instance.role(validated_data.get("role", instance.role))
        instance.invited_by(validated_data.get("invited_by", instance.invited_by))
        instance.has_accepted_invite(
            validated_data.get("has_accepted_invite", instance.has_accepted_invite)
        )
        instance.save()
        return instance


class UserUpdateSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer()

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "languages",
            "availability_status",
            "phone",
            "gender",
            "address",
            "city",
            "state",
            "pin_code",
            "age",
            "qualification",
            "guest_user",
            "enable_mail",
            "participation_type",
            "organization",
            "role",
            "is_active",
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
            "languages",
            "availability_status",
            "enable_mail",
            "first_name",
            "last_name",
            "phone",
            "gender",
            "address",
            "city",
            "state",
            "pin_code",
            "age",
            "qualification",
            "guest_user",
            "profile_photo",
            "role",
            "organization",
            "unverified_email",
            "date_joined",
            "participation_type",
            "prefer_cl_ui",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "organization",
            "unverified_email",
            "date_joined",
        ]


class UserFetchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "has_accepted_invite",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "has_accepted_invite",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        max_length=128, write_only=True, required=True
    )
    new_password = serializers.CharField(max_length=128, write_only=True, required=True)

    def match_old_password(self, instance, value):
        if not instance.check_password(value["current_password"]):
            return False
        return True

    def validation_checks(self, instance, data):
        try:
            password_validation.validate_password(data["new_password"], instance)
        except password_validation.ValidationError as e:
            return " ".join(e.messages)
        return "Validation successful"

    def save(self, instance, validated_data):
        instance.set_password(validated_data.get("new_password"))
        instance.save()
        return instance


class LanguageSerializer(serializers.Serializer):
    language = serializers.ListField(child=serializers.CharField())


class UserEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email"]


class ChangePasswordWithoutOldPassword(serializers.Serializer):
    new_password = serializers.CharField(max_length=128, write_only=True, required=True)

    def validation_checks(self, instance, data):
        try:
            password_validation.validate_password(data["new_password"], instance)
        except password_validation.ValidationError as e:
            return " ".join(e.messages)
        return "Validation successful"

    def save(self, instance, validated_data):
        instance.set_password(validated_data.get("new_password"))
        instance.save()
        return instance
