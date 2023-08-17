import datetime
from dateutil.relativedelta import relativedelta
from celery import shared_task
import pandas as pd
from django.conf import settings
from django.core.mail import EmailMessage

from tasks.models import (
    Annotation,
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
)
from .models import Workspace
from users.models import User
from projects.models import Project, ANNOTATION_STAGE, REVIEW_STAGE
from users.utils import get_role_name
from projects.utils import (
    convert_seconds_to_hours,
    get_audio_project_types,
    get_audio_transcription_duration,
)


def get_all_annotation_reports(
    proj_ids,
    userid,
    project_type,
    start_date=None,
    end_date=None,
):
    user = User.objects.get(pk=userid)
    participation_type = user.participation_type
    participation_type = (
        "Full Time"
        if participation_type == 1
        else "Part Time"
        if participation_type == 2
        else "Contract Basis"
        if participation_type == 4
        else "N/A"
    )
    role = get_role_name(user.role)
    userName = user.username
    email = user.email
    user_lang = user.languages

    if not start_date:
        submitted_tasks = Annotation.objects.filter(
            annotation_status="labeled",
            task__project_id__in=proj_ids,
            annotation_type=ANNOTATOR_ANNOTATION,
            completed_by=userid,
        )
    else:
        submitted_tasks = Annotation.objects.filter(
            annotation_status="labeled",
            task__project_id__in=proj_ids,
            annotation_type=ANNOTATOR_ANNOTATION,
            completed_by=userid,
            updated_at__range=[start_date, end_date],
        )

    submitted_tasks_count = submitted_tasks.count()

    project_type_lower = project_type.lower()
    is_translation_project = True if "translation" in project_type_lower else False
    total_audio_duration_list = []
    total_raw_audio_duration_list = []
    total_word_count_list = []
    if is_translation_project:
        for anno in submitted_tasks:
            try:
                total_word_count_list.append(anno.task.data["word_count"])
            except:
                pass
    elif (
        project_type in get_audio_project_types()
        or project_type == "AudioTranscription + Editing"
    ):
        for anno in submitted_tasks:
            try:
                total_audio_duration_list.append(
                    get_audio_transcription_duration(anno.result)
                )
                total_raw_audio_duration_list.append(anno.task.data["audio_duration"])
            except:
                pass

    total_word_count = sum(total_word_count_list)
    total_audio_duration = convert_seconds_to_hours(sum(total_audio_duration_list))
    total_raw_audio_duration = convert_seconds_to_hours(
        sum(total_raw_audio_duration_list)
    )

    result = {
        "Name": userName,
        "Email": email,
        "Participation Type": participation_type,
        "Role": role,
        "Type of Work": "Annotator",
        "Total Segments Duration": total_audio_duration,
        "Total Raw Audio Duration": total_raw_audio_duration,
        "Word Count": total_word_count,
        "Submitted Tasks": submitted_tasks_count,
        "Language": user_lang,
    }

    if (
        project_type in get_audio_project_types()
        or project_type == "AudioTranscription + Editing"
    ):
        del result["Word Count"]
    else:
        del result["Total Segments Duration"]
        del result["Total Raw Audio Duration"]

    return result


def get_all_review_reports(
    proj_ids,
    userid,
    project_type,
    start_date=None,
    end_date=None,
):
    user = User.objects.get(pk=userid)
    participation_type = user.participation_type
    participation_type = (
        "Full Time"
        if participation_type == 1
        else "Part Time"
        if participation_type == 2
        else "Contract Basis"
        if participation_type == 4
        else "N/A"
    )
    role = get_role_name(user.role)
    userName = user.username
    email = user.email
    user_lang = user.languages

    if not start_date:
        submitted_tasks = Annotation.objects.filter(
            annotation_status__in=[
                "accepted",
                "to_be_revised",
                "accepted_with_minor_changes",
                "accepted_with_major_changes",
            ],
            task__project_id__in=proj_ids,
            task__review_user=userid,
            annotation_type=REVIEWER_ANNOTATION,
        )
    else:
        submitted_tasks = Annotation.objects.filter(
            annotation_status__in=[
                "accepted",
                "to_be_revised",
                "accepted_with_minor_changes",
                "accepted_with_major_changes",
            ],
            task__project_id__in=proj_ids,
            task__review_user=userid,
            annotation_type=REVIEWER_ANNOTATION,
            updated_at__range=[start_date, end_date],
        )

    submitted_tasks_count = submitted_tasks.count()

    project_type_lower = project_type.lower()
    is_translation_project = True if "translation" in project_type_lower else False
    total_audio_duration_list = []
    total_raw_audio_duration_list = []
    total_word_count_list = []
    if is_translation_project:
        for anno in submitted_tasks:
            try:
                total_word_count_list.append(anno.task.data["word_count"])
            except:
                pass
    elif (
        project_type in get_audio_project_types()
        or project_type == "AudioTranscription + Editing"
    ):
        for anno in submitted_tasks:
            try:
                total_audio_duration_list.append(
                    get_audio_transcription_duration(anno.result)
                )
                total_raw_audio_duration_list.append(anno.task.data["audio_duration"])
            except:
                pass

    total_word_count = sum(total_word_count_list)
    total_audio_duration = convert_seconds_to_hours(sum(total_audio_duration_list))
    total_raw_audio_duration = convert_seconds_to_hours(
        sum(total_raw_audio_duration_list)
    )

    result = {
        "Name": userName,
        "Email": email,
        "Participation Type": participation_type,
        "Role": role,
        "Type of Work": "Review",
        "Total Segments Duration": total_audio_duration,
        "Total Raw Audio Duration": total_raw_audio_duration,
        "Word Count": total_word_count,
        "Submitted Tasks": submitted_tasks_count,
        "Language": user_lang,
    }

    if (
        project_type in get_audio_project_types()
        or project_type == "AudioTranscription + Editing"
    ):
        del result["Word Count"]
    else:
        del result["Total Segments Duration"]
        del result["Total Raw Audio Duration"]

    return result


