from dataclasses import fields
from rest_framework import serializers
from tasks.models import Task, Annotation

class TaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = '__all__'

class AnnotationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Annotation
        fields = '__all__'