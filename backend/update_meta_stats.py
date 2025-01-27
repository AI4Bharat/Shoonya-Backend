import os
import django
import random
from django.db.models import F
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shoonya_backend.settings")
django.setup()

from tasks.utils import compute_meta_stats_for_annotation
from tasks.models import Task, Annotation
from projects.models import Project
from tqdm import tqdm


def compute_meta_stats(ann_obj, project_type):

    ann_obj.meta_stats = compute_meta_stats_for_annotation(
        ann_obj=ann_obj, project_type=project_type
    )
    return ann_obj


def chunk_list(large_list, batch_size):
    return [
        large_list[i : i + batch_size] for i in range(0, len(large_list), batch_size)
    ]


def process_chunk(annotation_ids):
    annotations = (
        Annotation.objects.filter(id__in=annotation_ids)
        .annotate(project_type=F("task_id__project_id__project_type"))
        .iterator()
    )
    updated_annotations = []

    for annotation in annotations:
        updated_annotation = compute_meta_stats(
            ann_obj=annotation, project_type=annotation.project_type
        )
        updated_annotations.append(updated_annotation)
    # Update annotations in bulk
    Annotation.objects.bulk_update(updated_annotations, ["meta_stats"])


if __name__ == "__main__":

    project_types = [
        # "ConversationTranslation",
        "ConversationTranslationEditing",
        # "ConversationVerification",
        # "OCRTranscription",
        # "OCRTranscriptionEditing",
        # "OCRSegmentCategorizationEditing",
        # "AudioTranscription",
        # "AudioTranscriptionEditing",
        # "ContextualSentenceVerification",
        # "ContextualSentenceVerificationAndDomainClassification",
        # "ContextualTranslationEditing",
        # "TranslationEditing",
        # "AcousticNormalisedTranscriptionEditing",
    ]

    for pjt in tqdm(project_types, total=len(project_types)):

        print(f"Updating Meta Stats for {pjt}")

        annotations = (
            Annotation.objects.filter(task_id__project_id__project_type=pjt)
            .only("id")
            .values_list("id", flat=True)
        )

        chunks = chunk_list(annotations, batch_size=1000)

        print(f"Number of Chunks in current Project: {len(chunks)}")

        with ThreadPoolExecutor(
            max_workers=4
        ) as executor:  # Adjust max_workers as needed
            futures = [executor.submit(process_chunk, chunk) for chunk in chunks]

        # Wait for all threads to complete
        for idx, future in enumerate(futures):
            print(f"Chunk {idx} Done!")
