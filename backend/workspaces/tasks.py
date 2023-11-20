import datetime
from dateutil.relativedelta import relativedelta
from celery import shared_task
import pandas as pd
from django.conf import settings
from django.core.mail import EmailMessage
from organizations.models import Organization
from tasks.models import Task
from django.db.models import Q

from tasks.models import (
    Annotation,
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
)
from .models import Workspace
from users.models import User
from projects.models import Project, ANNOTATION_STAGE, REVIEW_STAGE, SUPERCHECK_STAGE
from users.utils import get_role_name
from projects.utils import (
    convert_seconds_to_hours,
    get_audio_project_types,
    get_audio_transcription_duration,
    calculate_word_error_rate_between_two_audio_transcription_annotation,
    get_audio_segments_count,
    ocr_word_count,
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
    if project_type == "AllAudioProjects":
        proj_objs = Project.objects.filter(
            workspace_id=ws_id,
            project_type__in=[
                "AudioTranscription",
                "AudioTranscriptionEditing",
                "AcousticNormalisedTranscriptionEditing",
            ],
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


@shared_task(queue="reports")
def send_project_analysis_reports_mail_ws(
    pk,
    user_id,
    tgt_language,
    project_type,
):
    ws = Workspace.objects.get(pk=pk)
    user = User.objects.get(id=user_id)
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
                [annotator for annotator in annotators_list if annotator not in owners]
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
            total_word_error_rate_rs_list = []
            total_word_error_rate_ar_list = []
            total_raw_duration_list = []
            if project_type in get_audio_project_types():
                for each_task in labeled_tasks:
                    try:
                        annotate_annotation = Annotation.objects.filter(
                            task=each_task,
                            annotation_type=ANNOTATOR_ANNOTATION,
                            annotation_status__in=["labeled"],
                        )[0]
                        total_duration_annotated_count_list.append(
                            get_audio_transcription_duration(annotate_annotation.result)
                        )
                    except:
                        pass

                for each_task in reviewed_tasks:
                    try:
                        review_annotation = Annotation.objects.filter(
                            task=each_task,
                            annotation_type=REVIEWER_ANNOTATION,
                            annotation_status__in=[
                                "accepted",
                                "accepted_with_minor_changes",
                                "accepted_with_major_changes",
                            ],
                        )[0]
                        total_duration_reviewed_count_list.append(
                            get_audio_transcription_duration(review_annotation.result)
                        )
                        total_word_error_rate_ar_list.append(
                            calculate_word_error_rate_between_two_audio_transcription_annotation(
                                review_annotation.result,
                                review_annotation.parent_annotation.result,
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
                            annotation_status__in=[
                                "validated",
                                "validated_with_changes",
                            ],
                        )[0]
                        total_duration_superchecked_count_list.append(
                            get_audio_transcription_duration(
                                supercheck_annotation.result
                            )
                        )
                        total_word_error_rate_rs_list.append(
                            calculate_word_error_rate_between_two_audio_transcription_annotation(
                                supercheck_annotation.result,
                                supercheck_annotation.parent_annotation.result,
                            )
                        )
                    except:
                        pass

                for each_task in all_tasks:
                    try:
                        total_raw_duration_list.append(each_task.data["audio_duration"])
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

            total_raw_duration = convert_seconds_to_hours(sum(total_raw_duration_list))

            if len(total_word_error_rate_rs_list) > 0:
                avg_word_error_rate_rs = sum(total_word_error_rate_rs_list) / len(
                    total_word_error_rate_rs_list
                )
            else:
                avg_word_error_rate_rs = 0
            if len(total_word_error_rate_ar_list) > 0:
                avg_word_error_rate_ar = sum(total_word_error_rate_ar_list) / len(
                    total_word_error_rate_ar_list
                )
            else:
                avg_word_error_rate_ar = 0

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
                "Project Type": project_type,
                "No .of Annotators Assigned": no_of_annotators_assigned,
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
                "Total Raw Audio Duration": total_raw_duration,
                "Annotated Tasks Word Count": total_word_annotated_count,
                "Reviewed Tasks Word Count": total_word_reviewed_count,
                "Exported Tasks Word Count": total_word_exported_count,
                "SuperChecked Tasks Word Count": total_word_superchecked_count,
                "Average Word Error Rate A/R": round(avg_word_error_rate_ar, 2),
                "Average Word Error Rate R/S": round(avg_word_error_rate_rs, 2),
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
                del result["Total Raw Audio Duration"]
                del result["Average Word Error Rate A/R"]
                del result["Average Word Error Rate R/S"]
            else:
                del result["Annotated Tasks Word Count"]
                del result["Reviewed Tasks Word Count"]
                del result["Exported Tasks Word Count"]
                del result["SuperChecked Tasks Word Count"]
                del result["Annotated Tasks Audio Duration"]
                del result["Reviewed Tasks Audio Duration"]
                del result["Exported Tasks Audio Duration"]
                del result["SuperChecked Tasks Audio Duration"]
                del result["Total Raw Audio Duration"]
                del result["Average Word Error Rate A/R"]
                del result["Average Word Error Rate R/S"]

            final_result.append(result)

    df = pd.DataFrame.from_dict(final_result)

    content = df.to_csv(index=False)
    content_type = "text/csv"
    filename = f"{ws.workspace_name}_project_analytics.csv"

    message = (
        "Dear "
        + str(user.username)
        + ",\nYour project analysis reports for the workspace "
        + f"{ws.workspace_name}"
        + " are ready.\nThanks for contributing on Shoonya!"
        + "\nProject Type: "
        + f"{project_type}"
    )

    email = EmailMessage(
        f"{ws.workspace_name}" + " Project Analytics",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        attachments=[(filename, content, content_type)],
    )
    email.send()


def get_supercheck_reports(proj_ids, userid, start_date, end_date, project_type=None):
    user = User.objects.get(id=userid)
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

    superchecker_languages = user.languages

    total_tasks = Task.objects.filter(project_id__in=proj_ids, super_check_user=userid)

    total_task_count = total_tasks.count()

    validated_objs = Annotation.objects.filter(
        annotation_status="validated",
        task__project_id__in=proj_ids,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    validated_objs_count = validated_objs.count()

    validated_with_changes_objs = Annotation.objects.filter(
        annotation_status="validated_with_changes",
        task__project_id__in=proj_ids,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    validated_with_changes_objs_count = validated_with_changes_objs.count()

    unvalidated_objs = Annotation.objects.filter(
        annotation_status="unvalidated",
        task__project_id__in=proj_ids,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    unvalidated_objs_count = unvalidated_objs.count()

    rejected_objs = Annotation.objects.filter(
        annotation_status="rejected",
        task__project_id__in=proj_ids,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    rejected_objs_count = rejected_objs.count()

    skipped_objs = Annotation.objects.filter(
        annotation_status="skipped",
        task__project_id__in=proj_ids,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    skipped_objs_count = skipped_objs.count()

    draft_objs = Annotation.objects.filter(
        annotation_status="draft",
        task__project_id__in=proj_ids,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    draft_objs_count = draft_objs.count()

    total_sup_annos = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    total_superchecked_annos = total_sup_annos.filter(task__task_status="super_checked")

    total_rejection_loop_value_list = [
        anno.task.revision_loop_count["super_check_count"] for anno in total_sup_annos
    ]
    if len(total_rejection_loop_value_list) > 0:
        avg_rejection_loop_value = sum(total_rejection_loop_value_list) / len(
            total_rejection_loop_value_list
        )
    else:
        avg_rejection_loop_value = 0
    tasks_rejected_max_times = 0
    for anno in total_sup_annos:
        if (
            anno.task.revision_loop_count["super_check_count"]
            >= anno.task.project_id.revision_loop_count
        ):
            tasks_rejected_max_times += 1

    if project_type != None:
        project_type_lower = project_type.lower()
        is_translation_project = True if "translation" in project_type_lower else False

        validated_word_count_list = []
        validated_with_changes_word_count_list = []
        rejected_word_count_list = []
        validated_audio_duration_list = []
        validated_with_changes_audio_duration_list = []
        rejected_audio_duration_list = []
        total_raw_audio_duration_list = []
        total_word_error_rate_rs_list = []
        if is_translation_project or project_type == "SemanticTextualSimilarity_Scale5":
            for anno in validated_objs:
                try:
                    validated_word_count_list.append(anno.task.data["word_count"])
                except:
                    pass
            for anno in validated_with_changes_objs:
                try:
                    validated_with_changes_word_count_list.append(
                        anno.task.data["word_count"]
                    )
                except:
                    pass
            for anno in rejected_objs:
                try:
                    rejected_word_count_list.append(anno.task.data["word_count"])
                except:
                    pass
        elif "OCRTranscription" in project_type:
            for anno in validated_objs:
                validated_word_count_list.append(ocr_word_count(anno.result))
            for anno in validated_with_changes_objs:
                validated_with_changes_word_count_list.append(
                    ocr_word_count(anno.result)
                )
            for anno in rejected_objs:
                rejected_word_count_list.append(ocr_word_count(anno.result))
        elif project_type in get_audio_project_types():
            for anno in validated_objs:
                try:
                    validated_audio_duration_list.append(
                        get_audio_transcription_duration(anno.result)
                    )
                except:
                    pass
            for anno in validated_with_changes_objs:
                try:
                    validated_with_changes_audio_duration_list.append(
                        get_audio_transcription_duration(anno.result)
                    )
                except:
                    pass
            for anno in rejected_objs:
                try:
                    rejected_audio_duration_list.append(
                        get_audio_transcription_duration(anno.result)
                    )
                except:
                    pass
            for anno in total_sup_annos:
                try:
                    total_word_error_rate_rs_list.append(
                        calculate_word_error_rate_between_two_audio_transcription_annotation(
                            anno.result, anno.parent_annotation.result
                        )
                    )
                    total_raw_audio_duration_list.append(
                        anno.task.data["audio_duration"]
                    )
                except:
                    pass
            for anno in total_superchecked_annos:
                try:
                    total_word_error_rate_rs_list.append(
                        calculate_word_error_rate_between_two_audio_transcription_annotation(
                            anno.result, anno.parent_annotation.result
                        )
                    )
                except:
                    pass

        validated_word_count = sum(validated_word_count_list)
        validated_with_changes_word_count = sum(validated_with_changes_word_count_list)
        rejected_word_count = sum(rejected_word_count_list)
        validated_audio_duration = convert_seconds_to_hours(
            sum(validated_audio_duration_list)
        )
        validated_with_changes_audio_duration = convert_seconds_to_hours(
            sum(validated_with_changes_audio_duration_list)
        )
        rejected_audio_duration = convert_seconds_to_hours(
            sum(rejected_audio_duration_list)
        )
        total_raw_audio_duration = convert_seconds_to_hours(
            sum(total_raw_audio_duration_list)
        )
        if len(total_word_error_rate_rs_list) > 0:
            avg_word_error_rate = sum(total_word_error_rate_rs_list) / len(
                total_word_error_rate_rs_list
            )
        else:
            avg_word_error_rate = 0

    result = {
        "SuperChecker Name": userName,
        "Email": email,
        "Participation Type": participation_type,
        "User Role": role,
        "Language": superchecker_languages,
        "Assigned": total_task_count,
        "Validated": validated_objs_count,
        "Validated With Changes": validated_with_changes_objs_count,
        "Rejected": rejected_objs_count,
        "Unvalidated": unvalidated_objs_count,
        "Skipped": skipped_objs_count,
        "Draft": draft_objs_count,
        "Average Rejection Loop Value": round(avg_rejection_loop_value, 2),
        "Tasks Rejected Maximum Time": tasks_rejected_max_times,
    }

    if project_type != None:
        if is_translation_project or project_type in [
            "SemanticTextualSimilarity_Scale5",
            "OCRTranscriptionEditing",
            "OCRTranscription",
        ]:
            result["Validated Word Count"] = validated_word_count
            result[
                "Validated With Changes Word Count"
            ] = validated_with_changes_word_count
            result["Rejected Word Count"] = rejected_word_count
        elif project_type in get_audio_project_types():
            result["Validated Audio Duration"] = validated_audio_duration
            result[
                "Validated With Changes Audio Duration"
            ] = validated_with_changes_audio_duration
            result["Rejected Audio Duration"] = rejected_audio_duration
            result["Total Raw Audio Duration"] = total_raw_audio_duration
            result["Average Word Error Rate R/S"] = round(avg_word_error_rate, 2)

    return result


def get_review_reports(
    proj_ids,
    userid,
    start_date,
    end_date,
    project_progress_stage=None,
    project_type=None,
):
    user = User.objects.get(id=userid)
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

    reviewer_languages = user.languages

    total_tasks = Task.objects.filter(project_id__in=proj_ids, review_user=userid)

    total_task_count = total_tasks.count()

    accepted_tasks = Annotation.objects.filter(
        annotation_status="accepted",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    accepted_objs_count = accepted_tasks.count()

    superchecked_accepted_annos = Annotation.objects.filter(
        parent_annotation_id__in=accepted_tasks,
        annotation_status__in=[
            "validated",
            "validated_with_changes",
        ],
    )

    superchecked_accepted_annos_count = superchecked_accepted_annos.count()

    accepted_objs_only = accepted_objs_count - superchecked_accepted_annos_count

    acceptedwt_minor_change_tasks = Annotation.objects.filter(
        annotation_status="accepted_with_minor_changes",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    minor_changes = acceptedwt_minor_change_tasks.count()

    superchecked_minor_annos = Annotation.objects.filter(
        parent_annotation_id__in=acceptedwt_minor_change_tasks,
        annotation_status__in=[
            "validated",
            "validated_with_changes",
        ],
    )

    superchecked_minor_annos_count = superchecked_minor_annos.count()

    minor_objs_only = minor_changes - superchecked_minor_annos_count

    acceptedwt_major_change_tasks = Annotation.objects.filter(
        annotation_status="accepted_with_major_changes",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    major_changes = acceptedwt_major_change_tasks.count()

    superchecked_major_annos = Annotation.objects.filter(
        parent_annotation_id__in=acceptedwt_major_change_tasks,
        annotation_status__in=[
            "validated",
            "validated_with_changes",
        ],
    )

    superchecked_major_annos_count = superchecked_major_annos.count()

    major_objs_only = major_changes - superchecked_major_annos_count

    labeled_tasks = Task.objects.filter(
        project_id__in=proj_ids, review_user=userid, task_status="annotated"
    )
    labeled_tasks_count = labeled_tasks.count()

    to_be_revised_tasks = Annotation.objects.filter(
        annotation_status="to_be_revised",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    to_be_revised_tasks_count = to_be_revised_tasks.count()

    skipped_tasks = Annotation.objects.filter(
        annotation_status="skipped",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    skipped_tasks_count = skipped_tasks.count()

    draft_tasks = Annotation.objects.filter(
        annotation_status="draft",
        task__project_id__in=proj_ids,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    draft_tasks_count = draft_tasks.count()

    total_rev_annos = Annotation.objects.filter(
        task__project_id__in=proj_ids,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    total_rev_sup_annos = Annotation.objects.filter(
        parent_annotation__in=total_rev_annos
    )

    total_superchecked_annos = total_rev_sup_annos.filter(
        task__task_status="super_checked"
    )

    total_rejection_loop_value_list = [
        anno.task.revision_loop_count["super_check_count"]
        for anno in total_rev_sup_annos
    ]
    if len(total_rejection_loop_value_list) > 0:
        avg_rejection_loop_value = sum(total_rejection_loop_value_list) / len(
            total_rejection_loop_value_list
        )
    else:
        avg_rejection_loop_value = 0
    tasks_rejected_max_times = 0
    for anno in total_rev_sup_annos:
        if (
            anno.task.revision_loop_count["super_check_count"]
            >= anno.task.project_id.revision_loop_count
        ):
            tasks_rejected_max_times += 1

    if project_type != None:
        project_type_lower = project_type.lower()
        is_translation_project = True if "translation" in project_type_lower else False
        total_rev_annos_accepted = total_rev_annos.filter(
            annotation_status__in=[
                "accepted",
                "accepted_with_minor_changes",
                "accepted_with_major_changes",
            ]
        )
        total_audio_duration_list = []
        total_raw_audio_duration_list = []
        total_word_count_list = []
        total_word_error_rate_ar_list = []
        total_word_error_rate_rs_list = []
        if is_translation_project or project_type == "SemanticTextualSimilarity_Scale5":
            for anno in total_rev_annos_accepted:
                total_word_count_list.append(anno.task.data["word_count"])
        elif "OCRTranscription" in project_type:
            for anno in total_rev_annos_accepted:
                total_word_count_list.append(ocr_word_count(anno.result))
        elif project_type in get_audio_project_types():
            for anno in total_rev_annos_accepted:
                try:
                    total_audio_duration_list.append(
                        get_audio_transcription_duration(anno.result)
                    )
                    total_raw_audio_duration_list.append(
                        anno.task.data["audio_duration"]
                    )
                    total_word_error_rate_ar_list.append(
                        calculate_word_error_rate_between_two_audio_transcription_annotation(
                            anno.result, anno.parent_annotation.result
                        )
                    )
                except:
                    pass
            for anno in total_superchecked_annos:
                try:
                    total_word_error_rate_rs_list.append(
                        calculate_word_error_rate_between_two_audio_transcription_annotation(
                            anno.result, anno.parent_annotation.result
                        )
                    )
                except:
                    pass

        total_word_count = sum(total_word_count_list)
        total_audio_duration = convert_seconds_to_hours(sum(total_audio_duration_list))
        total_raw_audio_duration = convert_seconds_to_hours(
            sum(total_raw_audio_duration_list)
        )
        if len(total_word_error_rate_ar_list) > 0:
            avg_word_error_rate_ar = sum(total_word_error_rate_ar_list) / len(
                total_word_error_rate_ar_list
            )
        else:
            avg_word_error_rate_ar = 0
        if len(total_word_error_rate_rs_list) > 0:
            avg_word_error_rate_rs = sum(total_word_error_rate_rs_list) / len(
                total_word_error_rate_rs_list
            )
        else:
            avg_word_error_rate_rs = 0

    if project_progress_stage == SUPERCHECK_STAGE:
        annotations_of_superchecker_validated = Annotation.objects.filter(
            task__project_id__in=proj_ids,
            annotation_status="validated",
            annotation_type=SUPER_CHECKER_ANNOTATION,
            parent_annotation__updated_at__range=[start_date, end_date],
        )
        parent_anno_ids = [
            ann.parent_annotation_id for ann in annotations_of_superchecker_validated
        ]
        accepted_validated_tasks = Annotation.objects.filter(
            id__in=parent_anno_ids,
            completed_by=userid,
        )

        annotations_of_superchecker_validated_with_changes = Annotation.objects.filter(
            task__project_id__in=proj_ids,
            annotation_status="validated_with_changes",
            annotation_type=SUPER_CHECKER_ANNOTATION,
            parent_annotation__updated_at__range=[start_date, end_date],
        )
        parent_anno_ids = [
            ann.parent_annotation_id
            for ann in annotations_of_superchecker_validated_with_changes
        ]
        accepted_validated_with_changes_tasks = Annotation.objects.filter(
            id__in=parent_anno_ids,
            completed_by=userid,
        )

        annotations_of_superchecker_rejected = Annotation.objects.filter(
            task__project_id__in=proj_ids,
            annotation_status="rejected",
            annotation_type=SUPER_CHECKER_ANNOTATION,
            parent_annotation__updated_at__range=[start_date, end_date],
        )
        parent_anno_ids = [
            ann.parent_annotation_id for ann in annotations_of_superchecker_rejected
        ]
        accepted_rejected_tasks = Annotation.objects.filter(
            id__in=parent_anno_ids, completed_by=userid, annotation_status="rejected"
        )

        result = {
            "Reviewer Name": userName,
            "Email": email,
            "Participation Type": participation_type,
            "User Role": role,
            "Language": reviewer_languages,
            "Assigned": total_task_count,
            "Accepted": accepted_objs_only,
            "Accepted With Minor Changes": minor_objs_only,
            "Accepted With Major Changes": major_objs_only,
            "Unreviewed": labeled_tasks_count,
            "To Be Revised": to_be_revised_tasks_count,
            "Skipped": skipped_tasks_count,
            "Draft": draft_tasks_count,
            "Validated": accepted_validated_tasks.count(),
            "Validated With Changes": accepted_validated_with_changes_tasks.count(),
            "Rejected": accepted_rejected_tasks.count(),
            "Average Rejection Loop Value": round(avg_rejection_loop_value, 2),
            "Tasks Rejected Maximum Time": tasks_rejected_max_times,
        }

        if project_type != None:
            if is_translation_project or project_type in [
                "SemanticTextualSimilarity_Scale5",
                "OCRTranscriptionEditing",
                "OCRTranscription",
            ]:
                result["Total Word Count"] = total_word_count
            elif project_type in get_audio_project_types():
                result["Total Segments Duration"] = total_audio_duration
                result["Total Raw Audio Duration"] = total_raw_audio_duration
                result["Average Word Error Rate A/R"] = round(avg_word_error_rate_ar, 2)
                result["Average Word Error Rate R/S"] = round(avg_word_error_rate_rs, 2)

        return result

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
        "Average Rejection Loop Value": round(avg_rejection_loop_value, 2),
        "Tasks Rejected Maximum Time": tasks_rejected_max_times,
    }

    if project_type != None:
        if is_translation_project or project_type in [
            "SemanticTextualSimilarity_Scale5",
            "OCRTranscriptionEditing",
            "OCRTranscription",
        ]:
            result["Total Word Count"] = total_word_count
        elif project_type in get_audio_project_types():
            result["Total Segments Duration"] = total_audio_duration
            result["Total Raw Audio Duration"] = total_raw_audio_duration
            result["Average Word Error Rate A/R"] = round(avg_word_error_rate_ar, 2)
            result["Average Word Error Rate R/S"] = round(avg_word_error_rate_rs, 2)

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
        annotation_type=REVIEWER_ANNOTATION,
        parent_annotation__updated_at__range=[start_date, end_date],
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
        annotation_type=REVIEWER_ANNOTATION,
        parent_annotation__updated_at__range=[start_date, end_date],
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
        annotation_type=REVIEWER_ANNOTATION,
        parent_annotation__updated_at__range=[start_date, end_date],
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
        annotation_type=REVIEWER_ANNOTATION,
        parent_annotation__updated_at__range=[start_date, end_date],
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
        annotation_type=ANNOTATOR_ANNOTATION,
        updated_at__range=[start_date, end_date],
        completed_by=each_annotation_user,
    )
    labeled_annotation_ids = [ann.id for ann in labeled_annotations]

    reviewed_ann = (
        Annotation.objects.filter(parent_annotation_id__in=labeled_annotation_ids)
        .exclude(annotation_status__in=["skipped", "draft"])
        .count()
    )

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
    elif "OCRTranscription" in project_type:
        total_word_count = 0
        for each_anno in labeled_annotations:
            total_word_count += ocr_word_count(each_anno.result)

    total_duration = "0:00:00"
    total_raw_duration = 0.0
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
                total_raw_duration_list.append(each_task.task.data["audio_duration"])
                total_audio_segments_list.append(
                    get_audio_segments_count(each_task.result)
                )
            except:
                pass
        total_duration = convert_seconds_to_hours(sum(total_duration_list))
        total_raw_duration = convert_seconds_to_hours(sum(total_raw_duration_list))
        total_audio_segments = sum(total_audio_segments_list)
        try:
            avg_segment_duration = sum(total_duration_list) / total_audio_segments
            avg_segments_per_task = total_audio_segments / len(
                total_audio_segments_list
            )
        except:
            avg_segment_duration = 0
            avg_segments_per_task = 0

    return (
        accepted.count(),
        to_be_revised.count(),
        accepted_wt_minor_changes.count(),
        accepted_wt_major_changes.count(),
        labeled,
        avg_lead_time,
        total_word_count,
        total_duration,
        total_raw_duration,
        avg_segment_duration,
        avg_segments_per_task,
    )


@shared_task(queue="reports")
def send_user_analysis_reports_mail_ws(
    pk,
    user_id,
    tgt_language,
    project_type,
    project_progress_stage,
    start_date,
    end_date,
    is_translation_project,
    reports_type,
):
    ws = Workspace.objects.get(pk=pk)
    user = User.objects.get(id=user_id)
    final_reports = []

    if reports_type == "review":
        proj_objs = Project.objects.filter(workspace_id=pk)
        if project_type != None:
            proj_objs = proj_objs.filter(project_type=project_type)
        if project_progress_stage == None:
            review_projects = [
                pro for pro in proj_objs if pro.project_stage > ANNOTATION_STAGE
            ]
        elif project_progress_stage in [REVIEW_STAGE, SUPERCHECK_STAGE]:
            review_projects = [
                pro for pro in proj_objs if pro.project_stage == project_progress_stage
            ]

        workspace_reviewer_list = []
        review_projects_ids = []
        for review_project in review_projects:
            reviewer_names_list = review_project.annotation_reviewers.all()
            reviewer_ids = [name.id for name in reviewer_names_list]
            workspace_reviewer_list.extend(reviewer_ids)
            review_projects_ids.append(review_project.id)

        workspace_reviewer_list = list(set(workspace_reviewer_list))

        if (
            user.role == User.ORGANIZATION_OWNER
            or user.role == User.WORKSPACE_MANAGER
            or user.is_superuser
        ):
            for id in workspace_reviewer_list:
                reviewer_projs = Project.objects.filter(
                    workspace_id=pk,
                    annotation_reviewers=id,
                    id__in=review_projects_ids,
                )
                reviewer_projs_ids = [review_proj.id for review_proj in reviewer_projs]

                result = get_review_reports(
                    reviewer_projs_ids,
                    id,
                    start_date,
                    end_date,
                    project_progress_stage,
                    project_type,
                )
                final_reports.append(result)
        elif user_id in workspace_reviewer_list:
            reviewer_projs = Project.objects.filter(
                workspace_id=pk,
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

    elif reports_type == "supercheck":
        proj_objs = Project.objects.filter(workspace_id=pk)
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
            user.role == User.ORGANIZATION_OWNER
            or user.role == User.WORKSPACE_MANAGER
            or user.is_superuser
        ):
            for id in workspace_superchecker_list:
                superchecker_projs = Project.objects.filter(
                    workspace_id=pk,
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
                workspace_id=pk,
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

        user_obj = list(ws.members.all())
        user_mail = [user.get_username() for user in ws.members.all()]
        user_name = [user.username for user in ws.members.all()]
        users_id = [user.id for user in ws.members.all()]

        selected_language = "-"
        for index, each_annotation_user in enumerate(users_id):
            name = user_name[index]
            email = user_mail[index]
            list_of_user_languages = user_obj[index].languages

            if tgt_language != None and tgt_language not in list_of_user_languages:
                continue
            if email == ws_owner or email == org_owner:
                continue
            if tgt_language == None:
                if project_progress_stage == None:
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
                        project_stage=project_progress_stage,
                    )

            else:
                selected_language = tgt_language
                if project_progress_stage == None:
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
                        project_stage=project_progress_stage,
                    )

            project_count = projects_objs.count()
            proj_ids = [eachid["id"] for eachid in projects_objs.values("id")]

            all_tasks_in_project = Task.objects.filter(
                Q(project_id__in=proj_ids) & Q(annotation_users=each_annotation_user)
            )
            assigned_tasks = all_tasks_in_project.count()

            if (
                project_progress_stage != None
                and project_progress_stage > ANNOTATION_STAGE
            ):
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
                    annotation_type=ANNOTATOR_ANNOTATION,
                    updated_at__range=[start_date, end_date],
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
                elif "OCRTranscription" in project_type:
                    total_word_count = 0
                    for each_anno in labeled_annotations:
                        total_word_count += ocr_word_count(each_anno.result)

                total_duration = "0:00:00"
                total_raw_duration = "0:00:00"
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
                    total_raw_duration = convert_seconds_to_hours(
                        sum(total_raw_duration_list)
                    )
                    total_audio_segments = sum(total_audio_segments_list)
                    try:
                        avg_segment_duration = (
                            sum(total_duration_list) / total_audio_segments
                        )
                        avg_segments_per_task = total_audio_segments / len(
                            labeled_annotations
                        )
                    except:
                        avg_segment_duration = 0
                        avg_segments_per_task = 0

            total_skipped_tasks = Annotation.objects.filter(
                task__project_id__in=proj_ids,
                annotation_status="skipped",
                annotation_type=ANNOTATOR_ANNOTATION,
                updated_at__range=[start_date, end_date],
                completed_by=each_annotation_user,
            ).count()
            all_pending_tasks_in_project = Annotation.objects.filter(
                task__project_id__in=proj_ids,
                annotation_status="unlabeled",
                annotation_type=ANNOTATOR_ANNOTATION,
                updated_at__range=[start_date, end_date],
                completed_by=each_annotation_user,
            ).count()

            all_draft_tasks_in_project = Annotation.objects.filter(
                task__project_id__in=proj_ids,
                annotation_status="draft",
                annotation_type=ANNOTATOR_ANNOTATION,
                updated_at__range=[start_date, end_date],
                completed_by=each_annotation_user,
            ).count()

            if (
                project_progress_stage != None
                and project_progress_stage > ANNOTATION_STAGE
            ):
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
                    "Total Segments Duration": total_duration,
                    "Total Raw Audio Duration": total_raw_duration,
                    "Average Annotation Time (In Seconds)": round(avg_lead_time, 2),
                    "Avg Segment Duration": round(avg_segment_duration, 2),
                    "Average Segments Per Task": round(avg_segments_per_task, 2),
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
                    "Total Segments Duration": total_duration,
                    "Total Raw Audio Duration": total_raw_duration,
                    "Average Annotation Time (In Seconds)": round(avg_lead_time, 2),
                    "Avg Segment Duration": round(avg_segment_duration, 2),
                    "Average Segments Per Task": round(avg_segments_per_task, 2),
                }

            if project_type in get_audio_project_types():
                del result["Word Count"]
            elif is_translation_project or project_type in [
                "SemanticTextualSimilarity_Scale5",
                "OCRTranscriptionEditing",
                "OCRTranscription",
            ]:
                del result["Total Segments Duration"]
                del result["Total Raw Audio Duration"]
                del result["Avg Segment Duration"]
                del result["Average Segments Per Task"]
            else:
                del result["Word Count"]
                del result["Total Segments Duration"]
                del result["Total Raw Audio Duration"]
                del result["Avg Segment Duration"]
                del result["Average Segments Per Task"]

            final_reports.append(result)

    df = pd.DataFrame.from_dict(final_reports)

    content = df.to_csv(index=False)
    content_type = "text/csv"
    filename = f"{ws.workspace_name}_user_analytics.csv"

    message = (
        "Dear "
        + str(user.username)
        + ",\nYour user analysis reports for the workspace "
        + f"{ws.workspace_name}"
        + " are ready.\n Thanks for contributing on Shoonya!"
        + "\nProject Type: "
        + f"{project_type}"
    )

    email = EmailMessage(
        f"{ws.workspace_name}" + " User Analytics",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        attachments=[(filename, content, content_type)],
    )
    email.send()
