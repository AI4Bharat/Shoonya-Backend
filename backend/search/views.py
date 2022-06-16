from rest_framework.generics import ListAPIView
from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework.decorators import action

from drf_yasg.utils import swagger_auto_schema

from .serializers import SearchSerializer
from projects.serializers import ProjectSerializer
from tasks.serializers import TaskSerializer
from users.serializers import UserProfileSerializer

from utils.search import process_search_query

from projects.models import Project
from tasks.models import Task
from users.models import User
from workspaces.models import Workspace

from shoonya_backend.pagination import CustomPagination, DEFAULT_PAGE_SIZE


class SearchViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """
    Processes the search queries and returns a DRF Response.
    It sends a proper response listing all projects, tasks
    """

    permission_classes = (IsAuthenticated,)
    role_dict = dict(User.ROLE_CHOICES)

    def get_serializer_class(self):
        """
        Dynamically chooses the serializer class for the queryset.
        """

        if self.query_type == "project":
            return ProjectSerializer
        elif self.query_type == "task":
            return TaskSerializer
        elif self.query_type == "user":
            return UserProfileSerializer

    def get_queryset(self):
        """
        Get the queryset based on GET ```type``` query param.
        """
        self.query_type = self.request.GET.get("type", "task")
        self.userRole = self.request.user.role

        # Authorization block: Select objects only with required permission levels
        if self.query_type == "task":
            if self.role_dict[self.userRole] == "Organization Owner":
                queryset = Task.objects.filter(
                    project_id__organization_id=self.request.user.organization
                )
            elif self.role_dict[self.userRole] == "Workspace Manager":
                queryset = Task.objects.filter(
                    project_id__workspace_id=self.request.user.workspace
                )
            elif self.role_dict[self.userRole] == "Reviewer":
                queryset = Task.objects.filter(review_user=self.request.user).union(
                    Task.objects.filter(annotation_users=request.user)
                )
            elif self.role_dict[self.userRole] == "Annotator":
                queryset = Task.objects.filter(annotation_users=self.request.user)
        elif self.query_type == "project":
            if self.role_dict[self.userRole] == "Organization Owner":
                queryset = Project.objects.filter(
                    organization_id=self.request.user.organization
                )
            elif self.role_dict[self.userRole] == "Workspace Manager":
                queryset = Project.objects.filter(
                    workspace_id=self.request.user.workspace
                )
            elif self.role_dict[self.userRole] == "Reviewer":
                queryset = Project.objects.filter(users=self.request.user)
            elif self.role_dict[self.userRole] == "Annotator":
                queryset = Project.objects.filter(users=self.request.user)
        elif self.query_type == "user":
            # TODO: For now, all users can see other users from their organization. Later, the access levels need to be figured out.
            queryset = User.objects.filter(
                    organization=self.request.user.organization
                )
            # if self.role_dict[self.userRole] == "Organization Owner":
            #     queryset = User.objects.filter(
            #         organization=self.request.user.organization
            #     )
            # elif self.role_dict[self.userRole] == "Workspace Manager":
            #     # queryset = User.objects.filter(Workspace.objects.filter(
            #     #     managers=self.request.user
            #     # ))
                
            #     queryset = User.objects.filter(
            #         organization=self.request.user.organization
            #     ) 
            #     # TODO: Currently keeping same access as Org Owner, but needs to 
            #     # be changed when proper m2m query is figured out. 
            # elif self.role_dict[self.userRole] == "Reviewer":
            #     queryset = Project.objects.filter(users=self.request.user)
            # elif self.role_dict[self.userRole] == "Annotator":
            #     queryset = Project.objects.filter(users=self.request.user)
            # else:
            #     queryset = User.objects.none()
        else:
            queryset = Task.objects.none()

        # Now filtering other parameters
        model_keys = list(Task.objects.first().data.keys())  # Defaults to Task model

        try:
            queryset = queryset.filter(
                **process_search_query(self.request.GET, "data", model_keys)
            )

            if self.query_type == "project":
                model_keys = [field.name for field in User._meta.get_fields()]

                queryset = queryset.filter(
                    **process_search_query(self.request.GET, "users", model_keys)
                )
            
            if self.query_type == "user":
                model_keys = []
                queryset = queryset.filter(
                    **process_search_query(self.request.GET, "", model_keys)
                )
        except:
            queryset = Task.objects.none()

        return queryset.order_by("id")

    def get(self, request, *args, **kwargs):
        page = request.GET.get("page")
        queryset = self.get_queryset()
        try:
            page = self.paginate_queryset(queryset)
        except Exception as e:
            page = []
            data = page
            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "message": "No more record.",
                    # TODO: should be results. Needs testing to be sure.
                    "data": data,
                }
            )

        if page is not None:
            serializer = (
                TaskSerializer(page, many=True)
                if self.query_type == "task"
                else ProjectSerializer(page, many=True)
            )
            data = serializer.data
            return self.get_paginated_response(data)