def get_all_supercheck_reports(
    proj_ids, userid, project_type, start_date=None, end_date=None
):
    user = User.objects.get(pk=userid)
    participation_type = (
        "Full Time"
        if user.participation_type == 1
        else "Part Time"
        if user.participation_type == 2
        else "Contract Basis"
        if user.participation_type == 4
        else "N/A"
    )
    role = get_role_name(user.role)
    userName = user.username
    email = user.email
    user_lang = user.languages

    if not start_date:
        submitted_tasks = Annotation.objects.filter(
            annotation_status__in=["validated", "validated_with_changes", "rejected"],
            task__project_id__in=proj_ids,
            task__super_check_user=userid,
            annotation_type=SUPER_CHECKER_ANNOTATION,
        )
    else:
        submitted_tasks = Annotation.objects.filter(
            annotation_status__in=["validated", "validated_with_changes", "rejected"],
            task__project_id__in=proj_ids,
            task__super_check_user=userid,
            annotation_type=SUPER_CHECKER_ANNOTATION,
            updated_at__range=[start_date, end_date],
        )

    submitted_tasks_count = submitted_tasks.count()

    project_type_lower = project_type.lower()
    is_translation_project = True if "translation" in project_type_lower else False

    validated_word_count_list = []
    validated_audio_duration_list = []
    validated_raw_audio_duration_list = []
    if is_translation_project:
        for anno in submitted_tasks:
            try:
                validated_word_count_list.append(anno.task.data["word_count"])
            except:
                pass
    elif (
        project_type in get_audio_project_types()
        or project_type == "AudioTranscription + Editing"
    ):
        for anno in submitted_tasks:
            try:
                validated_audio_duration_list.append(
                    get_audio_transcription_duration(anno.result)
                )
                validated_raw_audio_duration_list.append(
                    anno.task.data["audio_duration"]
                )
            except:
                pass

    validated_word_count = sum(validated_word_count_list)
    validated_audio_duration = convert_seconds_to_hours(
        sum(validated_audio_duration_list)
    )
    validated_raw_audio_duration = convert_seconds_to_hours(
        sum(validated_raw_audio_duration_list)
    )

    result = {
        "Name": userName,
        "Email": email,
        "Participation Type": participation_type,
        "Role": role,
        "Type of Work": "Supercheck",
        "Total Segments Duration": validated_audio_duration,
        "Total Raw Audio Duration": validated_raw_audio_duration,
        "Word Count": validated_word_count,
        "Submitted Tasks": submitted_tasks_count,
        "Language": user_lang,
    }

    if (
        project_type in get_audio_project_types()
        or project_type == "AudioTranscription + Editing"
    ):
        del result["Word Count"]
    else:
        del result["Total Segments Duration"]
        del result["Total Raw Audio Duration"]

    return result


