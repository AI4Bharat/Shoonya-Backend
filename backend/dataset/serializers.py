from rest_framework import serializers
from .models import *

class DatasetInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetInstance
        fields = '__all__'


class DatasetItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetBase
        fields = ["instance_id"]

# class CollectionDatasetSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CollectionDataset
#         fields = '__all__'

# class SpeechCollectionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SpeechCollection
#         fields = '__all__'

# class SpeechRecognitionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SpeechRecognition
#         fields = '__all__'

# class MonolingualSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Monolingual
#         fields = '__all__'

# class TranslationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Translation
#         fields = '__all__'

# class OCRSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OCR
#         fields = '__all__'

# class VideoSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Video
#         fields = '__all__'

# class VideoChunkSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = VideoChunk
#         fields = '__all__'
