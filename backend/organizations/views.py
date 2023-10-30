from cProfile import label
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status
from tasks.models import (
    Task,
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
)
from datetime import datetime
from .models import Organization
from .serializers import OrganizationSerializer
from .decorators import is_organization_owner, is_particular_organization_owner
from users.serializers import UserFetchSerializer
from users.models import User
from projects.models import Project, ANNOTATION_STAGE, REVIEW_STAGE, SUPERCHECK_STAGE
from django.db.models import Avg, Count, F, FloatField, Q, Value, Subquery
from django.db.models.functions import Cast, Coalesce
from regex import R
from tasks.models import Annotation
from projects.utils import is_valid_date, no_of_words, ocr_word_count
from datetime import datetime, timezone, timedelta
import pandas as pd
from dateutil import relativedelta
import calendar
from workspaces.views import (
    get_review_reports,
    get_supercheck_reports,
)
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
import csv
from django.http import StreamingHttpResponse
from tasks.views import SentenceOperationViewSet
from users.utils import get_role_name
from projects.utils import (
    minor_major_accepted_task,
    convert_seconds_to_hours,
    get_audio_project_types,
    get_translation_dataset_project_types,
    convert_hours_to_seconds,
    get_audio_transcription_duration,
    get_audio_segments_count,
)
from .tasks import (
    get_counts,
    send_user_reports_mail_org,
    send_project_analytics_mail_org,
    send_user_analytics_mail_org,
)


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


def get_annotated_tasks(proj_ids, annotator, status_list, start_date, end_date):
    annotated_tasks_objs = get_task_count(
        proj_ids, status_list, annotator, return_count=False
    )

    annotated_task_ids = list(annotated_tasks_objs.values_list("id", flat=True))
    annotated_labeled_tasks = Annotation.objects.filter(
        task_id__in=annotated_task_ids,
        parent_annotation_id=None,
        updated_at__range=[start_date, end_date],
        completed_by=annotator,
    )

    return annotated_labeled_tasks


def get_reviewd_tasks(
    proj_ids, annotator, status_list, start_date, end_date, parent_annotation_bool
):
    annotated_tasks_objs = get_task_count(
        proj_ids, status_list, annotator, return_count=False
    )

    annotated_task_ids = list(annotated_tasks_objs.values_list("id", flat=True))
    annotated_labeled_tasks = Annotation.objects.filter(
        task_id__in=annotated_task_ids,
        parent_annotation_id__isnull=parent_annotation_bool,
        updated_at__range=[start_date, end_date],
    )

    return annotated_labeled_tasks


