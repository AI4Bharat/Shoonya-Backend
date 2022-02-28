from django.shortcuts import render
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes, action

from users.models import User

from .serializers import * 
from .models import * 
# Create your views here.

class DatasetInstanceViewSet(viewsets.ModelViewSet):
    queryset = DatasetInstance.objects.all()
    serializer_class = DatasetInstanceSerializer
    permission_classes = IsAuthenticated


class CollectionDatasetViewSet(viewsets.ModelViewSet):
    queryset = CollectionDataset.objects.all()
    serializer_class = CollectionDatasetSerializer
    permission_classes = IsAuthenticated

class SpeechCollectionViewset(viewsets.ModelViewSet):
    queryset = SpeechCollection.objects.all()
    serializer_class = SpeechCollectionSerializer
    permission_classes = IsAuthenticated

class SpeechRecognitionViewSet(viewsets.ModelViewSet):
    queryset = SpeechRecognition.objects.all()
    serializer_class = SpeechRecognitionSerializer
    permission_classes = IsAuthenticated


class MonolingualViewSet(viewsets.ModelViewSet):
    queryset = Monolingual.objects.all()
    serializer_class = MonolingualSerializer
    permission_classes = IsAuthenticated

class TranslationViewSet(viewsets.ModelViewSet):
    queryset = Translation.objects.all()
    serializer_class = TranslationSerializer
    permission_classes = IsAuthenticated

class OCRViewSet(viewsets.ModelViewSet):
    queryset = OCR.objects.all()
    serializer_class = OCRSerializer
    permission_classes = IsAuthenticated

class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = IsAuthenticated

class VideoChunkViewSet(viewsets.ModelViewSet):
    queryset = VideoChunk.objects.all()
    serializer_class = VideoChunkSerializer
    permission_classes = IsAuthenticated