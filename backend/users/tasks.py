from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from celery.schedules import crontab
from shoonya_backend.celery import celery_app
from user_reports import (
    calculate_reports,
    fetch_task_counts,
    set_meta_stats,
    set_raw_duration,
)
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(name="send_mail_task")
def send_mail_task():
    calculate_reports()


@shared_task(name="fetchTaskCounts")
def fetchTaskCounts():
    fetch_task_counts()
    logger.info("Completed Task Count Update")


@shared_task(name="setWordCounts")
def setWordCounts():

    org_ids = [1, 2, 3]

    stat_types = ["word_count"]

    project_types = [
        "ContextualSentenceVerification",
        "ContextualSentenceVerificationAndDomainClassification",
        "ContextualTranslationEditing",
        "TranslationEditing",
        "ConversationTranslation",
        "ConversationTranslationEditing",
        "ConversationVerification",
        "OCRTranscription",
        "OCRTranscriptionEditing",
        "OCRSegmentCategorizationEditing",
    ]

    set_meta_stats(org_ids=org_ids, project_types=project_types, stat_types=stat_types)

    logger.info("Completed Word Count Update")


@shared_task(name="setSentenceCounts")
def setSentenceCounts():

    org_ids = [1, 2, 3]

    stat_types = ["sentence_count"]

    project_types = [
        "ConversationTranslation",
        "ConversationTranslationEditing",
        "ConversationVerification",
    ]

    set_meta_stats(org_ids=org_ids, project_types=project_types, stat_types=stat_types)

    logger.info("Completed Sentence Count Update")


@shared_task(name="setAudioWordCounts")
def setAudioWordCounts():

    org_ids = [1, 2, 3]

    stat_types = ["audio_word_count"]

    project_types = ["AudioTranscription", "AudioTranscriptionEditing"]

    set_meta_stats(org_ids=org_ids, project_types=project_types, stat_types=stat_types)

    logger.info("Completed Audio Word Count Update")


@shared_task(name="setRawDurations")
def setRawDurations():

    org_ids = [1, 2, 3]

    project_types = [
        "AudioTranscription",
        "AudioTranscriptionEditing",
        "AcousticNormalisedTranscriptionEditing",
    ]

    set_raw_duration(org_ids=org_ids, project_types=project_types)

    logger.info("Completed Raw Duration Update")


@shared_task(name="setSegmentDurations")
def setSegmentDurations():

    org_ids = [1, 2, 3]

    stat_types = ["total_segment_duration"]

    project_types = [
        "AudioTranscription",
        "AudioTranscriptionEditing",
        "AcousticNormalisedTranscriptionEditing",
    ]

    set_meta_stats(org_ids=org_ids, project_types=project_types, stat_types=stat_types)

    logger.info("Completed Segment Duration Update")


@shared_task(name="setNotNullSegmentDurations")
def setNotNullSegmentDurations():

    org_ids = [1, 2, 3]

    stat_types = ["not_null_segment_duration"]

    project_types = [
        "AudioTranscription",
        "AudioTranscriptionEditing",
        "AcousticNormalisedTranscriptionEditing",
    ]

    set_meta_stats(org_ids=org_ids, project_types=project_types, stat_types=stat_types)

    logger.info("Completed Not Null Segment Duration Update")


@shared_task(name="setAcousticNormalisedStats")
def setAcosticNormalisedStats():

    org_ids = [1, 2, 3]

    stat_types = [
        "acoustic_normalised_word_count",
        "acoustic_normalised_duration",
        "verbatim_word_count",
        "verbatim_duration",
    ]

    project_types = [
        "AcousticNormalisedTranscriptionEditing",
    ]

    set_meta_stats(org_ids=org_ids, project_types=project_types, stat_types=stat_types)

    logger.info("Completed ANTE Stats Update")


@shared_task(name="setTranscribedDurations")
def setTranscribedDurations():

    org_ids = [1, 2, 3]

    stat_types = ["transcribed_duration"]

    project_types = [
        "AudioTranscription",
        "AudioTranscriptionEditing",
    ]

    set_meta_stats(org_ids=org_ids, project_types=project_types, stat_types=stat_types)

    logger.info("Completed Transcribed Duration Update")