def get_translation_quality_reports(
    pk,
    annotator,
    project_type,
    start_date,
    end_date,
    is_translation_project,
    project_progress_stage=None,
    tgt_language=None,
):
    if not is_translation_project:
        return Response(
            {
                "message": "BLEU score and Normalized Character-level edit distance  is not available for Non Translation Projects"
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    sentence_operation = SentenceOperationViewSet()
    if tgt_language == None:
        projects_objs = Project.objects.filter(
            organization_id_id=pk,
            project_type=project_type,
            project_stage=project_progress_stage,
            annotators=annotator,
        )
    else:
        projects_objs = Project.objects.filter(
            organization_id_id=pk,
            project_type=project_type,
            project_stage=project_progress_stage,
            tgt_language=tgt_language,
            annotators=annotator,
        )

    proj_ids = [eachid["id"] for eachid in projects_objs.values("id")]

    all_reviewd_tasks = Annotation.objects.filter(
        annotation_status__in=[
            "accepted",
            "to_be_revised",
            "accepted_with_minor_changes",
            "accepted_with_major_changes",
        ],
        task__project_id__in=proj_ids,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    parent_anno_ids_of_reviewed = [
        ann.parent_annotation_id for ann in all_reviewd_tasks
    ]
    reviewed_annotations_of_user = Annotation.objects.filter(
        id__in=parent_anno_ids_of_reviewed,
        completed_by=annotator,
    )

    all_reviewd_tasks_count = reviewed_annotations_of_user.count()

    accepted_tasks = all_reviewd_tasks.all().exclude(
        annotation_status__in=[
            "to_be_revised",
            "accepted_with_minor_changes",
            "accepted_with_major_changes",
        ],
    )

    parent_anno_ids_of_accepted = [ann.parent_annotation_id for ann in accepted_tasks]
    accepted_annotations_of_user = Annotation.objects.filter(
        id__in=parent_anno_ids_of_accepted,
        completed_by=annotator,
    )

    accepted_count = accepted_annotations_of_user.count()

    if all_reviewd_tasks_count == 0:
        reviewed_except_accepted = 0
    else:
        reviewed_except_accepted = round(
            (accepted_count / all_reviewd_tasks_count) * 100, 2
        )

    accepted_with_minor_changes_tasks = all_reviewd_tasks.all().exclude(
        annotation_status__in=[
            "to_be_revised",
            "accepted",
            "accepted_with_major_changes",
        ],
    )

    parent_annotation_minor_changes = [
        ann.parent_annotation_id for ann in accepted_with_minor_changes_tasks
    ]
    minor_changes_annotations_of_user = Annotation.objects.filter(
        id__in=parent_annotation_minor_changes,
        completed_by=annotator,
    )
    minor_changes_count = minor_changes_annotations_of_user.count()

    accepted_with_major_changes_tasks = all_reviewd_tasks.all().exclude(
        annotation_status__in=[
            "to_be_revised",
            "accepted",
            "accepted_with_minor_changes",
        ],
    )

    parent_annotation_major_changes = [
        ann.parent_annotation_id for ann in accepted_with_major_changes_tasks
    ]
    major_changes_annotations_of_user = Annotation.objects.filter(
        id__in=parent_annotation_major_changes,
        completed_by=annotator,
    )
    major_changes_count = major_changes_annotations_of_user.count()

    accepted_with_changes_tasks = list(major_changes_annotations_of_user) + list(
        minor_changes_annotations_of_user
    )

    total_bleu_score = 0
    total_char_score = 0

    bleu_score_error_count = 0
    char_score_error_count = 0
    total_lead_time = []
    for annot in accepted_with_changes_tasks:
        annotator_obj = annot
        reviewer_obj = Annotation.objects.filter(parent_annotation_id=annot.id)

        str1 = annotator_obj.result[0]["value"]["text"]
        str2 = reviewer_obj[0].result[0]["value"]["text"]
        lead_time = reviewer_obj[0].lead_time
        total_lead_time.append(lead_time)

        data = {"sentence1": str1[0], "sentence2": str2[0]}
        try:
            bleu_score = sentence_operation.calculate_bleu_score(data)
            total_bleu_score += float(bleu_score.data["bleu_score"])
        except:
            bleu_score_error_count += 1
        try:
            char_level_distance = (
                sentence_operation.calculate_normalized_character_level_edit_distance(
                    data
                )
            )
            total_char_score += float(
                char_level_distance.data["normalized_character_level_edit_distance"]
            )
        except:
            char_score_error_count += 1

    if len(accepted_with_changes_tasks) + accepted_count > 0:
        accepted_with_change_minus_bleu_score_error = (
            len(accepted_with_changes_tasks) + accepted_count - bleu_score_error_count
        )
        accepted_with_change_minus_char_score_error = (
            len(accepted_with_changes_tasks) + accepted_count - char_score_error_count
        )

        if accepted_with_change_minus_bleu_score_error == 0:
            avg_bleu_score = "all tasks bleu scores given some error"
        else:
            avg_bleu_score = (
                total_bleu_score / accepted_with_change_minus_bleu_score_error
            )
            avg_bleu_score = round(avg_bleu_score, 3)

        if accepted_with_change_minus_char_score_error == 0:
            avg_char_score = "all tasks char scores given some error"

        else:
            avg_char_score = (
                total_char_score / accepted_with_change_minus_char_score_error
            )
            avg_char_score = round(avg_char_score, 3)

    else:
        avg_bleu_score = "no accepted with changes tasks"
        avg_char_score = "no accepted with changes tasks"

    avg_lead_time = 0
    if len(total_lead_time) > 0:
        avg_lead_time = sum(total_lead_time) / len(total_lead_time)
        avg_lead_time = round(avg_lead_time, 2)

    return (
        all_reviewd_tasks_count,
        accepted_count,
        reviewed_except_accepted,
        minor_changes_count,
        major_changes_count,
        avg_char_score,
        avg_bleu_score,
        avg_lead_time,
    )


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    A viewset for Organization CRUD, access limited only to organization Managers and Superuser.
    """

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = (IsAuthenticated,)

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

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "from_date": openapi.Schema(type=openapi.TYPE_STRING),
                "to_date": openapi.Schema(type=openapi.TYPE_STRING),
                "tgt_language": openapi.Schema(type=openapi.TYPE_STRING),
                "project_type": openapi.Schema(type=openapi.TYPE_STRING),
                "sort_by_column_name": openapi.Schema(type=openapi.TYPE_STRING),
                "descending_order": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "download_csv": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
            required=["from_date", "to_date", "project_type"],
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the Organization"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "Downloaded csv successfully or User analytics Json data successfully returned.",
            400: "Invalid request body parameters.",
            404: "Organization not found.",
        },
    )
    @is_organization_owner
    @action(
        detail=True,
        methods=["POST"],
        name="Testing Quality of Text Translation Annotated by each User",
        url_name="quality_reports",
    )
    def quality_reports(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )

        annotators = User.objects.filter(organization=organization).order_by("username")
        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")
        from_date = from_date + " 00:00"
        to_date = to_date + " 23:59"
        tgt_language = request.data.get("tgt_language")
        project_type = request.data.get("project_type")
        project_type_lower = project_type.lower()

        is_translation_project = True if "translation" in project_type_lower else False

        sort_by_column_name = request.data.get("sort_by_column_name")
        descending_order = request.data.get("descending_order")
        if sort_by_column_name == None:
            sort_by_column_name = "Translator"

        if descending_order == None:
            descending_order = False

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
        if tgt_language == None:
            annotators = User.objects.filter(organization=organization).order_by(
                "username"
            )
        else:
            proj_objects = Project.objects.filter(
                organization_id_id=pk,
                project_type=project_type,
                tgt_language=tgt_language,
            )

            proj_users_list = [
                list(pro_obj.annotators.all()) for pro_obj in proj_objects
            ]
            proj_users = sum(proj_users_list, [])
            annotators = list(set(proj_users))

        annotators = [
            ann_user
            for ann_user in annotators
            if (ann_user.participation_type in [1, 2, 4])
        ]

        result = []
        for annotator in annotators:
            participation_type = annotator.participation_type
            participation_type = (
                "Full Time"
                if participation_type == 1
                else "Part Time"
                if participation_type == 2
                else "Contract Basis"
                if participation_type == 4
                else "N/A"
            )
            role = get_role_name(annotator.role)
            user_id = annotator.id
            name = annotator.username
            email = annotator.get_username()
            user_lang_filter = User.objects.get(id=user_id)
            user_lang = user_lang_filter.languages
            if tgt_language == None:
                selected_language = user_lang
                if "English" in selected_language:
                    selected_language.remove("English")
            else:
                selected_language = tgt_language
            (
                all_reviewd_tasks_count,
                accepted_count,
                reviewed_except_accepted,
                accepted_wt_minor_changes,
                accepted_wt_major_changes,
                avg_char_score,
                avg_bleu_score,
                avg_lead_time,
            ) = get_translation_quality_reports(
                pk,
                annotator,
                project_type,
                start_date,
                end_date,
                is_translation_project,
                None if tgt_language == None else tgt_language,
            )

            result.append(
                {
                    "Translator": name,
                    "Email": email,
                    "Language": selected_language,
                    "Reviewed": all_reviewd_tasks_count,
                    "Accepted": accepted_count,
                    "(Accepted/Reviewed) Percentage": reviewed_except_accepted,
                    "Accepted With Minor Changes": accepted_wt_minor_changes,
                    "Accepted With Major Changes": accepted_wt_major_changes,
                    "Avg Character Edit Distance Score": avg_char_score,
                    "Average BLEU Score": avg_bleu_score,
                    "Avg Lead Time": avg_lead_time,
                    "Participation Type": participation_type,
                    "User Role": role,
                }
            )
        final_result = sorted(
            result, key=lambda x: x[sort_by_column_name], reverse=descending_order
        )
        return Response(final_result, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["POST"],
        name="Get Organization level  users analytics ",
        url_name="user_analytics",
    )
    def user_analytics(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        user_id = request.user.id
        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")
        from_date = from_date + " 00:00"
        to_date = to_date + " 23:59"
        project_progress_stage = request.data.get("project_progress_stage")
        tgt_language = request.data.get("tgt_language")
        project_type = request.data.get("project_type")
        reports_type = request.data.get("reports_type")
        project_type_lower = project_type.lower()
        is_translation_project = True if "translation" in project_type_lower else False
        sort_by_column_name = request.data.get("sort_by_column_name")
        descending_order = request.data.get("descending_order")
        send_mail = request.data.get("send_mail", False)
        if sort_by_column_name == None:
            sort_by_column_name = "Annotator"

        if descending_order == None:
            descending_order = False

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

        final_reports = []

        if reports_type == "review":
            proj_objs = Project.objects.filter(organization_id=pk)
            if project_type != None:
                proj_objs = proj_objs.filter(project_type=project_type)
            if project_progress_stage == None:
                review_projects = [
                    pro for pro in proj_objs if pro.project_stage > ANNOTATION_STAGE
                ]
            elif project_progress_stage in [REVIEW_STAGE, SUPERCHECK_STAGE]:
                review_projects = [
                    pro
                    for pro in proj_objs
                    if pro.project_stage == project_progress_stage
                ]
            else:
                final_response = {
                    "message": "Annotation stage projects don't have review reports."
                }
                return Response(final_response, status=status.HTTP_400_BAD_REQUEST)

            org_reviewer_list = []
            review_projects_ids = []
            for review_project in review_projects:
                reviewer_names_list = review_project.annotation_reviewers.all()
                reviewer_ids = [
                    name.id
                    for name in reviewer_names_list
                    if (name.participation_type in [1, 2, 4])
                ]
                org_reviewer_list.extend(reviewer_ids)
                review_projects_ids.append(review_project.id)

            org_reviewer_list = list(set(org_reviewer_list))

            if (
                request.user.role == User.ORGANIZATION_OWNER
                or request.user.role == User.WORKSPACE_MANAGER
                or request.user.is_superuser
            ):
                for id in org_reviewer_list:
                    reviewer_projs = Project.objects.filter(
                        organization_id=pk,
                        annotation_reviewers=id,
                        id__in=review_projects_ids,
                    )
                    reviewer_projs_ids = [
                        review_proj.id for review_proj in reviewer_projs
                    ]

                    result = get_review_reports(
                        reviewer_projs_ids,
                        id,
                        start_date,
                        end_date,
                        project_progress_stage,
                        project_type,
                    )
                    final_reports.append(result)
            elif user_id in org_reviewer_list:
                reviewer_projs = Project.objects.filter(
                    organization_id=pk,
                    annotation_reviewers=user_id,
                    id__in=review_projects_ids,
                )
                reviewer_projs_ids = [review_proj.id for review_proj in reviewer_projs]

                result = get_review_reports(
                    reviewer_projs_ids,
                    user_id,
                    start_date,
                    end_date,
                    project_progress_stage,
                    project_type,
                )
                final_reports.append(result)
            else:
                return Response(
                    {
                        "message": "You do not have enough permissions to access this view!"
                    }
                )

        elif reports_type == "supercheck":
            proj_objs = Project.objects.filter(organization_id=pk)
            if project_type != None:
                proj_objs = proj_objs.filter(project_type=project_type)
            supercheck_projects = [
                pro for pro in proj_objs if pro.project_stage > REVIEW_STAGE
            ]

            workspace_superchecker_list = []
            supercheck_projects_ids = []
            for supercheck_project in supercheck_projects:
                superchecker_names_list = supercheck_project.review_supercheckers.all()
                superchecker_ids = [name.id for name in superchecker_names_list]
                workspace_superchecker_list.extend(superchecker_ids)
                supercheck_projects_ids.append(supercheck_project.id)

            workspace_superchecker_list = list(set(workspace_superchecker_list))

            if (
                request.user.role == User.ORGANIZATION_OWNER
                or request.user.role == User.WORKSPACE_MANAGER
                or request.user.is_superuser
            ):
                for id in workspace_superchecker_list:
                    superchecker_projs = Project.objects.filter(
                        organization_id=pk,
                        review_supercheckers=id,
                        id__in=supercheck_projects_ids,
                    )
                    superchecker_projs_ids = [
                        supercheck_proj.id for supercheck_proj in superchecker_projs
                    ]

                    result = get_supercheck_reports(
                        superchecker_projs_ids, id, start_date, end_date, project_type
                    )
                    final_reports.append(result)
            elif user_id in workspace_superchecker_list:
                superchecker_projs = Project.objects.filter(
                    organization_id=pk,
                    review_supercheckers=id,
                    id__in=supercheck_projects_ids,
                )
                superchecker_projs_ids = [
                    supercheck_proj.id for supercheck_proj in superchecker_projs
                ]

                result = get_supercheck_reports(
                    superchecker_projs_ids, user_id, start_date, end_date, project_type
                )
                final_reports.append(result)

            else:
                return Response(
                    {
                        "message": "You do not have enough permissions to access this view!"
                    }
                )

        if not (
            request.user.is_authenticated
            and (
                request.user.role == User.ORGANIZATION_OWNER
                or request.user.is_superuser
            )
        ):
            final_response = {
                "message": "You do not have enough permissions to access this view!"
            }
            return Response(final_response, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(id=user_id)

        if send_mail == True:
            send_user_analytics_mail_org.delay(
                org_id=organization.id,
                tgt_language=tgt_language,
                project_type=project_type,
                user_id=user_id,
                sort_by_column_name=sort_by_column_name,
                descending_order=descending_order,
                pk=pk,
                start_date=start_date,
                end_date=end_date,
                is_translation_project=is_translation_project,
                project_progress_stage=project_progress_stage,
                final_reports=final_reports,
            )
            return Response(
                {"message": "Email scheduled successfully"}, status=status.HTTP_200_OK
            )
        else:
            if tgt_language == None:
                annotators = User.objects.filter(organization=organization).order_by(
                    "username"
                )
            else:
                proj_objects = Project.objects.filter(
                    organization_id_id=pk,
                    project_type=project_type,
                    tgt_language=tgt_language,
                )

                proj_users_list = [
                    list(pro_obj.annotators.all()) for pro_obj in proj_objects
                ]
                proj_users = sum(proj_users_list, [])
                annotators = list(set(proj_users))

            annotators = [
                ann_user
                for ann_user in annotators
                if (ann_user.participation_type in [1, 2, 4])
            ]

            result = []
            for annotator in annotators:
                participation_type = annotator.participation_type
                participation_type = (
                    "Full Time"
                    if participation_type == 1
                    else "Part Time"
                    if participation_type == 2
                    else "Contract Basis"
                    if participation_type == 4
                    else "N/A"
                )
                role = get_role_name(annotator.role)
                user_id = annotator.id
                name = annotator.username
                email = annotator.get_username()
                user_lang = user.languages
                if tgt_language == None:
                    selected_language = user_lang
                    if "English" in selected_language:
                        selected_language.remove("English")
                else:
                    selected_language = tgt_language
                (
                    total_no_of_tasks_count,
                    annotated_tasks_count,
                    accepted,
                    to_be_revised,
                    accepted_wt_minor_changes,
                    accepted_wt_major_changes,
                    labeled,
                    avg_lead_time,
                    total_skipped_tasks_count,
                    total_unlabeled_tasks_count,
                    total_draft_tasks_count,
                    no_of_projects,
                    no_of_workspaces_objs,
                    total_word_count,
                    total_duration,
                    total_raw_duration,
                    avg_segment_duration,
                    avg_segments_per_task,
                ) = get_counts(
                    pk,
                    annotator,
                    project_type,
                    start_date,
                    end_date,
                    is_translation_project,
                    project_progress_stage,
                    None if tgt_language == None else tgt_language,
                )

                if (
                    project_progress_stage != None
                    and project_progress_stage > ANNOTATION_STAGE
                ):
                    temp_result = {
                        "Annotator": name,
                        "Email": email,
                        "Language": selected_language,
                        "No. of Workspaces": no_of_workspaces_objs,
                        "No. of Projects": no_of_projects,
                        "Assigned": total_no_of_tasks_count,
                        "Labeled": labeled,
                        "Accepted": accepted,
                        "Accepted With Minor Changes": accepted_wt_minor_changes,
                        "Accepted With Major Changes": accepted_wt_major_changes,
                        "To Be Revised": to_be_revised,
                        "Unlabeled": total_unlabeled_tasks_count,
                        "Skipped": total_skipped_tasks_count,
                        "Draft": total_draft_tasks_count,
                        "Word Count": total_word_count,
                        "Total Segments Duration": total_duration,
                        "Total Raw Audio Duration": total_raw_duration,
                        "Average Annotation Time (In Seconds)": round(avg_lead_time, 2),
                        "Participation Type": participation_type,
                        "User Role": role,
                        "Avg Segment Duration": round(avg_segment_duration, 2),
                        "Average Segments Per Task": round(avg_segments_per_task, 2),
                    }
                    if project_type != None and is_translation_project:
                        (
                            avg_char_score,
                            avg_bleu_score,
                        ) = get_translation_quality_reports(
                            pk,
                            annotator,
                            project_type,
                            start_date,
                            end_date,
                            project_progress_stage,
                            tgt_language,
                        )
                        temp_result["Average Bleu Score"] = avg_bleu_score
                        temp_result["Avergae Char Score"] = avg_char_score
                else:
                    temp_result = {
                        "Annotator": name,
                        "Email": email,
                        "Language": selected_language,
                        "No. of Workspaces": no_of_workspaces_objs,
                        "No. of Projects": no_of_projects,
                        "Assigned": total_no_of_tasks_count,
                        "Annotated": annotated_tasks_count,
                        "Unlabeled": total_unlabeled_tasks_count,
                        "Skipped": total_skipped_tasks_count,
                        "Draft": total_draft_tasks_count,
                        "Word Count": total_word_count,
                        "Total Segments Duration": total_duration,
                        "Average Annotation Time (In Seconds)": round(avg_lead_time, 2),
                        "Participation Type": participation_type,
                        "User Role": role,
                        "Avg Segment Duration": round(avg_segment_duration, 2),
                        "Average Segments Per Task": round(avg_segments_per_task, 2),
                    }

                if project_type in get_audio_project_types():
                    del temp_result["Word Count"]
                elif is_translation_project or project_type in [
                    "SemanticTextualSimilarity_Scale5",
                    "OCRTranscriptionEditing",
                    "OCRTranscription",
                ]:
                    del temp_result["Total Segments Duration"]
                    del temp_result["Avg Segment Duration"]
                    del temp_result["Average Segments Per Task"]
                else:
                    del temp_result["Word Count"]
                    del temp_result["Total Segments Duration"]
                    del temp_result["Avg Segment Duration"]
                    del temp_result["Average Segments Per Task"]
                result.append(temp_result)
            final_result = sorted(
                result, key=lambda x: x[sort_by_column_name], reverse=descending_order
            )

            download_csv = request.data.get("download_csv", False)

            if download_csv:

                class Echo(object):
                    def write(self, value):
                        return value

                def iter_items(items, pseudo_buffer):
                    writer = csv.DictWriter(
                        pseudo_buffer, fieldnames=list(items[0].keys())
                    )
                    headers = {}
                    for key in list(items[0].keys()):
                        headers[key] = key
                    yield writer.writerow(headers)
                    print(list(items[0].keys()))
                    for item in items:
                        yield writer.writerow(item)

                response = StreamingHttpResponse(
                    iter_items(final_result, Echo()),
                    status=status.HTTP_200_OK,
                    content_type="text/csv",
                )
                response[
                    "Content-Disposition"
                ] = f'attachment; filename="{organization.title}_user_analytics.csv"'
                return response

            return Response(data=final_result, status=status.HTTP_200_OK)

    @is_organization_owner
    @action(
        detail=True,
        methods=["POST"],
        name="Get Organization level  Project analytics ",
        url_name="project_analytics",
    )
    def project_analytics(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )

        tgt_language = request.data.get("tgt_language")
        project_type = request.data.get("project_type")

        sort_by_column_name = request.data.get("sort_by_column_name")
        descending_order = request.data.get("descending_order")
        user_id = request.data.get("user_id")
        send_mail = request.data.get("send_mail", False)

        if send_mail == True:
            send_project_analytics_mail_org.delay(
                org_id=organization.id,
                tgt_language=tgt_language,
                project_type=project_type,
                user_id=user_id,
                sort_by_column_name=sort_by_column_name,
                descending_order=descending_order,
            )

            return Response(
                {"message": "Email scheduled successfully"}, status=status.HTTP_200_OK
            )
        else:
            if sort_by_column_name == None:
                sort_by_column_name = "User Name"

            if descending_order == None:
                descending_order = False

            if tgt_language == None:
                selected_language = "-"
                projects_obj = Project.objects.filter(
                    organization_id=organization.id, project_type=project_type
                )
            else:
                selected_language = tgt_language
                projects_obj = Project.objects.filter(
                    organization_id=organization.id,
                    tgt_language=tgt_language,
                    project_type=project_type,
                )
            final_result = []
            if projects_obj.count() != 0:
                for proj in projects_obj:
                    proj_manager = [
                        manager.get_username()
                        for manager in proj.workspace_id.managers.all()
                    ]
                    try:
                        org_owner = proj.organization_id.created_by.get_username()
                        proj_manager.append(org_owner)
                    except:
                        pass
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
                        user_.get_username() for user_ in proj.annotators.all()
                    ]
                    no_of_annotators_assigned = len(
                        [
                            annotator
                            for annotator in annotators_list
                            if annotator not in proj_manager
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

                    superchecked_tasks = Task.objects.filter(
                        project_id=proj.id, task_status="super_checked"
                    )
                    superchecked_count = superchecked_tasks.count()

                    total_word_annotated_count_list = []
                    total_word_reviewed_count_list = []
                    total_word_exported_count_list = []
                    total_word_superchecked_count_list = []
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
                        for each_task in superchecked_tasks:
                            try:
                                total_word_superchecked_count_list.append(
                                    each_task.data["word_count"]
                                )
                            except:
                                pass
                    elif "OCRTranscription" in project_type:
                        for each_task in labeled_tasks:
                            try:
                                annotate_annotation = Annotation.objects.filter(
                                    task=each_task, annotation_type=ANNOTATOR_ANNOTATION
                                )[0]
                                total_word_annotated_count_list.append(
                                    ocr_word_count(annotate_annotation.result)
                                )
                            except:
                                pass

                        for each_task in reviewed_tasks:
                            try:
                                review_annotation = Annotation.objects.filter(
                                    task=each_task, annotation_type=REVIEWER_ANNOTATION
                                )[0]
                                total_word_reviewed_count_list.append(
                                    ocr_word_count(review_annotation.result)
                                )
                            except:
                                pass

                        for each_task in exported_tasks:
                            try:
                                total_word_exported_count_list.append(
                                    ocr_word_count(each_task.correct_annotation.result)
                                )
                            except:
                                pass

                        for each_task in superchecked_tasks:
                            try:
                                supercheck_annotation = Annotation.objects.filter(
                                    task=each_task,
                                    annotation_type=SUPER_CHECKER_ANNOTATION,
                                )[0]
                                total_word_superchecked_count_list.append(
                                    ocr_word_count(supercheck_annotation.result)
                                )
                            except:
                                pass

                    total_word_annotated_count = sum(total_word_annotated_count_list)
                    total_word_reviewed_count = sum(total_word_reviewed_count_list)
                    total_word_exported_count = sum(total_word_exported_count_list)
                    total_word_superchecked_count = sum(
                        total_word_superchecked_count_list
                    )

                    total_duration_annotated_count_list = []
                    total_duration_reviewed_count_list = []
                    total_duration_exported_count_list = []
                    total_duration_superchecked_count_list = []
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
                        for each_task in superchecked_tasks:
                            try:
                                supercheck_annotation = Annotation.objects.filter(
                                    task=each_task,
                                    annotation_type=SUPER_CHECKER_ANNOTATION,
                                )[0]
                                total_duration_superchecked_count_list.append(
                                    get_audio_transcription_duration(
                                        supercheck_annotation.result
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
                    total_duration_superchecked_count = convert_seconds_to_hours(
                        sum(total_duration_superchecked_count_list)
                    )

                    if total_tasks == 0:
                        project_progress = 0.0
                    else:
                        if proj.project_stage == ANNOTATION_STAGE:
                            project_progress = (
                                (labeled_count + exported_count) / total_tasks
                            ) * 100
                        elif proj.project_stage == REVIEW_STAGE:
                            project_progress = (
                                (reviewed_count + exported_count) / total_tasks
                            ) * 100
                        else:
                            project_progress = (
                                (superchecked_count + exported_count) / total_tasks
                            ) * 100

                    result = {
                        "Project Id": project_id,
                        "Project Name": project_name,
                        "Language": selected_language,
                        "No. of Annotators Assigned": no_of_annotators_assigned,
                        "Total": total_tasks,
                        "Annotated": labeled_count,
                        "Incomplete": incomplete_count,
                        "Reviewed": reviewed_count,
                        "Exported": exported_count,
                        "SuperChecked": superchecked_count,
                        "Annotated Tasks Audio Duration": total_duration_annotated_count,
                        "Reviewed Tasks Audio Duration": total_duration_reviewed_count,
                        "Exported Tasks Audio Duration": total_duration_exported_count,
                        "SuperChecked Tasks Audio Duration": total_duration_superchecked_count,
                        "Annotated Tasks Word Count": total_word_annotated_count,
                        "Reviewed Tasks Word Count": total_word_reviewed_count,
                        "Exported Tasks Word Count": total_word_exported_count,
                        "SuperChecked Tasks Word Count": total_word_superchecked_count,
                        "Project Progress": round(project_progress, 3),
                    }

                    if project_type in get_audio_project_types():
                        del result["Annotated Tasks Word Count"]
                        del result["Reviewed Tasks Word Count"]
                        del result["Exported Tasks Word Count"]
                        del result["SuperChecked Tasks Word Count"]

                    elif is_translation_project or project_type in [
                        "SemanticTextualSimilarity_Scale5",
                        "OCRTranscriptionEditing",
                        "OCRTranscription",
                    ]:
                        del result["Annotated Tasks Audio Duration"]
                        del result["Reviewed Tasks Audio Duration"]
                        del result["Exported Tasks Audio Duration"]
                        del result["SuperChecked Tasks Audio Duration"]
                    else:
                        del result["Annotated Tasks Word Count"]
                        del result["Reviewed Tasks Word Count"]
                        del result["Exported Tasks Word Count"]
                        del result["SuperChecked Tasks Word Count"]
                        del result["Annotated Tasks Audio Duration"]
                        del result["Reviewed Tasks Audio Duration"]
                        del result["Exported Tasks Audio Duration"]
                        del result["SuperChecked Tasks Audio Duration"]

                    final_result.append(result)
            return Response(final_result)

    @action(
        detail=True,
        methods=["POST"],
        name="Get Cumulative tasks completed ",
        url_name="cumulative_tasks_count",
    )
    def cumulative_tasks_count(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        metainfo = False
        if "metainfo" in dict(request.query_params):
            metainfo = request.query_params["metainfo"]
            if metainfo == "true" or metainfo == "True":
                metainfo = True
        project_type = request.data.get("project_type")
        reviewer_reports = request.data.get("reviewer_reports")
        supercheck_reports = request.data.get("supercheck_reports")
        proj_objs = []
        if reviewer_reports == True:
            proj_objs = Project.objects.filter(
                organization_id=pk,
                project_type=project_type,
                project_stage__in=[REVIEW_STAGE, SUPERCHECK_STAGE],
            )
        elif supercheck_reports == True:
            proj_objs = Project.objects.filter(
                organization_id=pk,
                project_type=project_type,
                project_stage__in=[SUPERCHECK_STAGE],
            )
        else:
            proj_objs = Project.objects.filter(
                organization_id=pk, project_type=project_type
            )

        proj_objs_languages = Project.objects.filter(
            organization_id=pk, project_type=project_type
        )

        languages = list(set([proj.tgt_language for proj in proj_objs_languages]))
        general_lang = []
        other_lang = []
        for lang in languages:
            proj_lang_filter = proj_objs.filter(tgt_language=lang)
            tasks_count = 0
            if reviewer_reports == True:
                tasks = Task.objects.filter(
                    project_id__in=proj_lang_filter,
                    project_id__tgt_language=lang,
                    task_status__in=[
                        "reviewed",
                        "exported",
                        "super_checked",
                    ],
                )
                tasks_count = tasks.count()

                # Annotation.objects.filter(
                #     task__project_id__in=proj_lang_filter,
                #     task__project_id__tgt_language=lang,
                #     annotation_status__in=[
                #         "accepted",
                #         "accepted_with_minor_changes",
                #         "accepted_with_major_changes",
                #     ],
                #     parent_annotation_id__isnull=False,
                # ).count()

            elif supercheck_reports == True:
                tasks = Task.objects.filter(
                    project_id__in=proj_lang_filter,
                    project_id__tgt_language=lang,
                    task_status__in=[
                        "super_checked",
                    ],
                )
                tasks_count = tasks.count()

            else:
                tasks = Task.objects.filter(
                    project_id__in=proj_lang_filter,
                    project_id__tgt_language=lang,
                    task_status__in=[
                        "annotated",
                        "reviewed",
                        "exported",
                        "super_checked",
                    ],
                )
                tasks_count = tasks.count()

            if metainfo == True:
                result = {}

                if project_type in get_audio_project_types():
                    total_rev_duration_list = []
                    total_ann_duration_list = []
                    total_sup_duration_list = []

                    for each_task in tasks:
                        if reviewer_reports == True:
                            try:
                                if each_task.task_status == "reviewed":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=REVIEWER_ANNOTATION,
                                    )[0]
                                elif each_task.task_status == "super_checked":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=SUPER_CHECKER_ANNOTATION,
                                    )[0]
                                else:
                                    anno = each_task.correct_annotation
                                total_rev_duration_list.append(
                                    get_audio_transcription_duration(anno.result)
                                )
                            except:
                                pass
                        elif supercheck_reports == True:
                            try:
                                if each_task.task_status == "super_checked":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=SUPER_CHECKER_ANNOTATION,
                                    )[0]
                                else:
                                    anno = each_task.correct_annotation
                                total_sup_duration_list.append(
                                    get_audio_transcription_duration(anno.result)
                                )
                            except:
                                pass
                        else:
                            try:
                                if each_task.task_status == "reviewed":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=REVIEWER_ANNOTATION,
                                    )[0]
                                elif each_task.task_status == "exported":
                                    anno = each_task.correct_annotation
                                elif each_task.task_status == "super_checked":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=SUPER_CHECKER_ANNOTATION,
                                    )[0]
                                else:
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=ANNOTATOR_ANNOTATION,
                                    )[0]
                                total_ann_duration_list.append(
                                    get_audio_transcription_duration(anno.result)
                                )
                            except:
                                pass
                    if reviewer_reports == True:
                        rev_total_duration = sum(total_rev_duration_list)
                        rev_total_time = convert_seconds_to_hours(rev_total_duration)
                        result = {
                            "language": lang,
                            "cumulative_aud_duration": rev_total_time,
                        }
                    elif supercheck_reports == True:
                        sup_total_duration = sum(total_sup_duration_list)
                        sup_total_time = convert_seconds_to_hours(sup_total_duration)
                        result = {
                            "language": lang,
                            "cumulative_aud_duration": sup_total_time,
                        }
                    else:
                        ann_total_duration = sum(total_ann_duration_list)
                        ann_total_time = convert_seconds_to_hours(ann_total_duration)
                        result = {
                            "language": lang,
                            "cumulative_aud_duration": ann_total_time,
                        }
                elif "OCRTranscription" in project_type:
                    total_word_count = 0

                    for each_task in tasks:
                        if reviewer_reports == True:
                            try:
                                if each_task.task_status == "reviewed":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=REVIEWER_ANNOTATION,
                                    )[0]
                                elif each_task.task_status == "super_checked":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=SUPER_CHECKER_ANNOTATION,
                                    )[0]
                                else:
                                    anno = each_task.correct_annotation
                                total_word_count += ocr_word_count(anno.result)
                            except:
                                pass
                        elif supercheck_reports == True:
                            try:
                                if each_task.task_status == "super_checked":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=SUPER_CHECKER_ANNOTATION,
                                    )[0]
                                else:
                                    anno = each_task.correct_annotation
                                total_word_count += ocr_word_count(anno.result)
                            except:
                                pass
                        else:
                            try:
                                if each_task.task_status == "reviewed":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=REVIEWER_ANNOTATION,
                                    )[0]
                                elif each_task.task_status == "exported":
                                    anno = each_task.correct_annotation
                                elif each_task.task_status == "super_checked":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=SUPER_CHECKER_ANNOTATION,
                                    )[0]
                                else:
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=ANNOTATOR_ANNOTATION,
                                    )[0]
                                total_word_count += ocr_word_count(anno.result)
                            except:
                                pass
                    result = {
                        "language": lang,
                        "cumulative_word_count": total_word_count,
                    }
                elif (
                    project_type in get_translation_dataset_project_types()
                    or "ConversationTranslation" in project_type
                ):
                    total_word_count_list = []

                    for each_task in tasks:
                        try:
                            total_word_count_list.append(each_task.data["word_count"])
                        except:
                            pass

                    result = {
                        "language": lang,
                        "cumulative_word_count": sum(total_word_count_list),
                    }
            else:
                result = {"language": lang, "cumulative_tasks_count": tasks_count}

            if lang == None or lang == "":
                other_lang.append(result)
            else:
                general_lang.append(result)

        other_count = 0
        other_word_count = 0
        other_aud_dur = 0
        for dat in other_lang:
            if metainfo != True:
                other_count += dat["cumulative_tasks_count"]
            else:
                if project_type in get_audio_project_types():
                    other_aud_dur += convert_hours_to_seconds(
                        dat["cumulative_aud_duration"]
                    )
                elif (
                    project_type in get_translation_dataset_project_types()
                    or "ConversationTranslation" in project_type
                ):
                    other_word_count += dat["cumulative_word_count"]
        if len(other_lang) > 0:
            if metainfo != True:
                other_language = {
                    "language": "Others",
                    "cumulative_tasks_count": other_count,
                }
            else:
                if project_type in get_audio_project_types():
                    other_language = {
                        "language": "Others",
                        "cumulative_aud_duration": convert_seconds_to_hours(
                            other_aud_dur
                        ),
                    }
                elif (
                    project_type in get_translation_dataset_project_types()
                    or "ConversationTranslation" in project_type
                ):
                    other_language = {
                        "language": "Others",
                        "cumulative_word_count": other_word_count,
                    }

            general_lang.append(other_language)

        try:
            final_result = sorted(
                general_lang, key=lambda x: x["language"], reverse=False
            )
        except:
            final_result = []
        if metainfo == True and not (
            (project_type in get_audio_project_types())
            or (
                project_type in get_translation_dataset_project_types()
                or "ConversationTranslation" in project_type
            )
        ):
            final_result = []
        return Response(final_result)

    @action(
        detail=True,
        methods=["POST"],
        name="Get  tasks completed based on Periodically ",
        url_name="periodical_tasks_count",
    )
    def periodical_tasks_count(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        metainfo = False
        if "metainfo" in dict(request.query_params):
            metainfo = request.query_params["metainfo"]
            if metainfo == "true" or metainfo == "True":
                metainfo = True
        project_type = request.data.get("project_type")
        periodical_type = request.data.get("periodical_type")

        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        reviewer_reports = request.data.get("reviewer_reports")
        supercheck_reports = request.data.get("supercheck_reports")

        org_created_date = organization.created_at
        present_date = datetime.now(timezone.utc)

        if start_date != None:
            date1 = start_date
            org_created_date = datetime(
                int(date1.split("-")[0]),
                int(date1.split("-")[1]),
                int(date1.split("-")[2]),
                tzinfo=timezone(offset=timedelta()),
            )
        if end_date != None:
            date2 = end_date
            present_date = datetime(
                int(date2.split("-")[0]),
                int(date2.split("-")[1]),
                int(date2.split("-")[2]),
                tzinfo=timezone(offset=timedelta()),
            )

        periodical_list = []
        if periodical_type == "weekly":
            periodical_list.append(org_created_date)
            while org_created_date <= present_date:
                org_created_date = org_created_date + timedelta(days=7)
                if org_created_date <= present_date:
                    periodical_list.append(org_created_date)
                else:
                    periodical_list.append(present_date + timedelta(days=1))

        elif periodical_type == "monthly":
            start_date = org_created_date
            end_date = present_date

            periodical_list.append(start_date)
            count = 1
            start = start_date
            while start <= end_date:
                start = start_date + relativedelta.relativedelta(months=count)
                if (
                    start_date.day == 29
                    and start.month == 2
                    and (not calendar.isleap(start.year))
                ):
                    start = start + timedelta(days=1)
                if start_date.day == 30 and start.month == 2:
                    start = start + timedelta(days=1)
                if start_date.day == 31 and start.month in [2, 4, 6, 9, 11]:
                    start = start + timedelta(days=1)
                count += 1
                if start <= end_date:
                    periodical_list.append(start)
                else:
                    periodical_list.append(end_date + timedelta(days=1))

        elif periodical_type == "yearly":
            start_date = org_created_date
            end_date = present_date

            periodical_list.append(start_date)
            count = 1
            start = start_date
            while start <= end_date:
                start = start_date + relativedelta.relativedelta(years=count)
                if (
                    start_date.day == 29
                    and start.month == 2
                    and (not calendar.isleap(start.year))
                ):
                    start = start + timedelta(days=1)

                count += 1
                if start <= end_date:
                    periodical_list.append(start)
                else:
                    periodical_list.append(end_date + timedelta(days=1))
        proj_objs = []
        if reviewer_reports == True:
            proj_objs = Project.objects.filter(
                organization_id=pk,
                project_type=project_type,
                project_stage__in=[REVIEW_STAGE, SUPERCHECK_STAGE],
            )
        elif supercheck_reports == True:
            proj_objs = Project.objects.filter(
                organization_id=pk,
                project_type=project_type,
                project_stage__in=[SUPERCHECK_STAGE],
            )
        else:
            proj_objs = Project.objects.filter(
                organization_id=pk, project_type=project_type
            )
        proj_objs_languages = Project.objects.filter(
            organization_id=pk, project_type=project_type
        )

        languages = list(set([proj.tgt_language for proj in proj_objs_languages]))

        final_result = []

        for period in range(len(periodical_list) - 1):
            start_end_date = (
                str(periodical_list[period].date())
                + "  To "
                + str(
                    (periodical_list[period + 1].date() - pd.DateOffset(hours=1)).date()
                )
            )
            period_name = ""
            if periodical_type == "weekly":
                period_name = "week_number"
            elif periodical_type == "monthly":
                period_name = "month_number"
            elif periodical_type == "yearly":
                period_name = "year_number"

            data = []
            other_lang = []
            for lang in languages:
                proj_lang_filter = proj_objs.filter(tgt_language=lang)
                annotated_labeled_tasks_count = 0
                if reviewer_reports == True:
                    tasks = Task.objects.filter(
                        project_id__in=proj_lang_filter,
                        task_status__in=[
                            "reviewed",
                            "exported",
                            "super_checked",
                        ],
                    )
                    labeled_count_tasks_ids = list(tasks.values_list("id", flat=True))
                    annotated_labeled_tasks_count = (
                        Annotation.objects.filter(
                            task_id__in=labeled_count_tasks_ids,
                            annotation_type=REVIEWER_ANNOTATION,
                            updated_at__gte=periodical_list[period],
                            updated_at__lt=periodical_list[period + 1],
                        )
                        .exclude(annotation_status="to_be_revised")
                        .count()
                    )
                elif supercheck_reports == True:
                    tasks = Task.objects.filter(
                        project_id__in=proj_lang_filter,
                        task_status__in=[
                            "super_checked",
                        ],
                    )
                    labeled_count_tasks_ids = list(tasks.values_list("id", flat=True))
                    annotated_labeled_tasks_count = Annotation.objects.filter(
                        task_id__in=labeled_count_tasks_ids,
                        annotation_type=SUPER_CHECKER_ANNOTATION,
                        updated_at__gte=periodical_list[period],
                        updated_at__lt=periodical_list[period + 1],
                    ).count()
                else:
                    tasks = Task.objects.filter(
                        project_id__in=proj_lang_filter,
                        task_status__in=[
                            "annotated",
                            "reviewed",
                            "exported",
                            "super_checked",
                        ],
                    )

                    labeled_count_tasks_ids = list(tasks.values_list("id", flat=True))
                    annotated_labeled_tasks_count = Annotation.objects.filter(
                        task_id__in=labeled_count_tasks_ids,
                        annotation_type=ANNOTATOR_ANNOTATION,
                        updated_at__gte=periodical_list[period],
                        updated_at__lt=periodical_list[period + 1],
                    ).count()

                if metainfo == True:
                    result = {}

                    if project_type in get_audio_project_types():
                        total_rev_duration_list = []
                        total_ann_duration_list = []
                        total_sup_duration_list = []

                        for each_task in tasks:
                            if reviewer_reports == True:
                                try:
                                    if each_task.task_status == "reviewed":
                                        anno = Annotation.objects.filter(
                                            task=each_task,
                                            annotation_type=REVIEWER_ANNOTATION,
                                            updated_at__gte=periodical_list[period],
                                            updated_at__lt=periodical_list[period + 1],
                                        )[0]
                                    elif each_task.task_status == "super_checked":
                                        anno = Annotation.objects.filter(
                                            task=each_task,
                                            annotation_type=SUPER_CHECKER_ANNOTATION,
                                            updated_at__gte=periodical_list[period],
                                            updated_at__lt=periodical_list[period + 1],
                                        )[0]
                                    else:
                                        anno = Annotation.objects.filter(
                                            id=each_task.correct_annotation.id,
                                            updated_at__gte=periodical_list[period],
                                            updated_at__lt=periodical_list[period + 1],
                                        )[0]
                                    total_rev_duration_list.append(
                                        get_audio_transcription_duration(anno.result)
                                    )
                                except:
                                    pass
                            elif supercheck_reports == True:
                                try:
                                    if each_task.task_status == "super_checked":
                                        anno = Annotation.objects.filter(
                                            task=each_task,
                                            annotation_type=SUPER_CHECKER_ANNOTATION,
                                            updated_at__gte=periodical_list[period],
                                            updated_at__lt=periodical_list[period + 1],
                                        )[0]
                                    else:
                                        anno = Annotation.objects.filter(
                                            id=each_task.correct_annotation.id,
                                            updated_at__gte=periodical_list[period],
                                            updated_at__lt=periodical_list[period + 1],
                                        )[0]
                                    total_sup_duration_list.append(
                                        get_audio_transcription_duration(anno.result)
                                    )
                                except:
                                    pass
                            else:
                                try:
                                    if each_task.task_status == "reviewed":
                                        anno = Annotation.objects.filter(
                                            task=each_task,
                                            annotation_type=REVIEWER_ANNOTATION,
                                            updated_at__gte=periodical_list[period],
                                            updated_at__lt=periodical_list[period + 1],
                                        )[0]
                                    elif each_task.task_status == "exported":
                                        anno = Annotation.objects.filter(
                                            id=each_task.correct_annotation.id,
                                            updated_at__gte=periodical_list[period],
                                            updated_at__lt=periodical_list[period + 1],
                                        )[0]
                                    elif each_task.task_status == "super_checked":
                                        anno = Annotation.objects.filter(
                                            task=each_task,
                                            annotation_type=SUPER_CHECKER_ANNOTATION,
                                            updated_at__gte=periodical_list[period],
                                            updated_at__lt=periodical_list[period + 1],
                                        )[0]
                                    else:
                                        anno = Annotation.objects.filter(
                                            task=each_task,
                                            annotation_type=ANNOTATOR_ANNOTATION,
                                            updated_at__gte=periodical_list[period],
                                            updated_at__lt=periodical_list[period + 1],
                                        )[0]
                                    total_ann_duration_list.append(
                                        get_audio_transcription_duration(anno.result)
                                    )
                                except:
                                    pass
                        if reviewer_reports == True:
                            rev_total_duration = sum(total_rev_duration_list)
                            rev_total_time = convert_seconds_to_hours(
                                rev_total_duration
                            )
                            result = {
                                "language": lang,
                                "periodical_aud_duration": rev_total_time,
                            }
                        elif supercheck_reports == True:
                            sup_total_duration = sum(total_sup_duration_list)
                            sup_total_time = convert_seconds_to_hours(
                                sup_total_duration
                            )
                            result = {
                                "language": lang,
                                "periodical_aud_duration": sup_total_time,
                            }
                        else:
                            ann_total_duration = sum(total_ann_duration_list)
                            ann_total_time = convert_seconds_to_hours(
                                ann_total_duration
                            )
                            result = {
                                "language": lang,
                                "periodical_aud_duration": ann_total_time,
                            }
                    elif (
                        project_type in get_translation_dataset_project_types()
                        or "ConversationTranslation" in project_type
                    ):
                        total_rev_word_count_list = []
                        total_ann_word_count_list = []
                        total_sup_word_count_list = []

                        if reviewer_reports == True:
                            annotated_labeled_tasks = Annotation.objects.filter(
                                task_id__in=labeled_count_tasks_ids,
                                annotation_type=REVIEWER_ANNOTATION,
                                updated_at__gte=periodical_list[period],
                                updated_at__lt=periodical_list[period + 1],
                            )
                            for each_task in annotated_labeled_tasks:
                                try:
                                    total_rev_word_count_list.append(
                                        each_task.task.data["word_count"]
                                    )
                                except:
                                    pass
                            result = {
                                "language": lang,
                                "periodical_word_count": sum(total_rev_word_count_list),
                            }
                        elif supercheck_reports == True:
                            annotated_labeled_tasks = Annotation.objects.filter(
                                task_id__in=labeled_count_tasks_ids,
                                annotation_type=SUPER_CHECKER_ANNOTATION,
                                updated_at__gte=periodical_list[period],
                                updated_at__lt=periodical_list[period + 1],
                            )
                            for each_task in annotated_labeled_tasks:
                                try:
                                    total_sup_word_count_list.append(
                                        each_task.task.data["word_count"]
                                    )
                                except:
                                    pass
                            result = {
                                "language": lang,
                                "periodical_word_count": sum(total_sup_word_count_list),
                            }
                        else:
                            annotated_labeled_tasks = Annotation.objects.filter(
                                task_id__in=labeled_count_tasks_ids,
                                annotation_type=ANNOTATOR_ANNOTATION,
                                updated_at__gte=periodical_list[period],
                                updated_at__lt=periodical_list[period + 1],
                            )
                            for each_task in annotated_labeled_tasks:
                                try:
                                    total_ann_word_count_list.append(
                                        each_task.task.data["word_count"]
                                    )
                                except:
                                    pass
                            result = {
                                "language": lang,
                                "periodical_word_count": sum(total_ann_word_count_list),
                            }
                    elif "OCRTranscription" in project_type:
                        total_word_count = 0
                        annotations = Annotation.objects.filter(
                            task_id__in=labeled_count_tasks_ids,
                            updated_at__gte=periodical_list[period],
                            updated_at__lt=periodical_list[period + 1],
                        )

                        if reviewer_reports == True:
                            annotations = annotations.filter(
                                annotation_type=REVIEWER_ANNOTATION
                            )
                        elif supercheck_reports == True:
                            annotations = annotations.filter(
                                annotation_type=SUPER_CHECKER_ANNOTATION
                            )
                        else:
                            annotations = annotations.filter(
                                annotation_type=ANNOTATOR_ANNOTATION
                            )

                        for each_anno in annotations:
                            total_word_count += ocr_word_count(each_anno.result)

                        result = {
                            "language": lang,
                            "periodical_word_count": total_word_count,
                        }

                else:
                    result = {
                        "language": lang,
                        "periodical_tasks_count": annotated_labeled_tasks_count,
                    }

                if lang == None or lang == "":
                    other_lang.append(result)
                else:
                    data.append(result)

            other_count = 0
            other_word_count = 0
            other_aud_dur = 0
            for dat in other_lang:
                if metainfo != True:
                    other_count += dat["periodical_tasks_count"]
                else:
                    if project_type in get_audio_project_types():
                        other_aud_dur += convert_hours_to_seconds(
                            dat["periodical_aud_duration"]
                        )
                    elif (
                        project_type in get_translation_dataset_project_types()
                        or "ConversationTranslation" in project_type
                    ):
                        other_word_count += dat["periodical_word_count"]

            if len(other_lang) > 0:
                if metainfo != True:
                    other_language = {
                        "language": "Others",
                        "periodical_tasks_count": other_count,
                    }
                else:
                    if project_type in get_audio_project_types():
                        other_language = {
                            "language": "Others",
                            "periodical_aud_duration": convert_seconds_to_hours(
                                other_aud_dur
                            ),
                        }
                    elif (
                        project_type in get_translation_dataset_project_types()
                        or "ConversationTranslation" in project_type
                    ):
                        other_language = {
                            "language": "Others",
                            "periodical_word_count": other_word_count,
                        }

                data.append(other_language)

            try:
                period_result = sorted(data, key=lambda x: x["language"], reverse=False)
            except:
                period_result = []

            if metainfo == True and not (
                (project_type in get_audio_project_types())
                or (
                    project_type in get_translation_dataset_project_types()
                    or "ConversationTranslation" in project_type
                )
            ):
                period_result = []

            summary_period = {
                period_name: period + 1,
                "date_range": start_end_date,
                "data": period_result,
            }

            final_result.append(summary_period)
        return Response(final_result)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "project_type": openapi.Schema(type=openapi.TYPE_STRING),
                "participation_types": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                ),
            },
            required=["user_id", "project_type", "participation_types"],
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the Organization"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "Email successfully scheduled",
            400: "Invalid request body parameters.",
            401: "Unauthorized access.",
            404: "Organization/User not found.",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        name="Get Organization level users analytics (e-mail)",
        url_name="send_user_analytics",
    )
    def send_user_analytics(self, request, pk=None):
        if not (
            request.user.is_authenticated
            and (
                request.user.role == User.ORGANIZATION_OWNER
                or request.user.is_superuser
            )
        ):
            final_response = {
                "message": "You do not have enough permissions to access this view!"
            }
            return Response(final_response, status=status.HTTP_401_UNAUTHORIZED)

        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = request.data.get("user_id")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        participation_types = request.data.get("participation_types")
        if not set(participation_types).issubset({1, 2, 3, 4}):
            return Response(
                {"message": "Invalid participation types"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from_date = None
        to_date = None

        if "from_date" in dict(request.data) and "to_date" in dict(request.data):
            from_date = request.data.get("from_date")
            to_date = request.data.get("to_date")
            result_from, invalid_message = is_valid_date(from_date)
            result_to, invalid_message = is_valid_date(to_date)
            if not result_from or not result_to:
                return Response(
                    {"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST
                )
            start_date = datetime.strptime(from_date, "%Y-%m-%d")
            end_date = datetime.strptime(to_date, "%Y-%m-%d")

            if start_date > end_date:
                return Response(
                    {"message": "'To' Date should be after 'From' Date"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        project_type = request.data.get("project_type")

        send_user_reports_mail_org.delay(
            org_id=organization.id,
            user_id=user_id,
            project_type=project_type,
            participation_types=participation_types,
            start_date=from_date,
            end_date=to_date,
        )

        return Response(
            {"message": "Email scheduled successfully"}, status=status.HTTP_200_OK
        )


class OrganizationPublicViewSet(viewsets.ModelViewSet):
    """
    A viewset for  Organization , evry one can access this (out side of organization)
    """

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

    @action(
        detail=True,
        methods=["GET"],
        name="Get Cumulative tasks completed ",
        url_name="cumulative_tasks_count",
    )
    def cumulative_tasks_count(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        metainfo = False
        if "metainfo" in dict(request.query_params):
            metainfo = request.query_params["metainfo"]
            if metainfo == "true" or metainfo == "True":
                metainfo = True
        project_types = [
            "ContextualTranslationEditing",
            "ContextualSentenceVerification",
            "SemanticTextualSimilarity_Scale5",
            "AudioTranscriptionEditing",
            "AudioTranscription",
            "AudioSegmentation",
        ]
        if "project_type" in dict(request.query_params):
            project_type = request.query_params["project_type"]
            project_types = [project_type]
        final_result_for_all_types = {}
        for project_type in project_types:
            proj_objs = []
            proj_objs = Project.objects.filter(
                organization_id=pk, project_type=project_type
            )
            if not request.user.is_authenticated:
                proj_objs = proj_objs.filter(workspace_id__public_analytics=True)

            languages = list(set([proj.tgt_language for proj in proj_objs]))
            general_lang = []
            other_lang = []
            for lang in languages:
                proj_lang_filter = proj_objs.filter(tgt_language=lang)
                annotation_tasks_count = 0
                reviewer_task_count = 0
                reviewer_tasks = Task.objects.filter(
                    project_id__in=proj_lang_filter,
                    project_id__project_stage__in=[REVIEW_STAGE, SUPERCHECK_STAGE],
                    task_status__in=["reviewed", "exported", "super_checked"],
                )

                annotation_tasks = Task.objects.filter(
                    project_id__in=proj_lang_filter,
                    task_status__in=[
                        "annotated",
                        "reviewed",
                        "exported",
                        "super_checked",
                    ],
                )

                if metainfo == True:
                    result = {}

                    if project_type in get_audio_project_types():
                        # review audio duration calclation
                        total_rev_duration_list = []

                        for each_task in reviewer_tasks:
                            try:
                                if each_task.task_status == "reviewed":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=REVIEWER_ANNOTATION,
                                    )[0]
                                elif each_task.task_status == "super_checked":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=SUPER_CHECKER_ANNOTATION,
                                    )[0]
                                else:
                                    anno = each_task.correct_annotation
                                total_rev_duration_list.append(
                                    get_audio_transcription_duration(anno.result)
                                )
                            except:
                                pass
                        rev_total_duration = sum(total_rev_duration_list)
                        rev_total_time = convert_seconds_to_hours(rev_total_duration)

                        # annotation audio duration calclation

                        total_ann_duration_list = []

                        for each_task in annotation_tasks:
                            try:
                                if each_task.task_status == "reviewed":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=REVIEWER_ANNOTATION,
                                    )[0]
                                elif each_task.task_status == "exported":
                                    anno = each_task.correct_annotation
                                elif each_task.task_status == "super_checked":
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=SUPER_CHECKER_ANNOTATION,
                                    )[0]
                                else:
                                    anno = Annotation.objects.filter(
                                        task=each_task,
                                        annotation_type=ANNOTATOR_ANNOTATION,
                                    )[0]
                                total_ann_duration_list.append(
                                    get_audio_transcription_duration(anno.result)
                                )
                            except:
                                pass
                        ann_total_duration = sum(total_ann_duration_list)
                        ann_total_time = convert_seconds_to_hours(ann_total_duration)

                        result = {
                            "language": lang,
                            "ann_cumulative_aud_duration": ann_total_time,
                            "rew_cumulative_aud_duration": rev_total_time,
                        }

                    elif (
                        project_type in get_translation_dataset_project_types()
                        or "ConversationTranslation" in project_type
                    ):
                        total_rev_word_count_list = []
                        for reviewer_tas in reviewer_tasks:
                            try:
                                total_rev_word_count_list.append(
                                    reviewer_tas.data["word_count"]
                                )
                            except:
                                pass

                        total_ann_word_count_list = []

                        for annotation_tas in annotation_tasks:
                            try:
                                total_ann_word_count_list.append(
                                    annotation_tas.data["word_count"]
                                )
                            except:
                                pass

                        result = {
                            "language": lang,
                            "ann_cumulative_word_count": sum(total_ann_word_count_list),
                            "rew_cumulative_word_count": sum(total_rev_word_count_list),
                        }
                    elif "OCRTranscription" in project_type:
                        total_rev_word_count = 0

                        for each_task in reviewer_tasks:
                            if each_task.task_status == "reviewed":
                                anno = Annotation.objects.filter(
                                    task=each_task,
                                    annotation_type=REVIEWER_ANNOTATION,
                                )[0]
                            elif each_task.task_status == "super_checked":
                                anno = Annotation.objects.filter(
                                    task=each_task,
                                    annotation_type=SUPER_CHECKER_ANNOTATION,
                                )[0]
                            else:
                                anno = each_task.correct_annotation
                            total_rev_word_count += ocr_word_count(anno.result)

                        total_anno_word_count = 0

                        for each_task in annotation_tasks:
                            if each_task.task_status == "reviewed":
                                anno = Annotation.objects.filter(
                                    task=each_task,
                                    annotation_type=REVIEWER_ANNOTATION,
                                )[0]
                            elif each_task.task_status == "exported":
                                anno = each_task.correct_annotation
                            elif each_task.task_status == "super_checked":
                                anno = Annotation.objects.filter(
                                    task=each_task,
                                    annotation_type=SUPER_CHECKER_ANNOTATION,
                                )[0]
                            else:
                                anno = Annotation.objects.filter(
                                    task=each_task,
                                    annotation_type=ANNOTATOR_ANNOTATION,
                                )[0]
                            total_anno_word_count += ocr_word_count(anno.result)

                        result = {
                            "language": lang,
                            "ann_cumulative_aud_duration": total_anno_word_count,
                            "rew_cumulative_aud_duration": total_rev_word_count,
                        }

                else:
                    reviewer_task_count = reviewer_tasks.count()

                    annotation_tasks_count = annotation_tasks.count()

                    result = {
                        "language": lang,
                        "ann_cumulative_tasks_count": annotation_tasks_count,
                        "rew_cumulative_tasks_count": reviewer_task_count,
                    }

                if lang == None or lang == "":
                    other_lang.append(result)
                else:
                    general_lang.append(result)

            ann_task_count = 0
            rew_task_count = 0
            ann_word_count = 0
            rew_word_count = 0
            ann_aud_dur = 0
            rew_aud_dur = 0
            for dat in other_lang:
                if metainfo != True:
                    ann_task_count += dat["ann_cumulative_tasks_count"]
                    rew_task_count += dat["rew_cumulative_tasks_count"]
                else:
                    if project_type in get_audio_project_types():
                        ann_aud_dur += convert_hours_to_seconds(
                            dat["ann_cumulative_aud_duration"]
                        )
                        rew_aud_dur += convert_hours_to_seconds(
                            dat["rew_cumulative_aud_duration"]
                        )
                    elif (
                        project_type in get_translation_dataset_project_types()
                        or "ConversationTranslation" in project_type
                    ):
                        ann_word_count += dat["ann_cumulative_word_count"]
                        rew_word_count += dat["rew_cumulative_word_count"]

            if len(other_lang) > 0:
                if metainfo != True:
                    other_language = {
                        "language": "Others",
                        "ann_cumulative_tasks_count": ann_task_count,
                        "rew_cumulative_tasks_count": rew_task_count,
                    }
                else:
                    if project_type in get_audio_project_types():
                        other_language = {
                            "language": "Others",
                            "ann_cumulative_aud_duration": convert_seconds_to_hours(
                                ann_aud_dur
                            ),
                            "rew_cumulative_aud_duration": convert_seconds_to_hours(
                                rew_aud_dur
                            ),
                        }

                    elif (
                        project_type in get_translation_dataset_project_types()
                        or "ConversationTranslation" in project_type
                    ):
                        other_language = {
                            "language": "Others",
                            "ann_cumulative_word_count": ann_word_count,
                            "rew_cumulative_word_count": rew_word_count,
                        }

                general_lang.append(other_language)
            try:
                final_result = sorted(
                    general_lang, key=lambda x: x["language"], reverse=False
                )
            except:
                final_result = []

            if metainfo == True and not (
                (project_type in get_audio_project_types())
                or (
                    project_type in get_translation_dataset_project_types()
                    or "ConversationTranslation" in project_type
                )
            ):
                pass
            else:
                final_result_for_all_types[project_type] = final_result
        return Response(final_result_for_all_types)
