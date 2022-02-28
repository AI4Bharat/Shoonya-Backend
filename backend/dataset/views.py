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
    

class SpeechCollectionViewset(viewsets.ModelViewSet):

class SpeechRecognitionViewSet(viewsets.ModelViewSet):


class MonolingualViewSet(viewsets.ModelViewSet):

class TranslationViewSet(viewsets.ModelViewSet):

class OCRViewSet(viewsets.ModelViewSet):

class VideoViewSet(viewsets.ModelViewSet):

class VideoChunkViewSet(viewsets.ModelViewSet):