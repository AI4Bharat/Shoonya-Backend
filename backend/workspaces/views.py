from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated
from projects.serializers import ProjectSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from projects.models import Project
from users.models import User
from users.serializers import UserProfileSerializer
from tasks.models import Task
from organizations.models import Organization
from django.db.models import Q
from projects.utils import no_of_words
from tasks.models import Annotation
from projects.utils import is_valid_date
from datetime import datetime
from users.serializers import UserFetchSerializer
from users.views import get_role_name
from projects.utils import (
    minor_major_accepted_task,
    convert_seconds_to_hours,
    get_audio_project_types,
    get_audio_transcription_duration,
)


from .serializers import (
    UnAssignManagerSerializer,
    WorkspaceManagerSerializer,
    WorkspaceSerializer,
    WorkspaceNameSerializer,
)
from .models import Workspace
from .decorators import (
    workspace_is_archived,
    is_particular_workspace_manager,
    is_particular_organization_owner,
    is_organization_owner_or_workspace_manager,
    is_workspace_creator,
)


# Create your views here.

EMAIL_VALIDATION_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"


def get_task_count(proj_ids, status, annotator, return_count=True):
    annotated_tasks = Task.objects.filter(
        Q(project_id__in=proj_ids)
        & Q(task_status__in=status)
        & Q(annotation_users=annotator)
    )

    if return_count == True:
        annotated_tasks_count = annotated_tasks.count()
        return annotated_tasks_count
    else:
        return annotated_tasks


def get_task_count_project_analytics(proj_id, status_list, return_count=True):
    labeled_tasks = Task.objects.filter(project_id=proj_id, task_status__in=status_list)
    if return_count == True:
        labeled_tasks_count = labeled_tasks.count()
        return labeled_tasks_count
    else:
        return labeled_tasks


def get_annotated_tasks(proj_ids, annotator, status_list, start_date, end_date):
    annotated_tasks_objs = get_task_count(
        proj_ids, status_list, annotator, return_count=False
    )

    annotated_task_ids = list(annotated_tasks_objs.values_list("id", flat=True))
    annotated_labeled_tasks = Annotation.objects.filter(
        task_id__in=annotated_task_ids,
        parent_annotation_id=None,
        created_at__range=[start_date, end_date],
        completed_by=annotator,
    )

    return annotated_labeled_tasks


def get_annotated_tasks_project_analytics(proj_id, status_list, start_date, end_date):
    labeled_tasks = get_task_count_project_analytics(
        proj_id, status_list, return_count=False
    )

    labeled_tasks_ids = list(labeled_tasks.values_list("id", flat=True))
    annotated_labeled_tasks = Annotation.objects.filter(
        task_id__in=labeled_tasks_ids,
        parent_annotation_id=None,
        created_at__range=[start_date, end_date],
    )

    return annotated_labeled_tasks


