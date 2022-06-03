from django.apps import apps
from django.shortcuts import render
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.decorators import permission_classes, action
from rest_framework.views import APIView

from urllib.parse import parse_qsl

from users.models import User

from .serializers import DatasetItemsSerializer, DatasetInstanceSerializer, TranslationPairSerializer 
from dataset import models
from filters import filter
from dataset import serializers

# Create your views here.

class DatasetInstanceViewSet(viewsets.ModelViewSet):
    '''
    ViewSet for Dataset Instance
    '''
    queryset = models.DatasetInstance.objects.all()
    serializer_class = DatasetInstanceSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def list(self, request, *args, **kwargs):
        if "dataset_type" in dict(request.query_params):
            queryset = models.DatasetInstance.objects.filter(dataset_type__exact=request.query_params["dataset_type"])
        else:
            queryset = models.DatasetInstance.objects.all()
        serializer = DatasetInstanceSerializer(queryset, many=True)
        return Response(serializer.data)

class DatasetItemsViewSet(viewsets.ModelViewSet):
    '''
    ViewSet for Dataset Items
    '''
    queryset = models.DatasetBase.objects.all()
    serializer_class = DatasetItemsSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )

    @action(detail=False, methods=['POST'], name='Get data Items')
    def get_data_items(self, request, *args, **kwargs):
        dataset_instance_ids = request.data.get('instance_ids')
        dataset_type = request.data.get('dataset_type',"")
        if type(dataset_instance_ids) != list:
            dataset_instance_ids = [dataset_instance_ids]
        filter_string = request.data.get('filter_string')
        #  Get dataset type from first dataset instance if dataset_type not passed in json data from frontend
        if dataset_type=="":
            dataset_type = models.DatasetInstance.objects.get(instance_id=dataset_instance_ids[0]).dataset_type
        dataset_model = getattr(models, dataset_type)
        data_items = dataset_model.objects.filter(instance_id__in=dataset_instance_ids)        
        query_params = dict(parse_qsl(filter_string))
        query_params = filter.fix_booleans_in_dict(query_params)
        filtered_set = filter.filter_using_dict_and_queryset(query_params, data_items)
        # filtered_data = filtered_set.values()
        # serializer = DatasetItemsSerializer(filtered_set, many=True)
        page = request.GET.get('page')
        try:
            page = self.paginate_queryset(filtered_set)
        except Exception as e:
            page = []
            data = page
            return Response({
                "status": status.HTTP_200_OK,
                "message": 'No more record.',
                #TODO: should be results. Needs testing to be sure.
                "data": data
            })

        if page is not None:
            datset_serializer=getattr(serializers, dataset_type+"Serializer")
            serializer=datset_serializer(page,many=True)
            data=serializer.data
            return self.get_paginated_response(data)

        return Response(status=status.HTTP_400_BAD_REQUEST)
        # return Response(filtered_data)


class DatasetTypeView(APIView):
    '''
    ViewSet for Dataset Type
    '''
    permission_classes = (IsAuthenticatedOrReadOnly, )

    
    def get(self, request, dataset_type):
        model = apps.get_model('dataset', dataset_type)
        fields = model._meta.get_fields()
        dict = {}
        for field in fields:
            try:
                dict[field.name] = {'name':str(field.get_internal_type()),'choices':vars(field)['choices']}
            except:
                dict[field.name] = {'name':str(field.get_internal_type()),'choices':None}
        return Response(dict,status=status.HTTP_200_OK)
# class SentenceTextViewSet(viewsets.ModelViewSet):
#     queryset = SentenceText.objects.all()
#     serializer_class = SentenceTextSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class SpeechCollectionViewset(viewsets.ModelViewSet):
#     queryset = SpeechCollection.objects.all()
#     serializer_class = SpeechCollectionSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class SpeechRecognitionViewSet(viewsets.ModelViewSet):
#     queryset = SpeechRecognition.objects.all()
#     serializer_class = SpeechRecognitionSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )


# class MonolingualViewSet(viewsets.ModelViewSet):
#     queryset = Monolingual.objects.all()
#     serializer_class = MonolingualSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class TranslationViewSet(viewsets.ModelViewSet):
#     queryset = Translation.objects.all()
#     serializer_class = TranslationSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class OCRViewSet(viewsets.ModelViewSet):
#     queryset = OCR.objects.all()
#     serializer_class = OCRSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class VideoViewSet(viewsets.ModelViewSet):
#     queryset = Video.objects.all()
#     serializer_class = VideoSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )

# class VideoChunkViewSet(viewsets.ModelViewSet):
#     queryset = VideoChunk.objects.all()
#     serializer_class = VideoChunkSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly, )
