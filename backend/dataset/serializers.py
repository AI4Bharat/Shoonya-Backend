from rest_framework import serializers
from .models import *

class DatasetInstanceSerializer(serial.ModelSerializer):
    class Meta:
        model = DatasetInstance
        fields = '__all__'

class CollectionDatasetSerializer(serial.ModelSerializer):
    class Meta:
        model = CollectionDataset
        fields = '__all__'

class SpeechCollectionSerializer(serial.ModelSerializer):
    class Meta:
        model = SpeechCollection
        fields = '__all__'

class SpeechRecognitionSerializer(serial.ModelSerializer):
    class Meta:
        model = SpeechRecognition
        fields = '__all__'

class MonolingualSerializer(serial.ModelSerializer):
    class Meta:
        model = Monolingual
        fields = '__all__'

class TranslationSerializer(serial.ModelSerializer):
    class Meta:
        model = Translation
        fields = '__all__'

class OCRSerializer(serial.ModelSerializer):
    class Meta:
        model = OCR
        fields = '__all__'

class VideoSerializer(serial.ModelSerializer):
    class Meta:
        model = Video
        fields = '__all__'

class VideoChunkSerializer(serial.ModelSerializer):
    class Meta:
        model = VideoChunk
        fields = '__all__'