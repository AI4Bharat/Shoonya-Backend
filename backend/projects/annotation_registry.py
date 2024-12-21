from projects.registry_helper import ProjectRegistry
from dataset import models as dataset_models
from users.utils import generate_random_string
from dataset.models import SpeechConversation

ANNOTATION_REGISTRY_DICT = {
    "MonolingualTranslation": {
        "output_text": {
            "to_name": "input_text",
            "from_name": "output_text",
            "type": "textarea",
        },
    },
    "TranslationEditing": {
        "output_text": {
            "to_name": "input_text",
            "from_name": "output_text",
            "type": "textarea",
        },
    },
    "SemanticTextualSimilarity_Scale5": {
        "rating": {
            "to_name": "output_text",
            "from_name": "rating",
            "type": "choices",
        },
    },
    "ContextualTranslationEditing": {
        "output_text": {
            "to_name": "input_text",
            "from_name": "output_text",
            "type": "textarea",
        },
    },
    "ContextualSentenceVerification": {
        "corrected_text": {
            "to_name": "text",
            "from_name": "corrected_text",
            "type": "textarea",
        },
        "quality_status": {
            "to_name": "text",
            "from_name": "quality_status",
            "type": "choices",
        },
    },
    "ContextualSentenceVerificationAndDomainClassification": {
        "corrected_text": {
            "to_name": "text",
            "from_name": "corrected_text",
            "type": "textarea",
        },
        "quality_status": {
            "to_name": "text",
            "from_name": "quality_status",
            "type": "choices",
        },
        "domain": {
            "to_name": "text",
            "from_name": "domain",
            "type": "taxonomy",
        },
    },
    "ConversationTranslation": {
        "conversation_json": {
            "to_name": "dialog_i_j",
            "from_name": "output_i_j",
            "type": "textarea",
        },
    },
    "ConversationTranslationEditing": {
        "conversation_json": {
            "to_name": "dialog_i_j",
            "from_name": "output_i_j",
            "type": "textarea",
        },
    },
    "ConversationVerification": {
        "conversation_json": {
            "to_name": "dialog_i_j",
            "from_name": "output_i_j",
            "type": "textarea",
        },
        "conversation_quality_status": {
            "to_name": "quality_status",
            "from_name": "quality_status",
            "type": "choices",
        },
    },
    "AudioTranscription": {
        "transcribed_json": {
            "to_name": "audio_url",
            "from_name": ["labels", "transcribed_json"],
            "type": ["labels", "textarea"],
        },
    },
    "AudioTranscriptionEditing": {
        "transcribed_json": {
            "to_name": "audio_url",
            "from_name": ["labels", "transcribed_json"],
            "type": ["labels", "textarea"],
        },
    },
    "AudioSegmentation": {
        "prediction_json": {
            "to_name": "audio_url",
            "from_name": "labels",
            "type": "labels",
        },
    },
    "OCRTextlineSegmentation": {
        "ocr_transcribed_json": {
            "to_name": "image_url",
            "from_name": [
                "annotation_bboxes",
            ],
            "type": ["rectangle"],
        },
    },
    "OCRTranscription": {
        "ocr_transcribed_json": {
            "to_name": "image_url",
            "from_name": [
                "annotation_bboxes",
                "annotation_labels",
                "annotation_transcripts",
            ],
            "type": ["textarea", "labels", "textarea"],
        },
    },
    "OCRTranscriptionEditing": {
        "ocr_transcribed_json": {
            "to_name": "image_url",
            "from_name": [
                "annotation_bboxes",
                "annotation_labels",
                "annotation_transcripts",
            ],
            "type": ["textarea", "labels", "textarea"],
        },
    },
    "OCRSegmentCategorization": {
        "ocr_transcribed_json": {
            "to_name": "image_url",
            "from_name": [
                "annotation_bboxes",
                "annotation_labels",
                "annotation_transcripts",
            ],
            "type": ["textarea", "labels", "textarea"],
        },
    },
    "OCRSegmentCategorizationEditing": {
        "ocr_transcribed_json": {
            "to_name": "image_url",
            "from_name": [
                "annotation_bboxes",
                "annotation_labels",
                "annotation_transcripts",
            ],
            "type": ["textarea", "labels", "textarea"],
        },
    },
    "OCRSegmentCategorisationRelationMappingEditing": {
        "ocr_transcribed_json": {
            "to_name": "image_url",
            "from_name": [
                "annotation_bboxes",
                "annotation_labels",
                "annotation_transcripts",
            ],
            "type": ["textarea", "labels", "textarea"],
        },
    },
    "AcousticNormalisedTranscriptionEditing": {
        "transcribed_json": {
            "to_name": "audio_url",
            "from_name": [
                "labels",
                "verbatim_transcribed_json",
                "acoustic_normalised_transcribed_json",
                "standardised_transcription",
            ],
            "type": ["labels", "textarea", "textarea", "textarea"],
        },
    },
    "StandardizedTranscriptionEditing": {
        "transcribed_json": {
            "to_name": "audio_url",
            "from_name": [
                "labels",
                "verbatim_transcribed_json",
                "acoustic_normalised_transcribed_json",
                "acoustic_standardised_transcribed_json",
            ],
            "type": ["labels", "textarea", "textarea", "textarea"],
        },
    },
}


