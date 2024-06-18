from rest_framework import serializers


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
    source_text = serializers.CharField()
    target_text = serializers.CharField()
    transliterated_text = serializers.CharField()
