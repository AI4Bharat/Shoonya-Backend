import os
import django
import random
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shoonya_backend.settings")
django.setup()

from tasks.utils import compute_meta_stats_for_annotation
from tasks.models import Task, Annotation
from projects.models import Project
from tqdm import tqdm


def compute_meta_stats_for_tasks(item):
    task, pjt = item
    annots = Annotation.objects.filter(task=task)

    for annot in annots:
        try:
            meta_stats = compute_meta_stats_for_annotation(annot, pjt)
            annot.meta_stats = meta_stats
            annot.save()
        except Exception as e:
            pass


if __name__ == "__main__":

    project_types = [
        # "ConversationTranslation",
        # "ConversationTranslationEditing",
        # "ConversationVerification",
        # "OCRTranscription",
        # "OCRTranscriptionEditing",
        # "OCRSegmentCategorizationEditing",
        "AudioTranscription",
        "AudioTranscriptionEditing",
        "ContextualSentenceVerification",
        "ContextualSentenceVerificationAndDomainClassification",
        # "ContextualTranslationEditing",
        # "TranslationEditing",
        # "AcousticNormalisedTranscriptionEditing",
    ]

    executor = ProcessPoolExecutor(max_workers=10)

    for pjt in tqdm(project_types, total=len(project_types)):

        print(f"Updating Meta Stats for {pjt}")
        proj_objs = Project.objects.filter(project_type=pjt)
        print("--------------------------------------")
        for pobj in tqdm(proj_objs, total=len(proj_objs), leave=False):

            tasks = Task.objects.filter(project_id_id=pobj.id)
            tasks = [[task, pjt] for task in tasks]

            for result in executor.map(compute_meta_stats_for_tasks, tasks):
                pass

            # annot.meta_stats = meta_stats

            # annot.save()