@shared_task()
def send_user_reports_mail_ws(
    ws_id,
    user_id,
    project_type,
    participation_types,
    start_date=None,
    end_date=None,
    period=None,
):
    """Function to generate CSV of workspace user reports and send mail to the manager/owner/admin

    Args:
        ws_id (int): ID of the workspace.
        user_id (int): ID of the user requesting the report.
        project_type (str): Type of project.
        participation_types (list, optional): User participation types. Defaults to [1, 2, 4].
        start_date (datetime, optional): Start date of the report. Defaults to None.
        end_date (datetime, optional): End date of the report. Defaults to None.
        period (str, optional): Period of the report. Defaults to None.
    """

    user = User.objects.get(id=user_id)
    workspace = Workspace.objects.get(pk=ws_id)
    if project_type == "AudioTranscription + Editing":
        proj_objs = Project.objects.filter(
            workspace_id=ws_id,
            project_type__in=["AudioTranscription", "AudioTranscriptionEditing"],
        )
    else:
        proj_objs = Project.objects.filter(
            workspace_id=ws_id, project_type=project_type
        )

    if period:
        if period == "Daily":
            start_date = datetime.datetime.now() + relativedelta(days=-1)
            end_date = datetime.datetime.now() + relativedelta(days=-1)
        elif period == "Weekly":
            start_date = datetime.datetime.now() + relativedelta(days=-7)
            end_date = datetime.now() + relativedelta(days=-1)
        elif period == "Monthly":
            start_date = datetime.datetime.now() + relativedelta(months=-1)
            end_date = datetime.datetime.now() + relativedelta(days=-1)

    if start_date:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        start_date = datetime.datetime.combine(start_date, datetime.time.min)
        end_date = datetime.datetime.combine(end_date, datetime.time.max)

    start_date = start_date.replace(tzinfo=datetime.timezone.utc)
    end_date = end_date.replace(tzinfo=datetime.timezone.utc)

    if not participation_types:
        participation_types = [1, 2, 4]

    ws_anno_list = []
    ws_reviewer_list = []
    ws_superchecker_list = []
    for project in proj_objs:
        anno_list = project.annotators.all()
        reviewer_list = project.annotation_reviewers.all()
        superchecker_list = project.review_supercheckers.all()
        anno_ids = [
            name.id
            for name in anno_list
            if (name.participation_type in participation_types)
        ]
        reviewer_ids = [
            name.id
            for name in reviewer_list
            if (name.participation_type in participation_types)
        ]
        superchecker_ids = [
            name.id
            for name in superchecker_list
            if (name.participation_type in participation_types)
        ]
        ws_anno_list.extend(anno_ids)
        ws_reviewer_list.extend(reviewer_ids)
        ws_superchecker_list.extend(superchecker_ids)

    ws_anno_list = list(set(ws_anno_list))
    ws_reviewer_list = list(set(ws_reviewer_list))
    ws_superchecker_list = list(set(ws_superchecker_list))

    final_reports = []

    for id in ws_anno_list:
        anno_projs = proj_objs.filter(annotators=id)
        user_projs_ids = [user_proj.id for user_proj in anno_projs]
        annotate_result = get_all_annotation_reports(
            user_projs_ids,
            id,
            project_type,
            start_date,
            end_date,
        )
        final_reports.append(annotate_result)

    for id in ws_reviewer_list:
        review_projs = proj_objs.filter(annotation_reviewers=id)
        user_projs_ids = [
            user_proj.id
            for user_proj in review_projs
            # if user_proj.project_stage > ANNOTATION_STAGE
        ]
        review_result = get_all_review_reports(
            user_projs_ids,
            id,
            project_type,
            start_date,
            end_date,
        )
        final_reports.append(review_result)

    for id in ws_superchecker_list:
        supercheck_projs = proj_objs.filter(review_supercheckers=id)
        user_projs_ids = [
            user_proj.id
            for user_proj in supercheck_projs
            # if user_proj.project_stage > REVIEW_STAGE
        ]
        supercheck_result = get_all_supercheck_reports(
            user_projs_ids,
            id,
            project_type,
            start_date,
            end_date,
        )
        final_reports.append(supercheck_result)

    final_reports = sorted(final_reports, key=lambda x: x["Name"], reverse=False)

    df = pd.DataFrame.from_dict(final_reports)

    content = df.to_csv(index=False)
    content_type = "text/csv"
    filename = f"{workspace.workspace_name}_user_analytics.csv"

    participation_types = [
        "Full Time"
        if participation_type == 1
        else "Part Time"
        if participation_type == 2
        else "Contract Basis"
        if participation_type == 4
        else "N/A"
        for participation_type in participation_types
    ]
    participation_types_string = ", ".join(participation_types)

    message = (
        "Dear "
        + str(user.username)
        + ",\nYour user payment reports for the workspace "
        + f"{workspace.workspace_name}"
        + " are ready.\n Thanks for contributing on Shoonya!"
        + "\nProject Type: "
        + f"{project_type}"
        + "\nParticipation Types: "
        + f"{participation_types_string}"
        + (
            "\nStart Date: " + f"{start_date}" + "\nEnd Date: " + f"{end_date}"
            if start_date
            else ""
        )
    )

    email = EmailMessage(
        f"{workspace.workspace_name}" + " Payment Reports",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        attachments=[(filename, content, content_type)],
    )
    email.send()
