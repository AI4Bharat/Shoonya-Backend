from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response

from users.models import User

from .serializers import *
from .models import *
from .decorators import *

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

    @is_organization_owner
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @is_organization_owner    
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @is_organization_owner
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)        
    
    @is_organization_owner
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        return Response({
            'message': 'Deleting of Organizations is not supported!'
        }, status=403)
