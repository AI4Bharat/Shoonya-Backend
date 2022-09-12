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


def get_task_count(
    annotator, tgt_language, project_type, status_list, organization, return_count=True
):
    labeled_task = []
    if tgt_language == None:
        labeled_task = Task.objects.filter(
            annotation_users=annotator,
            project_id__project_type=project_type,
            task_status__in=status_list,
            project_id__organization_id=organization,
        )
    else:
        labeled_task = Task.objects.filter(
            annotation_users=annotator,
            project_id__tgt_language=tgt_language,
            project_id__project_type=project_type,
            task_status__in=status_list,
            project_id__organization_id=organization,
        )
    if return_count == True:
        labled_task_count = len(labeled_task)
        return labled_task_count
    else:
        return labeled_task


def get_annotated_tasks(
    annotator,
    tgt_language,
    project_type,
    status_list,
    organization,
    start_date,
    end_date,
):
    annotated_tasks = get_task_count(
        annotator,
        tgt_language,
        project_type,
        status_list,
        organization,
        return_count=False,
    )
    annotated_task_ids = list(annotated_tasks.values_list("id", flat=True))
    annotated_labeled_tasks = Annotation.objects.filter(
        task_id__in=annotated_task_ids,
        parent_annotation_id=None,
        created_at__range=[start_date, end_date],
        completed_by=annotator,
    )
    return annotated_labeled_tasks


