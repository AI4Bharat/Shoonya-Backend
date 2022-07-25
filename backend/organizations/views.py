from datetime import datetime

from django.db.models import Avg, Count, F, FloatField, Q, Value
from django.db.models.functions import Cast, Coalesce
from projects.models import Project
from projects.utils import Round, is_valid_date, no_of_words
from regex import R
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from tasks.models import Task
from users.models import User
from users.serializers import UserFetchSerializer

from .decorators import is_organization_owner, is_particular_organization_owner
from .models import Organization
from .serializers import OrganizationSerializer


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    A viewset for Organization CRUD, access limited only to organization Managers and Superuser.
    """

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

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
        return Response(
            {"message": "Deleting of Organizations is not supported!"},
            status=status.HTTP_403_FORBIDDEN,
        )

    @is_particular_organization_owner
    @action(
        detail=True, methods=["GET"], name="Get Organization users", url_name="users"
    )
    def users(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        users = User.objects.filter(organization=organization)
        serializer = UserFetchSerializer(users, many=True)
        return Response(serializer.data)


    @is_organization_owner
    @action(
        detail=True, methods=["POST"], name="Get Organization level  users analytics ", url_name="user_analytics"
    )
    def user_analytics(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        users = User.objects.filter(organization=organization)

        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        from_date = from_date + ' 00:00'
        to_date = to_date + ' 23:59'
        tgt_language = request.data.get('tgt_language')
        project_type = request.data.get("project_type")
        sort_by_column_name = request.data.get('sort_by_column_name')
        descending_order = request.data.get('descending_order')
        if sort_by_column_name == None :
            sort_by_column_name = "User Name"

        if descending_order == None :
            descending_order = False

        cond, invalid_message = is_valid_date(from_date)
        if not cond:
            return Response({"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST)
        
        cond, invalid_message = is_valid_date(to_date)
        if not cond:
            return Response({"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST)

        start_date = datetime.strptime(from_date, '%Y-%m-%d %H:%M')
        end_date = datetime.strptime(to_date, '%Y-%m-%d %H:%M')

        if start_date > end_date:
            return Response({"message": "'To' Date should be after 'From' Date"}, status=status.HTTP_400_BAD_REQUEST)

        if tgt_language == None :
            tgt_language = r'.'

        # is_translation_project = True if  "translation" in  project_type.lower()  else False

        result = (
            User.objects.filter(organization=organization)
            .annotate(no_of_projects=Count("project_users", distinct=True))
            .annotate(
                no_of_workspaces=Count("project_users__workspace_id", distinct=True)
            )
            .annotate(
                total_tasks=Count(
                    "project_users__tasks",
                    filter=Q(project_users__project_type=project_type)
                    & Q(project_users__tgt_language__regex=tgt_language),
                )
            )
            .annotate(
                accepted_tasks=Count(
                    "project_users__tasks",
                    filter=Q(project_users__tasks__task_status="accepted") & Q(project_users__tasks__correct_annotation__created_at__range=[start_date, end_date]),
                )
            )
            .annotate(
                skipped_tasks=Count(
                    "project_users__tasks",
                    filter=Q(project_users__tasks__task_status="skipped"),
                )
            )
            .annotate(
                draft_tasks=Count(
                    "project_users__tasks",
                    filter=Q(project_users__tasks__task_status="draft"),
                )
            )
            .annotate(
                unlabeled_tasks=Count(
                    "project_users__tasks",
                    filter=Q(project_users__tasks__task_status="unlabeled"),
                )
            )
            .annotate(
                avg_annotation_time=Coalesce(
                    Avg(
                        "project_users__tasks__correct_annotation__lead_time",
                        filter=Q(project_users__tasks__task_status="accepted"),
                    ),
                    0.00,
                )
            )
            .annotate(avg_annotation_time_rounded=Round('avg_annotation_time'))
            .values(
                Annotator=F('username'),
                Email=F('email'),
                Language=Value(tgt_language),
                No_of_Workspaces= F('no_of_workspaces'),
                No_of_Projects=F('no_of_projects'),
                Project_Type=Value(project_type),
                No_of_Tasks_Assigned=F('total_tasks'),
                No_of_Annotated_Tasks=F('accepted_tasks'),
                Unlabeled_Tasks=F('unlabeled_tasks'),
                Skipped_Tasks=F('skipped_tasks'),
                Draft_Tasks=F('draft_tasks'),
                Word_Count_Of_Annotated_Tasks=Value('-'),
                Average_Annotation_Time_In_Seconds=F('avg_annotation_time_rounded')
            )
        )
        
        return Response(data=result, status=status.HTTP_200_OK)


    @is_organization_owner
    @action(
        detail=True, methods=["POST"], name="Get Organization level  Project analytics ", url_name="project_analytics"
    )
    def project_analytics(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        from_date = from_date + ' 00:00'
        to_date = to_date + ' 23:59'
        tgt_language = request.data.get('tgt_language')
        project_type = request.data.get("project_type")
        

        sort_by_column_name = request.data.get('sort_by_column_name')
        descending_order = request.data.get('descending_order')
        if sort_by_column_name == None :
            sort_by_column_name = "User Name"

        if descending_order == None :
            descending_order = False

        cond, invalid_message = is_valid_date(from_date)
        if not cond:
            return Response({"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST)
        
        cond, invalid_message = is_valid_date(to_date)
        if not cond:
            return Response({"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST)

        start_date = datetime.strptime(from_date, '%Y-%m-%d %H:%M')
        end_date = datetime.strptime(to_date, '%Y-%m-%d %H:%M')

        if start_date > end_date:
            return Response({"message": "'To' Date should be after 'From' Date"}, status=status.HTTP_400_BAD_REQUEST)

        if tgt_language == None :
            selected_language = '-'
            projects_obj  = Project.objects.filter(organization_id = organization,project_type = project_type)
        else :
            selected_language = tgt_language
            projects_obj  = Project.objects.filter(organization_id = organization,tgt_language = tgt_language,project_type = project_type)
        final_result = []
        if projects_obj.count() !=0:
            for proj in projects_obj:
                proj_manager = [manager.get_username() for manager in proj.workspace_id.managers.all()]
                try :
                    org_owner = proj.organization_id.created_by.get_username()
                    proj_manager.append(org_owner)
                except:
                    pass
                project_id = proj.id
                project_name = proj.title
                project_type = proj.project_type
                all_tasks = Task.objects.filter(project_id = proj.id)
                total_tasks = all_tasks.count()
                annotators_list = [ user_.get_username()  for user_ in   proj.users.all()]
                no_of_annotators_assigned = len( [annotator for annotator in annotators_list if annotator not in proj_manager ])
                un_labeled_task = Task.objects.filter(project_id = proj.id,task_status = 'unlabeled')
                un_labeled_count = un_labeled_task.count()
                labeled_count = Task.objects.filter(Q (project_id = proj.id) & Q(task_status = 'accepted') & Q (correct_annotation__created_at__range = [start_date, end_date])).count()
                skipped_count = Task.objects.filter(project_id = proj.id,task_status = 'skipped').count()
                dropped_tasks = Task.objects.filter(project_id = proj.id,task_status = 'draft').count()
                if total_tasks == 0:
                    project_progress = 0.0
                else :
                    project_progress = (labeled_count / total_tasks) * 100
                result = {
                    "Project Id" : project_id,
                    "Project Name" : project_name,
                    "Project Type" : project_type,
                    "Language" : selected_language,
                    "No.Of Annotators Assigned" : no_of_annotators_assigned,
                    "No.Of Tasks" : total_tasks,
                    "Annotated Tasks" : labeled_count,
                    "Unlabeled Tasks" : un_labeled_count,
                    "Skipped Tasks": skipped_count,
                    "Draft Tasks" : dropped_tasks,
                    "Project Progress" : round(project_progress,3)
                    }
                final_result.append(result)
        return Response(final_result)
