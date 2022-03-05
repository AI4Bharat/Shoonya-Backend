import re
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

from users.models import User
from users.serializers import UserProfileSerializer

from .serializers import WorkspaceManagerSerializer, WorkspaceSerializer
from .models import Workspace
from .decorators import (
    is_organization_owner_or_workspace_manager,
    workspace_is_archived,
    is_particular_workspace_manager,
)

# Create your views here.

EMAIL_VALIDATION_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"


class WorkspaceViewSet(viewsets.ModelViewSet):
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer
    permission_classes = (IsAuthenticated, )

    def list(self, request, *args, **kwargs):
        if request.user.role == User.ANNOTATOR:
            data = self.queryset.filter(users=request.user)
            serializer = self.serializer_class(data=data)
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_200_OK)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, pk=None, *args, **kwargs):
        print(pk)
        return super().retrieve(request, *args, **kwargs)

    @is_organization_owner_or_workspace_manager
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @is_particular_workspace_manager
    @workspace_is_archived
    def update(self, request, pk=None, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @is_particular_workspace_manager
    @workspace_is_archived
    def partial_update(self, request, pk=None, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        return Response(
            {"message": "Deleting of Workspaces is not supported!"},
            status=status.HTTP_403_FORBIDDEN,
        )

    @is_particular_workspace_manager
    @action(detail=True, methods=["GET"], name="Get Workspace users", url_name="users")
    def users(self, request, pk=None):
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response(
                {"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )
        users = workspace.users.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data)

    # TODO : add exceptions
    @action(
        detail=True,
        methods=["POST", "GET"],
        name="Archive Workspace",
        url_name="archive",
    )
    @is_particular_workspace_manager
    def archive(self, request, pk=None, *args, **kwargs):
        print(pk)
        workspace = Workspace.objects.get(pk=pk)
        workspace.is_archived = not workspace.is_archived
        workspace.save()
        return super().retrieve(request, *args, **kwargs)

    # TODO : add exceptions
    @action(
        detail=True, methods=["POST"], name="Assign Manager", url_name="assign_manager"
    )
    @is_particular_workspace_manager
    def assign_manager(self, request, pk=None, *args, **kwargs):
        ret_dict = {}
        ret_status = 0
        email = str(request.data["email"])
        try:
            if re.fullmatch(EMAIL_VALIDATION_REGEX, email):
                user = User.objects.get(email=email)
                workspace = Workspace.objects.get(pk=pk)
                workspace.manager = user
                workspace.save()
                serializer = WorkspaceManagerSerializer(workspace, many=False)
                ret_dict = serializer.data
                ret_status = status.HTTP_200_OK
            else:
                ret_dict = {"message": "Enter a valid Email!"}
                ret_status = status.HTTP_400_BAD_REQUEST
        except User.DoesNotExist:
            ret_dict = {"message": "User with such Email does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except Exception:
            ret_dict = {"message": "Email is required!"}
            ret_status = status.HTTP_400_BAD_REQUEST
        return Response(ret_dict, status=ret_status)
