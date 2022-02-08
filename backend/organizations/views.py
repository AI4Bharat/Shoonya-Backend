import secrets
import string
from django.shortcuts import render
from rest_framework import viewsets, status
import re
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import Invite, Organization
from .serializers import InviteGenerationSerializer,OrganizationSerializer
from users.models import User
from rest_framework.decorators import action
from .decorators import is_organization_owner, is_particular_organization_owner



regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"


def generate_random_string(length=12):
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(length))


class InviteViewSet(viewsets.ViewSet):
    @swagger_auto_schema(request_body=InviteGenerationSerializer)
    @action(detail=False, methods=["post"], url_path="generate")
    def invite_users(self, request):
        emails = request.data.get("emails")
        organization_id = request.data.get("organization_id")
        users = []
        for email in emails:
            if re.fullmatch(regex, email):
                user = User(username=generate_random_string(12), email=email, password=generate_random_string())
                users.append(user)
            else:
                print("Invalide email: " + email)
        users = User.objects.bulk_create(users)
        try:
            org = Organization.objects.get(organization_id=organization_id)
        except Organization.DoesNotExist():
            return Response({"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        Invite.create_invite(organization=org, users=users)
        return Response({"message": "Invite sent"}, status=status.HTTP_200_OK)

class OrganizationViewSet(viewsets.ModelViewSet):
    """
    A viewset for Organization CRUD, access limited only to organization Managers and Superuser.
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

    @is_organization_owner    
    def create(self, request, pk=None, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @is_particular_organization_owner
    def update(self, request, pk=None, *args, **kwargs):
        return super().update(request, *args, **kwargs)        
    
    @is_particular_organization_owner
    def partial_update(self, request, pk=None, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        return Response({
            'message': 'Deleting of Organizations is not supported!'
        }, status=403)
