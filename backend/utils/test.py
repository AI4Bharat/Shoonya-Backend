
from tasks.models import (Annotation, REVIEWER_ANNOTATION, ACCEPTED, ACCEPTED_WITH_MINOR_CHANGES, ACCEPTED_WITH_MAJOR_CHANGES,
                          SUPER_CHECKER_ANNOTATION, VALIDATED, VALIDATED_WITH_CHANGES, ANNOTATOR_ANNOTATION)
from projects.utils import calculate_word_error_rate_between_two_audio_transcription_annotation
from tasks.views import SentenceOperationViewSet

all_annotations_across_ = Annotation.objects.all()

for all_anno in all_annotations:

ar_wer_score, as_wer_score, rs_wer_score = 0, 0, 0
ar_bleu_score, rs_bleu_score = 0, 0
ar_done, as_done, rs_done = False, False, False
ann_ann, rev_ann, sup_ann = "", "", ""
for a in all_annotations:
    if a.annotation_type == REVIEWER_ANNOTATION and a.annotation_status in [
        ACCEPTED,
        ACCEPTED_WITH_MINOR_CHANGES,
        ACCEPTED_WITH_MAJOR_CHANGES,
    ]:
        rev_ann = a
    elif a.annotation_type == SUPER_CHECKER_ANNOTATION and a.annotation_status in [
        VALIDATED,
        VALIDATED_WITH_CHANGES,
    ]:
        sup_ann = a
    elif a.annotation_type == ANNOTATOR_ANNOTATION:
        ann_ann = a
    if ann_ann and rev_ann and not ar_done:
        try:
            ar_wer_score += calculate_word_error_rate_between_two_audio_transcription_annotation(
                rev_ann.result, ann_ann.result, None
            )
            ar_done = True
        except Exception as e:
            pass
        try:
            s1 = SentenceOperationViewSet()
            sampleRequest = {
                "annotation_result1": rev_ann.result,
                "annotation_result2": ann_ann.result,
            }
            ar_bleu_score += float(
                s1.calculate_bleu_score(sampleRequest).data["ar_bleu_score"]
            )
        except Exception as e:
            pass
    if rev_ann and sup_ann and not rs_done:
        try:
            rs_wer_score += calculate_word_error_rate_between_two_audio_transcription_annotation(
                sup_ann.result, rev_ann.result, None
            )
            rs_done = True
        except Exception as e:
            pass
        try:
            s1 = SentenceOperationViewSet()
            sampleRequest = {
                "annotation_result1": sup_ann.result,
                "annotation_result2": rev_ann.result,
            }
            rs_bleu_score += float(
                s1.calculate_bleu_score(sampleRequest).data["rs_bleu_score"]
            )
        except Exception as e:
            pass
    if ann_ann and sup_ann and not as_done:
        meta_stats = sup_ann.meta_stats
        if "as_wer_score" in meta_stats:
            as_wer_score += meta_stats["as_wer_score"]
            as_done = True
        try:
            as_wer_score += calculate_word_error_rate_between_two_audio_transcription_annotation(
                sup_ann.result, ann_ann.result, None
            )
            as_done = True
        except Exception as e:
            pass