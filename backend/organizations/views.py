from cProfile import label
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status
from tasks.models import Task
from datetime import datetime
from .models import Organization
from .serializers import OrganizationSerializer
from .decorators import is_organization_owner, is_particular_organization_owner
from users.serializers import UserFetchSerializer
from users.models import User
from projects.models import Project
from django.db.models import Avg, Count, F, FloatField, Q, Value, Subquery
from django.db.models.functions import Cast, Coalesce
from regex import R
from tasks.models import Annotation
from projects.utils import is_valid_date, no_of_words
from datetime import datetime, timezone, timedelta
import pandas as pd
from dateutil import relativedelta
import calendar
from workspaces.views import get_review_reports
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
import csv
from django.http import StreamingHttpResponse
from tasks.views import SentenceOperationViewSet


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
        created_at__range=[start_date, end_date],
        completed_by=annotator,
    )

    return annotated_labeled_tasks


def get_reviewd_tasks(proj_ids, annotator, status_list, start_date, end_date):

    annotated_tasks_objs = get_task_count(
        proj_ids, status_list, annotator, return_count=False
    )

    annotated_task_ids = list(annotated_tasks_objs.values_list("id", flat=True))
    annotated_labeled_tasks = Annotation.objects.filter(
        task_id__in=annotated_task_ids,
        parent_annotation_id__isnull=False,
        created_at__range=[start_date, end_date],
    )

    return annotated_labeled_tasks


def un_pack_annotation_tasks(
    proj_ids, each_annotation_user, start_date, end_date, is_translation_project
):

    accepted = get_annotated_tasks(
        proj_ids,
        each_annotation_user,
        ["accepted"],
        start_date,
        end_date,
    )

    to_be_revised = get_annotated_tasks(
        proj_ids,
        each_annotation_user,
        ["to_be_revised"],
        start_date,
        end_date,
    )
    accepted_with_changes = get_annotated_tasks(
        proj_ids,
        each_annotation_user,
        ["accepted_with_changes"],
        start_date,
        end_date,
    )
    labeled = get_annotated_tasks(
        proj_ids,
        each_annotation_user,
        ["labeled"],
        start_date,
        end_date,
    )

    all_annotated_tasks = (
        list(accepted)
        + list(to_be_revised)
        + list(accepted_with_changes)
        + list(labeled)
    )
    lead_time_annotated_tasks = [eachtask.lead_time for eachtask in all_annotated_tasks]
    avg_lead_time = 0
    if len(lead_time_annotated_tasks) > 0:
        avg_lead_time = sum(lead_time_annotated_tasks) / len(lead_time_annotated_tasks)
    total_word_count = 0
    if is_translation_project:

        total_word_count_list = [
            each_task.task.data["word_count"] for each_task in all_annotated_tasks
        ]
        total_word_count = sum(total_word_count_list)

    return (
        accepted.count(),
        to_be_revised.count(),
        accepted_with_changes.count(),
        labeled.count(),
        avg_lead_time,
        total_word_count,
    )