def get_review_reports(proj_ids, userid, start_date, end_date):
    user = User.objects.get(id=userid)
    participation_type = user.participation_type
    participation_type = (
        "Full Time"
        if participation_type == 1
        else "Part Time"
        if participation_type == 2
        else "N/A"
    )
    role = get_role_name(user.role)
    userName = user.username
    email = user.email

    reviewer_languages = user.languages

    total_tasks = Task.objects.filter(project_id__in=proj_ids, review_user=userid)

    total_task_count = total_tasks.count()

    accepted_tasks = Annotation.objects.filter(
        annotation_status="accepted",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    accepted_objs_count = accepted_tasks.count()

    acceptedwt_minor_change_tasks = Annotation.objects.filter(
        annotation_status="accepted_with_minor_changes",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    minor_changes = acceptedwt_minor_change_tasks.count()

    acceptedwt_major_change_tasks = Annotation.objects.filter(
        annotation_status="accepted_with_major_changes",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    major_changes = acceptedwt_major_change_tasks.count()

    labeled_tasks = Task.objects.filter(
        project_id__in=proj_ids, review_user=userid, task_status="annotated"
    )
    labeled_tasks_count = labeled_tasks.count()

    to_be_revised_tasks = Annotation.objects.filter(
        annotation_status="to_be_revised",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    to_be_revised_tasks_count = to_be_revised_tasks.count()

    skipped_tasks = Annotation.objects.filter(
        annotation_status="skipped",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    skipped_tasks_count = skipped_tasks.count()

    draft_tasks = Annotation.objects.filter(
        annotation_status="draft",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    draft_tasks_count = draft_tasks.count()

    result = {
        "Reviewer Name": userName,
        "Email": email,
        "Participation Type": participation_type,
        "User Role": role,
        "Language": reviewer_languages,
        "Assigned": total_task_count,
        "Accepted": accepted_objs_count,
        "Accepted With Minor Changes": minor_changes,
        "Accepted With Major Changes": major_changes,
        "Unreviewed": labeled_tasks_count,
        "To Be Revised": to_be_revised_tasks_count,
        "Skipped": skipped_tasks_count,
        "Draft": draft_tasks_count,
    }
    return result


def un_pack_annotation_tasks(
    proj_ids,
    each_annotation_user,
    start_date,
    end_date,
    is_translation_project,
    project_type,
):
    annotations_of_reviewer_accepted = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        annotation_status="accepted",
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )
    parent_anno_ids = [
        ann.parent_annotation_id for ann in annotations_of_reviewer_accepted
    ]
    accepted = Annotation.objects.filter(
        id__in=parent_anno_ids,
        completed_by=each_annotation_user,
    )

    annotations_of_reviewer_to_be_revised = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        annotation_status="to_be_revised",
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )
    parent_anno_ids_of_to_be_revised = [
        ann.parent_annotation_id for ann in annotations_of_reviewer_to_be_revised
    ]
    to_be_revised = Annotation.objects.filter(
        id__in=parent_anno_ids_of_to_be_revised,
        completed_by=each_annotation_user,
    )

    # accepted with minor change

    annotations_of_reviewer_minor = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        annotation_status="accepted_with_minor_changes",
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    parent_anno_ids_of_minor = [
        ann.parent_annotation_id for ann in annotations_of_reviewer_minor
    ]
    accepted_wt_minor_changes = Annotation.objects.filter(
        id__in=parent_anno_ids_of_minor,
        completed_by=each_annotation_user,
    )

    # accepted with Major changes

    annotations_of_reviewer_major = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        annotation_status="accepted_with_major_changes",
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    parent_anno_ids_of_major = [
        ann.parent_annotation_id for ann in annotations_of_reviewer_major
    ]
    accepted_wt_major_changes = Annotation.objects.filter(
        id__in=parent_anno_ids_of_major,
        completed_by=each_annotation_user,
    )

    # labeled task count

    labeled_annotations = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        annotation_status="labeled",
        parent_annotation_id__isnull=True,
        created_at__range=[start_date, end_date],
        completed_by=each_annotation_user,
    )
    labeled_annotation_ids = [ann.id for ann in labeled_annotations]

    reviewed_ann = Annotation.objects.filter(
        parent_annotation_id__in=labeled_annotation_ids
    ).count()

    labeled = len(labeled_annotations) - reviewed_ann

    lead_time_annotated_tasks = [eachtask.lead_time for eachtask in labeled_annotations]
    avg_lead_time = 0
    if len(lead_time_annotated_tasks) > 0:
        avg_lead_time = sum(lead_time_annotated_tasks) / len(lead_time_annotated_tasks)
    total_word_count = 0
    if is_translation_project or project_type == "SemanticTextualSimilarity_Scale5":
        total_word_count_list = []
        for each_task in labeled_annotations:
            try:
                total_word_count_list.append(each_task.task.data["word_count"])
            except:
                pass

        total_word_count = sum(total_word_count_list)
    total_duration = "0:00:00"
    if project_type in get_audio_project_types():
        total_duration_list = []
        for each_task in labeled_annotations:
            try:
                total_duration_list.append(
                    get_audio_transcription_duration(each_task.result)
                )
            except:
                pass
        total_duration = convert_seconds_to_hours(sum(total_duration_list))

    return (
        accepted.count(),
        to_be_revised.count(),
        accepted_wt_minor_changes.count(),
        accepted_wt_major_changes.count(),
        labeled,
        avg_lead_time,
        total_word_count,
        total_duration,
    )


class WorkspaceViewSet(viewsets.ModelViewSet):
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        if int(request.user.role) == User.WORKSPACE_MANAGER:
            data = self.queryset.filter(
                managers=request.user,
                is_archived=False,
                organization=request.user.organization,
            )
            serializer = WorkspaceSerializer(data, many=True)
            return Response(serializer.data)
        elif int(request.user.role) == User.ORGANIZATION_OWNER:
            data = self.queryset.filter(organization=request.user.organization)
            serializer = WorkspaceSerializer(data, many=True)
            return Response(serializer.data)
        else:
            return Response(
                {"message": "Not authorized!"}, status=status.HTTP_403_FORBIDDEN
            )

    def retrieve(self, request, pk=None, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @is_workspace_creator
    def create(self, request, *args, **kwargs):
        # TODO: Make sure to add the user to the workspace and created_by
        # return super().create(request, *args, **kwargs)
        try:
            data = self.serializer_class(data=request.data)
            if data.is_valid():
                if request.user.organization == data.validated_data["organization"]:
                    obj = data.save()
                    obj.members.add(request.user)
                    obj.created_by = request.user
                    obj.save()
                    return Response(
                        {"message": "Workspace created!"},
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    return Response(
                        {
                            "message": "You are not authorized to create workspace for this organization!"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            else:
                return Response(
                    {"message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST
                )
        except:
            return Response(
                {"message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST
            )

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


class WorkspaceCustomViewSet(viewsets.ViewSet):
    @swagger_auto_schema(responses={200: UserProfileSerializer})
    @is_particular_workspace_manager
    @action(
        detail=True, methods=["GET"], name="Get Workspace members", url_name="members"
    )
    def members(self, request, pk=None):
        """
        Get all members of a workspace
        """
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response(
                {"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )
        members = workspace.members.all()
        serializer = UserProfileSerializer(members, many=True)
        return Response(serializer.data)

    # TODO : add exceptions
    @action(
        detail=True,
        methods=["POST"],
        name="Archive Workspace",
        url_name="archive",
    )
    @is_particular_organization_owner
    def archive(self, request, pk=None, *args, **kwargs):
        workspace = Workspace.objects.get(pk=pk)
        workspace.is_archived = not workspace.is_archived
        workspace.save()
        return Response({"done": True}, status=status.HTTP_200_OK)

    # TODO: Add serializer
    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "ids": openapi.Schema(type=openapi.TYPE_STRING, format="email")
            },
            required=["ids"],
        ),
        responses={
            200: "Done",
            404: "User with such Username does not exist!",
            400: "Bad request,Some exception occured",
        },
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
    )
    @action(
        detail=True, methods=["POST"], name="Assign Manager", url_name="assign_manager"
    )
    @is_particular_organization_owner
    def assign_manager(self, request, pk=None, *args, **kwargs):
        """
        API for assigning manager to a workspace
        """
        ret_dict = {}
        ret_status = 0
        if "ids" in dict(request.data):
            ids = request.data.get("ids", "")
        else:
            return Response(
                {"message": "key doesnot match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for id1 in ids:
            try:
                user = User.objects.get(id=id1)
            except User.DoesNotExist:
                return Response(
                    {"message": "User with such id does not exist!"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            try:
                workspace = Workspace.objects.get(pk=pk)
            except Workspace.DoesNotExist:
                ret_dict["message"] = "Workspace not found!"
                ret_status = status.HTTP_404_NOT_FOUND
                return Response(ret_dict, status=ret_status)
            if user in workspace.managers.all():
                ret_dict["message"] = "User already exists in workspace!"
                ret_status = status.HTTP_400_BAD_REQUEST
                return Response(ret_dict, status=ret_status)
            workspace.managers.add(user)
            workspace.members.add(user)
            workspace.save()
            serializer = WorkspaceManagerSerializer(workspace, many=False)
        return Response({"done": True}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["POST"],
        name="Unassign Manager",
        url_name="unassign_manager",
    )
    @is_particular_organization_owner
    def unassign_manager(self, request, pk=None, *args, **kwargs):
        """
        API Endpoint for unassigning an workspace manager
        """
        ret_dict = {}
        ret_status = 0
        if "ids" in dict(request.data):
            ids = request.data.get("ids", "")
        else:
            return Response(
                {"message": "key doesnot match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            workspace = Workspace.objects.get(pk=pk)

            for id1 in ids:
                try:
                    user = User.objects.get(id=id1)
                except User.DoesNotExist:
                    return Response(
                        {"message": "User with such id does not exist!"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                if user not in workspace.managers.all():
                    return Response(
                        {"message": "user not found in workspace"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    workspace.managers.remove(user)
            return Response({"done": True}, status=status.HTTP_200_OK)
        except Workspace.DoesNotExist:
            ret_dict["message"] = "Workspace not found!"
            ret_status = status.HTTP_404_NOT_FOUND
            return Response(ret_dict, status=ret_status)

    @swagger_auto_schema(
        method="get",
        responses={200: ProjectSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                "only_active",
                openapi.IN_QUERY,
                description=(
                    "It is passed as true to get all the projects which are not archived,to get all it is passed as false"
                ),
                type=openapi.TYPE_BOOLEAN,
                required=False,
            ),
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
    )
    @action(
        detail=True,
        methods=["GET"],
        name="Get Projects",
        url_path="projects",
        url_name="projects",
    )
    @is_particular_workspace_manager
    def get_projects(self, request, pk=None):
        """
        API for getting all projects of a workspace
        """
        only_active = str(request.GET.get("only_active", "false"))
        only_active = True if only_active == "true" else False
        try:
            workspace = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response(
                {"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if request.user.role == User.ANNOTATOR:
            projects = Project.objects.filter(
                annotators=request.user, workspace_id=workspace
            )
        else:
            projects = Project.objects.filter(workspace_id=workspace)
        if only_active == True:
            projects = projects.filter(is_archived=False)
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["POST"],
        name="Workspace Project Details",
        url_path="project_analytics",
        url_name="project_analytics",
    )
    @is_particular_workspace_manager
    def project_analytics(self, request, pk=None):
        """
        API for getting project_analytics of a workspace
        """
        try:
            ws = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response(
                {"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            ws_owner = ws.created_by.get_username()
        except:
            ws_owner = ""
        try:
            org_id = ws.organization.id
            org_obj = Organization.objects.get(id=org_id)
            org_owner = org_obj.created_by.get_username()
        except:
            org_owner = ""

        tgt_language = request.data.get("tgt_language")
        project_type = request.data.get("project_type")
        # enable_task_reviews = request.data.get("enable_task_reviews")
        selected_language = "-"
        if tgt_language == None:
            projects_objs = Project.objects.filter(
                workspace_id=pk, project_type=project_type
            )
        else:
            selected_language = tgt_language
            projects_objs = Project.objects.filter(
                workspace_id=pk, project_type=project_type, tgt_language=tgt_language
            )
        final_result = []
        if projects_objs.count() != 0:
            for proj in projects_objs:
                owners = [org_owner, ws_owner]
                project_id = proj.id
                project_name = proj.title
                project_type = proj.project_type
                project_type_lower = project_type.lower()
                is_translation_project = (
                    True if "translation" in project_type_lower else False
                )

                all_tasks = Task.objects.filter(project_id=proj.id)
                total_tasks = all_tasks.count()
                annotators_list = [
                    annotator.get_username() for annotator in proj.annotators.all()
                ]
                try:
                    proj_owner = proj.created_by.get_username()
                    owners.append(proj_owner)
                except:
                    pass
                no_of_annotators_assigned = len(
                    [
                        annotator
                        for annotator in annotators_list
                        if annotator not in owners
                    ]
                )

                incomplete_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="incomplete"
                )
                incomplete_count = incomplete_tasks.count()

                labeled_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="annotated"
                )
                labeled_count = labeled_tasks.count()

                reviewed_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="reviewed"
                )

                reviewed_count = reviewed_tasks.count()

                exported_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="exported"
                )
                exported_count = exported_tasks.count()

                total_word_annotated_count_list = []
                total_word_reviewed_count_list = []
                total_word_exported_count_list = []
                if (
                    is_translation_project
                    or project_type == "SemanticTextualSimilarity_Scale5"
                ):
                    for each_task in labeled_tasks:
                        try:
                            total_word_annotated_count_list.append(
                                each_task.data["word_count"]
                            )
                        except:
                            pass

                    for each_task in reviewed_tasks:
                        try:
                            total_word_reviewed_count_list.append(
                                each_task.data["word_count"]
                            )
                        except:
                            pass
                    for each_task in exported_tasks:
                        try:
                            total_word_exported_count_list.append(
                                each_task.data["word_count"]
                            )
                        except:
                            pass
                total_word_annotated_count = sum(total_word_annotated_count_list)
                total_word_reviewed_count = sum(total_word_reviewed_count_list)
                total_word_exported_count = sum(total_word_exported_count_list)

                total_duration_annotated_count_list = []
                total_duration_reviewed_count_list = []
                total_duration_exported_count_list = []
                if project_type in get_audio_project_types():
                    for each_task in labeled_tasks:
                        try:
                            annotate_annotation = Annotation.objects.filter(
                                task=each_task, parent_annotation_id__isnull=True
                            )[0]
                            total_duration_annotated_count_list.append(
                                get_audio_transcription_duration(
                                    annotate_annotation.result
                                )
                            )
                        except:
                            pass

                    for each_task in reviewed_tasks:
                        try:
                            review_annotation = Annotation.objects.filter(
                                task=each_task, parent_annotation_id__isnull=False
                            )[0]
                            total_duration_reviewed_count_list.append(
                                get_audio_transcription_duration(
                                    review_annotation.result
                                )
                            )
                        except:
                            pass

                    for each_task in exported_tasks:
                        try:
                            total_duration_exported_count_list.append(
                                get_audio_transcription_duration(
                                    each_task.correct_annotation.result
                                )
                            )
                        except:
                            pass

                total_duration_annotated_count = convert_seconds_to_hours(
                    sum(total_duration_annotated_count_list)
                )
                total_duration_reviewed_count = convert_seconds_to_hours(
                    sum(total_duration_reviewed_count_list)
                )
                total_duration_exported_count = convert_seconds_to_hours(
                    sum(total_duration_exported_count_list)
                )

                if total_tasks == 0:
                    project_progress = 0.0
                else:
                    project_progress = (reviewed_count / total_tasks) * 100
                result = {
                    "Project Id": project_id,
                    "Project Name": project_name,
                    "Language": selected_language,
                    "Project Type": project_type,
                    "No .of Annotators Assigned": no_of_annotators_assigned,
                    "Total": total_tasks,
                    "Annotated": labeled_count,
                    "Incomplete": incomplete_count,
                    "Reviewed": reviewed_count,
                    "Exported": exported_count,
                    "Annotated Tasks Audio Duration": total_duration_annotated_count,
                    "Reviewed Tasks Audio Duration": total_duration_reviewed_count,
                    "Exported Tasks Audio Duration": total_duration_exported_count,
                    "Annotated Tasks Word Count": total_word_annotated_count,
                    "Reviewed Tasks Word Count": total_word_reviewed_count,
                    "Exported Tasks Word Count": total_word_exported_count,
                    "Project Progress(Reviewed/Total)": round(project_progress, 3),
                }

                if project_type in get_audio_project_types():
                    del result["Annotated Tasks Word Count"]
                    del result["Reviewed Tasks Word Count"]
                    del result["Exported Tasks Word Count"]

                elif (
                    is_translation_project
                    or project_type == "SemanticTextualSimilarity_Scale5"
                ):
                    del result["Annotated Tasks Audio Duration"]
                    del result["Reviewed Tasks Audio Duration"]
                    del result["Exported Tasks Audio Duration"]
                else:
                    del result["Annotated Tasks Word Count"]
                    del result["Reviewed Tasks Word Count"]
                    del result["Exported Tasks Word Count"]
                    del result["Annotated Tasks Audio Duration"]
                    del result["Reviewed Tasks Audio Duration"]
                    del result["Exported Tasks Audio Duration"]

                final_result.append(result)
        ret_status = status.HTTP_200_OK
        return Response(final_result, status=ret_status)

    @action(
        detail=True,
        methods=["POST"],
        name="Workspace member Details",
        url_path="user_analytics",
        url_name="user_analytics",
    )
    def user_analytics(self, request, pk=None):
        """
        API for getting user_analytics of a workspace
        """
        try:
            ws = Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            return Response(
                {"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            ws_owner = ws.created_by.get_username()
        except:
            ws_owner = ""
        try:
            org_id = ws.organization.id
            org_obj = Organization.objects.get(id=org_id)
            org_owner = org_obj.created_by.get_username()
        except:
            org_owner = ""
        user_id = request.user.id
        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")
        from_date = from_date + " 00:00"
        to_date = to_date + " 23:59"
        only_review_proj = request.data.get("only_review_projects")
        reports_type = request.data.get("reports_type")
        tgt_language = request.data.get("tgt_language")
        project_type = request.data.get("project_type")
        project_type_lower = project_type.lower()
        is_translation_project = True if "translation" in project_type_lower else False
        # enable_task_reviews = request.data.get("enable_task_reviews")

        cond, invalid_message = is_valid_date(from_date)
        if not cond:
            return Response(
                {"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST
            )
        cond, invalid_message = is_valid_date(to_date)
        if not cond:
            return Response(
                {"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST
            )
        start_date = datetime.strptime(from_date, "%Y-%m-%d %H:%M")
        end_date = datetime.strptime(to_date, "%Y-%m-%d %H:%M")

        if start_date > end_date:
            return Response(
                {"message": "'To' Date should be after 'From' Date"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reports_type == "review":
            proj_objs = Project.objects.filter(workspace_id=pk)
            review_projects = [pro for pro in proj_objs if pro.enable_task_reviews]

            workspace_reviewer_list = []
            for review_project in review_projects:
                reviewer_names_list = review_project.annotation_reviewers.all()
                reviewer_ids = [name.id for name in reviewer_names_list]
                workspace_reviewer_list.extend(reviewer_ids)

            workspace_reviewer_list = list(set(workspace_reviewer_list))
            final_reports = []

            if (
                request.user.role == User.ORGANIZATION_OWNER
                or request.user.role == User.WORKSPACE_MANAGER
                or request.user.is_superuser
            ):
                for id in workspace_reviewer_list:
                    reviewer_projs = Project.objects.filter(
                        workspace_id=pk, annotation_reviewers=id
                    )
                    reviewer_projs_ids = [
                        review_proj.id for review_proj in reviewer_projs
                    ]

                    result = get_review_reports(
                        reviewer_projs_ids, id, start_date, end_date
                    )
                    final_reports.append(result)
            elif user_id in workspace_reviewer_list:
                reviewer_projs = Project.objects.filter(
                    workspace_id=pk, annotation_reviewers=user_id
                )
                reviewer_projs_ids = [review_proj.id for review_proj in reviewer_projs]

                result = get_review_reports(
                    reviewer_projs_ids, user_id, start_date, end_date
                )
                final_reports.append(result)

            else:
                final_reports = {
                    "message": "You do not have enough permissions to access this view!"
                }

            return Response(final_reports)

        if not (
            request.user.is_authenticated
            and (
                request.user.role == User.ORGANIZATION_OWNER
                or request.user.role == User.WORKSPACE_MANAGER
                or request.user.is_superuser
            )
        ):
            final_response = {
                "message": "You do not have enough permissions to access this view!"
            }
            return Response(final_response, status=status.HTTP_400_BAD_REQUEST)

        user_obj = list(ws.members.all())
        user_mail = [user.get_username() for user in ws.members.all()]
        user_name = [user.username for user in ws.members.all()]
        users_id = [user.id for user in ws.members.all()]

        selected_language = "-"
        final_result = []
        for index, each_annotation_user in enumerate(users_id):
            name = user_name[index]
            email = user_mail[index]
            list_of_user_languages = user_obj[index].languages

            if tgt_language != None and tgt_language not in list_of_user_languages:
                continue
            if email == ws_owner or email == org_owner:
                continue
            if tgt_language == None:
                if only_review_proj == None:
                    projects_objs = Project.objects.filter(
                        workspace_id=pk,
                        annotators=each_annotation_user,
                        project_type=project_type,
                    )
                else:
                    projects_objs = Project.objects.filter(
                        workspace_id=pk,
                        annotators=each_annotation_user,
                        project_type=project_type,
                        enable_task_reviews=only_review_proj,
                    )

            else:
                selected_language = tgt_language
                if only_review_proj == None:
                    projects_objs = Project.objects.filter(
                        workspace_id=pk,
                        annotators=each_annotation_user,
                        project_type=project_type,
                        tgt_language=tgt_language,
                    )
                else:
                    projects_objs = Project.objects.filter(
                        workspace_id=pk,
                        annotators=each_annotation_user,
                        project_type=project_type,
                        tgt_language=tgt_language,
                        enable_task_reviews=only_review_proj,
                    )

            project_count = projects_objs.count()
            proj_ids = [eachid["id"] for eachid in projects_objs.values("id")]

            all_tasks_in_project = Task.objects.filter(
                Q(project_id__in=proj_ids) & Q(annotation_users=each_annotation_user)
            )
            assigned_tasks = all_tasks_in_project.count()

            if only_review_proj:
                (
                    accepted,
                    to_be_revised,
                    accepted_wt_minor_changes,
                    accepted_wt_major_changes,
                    labeled,
                    avg_lead_time,
                    total_word_count,
                    total_duration,
                ) = un_pack_annotation_tasks(
                    proj_ids,
                    each_annotation_user,
                    start_date,
                    end_date,
                    is_translation_project,
                    project_type,
                )

            else:
                labeled_annotations = Annotation.objects.filter(
                    task__project_id__in=proj_ids,
                    annotation_status="labeled",
                    parent_annotation_id__isnull=True,
                    created_at__range=[start_date, end_date],
                    completed_by=each_annotation_user,
                )

                annotated_tasks = labeled_annotations.count()
                lead_time_annotated_tasks = [
                    eachtask.lead_time for eachtask in labeled_annotations
                ]
                avg_lead_time = 0
                if len(lead_time_annotated_tasks) > 0:
                    avg_lead_time = sum(lead_time_annotated_tasks) / len(
                        lead_time_annotated_tasks
                    )
                total_word_count = 0
                if (
                    is_translation_project
                    or project_type == "SemanticTextualSimilarity_Scale5"
                ):
                    total_word_count_list = []
                    for each_task in labeled_annotations:
                        try:
                            total_word_count_list.append(
                                each_task.task.data["word_count"]
                            )
                        except:
                            pass

                    total_word_count = sum(total_word_count_list)
                total_duration = "0:00:00"
                if project_type in get_audio_project_types():
                    total_duration_list = []

                    for each_task in labeled_annotations:
                        try:
                            total_duration_list.append(
                                get_audio_transcription_duration(each_task.result)
                            )
                        except:
                            pass
                    total_duration = convert_seconds_to_hours(sum(total_duration_list))

            total_skipped_tasks = Annotation.objects.filter(
                task__project_id__in=proj_ids,
                annotation_status="skipped",
                parent_annotation_id__isnull=True,
                created_at__range=[start_date, end_date],
                completed_by=each_annotation_user,
            ).count()
            all_pending_tasks_in_project = Annotation.objects.filter(
                task__project_id__in=proj_ids,
                annotation_status="unlabeled",
                parent_annotation_id__isnull=True,
                created_at__range=[start_date, end_date],
                completed_by=each_annotation_user,
            ).count()

            all_draft_tasks_in_project = Annotation.objects.filter(
                task__project_id__in=proj_ids,
                annotation_status="draft",
                parent_annotation_id__isnull=True,
                created_at__range=[start_date, end_date],
                completed_by=each_annotation_user,
            ).count()

            if only_review_proj:
                result = {
                    "Annotator": name,
                    "Email": email,
                    "Language": selected_language,
                    "No.of Projects": project_count,
                    "Assigned": assigned_tasks,
                    "Labeled": labeled,
                    "Accepted": accepted,
                    "Accepted With Minor Changes": accepted_wt_minor_changes,
                    "Accepted With Major Changes": accepted_wt_major_changes,
                    "To Be Revised": to_be_revised,
                    "Unlabeled": all_pending_tasks_in_project,
                    "Skipped": total_skipped_tasks,
                    "Draft": all_draft_tasks_in_project,
                    "Word Count": total_word_count,
                    "Total Audio Duration": total_duration,
                    "Average Annotation Time (In Seconds)": round(avg_lead_time, 2),
                }
            else:
                result = {
                    "Annotator": name,
                    "Email": email,
                    "Language": selected_language,
                    "No.of Projects": project_count,
                    "Assigned": assigned_tasks,
                    "Annotated": annotated_tasks,
                    "Unlabeled": all_pending_tasks_in_project,
                    "Skipped": total_skipped_tasks,
                    "Draft": all_draft_tasks_in_project,
                    "Word Count": total_word_count,
                    "Total Audio Duration": total_duration,
                    "Average Annotation Time (In Seconds)": round(avg_lead_time, 2),
                }

            if project_type in get_audio_project_types():
                del result["Word Count"]
            elif (
                is_translation_project
                or project_type == "SemanticTextualSimilarity_Scale5"
            ):
                del result["Total Audio Duration"]
            else:
                del result["Word Count"]
                del result["Total Audio Duration"]

            final_result.append(result)
        return Response(final_result)


class WorkspaceusersViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="String containing emails separated by commas",
                )
            },
            required=["user_id"],
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "Users added Successfully",
            403: "Not authorized",
            400: "No valid user_ids found",
            404: "Workspace not found",
            500: "Server error occured",
        },
    )
    @permission_classes((IsAuthenticated,))
    @action(
        detail=True, methods=["POST"], url_path="addmembers", url_name="add_members"
    )
    @is_particular_workspace_manager
    def add_members(self, request, pk=None):
        user_id = request.data.get("user_id", "")
        try:
            workspace = Workspace.objects.get(pk=pk)

            if (
                (
                    (request.user.role) == (User.ORGANIZATION_OWNER)
                    and (request.user.organization) == (workspace.organization)
                )
                or (
                    (request.user.role == User.WORKSPACE_MANAGER)
                    and (request.user in workspace.managers.all())
                )
            ) == False:
                return Response(
                    {"message": "Not authorized!"}, status=status.HTTP_403_FORBIDDEN
                )
            user_ids = user_id.split(",")
            invalid_user_ids = []
            for user_id in user_ids:
                try:
                    user = User.objects.get(pk=user_id)
                    if (user.organization) == (workspace.organization):
                        workspace.members.add(user)
                    else:
                        invalid_user_ids.append(user_id)
                except User.DoesNotExist:
                    invalid_user_ids.append(user_id)
            workspace.save()
            if len(invalid_user_ids) == 0:
                return Response(
                    {"message": "users added successfully"}, status=status.HTTP_200_OK
                )
            elif len(invalid_user_ids) == len(user_ids):
                return Response(
                    {"message": "No valid user_ids found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {
                    "message": f"users added partially! Invalid user_ids: {','.join(invalid_user_ids)}"
                },
                status=status.HTTP_200_OK,
            )
        except Workspace.DoesNotExist:
            return Response(
                {"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {"message": "Server Error occured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, format="email")
            },
            required=["user_id"],
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "User removed Successfully",
            403: "Not authorized",
            404: "Workspace not found/User not in the workspace/User not found",
            500: "Server error occured",
        },
    )
    @permission_classes((IsAuthenticated,))
    @action(
        detail=True,
        methods=["POST"],
        url_path="removemembers",
        url_name="remove_members",
    )
    @is_particular_workspace_manager
    def remove_members(self, request, pk=None):
        user_id = request.data.get("user_id", "")
        try:
            workspace = Workspace.objects.get(pk=pk)

            if (
                (
                    (request.user.role) == (User.ORGANIZATION_OWNER)
                    and (request.user.organization) == (workspace.organization)
                )
                or (
                    (request.user.role == User.WORKSPACE_MANAGER)
                    and (request.user in workspace.managers.all())
                )
            ) == False:
                return Response(
                    {"message": "Not authorized!"}, status=status.HTTP_403_FORBIDDEN
                )
            try:
                user = User.objects.get(pk=user_id)
                if user in workspace.members.all():
                    workspace.members.remove(user)
                    return Response(
                        {"message": "User removed successfully"},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"message": "User not in workspace"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            except User.DoesNotExist:
                return Response(
                    {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )
        except Workspace.DoesNotExist:
            return Response(
                {"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {"message": "Server Error occured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the workspace"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: UserFetchSerializer(many=True),
            403: "Not authorized",
            404: "Workspace not found/User not in the workspace/User not found",
            500: "Server error occured",
        },
    )
    @action(
        detail=True, methods=["GET"], url_path="list-managers", url_name="list_managers"
    )
    def list_managers(self, request, pk):
        try:
            workspace = Workspace.objects.get(pk=pk)
            managers = workspace.managers.all()
            user_serializer = UserFetchSerializer(managers, many=True)
            return Response(user_serializer.data)
        except Workspace.DoesNotExist:
            return Response(
                {"message": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print("the exception was ", e)
            return Response(
                {"message": "Server Error occured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=["GET"],
        url_path="user-workspaces/loggedin-user-workspaces",
        url_name="loggedin_user_workspaces",
    )
    def loggedin_user_workspaces(self, request):
        if request.user.is_anonymous:
            return Response({"message": "Access Denied."})
        workspaces = Workspace.objects.filter(members__in=[request.user.pk])
        workspaces_serializer = WorkspaceNameSerializer(workspaces, many=True)
        return Response(workspaces_serializer.data)
