"""Date-scoped cumulative task counts for organization and workspace reports."""

from datetime import datetime, time, timedelta, timezone

from django.db.models import Count, Q

from projects.models import REVIEW_STAGE, SUPERCHECK_STAGE
from tasks.models import (
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
    Annotation,
)


def analytics_date_bounds(params):
    """Convert inclusive calendar dates to UTC bounds, or None for all time."""
    values = (params.get("start_date"), params.get("end_date"))
    if values == (None, None):
        return None
    if not all(values):
        raise ValueError("start_date and end_date must be provided together")

    dates = []
    for value in values:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
            if value != parsed.isoformat():
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("start_date and end_date must use YYYY-MM-DD format")
        dates.append(parsed)

    start, end = dates
    if start > end:
        raise ValueError("end_date must be on or after start_date")
    if end > datetime.now(timezone.utc).date():
        raise ValueError("start_date and end_date cannot be in the future")

    return (
        datetime.combine(start, time.min, tzinfo=timezone.utc),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


def cumulative_counts_in_range(projects, project_types, bounds):
    """Count each task once per annotation role within its completion dates."""
    start, end = bounds
    completed_annotations = Q(
        annotation_type=ANNOTATOR_ANNOTATION,
        task__task_status__in=("annotated", "reviewed", "super_checked", "exported"),
    )
    completed_reviews = Q(
        annotation_type=REVIEWER_ANNOTATION,
        task__task_status__in=("reviewed", "super_checked", "exported"),
        task__project_id__project_stage__in=(REVIEW_STAGE, SUPERCHECK_STAGE),
    ) & ~Q(annotation_status="to_be_revised")
    completed_superchecks = Q(
        annotation_type=SUPER_CHECKER_ANNOTATION,
        task__task_status__in=("super_checked", "exported"),
        task__project_id__project_stage=SUPERCHECK_STAGE,
    )

    type_field = "task__project_id__project_type"
    language_field = "task__project_id__tgt_language"
    totals = (
        Annotation.objects.filter(
            completed_annotations | completed_reviews | completed_superchecks,
            task__project_id__in=projects,
            task__project_id__project_type__in=project_types,
            annotated_at__gte=start,
            annotated_at__lt=end,
        )
        .order_by()
        .values(type_field, language_field, "annotation_type")
        .annotate(task_count=Count("task_id", distinct=True))
    )

    count_fields = {
        ANNOTATOR_ANNOTATION: "ann_cumulative_tasks_count",
        REVIEWER_ANNOTATION: "rew_cumulative_tasks_count",
        SUPER_CHECKER_ANNOTATION: "sup_cumulative_tasks_count",
    }
    report = {project_type: {} for project_type in project_types}
    for total in totals:
        language = total[language_field] or "Others"
        languages = report[total[type_field]]
        if language not in languages:
            languages[language] = dict.fromkeys(count_fields.values(), 0)
            languages[language]["language"] = language
        count_field = count_fields[total["annotation_type"]]
        languages[language][count_field] += total["task_count"]

    return {
        project_type: [languages[language] for language in sorted(languages)]
        for project_type, languages in report.items()
    }