def get_counts(
    pk,
    annotator,
    project_type,
    start_date,
    end_date,
    is_translation_project,
    only_review_proj,
    tgt_language=None,
):

    annotated_tasks = 0
    accepted = 0
    to_be_revised = 0
    accepted_with_changes = 0
    labeled = 0
    if tgt_language == None:
        if only_review_proj == None:
            projects_objs = Project.objects.filter(
                organization_id_id=pk,
                project_type=project_type,
                annotators=annotator,
            )
        else:
            projects_objs = Project.objects.filter(
                organization_id_id=pk,
                project_type=project_type,
                enable_task_reviews=only_review_proj,
                annotators=annotator,
            )
    else:
        if only_review_proj == None:
            projects_objs = Project.objects.filter(
                organization_id_id=pk,
                project_type=project_type,
                tgt_language=tgt_language,
                annotators=annotator,
            )
        else:
            projects_objs = Project.objects.filter(
                organization_id_id=pk,
                project_type=project_type,
                enable_task_reviews=only_review_proj,
                tgt_language=tgt_language,
                annotators=annotator,
            )
    project_count = projects_objs.count()
    no_of_workspaces_objs = len(
        set([each_proj.workspace_id.id for each_proj in projects_objs])
    )
    proj_ids = [eachid["id"] for eachid in projects_objs.values("id")]

    all_tasks_in_project = Task.objects.filter(
        Q(project_id__in=proj_ids) & Q(annotation_users=annotator)
    )
    assigned_tasks = all_tasks_in_project.count()

    if only_review_proj:

        (
            accepted,
            to_be_revised,
            accepted_with_changes,
            labeled,
            avg_lead_time,
            total_word_count,
        ) = un_pack_annotation_tasks(
            proj_ids,
            annotator,
            start_date,
            end_date,
            is_translation_project,
        )

    else:
        annotated_labeled_tasks = get_annotated_tasks(
            proj_ids,
            annotator,
            ["accepted", "to_be_revised", "accepted_with_changes", "labeled"],
            start_date,
            end_date,
        )

        annotated_tasks = annotated_labeled_tasks.count()
        lead_time_annotated_tasks = [
            eachtask.lead_time for eachtask in annotated_labeled_tasks
        ]
        avg_lead_time = 0
        if len(lead_time_annotated_tasks) > 0:
            avg_lead_time = sum(lead_time_annotated_tasks) / len(
                lead_time_annotated_tasks
            )
        total_word_count = 0
        if is_translation_project:
            total_word_count_list = [
                each_task.task.data["word_count"]
                for each_task in annotated_labeled_tasks
            ]
            total_word_count = sum(total_word_count_list)

    total_skipped_tasks = get_task_count(proj_ids, ["skipped"], annotator)
    all_pending_tasks_in_project = get_task_count(proj_ids, ["unlabeled"], annotator)
    all_draft_tasks_in_project = get_task_count(proj_ids, ["draft"], annotator)

    return (
        assigned_tasks,
        annotated_tasks,
        accepted,
        to_be_revised,
        accepted_with_changes,
        labeled,
        avg_lead_time,
        total_skipped_tasks,
        all_pending_tasks_in_project,
        all_draft_tasks_in_project,
        project_count,
        no_of_workspaces_objs,
        total_word_count,
    )


