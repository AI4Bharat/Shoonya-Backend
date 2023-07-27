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
from .models import Organization
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
    project_type=None,
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

    submitted_tasks = Annotation.objects.filter(
        annotation_status="labeled",
        task__project_id__in=proj_ids,
        annotation_type=ANNOTATOR_ANNOTATION,
        completed_by=userid,
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
    elif project_type in get_audio_project_types():
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
    }

    if project_type in get_audio_project_types():
        del result["Word Count"]
    else:
        del result["Total Segments Duration"]
        del result["Total Raw Audio Duration"]

    return result


def get_all_review_reports(
    proj_ids,
    userid,
    project_type=None,
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
    elif project_type in get_audio_project_types():
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
    }

    if project_type in get_audio_project_types():
        del result["Word Count"]
    else:
        del result["Total Segments Duration"]
        del result["Total Raw Audio Duration"]

    return result


def get_all_supercheck_reports(proj_ids, userid, project_type=None):
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

    submitted_tasks = Annotation.objects.filter(
        annotation_status__in=["validated", "validated_with_changes", "rejected"],
        task__project_id__in=proj_ids,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
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
    elif project_type in get_audio_project_types():
        for anno in submitted_tasks:
            try:
                validated_audio_duration_list.append(
                    get_audio_transcription_duration(anno.result)
                )
                validated_audio_duration_list.append(anno.task.data["audio_duration"])
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
    }

    if project_type in get_audio_project_types():
        del result["Word Count"]
    else:
        del result["Total Segments Duration"]
        del result["Total Raw Audio Duration"]

    return result


@shared_task()
def send_user_reports_mail_org(org_id, user_id, project_type, participation_types):
    """Function to generate CSV of organization user reports and send mail to the owner/admin

    Args:
        org_id (int): ID of the organization
        user_id (int): ID of the user requesting the report
        project_type (str): Type of project
        participation_types (list): User participation types
    """

    user = User.objects.get(id=user_id)
    organization = Organization.objects.get(pk=org_id)
    proj_objs = Project.objects.filter(
        organization_id=org_id, project_type=project_type
    )

    org_anno_list = []
    org_reviewer_list = []
    org_superchecker_list = []
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
        org_anno_list.extend(anno_ids)
        org_reviewer_list.extend(reviewer_ids)
        org_superchecker_list.extend(superchecker_ids)

    org_anno_list = list(set(org_anno_list))
    org_reviewer_list = list(set(org_reviewer_list))
    org_superchecker_list = list(set(org_superchecker_list))

    final_reports = []

    for id in org_anno_list:
        anno_projs = proj_objs.filter(annotators=id)
        user_projs_ids = [user_proj.id for user_proj in anno_projs]
        annotate_result = get_all_annotation_reports(
            user_projs_ids,
            id,
            project_type,
        )
        final_reports.append(annotate_result)

    for id in org_reviewer_list:
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
        )
        final_reports.append(review_result)

    for id in org_superchecker_list:
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
        )
        final_reports.append(supercheck_result)

    final_reports = sorted(final_reports, key=lambda x: x["Name"], reverse=False)

    df = pd.DataFrame.from_dict(final_reports)

    content = df.to_csv(index=False)
    content_type = "text/csv"
    filename = f"{organization.title}_user_analytics.csv"

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
        + ",\nYour user payment reports for "
        + f"{organization.title}"
        + " are ready.\n Thanks for contributing on Shoonya!"
        + "\nProject Type: "
        + f"{project_type}"
        + "\nParticipation Types: "
        + f"{participation_types_string}"
    )

    email = EmailMessage(
        f"{organization.title}" + " Payment Reports",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        attachments=[(filename, content, content_type)],
    )
    email.send()