def convert_conversation_json_to_annotation_result(conversation_json, idx):
    result = []
    for i in range(len(conversation_json)):
        for j in range(len(conversation_json[i]["sentences"])):
            id = f"shoonya_{idx}s{i}s{j}s{generate_random_string(15-len(str(i))-len(str(j)))}"
            text_dict = {
                "id": id,
                "type": "textarea",
                "value": {"text": [conversation_json[i]["sentences"][j]]},
                "origin": "manual",
                "to_name": f"dialog_{i}_{j}",
                "from_name": f"output_{i}_{j}",
            }
            result.append(text_dict)

    return result


def draft_data_json_to_annotation_result(draft_data_json, project_type, pk=None):
    from projects.views import convert_prediction_json_to_annotation_result

    registry_helper = ProjectRegistry.get_instance()
    input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)
    dataset_model = getattr(dataset_models, input_dataset_info["dataset_type"])
    try:
        dataset_item = dataset_model.objects.get(pk=pk)
    except:
        dataset_item = None
        pass
    result = []
    idx = 0
    for field, value in draft_data_json.items():
        try:
            id = f"shoonya_{idx}g{generate_random_string(13-len(str(idx)))}"
            field_dict = {
                "id": id,
                "origin": "manual",
                "type": ANNOTATION_REGISTRY_DICT[project_type][field]["type"],
                "to_name": ANNOTATION_REGISTRY_DICT[project_type][field]["to_name"],
                "from_name": ANNOTATION_REGISTRY_DICT[project_type][field]["from_name"],
            }
            field_type = ANNOTATION_REGISTRY_DICT[project_type][field]["type"]
            ans = []
            if field == "conversation_json":
                ans = convert_conversation_json_to_annotation_result(value, idx)
            elif field == "transcribed_json" or field == "prediction_json":
                assert type(value) in [
                    list,
                    dict,
                ], f"Something wrong is there in the type of {value}"
                if isinstance(value, list):
                    value = {"verbatim_transcribed_json": value}
                sub_ans = convert_prediction_json_to_annotation_result(
                    None,
                    project_type,
                    dataset_item,
                    value,
                    True,
                )
                ans.extend(sub_ans)
            else:
                if field_type == "textarea":
                    field_dict["value"] = {"text": [value]}
                elif field_type == "choices":
                    field_dict["value"] = {"choices": [value]}
                elif field_type == "taxonomy":
                    field_dict["value"] = {"taxonomy": [value.split(",")]}

                ans.append(field_dict)

            result.extend(ans)
            idx += 1
        except:
            pass

    return result