def get_counts(
    annotator,
    project_type,
    organization,
    start_date,
    end_date,
    is_translation_project,
    tgt_language=None,
):
    total_no_of_tasks_count = 0
    annotated_tasks_count = 0
    avg_lead_time = 0.00
    total_skipped_tasks_count = 0
    total_unlabeled_tasks_count = 0
    total_draft_tasks_count = 0
    no_of_projects = 0
    no_of_workspaces_objs = 0
    annotated_labeled_tasks = []
    projects_objs = []

    if tgt_language == None:
        total_no_of_tasks_assigned = Task.objects.filter(
            annotation_users=annotator,
            project_id__project_type=project_type,
            project_id__organization_id=organization,
        )
        total_no_of_tasks_count = total_no_of_tasks_assigned.count()

        annotated_labeled_tasks = get_annotated_tasks(
            annotator,
            None,
            project_type,
            ["accepted", "to_be_revised", "accepted_with_changes", "labeled"],
            organization,
            start_date,
            end_date,
        )
        annotated_tasks_count = annotated_labeled_tasks.count()

        total_skipped_tasks_count = get_task_count(
            annotator, None, project_type, ["skipped"], organization
        )

        total_unlabeled_tasks_count = get_task_count(
            annotator, None, project_type, ["unlabeled"], organization
        )

        total_draft_tasks_count = get_task_count(
            annotator, None, project_type, ["draft"], organization
        )

        projects_objs = Project.objects.filter(
            annotators=annotator,
            project_type=project_type,
            organization_id=organization,
        )
        no_of_projects = projects_objs.count()

    else:

        total_no_of_tasks_assigned = Task.objects.filter(
            annotation_users=annotator,
            project_id__project_type=project_type,
            project_id__tgt_language=tgt_language,
            project_id__organization_id=organization,
        )
        total_no_of_tasks_count = total_no_of_tasks_assigned.count()

        annotated_labeled_tasks = get_annotated_tasks(
            annotator,
            tgt_language,
            project_type,
            ["accepted", "to_be_revised", "accepted_with_changes", "labeled"],
            organization,
            start_date,
            end_date,
        )
        annotated_tasks_count = annotated_labeled_tasks.count()

        total_skipped_tasks_count = get_task_count(
            annotator, tgt_language, project_type, ["skipped"], organization
        )

        total_unlabeled_tasks_count = get_task_count(
            annotator, tgt_language, project_type, ["unlabeled"], organization
        )

        total_draft_tasks_count = get_task_count(
            annotator, tgt_language, project_type, ["draft"], organization
        )

        projects_objs = Project.objects.filter(
            annotators=annotator,
            project_type=project_type,
            tgt_language=tgt_language,
            organization_id=organization,
        )
        no_of_projects = projects_objs.count()

    lead_time_annotated_tasks = [
        eachtask.lead_time for eachtask in annotated_labeled_tasks
    ]
    if len(lead_time_annotated_tasks) > 0:
        avg_lead_time = sum(lead_time_annotated_tasks) / len(lead_time_annotated_tasks)

    no_of_workspaces_objs = len(
        set([each_proj.workspace_id.id for each_proj in projects_objs])
    )
    total_word_count = "not applicable"
    if is_translation_project:
        total_word_count_list = [
            no_of_words(each_task.task.data["input_text"])
            for each_task in annotated_labeled_tasks
        ]
        total_word_count = sum(total_word_count_list)

    return (
        total_no_of_tasks_count,
        annotated_tasks_count,
        avg_lead_time,
        total_skipped_tasks_count,
        total_unlabeled_tasks_count,
        total_draft_tasks_count,
        no_of_projects,
        no_of_workspaces_objs,
        total_word_count,
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

    @is_organization_owner
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

        result = []
        for annotator in annotators:
            name = annotator.username
            email = annotator.get_username()
            if tgt_language == None:
                selected_language = "-"
                (
                    total_no_of_tasks_count,
                    annotated_tasks_count,
                    avg_lead_time,
                    total_skipped_tasks_count,
                    total_unlabeled_tasks_count,
                    total_draft_tasks_count,
                    no_of_projects,
                    no_of_workspaces_objs,
                    total_word_count,
                ) = get_counts(
                    annotator,
                    project_type,
                    organization,
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
                    total_no_of_tasks_count,
                    annotated_tasks_count,
                    avg_lead_time,
                    total_skipped_tasks_count,
                    total_unlabeled_tasks_count,
                    total_draft_tasks_count,
                    no_of_projects,
                    no_of_workspaces_objs,
                    total_word_count,
                ) = get_counts(
                    annotator,
                    project_type,
                    organization,
                    start_date,
                    end_date,
                    is_translation_project,
                    tgt_language,
                )

            if total_word_count == "not applicable":
                result.append(
                    {
                        "Annotator": name,
                        "Email": email,
                        "Language": selected_language,
                        "No. of Workspaces": no_of_workspaces_objs,
                        "No. of Projects": no_of_projects,
                        "Project Type": project_type,
                        "No.Of Tasks Assigned": total_no_of_tasks_count,
                        "No. of Annotated Tasks": annotated_tasks_count,
                        "Unlabeled Tasks": total_unlabeled_tasks_count,
                        "Skipped Tasks": total_skipped_tasks_count,
                        "Draft Tasks": total_draft_tasks_count,
                        "Average Annotation Time (In Seconds)": round(avg_lead_time, 2),
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
                        "Project Type": project_type,
                        "No.Of Tasks Assigned": total_no_of_tasks_count,
                        "No. of Annotated Tasks": annotated_tasks_count,
                        "Unlabeled Tasks": total_unlabeled_tasks_count,
                        "Skipped Tasks": total_skipped_tasks_count,
                        "Draft Tasks": total_draft_tasks_count,
                        "Word Count Of Annotated Tasks": total_word_count,
                        "Average Annotation Time (In Seconds)": round(avg_lead_time, 2),
                    }
                )
        final_result = sorted(
            result, key=lambda x: x[sort_by_column_name], reverse=descending_order
        )
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
                    "No.Of Tasks": total_tasks,
                    "Annotated Tasks": labeled_count,
                    "Unlabeled Tasks": un_labeled_count,
                    "Skipped Tasks": skipped_count,
                    "Draft Tasks": dropped_tasks,
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
        proj_objs = Project.objects.filter(
            organization_id=pk, project_type=project_type
        )

        languages = list(set([proj.tgt_language for proj in proj_objs]))
        general_lang = []
        other_lang = []
        for lang in languages:
            proj_lang_filter = proj_objs.filter(tgt_language=lang)
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

        proj_objs = Project.objects.filter(
            organization_id=pk, project_type=project_type
        )

        languages = list(set([proj.tgt_language for proj in proj_objs]))

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

                labeled_count_tasks_ids = list(tasks_objs.values_list("id", flat=True))
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
