from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response

from users.models import User

from .serializers import *
from .models import *

# Create your views here.

class OrganizationViewSet(viewsets.ModelViewSet):
    """
    A viewset for Organization CRUD, access limited only to organization Managers and Superuser.
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

    PERMISSION_ERROR = {
        'message': 'You do not have enough permissions to access this view!'
    }

    def retrieve(self, request, *args, **kwargs):
        if request.user == User.ORGANIZAION_OWNER or request.user.is_superuser:
            return super().retrieve(request, *args, **kwargs)
        return Response(self.PERMISSION_ERROR, status=403)

    def create(self, request, *args, **kwargs):
        if request.user == User.ORGANIZAION_OWNER or request.user.is_superuser:
            return super().create(request, *args, **kwargs)
        return Response(self.PERMISSION_ERROR, status=403)

    def update(self, request, *args, **kwargs):
        if request.user == User.ORGANIZAION_OWNER or request.user.is_superuser:
            return super().update(request, *args, **kwargs)        
        return Response(self.PERMISSION_ERROR, status=403)
    
    def partial_update(self, request, *args, **kwargs):
        if request.user == User.ORGANIZAION_OWNER or request.user.is_superuser:
            return super().partial_update(request, *args, **kwargs)
        return Response(self.PERMISSION_ERROR, status=403)
    
    def destroy(self, request, *args, **kwargs):
        return Response({
            'message': 'Deleting of Organizations is not supported!'
        }, status=403)