def get_translation_quality_reports(
    pk,
    annotator,
    project_type,
    start_date,
    end_date,
    is_translation_project,
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
            enable_task_reviews=True,
            annotators=annotator,
        )
    else:
        projects_objs = Project.objects.filter(
            organization_id_id=pk,
            project_type=project_type,
            enable_task_reviews=True,
            tgt_language=tgt_language,
            annotators=annotator,
        )

    proj_ids = [eachid["id"] for eachid in projects_objs.values("id")]

    all_reviewd_tasks = get_reviewd_tasks(
        proj_ids,
        annotator,
        ["accepted", "to_be_revised", "accepted_with_changes", "labeled"],
        start_date,
        end_date,
    )
    all_reviewd_tasks_count = all_reviewd_tasks.count()

    accepted_count = get_reviewd_tasks(
        proj_ids,
        annotator,
        ["accepted"],
        start_date,
        end_date,
    ).count()
    if all_reviewd_tasks_count == 0:
        reviewed_except_accepted = 0
    else:
        reviewed_except_accepted = round(
            (accepted_count / all_reviewd_tasks_count) * 100, 2
        )

    accepted_with_changes_tasks = get_reviewd_tasks(
        proj_ids,
        annotator,
        ["accepted_with_changes"],
        start_date,
        end_date,
    )
    total_bleu_score = 0
    total_char_score = 0

    bleu_score_error_count = 0
    char_score_error_count = 0

    for annot in accepted_with_changes_tasks:
        annotator_obj = Annotation.objects.get(
            task_id=annot.task_id, parent_annotation_id=None
        )

        str1 = annotator_obj.result[0]["value"]["text"]
        str2 = annot.result[0]["value"]["text"]

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

    if len(accepted_with_changes_tasks) > 0:

        accepted_with_change_minus_bleu_score_error = (
            len(accepted_with_changes_tasks) - bleu_score_error_count
        )
        accepted_with_change_minus_char_score_error = (
            len(accepted_with_changes_tasks) - char_score_error_count
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

    total_lead_time = [annot.lead_time for annot in all_reviewd_tasks]
    avg_lead_time = 0
    if len(total_lead_time) > 0:
        avg_lead_time = sum(total_lead_time) / len(total_lead_time)
        avg_lead_time = round(avg_lead_time, 2)

    return (
        all_reviewd_tasks_count,
        accepted_count,
        reviewed_except_accepted,
        accepted_with_changes_tasks.count(),
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

        result = []
        for annotator in annotators:
            user_id = annotator.id
            name = annotator.username
            email = annotator.get_username()
            if tgt_language == None:
                user_lang_filter = User.objects.get(id=user_id)
                user_lang = user_lang_filter.languages
                selected_language = user_lang
                if "English" in selected_language:
                    selected_language.remove("English")
                (
                    all_reviewd_tasks_count,
                    accepted_count,
                    reviewed_except_accepted,
                    accepted_with_changes_tasks_count,
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
                )

            else:
                selected_language = tgt_language
                list_of_user_languages = annotator.languages
                if tgt_language != None and tgt_language not in list_of_user_languages:
                    continue
                (
                    all_reviewd_tasks_count,
                    accepted_count,
                    reviewed_except_accepted,
                    accepted_with_changes_tasks_count,
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
                    tgt_language,
                )
            result.append(
                {
                    "Translator": name,
                    "Language": selected_language,
                    "Reviewed": all_reviewd_tasks_count,
                    "Accepted": accepted_count,
                    "(Reviewed /Accepted) Percentage ": reviewed_except_accepted,
                    "Accepted With Changes": accepted_with_changes_tasks_count,
                    "Avg Character Edit Distance Score": avg_char_score,
                    "Average BLEU Score": avg_bleu_score,
                    "Avg Lead Time": avg_lead_time,
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
        annotators = User.objects.filter(organization=organization).order_by("username")
        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")
        from_date = from_date + " 00:00"
        to_date = to_date + " 23:59"
        only_review_proj = request.data.get("only_review_projects")
        tgt_language = request.data.get("tgt_language")
        project_type = request.data.get("project_type")
        reports_type = request.data.get("reports_type")
        project_type_lower = project_type.lower()
        is_translation_project = True if "translation" in project_type_lower else False
        sort_by_column_name = request.data.get("sort_by_column_name")
        descending_order = request.data.get("descending_order")
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

        if reports_type == "review":

            proj_objs = Project.objects.filter(organization_id=pk)
            review_projects = [pro for pro in proj_objs if pro.enable_task_reviews]

            org_reviewer_list = []
            for review_project in review_projects:
                reviewer_names_list = review_project.annotation_reviewers.all()
                reviewer_ids = [name.id for name in reviewer_names_list]
                org_reviewer_list.extend(reviewer_ids)

            org_reviewer_list = list(set(org_reviewer_list))

            final_reports = []

            if (
                request.user.role == User.ORGANIZATION_OWNER
                or request.user.role == User.WORKSPACE_MANAGER
                or request.user.is_superuser
            ):

                for id in org_reviewer_list:
                    reviewer_projs = Project.objects.filter(
                        organization_id=pk, annotation_reviewers=id
                    )
                    reviewer_projs_ids = [
                        review_proj.id for review_proj in reviewer_projs
                    ]

                    result = get_review_reports(
                        reviewer_projs_ids, id, start_date, end_date
                    )
                    final_reports.append(result)
            elif user_id in org_reviewer_list:
                reviewer_projs = Project.objects.filter(
                    organization_id=pk, annotation_reviewers=user_id
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
                or request.user.is_superuser
            )
        ):
            final_response = {
                "message": "You do not have enough permissions to access this view!"
            }
            return Response(final_response, status=status.HTTP_400_BAD_REQUEST)
        result = []
        for annotator in annotators:
            user_id = annotator.id
            name = annotator.username
            email = annotator.get_username()
            if tgt_language == None:
                user_lang_filter = User.objects.get(id=user_id)
                user_lang = user_lang_filter.languages
                selected_language = user_lang
                if "English" in selected_language:
                    selected_language.remove("English")
                (
                    total_no_of_tasks_count,
                    annotated_tasks_count,
                    accepted,
                    to_be_revised,
                    accepted_with_changes,
                    labeled,
                    avg_lead_time,
                    total_skipped_tasks_count,
                    total_unlabeled_tasks_count,
                    total_draft_tasks_count,
                    no_of_projects,
                    no_of_workspaces_objs,
                    total_word_count,
                ) = get_counts(
                    pk,
                    annotator,
                    project_type,
                    start_date,
                    end_date,
                    is_translation_project,
                    only_review_proj,
                )

            else:
                selected_language = tgt_language
                list_of_user_languages = annotator.languages
                if tgt_language != None and tgt_language not in list_of_user_languages:
                    continue
                (
                    total_no_of_tasks_count,
                    annotated_tasks_count,
                    accepted,
                    to_be_revised,
                    accepted_with_changes,
                    labeled,
                    avg_lead_time,
                    total_skipped_tasks_count,
                    total_unlabeled_tasks_count,
                    total_draft_tasks_count,
                    no_of_projects,
                    no_of_workspaces_objs,
                    total_word_count,
                ) = get_counts(
                    pk,
                    annotator,
                    project_type,
                    start_date,
                    end_date,
                    is_translation_project,
                    only_review_proj,
                    tgt_language,
                )

            if is_translation_project:
                if only_review_proj:

                    result.append(
                        {
                            "Annotator": name,
                            "Email": email,
                            "Language": selected_language,
                            "No. of Workspaces": no_of_workspaces_objs,
                            "No. of Projects": no_of_projects,
                            "Assigned": total_no_of_tasks_count,
                            "Labeled": labeled,
                            "Accepted": accepted,
                            "Accepted With Changes": accepted_with_changes,
                            "To Be Revised": to_be_revised,
                            "Unlabeled": total_unlabeled_tasks_count,
                            "Skipped": total_skipped_tasks_count,
                            "Draft": total_draft_tasks_count,
                            "Word Count": total_word_count,
                            "Average Annotation Time (In Seconds)": round(
                                avg_lead_time, 2
                            ),
                        }
                    )
                else:
                    result.append(
                        {
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
                            "Average Annotation Time (In Seconds)": round(
                                avg_lead_time, 2
                            ),
                        }
                    )

            else:
                if only_review_proj:

                    result.append(
                        {
                            "Annotator": name,
                            "Email": email,
                            "Language": selected_language,
                            "No. of Workspaces": no_of_workspaces_objs,
                            "No. of Projects": no_of_projects,
                            "Assigned": total_no_of_tasks_count,
                            "Labeled": labeled,
                            "Accepted": accepted,
                            "Accepted With Changes": accepted_with_changes,
                            "To Be Revised": to_be_revised,
                            "Unlabeled": total_unlabeled_tasks_count,
                            "Skipped": total_skipped_tasks_count,
                            "Draft": total_draft_tasks_count,
                            "Average Annotation Time (In Seconds)": round(
                                avg_lead_time, 2
                            ),
                        }
                    )
                else:
                    result.append(
                        {
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
                            "Average Annotation Time (In Seconds)": round(
                                avg_lead_time, 2
                            ),
                        }
                    )

        final_result = sorted(
            result, key=lambda x: x[sort_by_column_name], reverse=descending_order
        )

        download_csv = request.data.get("download_csv", False)

        if download_csv:

            class Echo(object):
                def write(self, value):
                    return value

            def iter_items(items, pseudo_buffer):
                writer = csv.DictWriter(pseudo_buffer, fieldnames=list(items[0].keys()))
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

        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")
        from_date = from_date + " 00:00"
        to_date = to_date + " 23:59"
        tgt_language = request.data.get("tgt_language")
        project_type = request.data.get("project_type")

        sort_by_column_name = request.data.get("sort_by_column_name")
        descending_order = request.data.get("descending_order")
        if sort_by_column_name == None:
            sort_by_column_name = "User Name"

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
            selected_language = "-"
            projects_obj = Project.objects.filter(
                organization_id=organization, project_type=project_type
            )
        else:
            selected_language = tgt_language
            projects_obj = Project.objects.filter(
                organization_id=organization,
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
                un_labeled_task = Task.objects.filter(
                    project_id=proj.id, task_status="unlabeled"
                )
                un_labeled_count = un_labeled_task.count()
                labeled_count_tasks = Task.objects.filter(
                    Q(project_id=proj.id)
                    & Q(
                        task_status__in=[
                            "accepted",
                            "to_be_revised",
                            "accepted_with_changes",
                            "labeled",
                        ]
                    )
                )

                labeled_count_tasks_ids = list(
                    labeled_count_tasks.values_list("id", flat=True)
                )
                annotated_labeled_tasks = Annotation.objects.filter(
                    task_id__in=labeled_count_tasks_ids,
                    parent_annotation_id=None,
                    created_at__range=[start_date, end_date],
                )

                labeled_count = annotated_labeled_tasks.count()

                skipped_count = Task.objects.filter(
                    project_id=proj.id, task_status="skipped"
                ).count()
                dropped_tasks = Task.objects.filter(
                    project_id=proj.id, task_status="draft"
                ).count()
                if total_tasks == 0:
                    project_progress = 0.0
                else:
                    project_progress = (labeled_count / total_tasks) * 100
                result = {
                    "Project Id": project_id,
                    "Project Name": project_name,
                    "Project Type": project_type,
                    "Language": selected_language,
                    "No.Of Annotators Assigned": no_of_annotators_assigned,
                    "Total": total_tasks,
                    "Annotated": labeled_count,
                    "Unlabeled": un_labeled_count,
                    "Skipped": skipped_count,
                    "Draft": dropped_tasks,
                    "Project Progress": round(project_progress, 3),
                }
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
        project_type = request.data.get("project_type")
        reviewer_reports = request.data.get("reviewer_reports")
        proj_objs = []
        if reviewer_reports == True:
            proj_objs = Project.objects.filter(
                organization_id=pk, project_type=project_type, enable_task_reviews=True
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
                tasks_count = Task.objects.filter(
                    project_id__in=proj_lang_filter,
                    project_id__tgt_language=lang,
                    task_status__in=["accepted", "accepted_with_changes"],
                ).count()
            else:
                tasks_count = Task.objects.filter(
                    project_id__in=proj_lang_filter,
                    project_id__tgt_language=lang,
                    task_status__in=[
                        "labeled",
                        "accepted",
                        "accepted_with_changes",
                        "to_be_revised",
                        "complete",
                    ],
                ).count()

            result = {"language": lang, "cumulative_tasks_count": tasks_count}

            if lang == None or lang == "":
                other_lang.append(result)
            else:
                general_lang.append(result)

        other_count = 0
        for dat in other_lang:
            other_count += dat["cumulative_tasks_count"]
        if len(other_lang) > 0:
            other_language = {
                "language": "Others",
                "cumulative_tasks_count": other_count,
            }
            general_lang.append(other_language)

        final_result = sorted(general_lang, key=lambda x: x["language"], reverse=False)
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
        project_type = request.data.get("project_type")
        periodical_type = request.data.get("periodical_type")

        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        reviewer_reports = request.data.get("reviewer_reports")

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
                organization_id=pk, project_type=project_type, enable_task_reviews=True
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
                    tasks_objs = Task.objects.filter(
                        project_id__in=proj_lang_filter,
                        task_status__in=["accepted", "accepted_with_changes"],
                    )
                    labeled_count_tasks_ids = list(
                        tasks_objs.values_list("id", flat=True)
                    )
                    annotated_labeled_tasks_count = Annotation.objects.filter(
                        task_id__in=labeled_count_tasks_ids,
                        parent_annotation_id__isnull=False,
                        created_at__gte=periodical_list[period],
                        created_at__lt=periodical_list[period + 1],
                    ).count()
                else:
                    tasks_objs = Task.objects.filter(
                        project_id__in=proj_lang_filter,
                        task_status__in=[
                            "labeled",
                            "accepted",
                            "accepted_with_changes",
                            "to_be_revised",
                            "complete",
                        ],
                    )

                    labeled_count_tasks_ids = list(
                        tasks_objs.values_list("id", flat=True)
                    )
                    annotated_labeled_tasks_count = Annotation.objects.filter(
                        task_id__in=labeled_count_tasks_ids,
                        parent_annotation_id=None,
                        created_at__gte=periodical_list[period],
                        created_at__lt=periodical_list[period + 1],
                    ).count()

                summary_lang = {
                    "language": lang,
                    "annotations_completed": annotated_labeled_tasks_count,
                }
                if lang == None or lang == "":
                    other_lang.append(summary_lang)
                else:
                    data.append(summary_lang)

            other_count = 0
            for dat in other_lang:
                other_count += dat["annotations_completed"]
            if len(other_lang) > 0:
                other_language = {
                    "language": "Others",
                    "annotations_completed": other_count,
                }
                data.append(other_language)
            data1 = sorted(data, key=lambda x: x["language"], reverse=False)
            summary_period = {
                period_name: period + 1,
                "date_range": start_end_date,
                "data": data1,
            }

            final_result.append(summary_period)

        return Response(final_result)
