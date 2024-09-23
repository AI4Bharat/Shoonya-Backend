from tasks.models import (
    Annotation,
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
    LABELED,
    ACCEPTED,
    ACCEPTED_WITH_MINOR_CHANGES,
    ACCEPTED_WITH_MAJOR_CHANGES,
    VALIDATED,
    VALIDATED_WITH_CHANGES,
)


def filter_tasks_by_ann_type(annotation_tasks, reviewer_tasks, supercheck_tasks):
    filtered_annotation_tasks, filtered_reviewer_tasks, filtered_supercheck_tasks = (
        [],
        [],
        [],
    )
    for a in annotation_tasks:
        anno = Annotation.objects.filter(
            task=a, annotation_type=ANNOTATOR_ANNOTATION, annotation_status=LABELED
        )[0]
        if anno:
            filtered_annotation_tasks.append(a)
    for r in reviewer_tasks:
        anno = Annotation.objects.filter(
            task=r,
            annotation_type=REVIEWER_ANNOTATION,
            annotation_status__in=[
                ACCEPTED,
                ACCEPTED_WITH_MINOR_CHANGES,
                ACCEPTED_WITH_MAJOR_CHANGES,
            ],
        )[0]
        if anno:
            filtered_reviewer_tasks.append(r)
    for s in supercheck_tasks:
        anno = Annotation.objects.filter(
            task=s,
            annotation_type=SUPER_CHECKER_ANNOTATION,
            annotation_status__in=[VALIDATED, VALIDATED_WITH_CHANGES],
        )[0]
        if anno:
            filtered_supercheck_tasks.append(s)
    return filtered_annotation_tasks, filtered_reviewer_tasks, filtered_supercheck_tasks
