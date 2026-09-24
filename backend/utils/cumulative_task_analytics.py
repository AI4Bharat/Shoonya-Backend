from datetime import datetime, time, timedelta, timezone

from django.db.models import Count, Q

from projects.models import REVIEW_STAGE, SUPERCHECK_STAGE
from tasks.models import (
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
    Annotation,
)


COMPLETED_TASK_STATUSES = ["annotated", "reviewed", "super_checked", "exported"]
REVIEWED_TASK_STATUSES = ["reviewed", "super_checked", "exported"]
SUPERCHECKED_TASK_STATUSES = ["super_checked", "exported"]


def parse_cumulative_date_range(query_params):
    """Return an inclusive UTC date range as a half-open datetime interval."""
    start_date_value = query_params.get("start_date")
    end_date_value = query_params.get("end_date")

    if start_date_value is None and end_date_value is None:
        return None

    if not start_date_value or not end_date_value:
        raise ValueError("start_date and end_date must be provided together")

    try:
        start_date = datetime.strptime(start_date_value, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError("start_date and end_date must use YYYY-MM-DD format")

    if start_date > end_date:
        raise ValueError("end_date must be on or after start_date")

    if end_date > datetime.now(timezone.utc).date():
        raise ValueError("start_date and end_date cannot be in the future")

    start_datetime = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_datetime = datetime.combine(
        end_date + timedelta(days=1), time.min, tzinfo=timezone.utc
    )
    return start_datetime, end_datetime


def get_date_filtered_cumulative_task_counts(
    projects, project_types, start_datetime, end_datetime
):
    """Return date-filtered task counts grouped by project type and language."""
    counts = Annotation.objects.filter(
        task__project_id__in=projects,
        task__project_id__project_type__in=project_types,
        annotated_at__gte=start_datetime,
        annotated_at__lt=end_datetime,
    )

    rows = counts.values(
        "task__project_id__project_type", "task__project_id__tgt_language"
    ).annotate(
        annotation_count=Count(
            "task_id",
            filter=Q(
                annotation_type=ANNOTATOR_ANNOTATION,
                task__task_status__in=COMPLETED_TASK_STATUSES,
            ),
            distinct=True,
        ),
        reviewer_count=Count(
            "task_id",
            filter=Q(
                annotation_type=REVIEWER_ANNOTATION,
                task__task_status__in=REVIEWED_TASK_STATUSES,
                task__project_id__project_stage__in=[REVIEW_STAGE, SUPERCHECK_STAGE],
            )
            & ~Q(annotation_status="to_be_revised"),
            distinct=True,
        ),
        superchecker_count=Count(
            "task_id",
            filter=Q(
                annotation_type=SUPER_CHECKER_ANNOTATION,
                task__task_status__in=SUPERCHECKED_TASK_STATUSES,
                task__project_id__project_stage=SUPERCHECK_STAGE,
            ),
            distinct=True,
        ),
    )

    grouped_counts = {project_type: {} for project_type in project_types}
    for row in rows:
        project_type = row["task__project_id__project_type"]
        language = row["task__project_id__tgt_language"] or "Others"
        language_counts = grouped_counts[project_type].setdefault(
            language,
            {
                "language": language,
                "ann_cumulative_tasks_count": 0,
                "rew_cumulative_tasks_count": 0,
                "sup_cumulative_tasks_count": 0,
            },
        )
        language_counts["ann_cumulative_tasks_count"] += row["annotation_count"]
        language_counts["rew_cumulative_tasks_count"] += row["reviewer_count"]
        language_counts["sup_cumulative_tasks_count"] += row["superchecker_count"]

    result = {}
    for project_type in project_types:
        language_counts = grouped_counts[project_type].values()
        non_empty_counts = [
            item
            for item in language_counts
            if item["ann_cumulative_tasks_count"]
            or item["rew_cumulative_tasks_count"]
            or item["sup_cumulative_tasks_count"]
        ]
        result[project_type] = sorted(
            non_empty_counts, key=lambda item: item["language"]
        )

    return result
