import datetime
from dateutil.relativedelta import relativedelta
from celery import shared_task
import pandas as pd
from django.conf import settings
from django.core.mail import EmailMessage
from tasks.views import SentenceOperationViewSet

from tasks.models import (
    Task,
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
    get_audio_segments_count,
    ocr_word_count,
)
from workspaces.tasks import (
    un_pack_annotation_tasks,
)
from django.db.models import Q


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
    elif "OCRTranscription" in project_type:
        for anno in submitted_tasks:
            total_word_count_list.append(ocr_word_count(anno.result))
    elif (
        project_type in get_audio_project_types() or project_type == "AllAudioProjects"
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

    if project_type in get_audio_project_types() or project_type == "AllAudioProjects":
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
    elif "OCRTranscription" in project_type:
        for anno in submitted_tasks:
            total_word_count_list.append(ocr_word_count(anno.result))
    elif (
        project_type in get_audio_project_types() or project_type == "AllAudioProjects"
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

    if project_type in get_audio_project_types() or project_type == "AllAudioProjects":
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
    elif "OCRTranscription" in project_type:
        for anno in submitted_tasks:
            validated_word_count_list.append(ocr_word_count(anno.result))
    elif (
        project_type in get_audio_project_types() or project_type == "AllAudioProjects"
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

    if project_type in get_audio_project_types() or project_type == "AllAudioProjects":
        del result["Word Count"]
    else:
        del result["Total Segments Duration"]
        del result["Total Raw Audio Duration"]

    return result


@shared_task(queue="reports")
def send_user_reports_mail_org(
    org_id,
    user_id,
    project_type,
    participation_types=None,
    start_date=None,
    end_date=None,
    period=None,
):
    """Function to generate CSV of organization user reports and send mail to the owner/admin

    Args:
        org_id (int): ID of the organization.
        user_id (int): ID of the user requesting the report.
        project_type (str): Type of project.
        participation_types (list, optional): User participation types. Defaults to [1, 2, 4].
        start_date (datetime, optional): Start date of the report. Defaults to None.
        end_date (datetime, optional): End date of the report. Defaults to None.
        period (str, optional): Period of the report. Defaults to None.
    """

    user = User.objects.get(id=user_id)
    organization = Organization.objects.get(pk=org_id)
    if project_type == "AllAudioProjects":
        proj_objs = Project.objects.filter(
            organization_id=org_id,
            project_type__in=[
                "AudioTranscription",
                "AudioTranscriptionEditing",
                "AcousticNormalisedTranscriptionEditing",
            ],
        )
    else:
        proj_objs = Project.objects.filter(
            organization_id=org_id, project_type=project_type
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
            start_date,
            end_date,
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
            start_date,
            end_date,
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
            start_date,
            end_date,
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
        + (
            "\nStart Date: " + f"{start_date}" + "\nEnd Date: " + f"{end_date}"
            if start_date
            else ""
        )
    )

    email = EmailMessage(
        f"{organization.title}" + " Payment Reports",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        attachments=[(filename, content, content_type)],
    )
    email.send()


def get_counts(
    pk,
    annotator,
    project_type,
    start_date,
    end_date,
    is_translation_project,
    project_progress_stage,
    tgt_language=None,
):
    annotated_tasks = 0
    accepted = 0
    to_be_revised = 0
    accepted_wt_minor_changes = 0
    accepted_wt_major_changes = 0
    labeled = 0
    if tgt_language == None:
        if project_progress_stage == None:
            projects_objs = Project.objects.filter(
                organization_id_id=pk,
                project_type=project_type,
                annotators=annotator,
            )
        else:
            projects_objs = Project.objects.filter(
                organization_id_id=pk,
                project_type=project_type,
                project_stage=project_progress_stage,
                annotators=annotator,
            )
    else:
        if project_progress_stage == None:
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
                project_stage=project_progress_stage,
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
    total_raw_duration = 0

    if project_progress_stage != None and project_progress_stage > ANNOTATION_STAGE:
        (
            accepted,
            to_be_revised,
            accepted_wt_minor_changes,
            accepted_wt_major_changes,
            labeled,
            avg_lead_time,
            total_word_count,
            total_duration,
            total_raw_duration,
            avg_segment_duration,
            avg_segments_per_task,
        ) = un_pack_annotation_tasks(
            proj_ids,
            annotator,
            start_date,
            end_date,
            is_translation_project,
            project_type,
        )

    else:
        labeled_annotations = Annotation.objects.filter(
            task__project_id__in=proj_ids,
            annotation_status="labeled",
            annotation_type=ANNOTATOR_ANNOTATION,
            updated_at__range=[start_date, end_date],
            completed_by=annotator,
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
        if is_translation_project or project_type == "SemanticTextualSimilarity_Scale5":
            total_word_count_list = []
            for each_task in labeled_annotations:
                try:
                    total_word_count_list.append(each_task.task.data["word_count"])
                except:
                    pass

            total_word_count = sum(total_word_count_list)
        elif "OCRTranscription" in project_type:
            total_word_count = 0
            for each_anno in labeled_annotations:
                total_word_count += ocr_word_count(each_anno.result)

        total_duration = "0:00:00"
        avg_segment_duration = 0
        avg_segments_per_task = 0
        if project_type in get_audio_project_types():
            total_duration_list = []
            total_raw_duration_list = []
            total_audio_segments_list = []
            for each_task in labeled_annotations:
                try:
                    total_duration_list.append(
                        get_audio_transcription_duration(each_task.result)
                    )
                    total_audio_segments_list.append(
                        get_audio_segments_count(each_task.result)
                    )
                    total_raw_duration_list.append(
                        each_task.task.data["audio_duration"]
                    )
                except:
                    pass
            total_duration = convert_seconds_to_hours(sum(total_duration_list))
            total_raw_duration = convert_seconds_to_hours(sum(total_raw_duration_list))
            total_audio_segments = sum(total_audio_segments_list)
            try:
                avg_segment_duration = total_duration / total_audio_segments
                avg_segments_per_task = total_audio_segments / len(labeled_annotations)
            except:
                avg_segment_duration = 0
                avg_segments_per_task = 0

    total_skipped_tasks = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        annotation_status="skipped",
        annotation_type=ANNOTATOR_ANNOTATION,
        updated_at__range=[start_date, end_date],
        completed_by=annotator,
    )
    all_pending_tasks_in_project = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        annotation_status="unlabeled",
        annotation_type=ANNOTATOR_ANNOTATION,
        updated_at__range=[start_date, end_date],
        completed_by=annotator,
    )

    all_draft_tasks_in_project = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        annotation_status="draft",
        annotation_type=ANNOTATOR_ANNOTATION,
        updated_at__range=[start_date, end_date],
        completed_by=annotator,
    )

    return (
        assigned_tasks,
        annotated_tasks,
        accepted,
        to_be_revised,
        accepted_wt_minor_changes,
        accepted_wt_major_changes,
        labeled,
        avg_lead_time,
        total_skipped_tasks.count(),
        all_pending_tasks_in_project.count(),
        all_draft_tasks_in_project.count(),
        project_count,
        no_of_workspaces_objs,
        total_word_count,
        total_duration,
        total_raw_duration,
        avg_segment_duration,
        avg_segments_per_task,
    )


def get_translation_quality_reports(
    pk,
    annotator,
    project_type,
    start_date,
    end_date,
    project_progress_stage=None,
    tgt_language=None,
):
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


@shared_task(queue="reports")
def send_project_analytics_mail_org(
    org_id,
    tgt_language,
    project_type,
    user_id,
    sort_by_column_name,
    descending_order,
):
    organization = Organization.objects.get(pk=org_id)
    user = User.objects.get(id=user_id)

    if sort_by_column_name == None:
        sort_by_column_name = "User Name"

    if descending_order == None:
        descending_order = False

    if tgt_language == None:
        selected_language = "-"
        projects_obj = Project.objects.filter(
            organization_id=org_id, project_type=project_type
        )
    else:
        selected_language = tgt_language
        projects_obj = Project.objects.filter(
            organization_id=org_id,
            tgt_language=tgt_language,
            project_type=project_type,
        )
    final_result = []
    if projects_obj.count() != 0:
        for proj in projects_obj:
            proj_manager = [
                manager.get_username() for manager in proj.workspace_id.managers.all()
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
            annotators_list = [user_.get_username() for user_ in proj.annotators.all()]
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
                            task=each_task, annotation_type=SUPER_CHECKER_ANNOTATION
                        )[0]
                        total_word_superchecked_count_list.append(
                            ocr_word_count(supercheck_annotation.result)
                        )
                    except:
                        pass

            total_word_annotated_count = sum(total_word_annotated_count_list)
            total_word_reviewed_count = sum(total_word_reviewed_count_list)
            total_word_exported_count = sum(total_word_exported_count_list)
            total_word_superchecked_count = sum(total_word_superchecked_count_list)

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
                            get_audio_transcription_duration(annotate_annotation.result)
                        )
                    except:
                        pass

                for each_task in reviewed_tasks:
                    try:
                        review_annotation = Annotation.objects.filter(
                            task=each_task, parent_annotation_id__isnull=False
                        )[0]
                        total_duration_reviewed_count_list.append(
                            get_audio_transcription_duration(review_annotation.result)
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
                            task=each_task, annotation_type=SUPER_CHECKER_ANNOTATION
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

    df = pd.DataFrame.from_dict(final_result)

    content = df.to_csv(index=False)
    content_type = "text/csv"
    filename = f"{organization.title}_project_analytics.csv"

    message = (
        "Dear "
        + str(user.username)
        + ",\nYour project analysis reports for "
        + f"{organization.title}"
        + " are ready.\n Thanks for contributing on Shoonya!"
        + "\nProject Type: "
        + f"{project_type}"
    )

    email = EmailMessage(
        f"{organization.title}" + " Project Analytics",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        attachments=[(filename, content, content_type)],
    )
    email.send()


@shared_task(queue="reports")
def send_user_analytics_mail_org(
    org_id,
    tgt_language,
    project_type,
    user_id,
    sort_by_column_name,
    descending_order,
    pk,
    start_date,
    end_date,
    is_translation_project,
    project_progress_stage,
    final_reports,
):
    organization = Organization.objects.get(pk=org_id)
    user = User.objects.get(id=user_id)
    if not final_reports:
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
    else:
        final_result = final_reports

    df = pd.DataFrame.from_dict(final_result)

    content = df.to_csv(index=False)
    content_type = "text/csv"
    filename = f"{organization.title}_user_analytics.csv"

    message = (
        "Dear "
        + str(user.username)
        + ",\nYour user analysis reports for "
        + f"{organization.title}"
        + " are ready.\n Thanks for contributing on Shoonya!"
        + "\nProject Type: "
        + f"{project_type}"
    )

    email = EmailMessage(
        f"{organization.title}" + " User Analytics",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        attachments=[(filename, content, content_type)],
    )
    email.send()
