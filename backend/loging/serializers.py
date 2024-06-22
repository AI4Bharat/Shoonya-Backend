from rest_framework import serializers
import uuid


class SelectionSerializer(serializers.Serializer):
    keystrokes = serializers.CharField()
    results = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    opted = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class TransliterationSerializer(serializers.Serializer):
    uuid = serializers.CharField()
    parent_uuid = serializers.CharField()
    word = serializers.CharField()
    source = serializers.CharField()
    language = serializers.CharField()
    steps = SelectionSerializer(many=True)


class TransliterationLogSerializer(serializers.Serializer):
    source_english_text = serializers.CharField()
    indic_translation_text = serializers.CharField()
    romanised_text = serializers.CharField()
    edited_romanised_text = serializers.CharField(required=False)
    language = serializers.CharField()
    uuid = serializers.UUIDField(default=uuid.uuid4, read_only=True)

