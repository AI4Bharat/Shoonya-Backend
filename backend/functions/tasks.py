import datetime
import zipfile
import threading
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import pandas as pd
from celery import shared_task
from dataset import models as dataset_models
from organizations.models import Organization
from projects.models import Project
from projects.utils import (
    convert_seconds_to_hours,
    get_audio_project_types,
    get_audio_transcription_duration,
    calculate_word_error_rate_between_two_audio_transcription_annotation,
    ocr_word_count,
    get_not_null_audio_transcription_duration,
)
from projects.views import get_task_count_unassigned, ProjectViewSet
from shoonya_backend import settings
from tasks.models import (
    Annotation,
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
    REVIEWED,
    SUPER_CHECKED,
    Task,
    ANNOTATED,
)
from tasks.views import SentenceOperationViewSet
from users.models import User
from django.core.mail import EmailMessage

from utils.blob_functions import (
    extract_account_name,
    extract_account_key,
    extract_endpoint_suffix,
    test_container_connection,
)
from utils.custom_bulk_create import multi_inheritance_table_bulk_insert
from workspaces.models import Workspace

from .utils import (
    get_batch_translations,
    get_batch_ocr_predictions,
    get_batch_asr_predictions,
)
from django.db import transaction, DataError, IntegrityError
from dataset.models import DatasetInstance
from django.apps import apps
from rest_framework.test import APIRequestFactory
from django.http import QueryDict
from rest_framework.request import Request
import os
import tempfile


## CELERY SHARED TASKS
@shared_task(bind=True)
def sentence_text_translate_and_save_translation_pairs(
    self,
    languages,
    input_dataset_instance_id,
    output_dataset_instance_id,
    batch_size,
    api_type="indic-trans-v2",
    checks_for_particular_languages=False,
    automate_missing_data_items=True,
):  # sourcery skip: raise-specific-error
    """Function to translate SentenceTexts and to save the TranslationPairs in the database.

    Args:
        languages (list): List of output languages for the translations.
        input_dataset_instance_id (int): ID of the input dataset instance.
        output_dataset_instance_id (int): ID of the output dataset instance.
        batch_size (int): Number of sentences to be translated in a single batch.
        api_type (str): Type of API to be used for translation. (default: indic-trans-v2)
            Allowed - [indic-trans, google, indic-trans-v2, azure, blank]
        checks_for_particular_languages (bool): If True, checks for the particular languages in the translations.
        automate_missing_data_items (bool): If True, consider only those data items that are missing in the target dataset instance.
    """

    output_sentences = list(
        dataset_models.TranslationPair.objects.filter(
            instance_id=output_dataset_instance_id,
            output_language__in=languages,
        ).values_list(
            "id",
            "output_language",
            "parent_data_id",
        )
    )

    # Collect the sentences from Sentence Text based on dataset id
    input_sentences = list(
        dataset_models.SentenceText.objects.filter(
            instance_id=input_dataset_instance_id
        ).values_list(
            "id",
            "corrected_text",
            "language",
            "context",
            "quality_status",
            "metadata_json",
        )
    )

    # Convert the input_sentences list into a dataframe
    input_sentences_complete_df = pd.DataFrame(
        input_sentences,
        columns=[
            "sentence_text_id",
            "corrected_text",
            "input_language",
            "context",
            "quality_status",
            "metadata",
        ],
    )

    # Keep only the clean sentences
    input_sentences_complete_df = input_sentences_complete_df[
        (input_sentences_complete_df["quality_status"] == "Clean")
    ].reset_index(drop=True)

    # Check if the dataframe is empty
    if input_sentences_complete_df.shape[0] == 0:
        # Update the task status
        self.update_state(
            state="FAILURE",
            meta={
                "No sentences to upload.",
            },
        )

        raise Exception("No clean sentences found. Perform project export first.")

    # Get the output dataset instance
    output_dataset_instance = dataset_models.DatasetInstance.objects.get(
        instance_id=output_dataset_instance_id
    )

    # Keep count of the number of sentences translated
    translated_sentences_count = 0

    # Iterate through the languages
    for output_language in languages:
        if automate_missing_data_items == True:
            # Fetch all parent ids of translation pairs present in the target dataset instance
            output_sentences_parent_ids = [
                t[2] for t in output_sentences if t[1] == output_language
            ]

            # Fetch samples from the input dataset instance which are not yet translated
            input_sentences_df = input_sentences_complete_df[
                ~input_sentences_complete_df["sentence_text_id"].isin(
                    output_sentences_parent_ids
                )
            ].reset_index(drop=True)
        else:
            # Fetch all samples from the input dataset instance
            input_sentences_df = input_sentences_complete_df

        # Make a sentence list for valid sentences to be translated
        all_sentences_to_be_translated = input_sentences_df["corrected_text"].tolist()

        # Loop through all the sentences to be translated in batch format
        for i in range(0, len(all_sentences_to_be_translated), batch_size):
            # Create a TranslationPair object list
            translation_pair_objects = []

            batch_of_input_sentences = all_sentences_to_be_translated[
                i : i + batch_size
            ]

            # Get the translations for the batch of sentences
            translations_output = get_batch_translations(
                sentences_to_translate=batch_of_input_sentences,
                source_lang=input_sentences_df["input_language"].iloc[0],
                target_lang=output_language,
                api_type=api_type,
                checks_for_particular_languages=checks_for_particular_languages,
            )

            if translations_output["status"] == "failure":
                # Update the task status and raise an exception
                self.update_state(
                    state="FAILURE",
                    meta={
                        "API Error",
                    },
                )

                raise Exception(
                    translations_output["output"]
                )  # sourcery skip: raise-specific-error

            else:
                translated_sentences = translations_output["output"]

            # Check if the translated sentences are equal to the input sentences
            if len(translated_sentences) != len(batch_of_input_sentences):
                # Update the task status and raise an exception
                self.update_state(
                    state="FAILURE",
                    meta={
                        "Error: Number of translated sentences does not match with the number of input sentences.",
                    },
                )
                raise Exception(
                    "The number of translated sentences does not match the number of input sentences."
                )

            # Iterate through the dataframe
            for index, row in input_sentences_df[i : i + batch_size].iterrows():
                # Get the values for the TranslationPair model
                sentence_text_id = row["sentence_text_id"]
                input_sentence = row["corrected_text"]
                input_language = row["input_language"]
                translated_sentence = translated_sentences[index - i]
                metadata = row["metadata"]
                context = row["context"]

                # Get the sentencetext model object by ID
                sentence_text_object = dataset_models.SentenceText.objects.get(
                    id=sentence_text_id
                )

                # Create and save a TranslationPair object
                translation_pair_obj = dataset_models.TranslationPair(
                    parent_data=sentence_text_object,
                    instance_id=output_dataset_instance,
                    input_language=input_language,
                    output_language=output_language,
                    input_text=input_sentence,
                    machine_translation=translated_sentence,
                    context=context,
                    metadata_json=metadata,
                )

                # Append the object to TranslationPair list for bulk create
                translation_pair_objects.append(translation_pair_obj)

            # Bulk create the TranslationPair objects for the particular language
            multi_inheritance_table_bulk_insert(translation_pair_objects)
            translated_sentences_count += len(translation_pair_objects)

    return f"{translated_sentences_count} translation pairs created for languages: {str(languages)}"


@shared_task(bind=True)
def conversation_data_machine_translation(
    self,
    languages,
    input_dataset_instance_id,
    output_dataset_instance_id,
    batch_size,
    api_type,
    checks_for_particular_languages,
):
    """Function to translate Conversation data item and to save the translations in another Conversation dataitem.
    Args:
        languages (list): List of output languages for the translations.
        input_dataset_instance_id (int): ID of the input dataset instance.
        output_dataset_instance_id (int): ID of the output dataset instance.
        batch_size (int): Number of sentences to be translated in a single batch.
        api_type (str): Type of API to be used for translation. (default: indic-trans)
            Allowed - [indic-trans, google, indic-trans-v2, azure, blank]
        checks_for_particular_languages (bool): If True, checks for the particular languages in the translations.
    """

    # Get the output dataset instance
    output_dataset_instance = dataset_models.DatasetInstance.objects.get(
        instance_id=output_dataset_instance_id
    )

    # Collect all the Conversation dataitems for the input DatasetInstance and convert to dataframe
    conversation_dataitems = dataset_models.Conversation.objects.filter(
        instance_id=input_dataset_instance_id
    ).values_list("id", "scenario", "prompt", "conversation_json", "language")

    conversation_dataitems_df = pd.DataFrame(
        conversation_dataitems,
        columns=["id", "scenario", "prompt", "conversation_json", "language"],
    )

    # Check if the dataframe is empty
    if conversation_dataitems_df.shape[0] == 0:
        # Update the task status
        self.update_state(
            state="FAILURE",
            meta={
                "No sentences to upload.",
            },
        )

        raise Exception("The conversation data is empty.")

    # Iterate through the languages
    for output_language in languages:
        all_translated_conversation_objects = []
        # Iterate through the conversation dataitems
        for index, row in conversation_dataitems_df.iterrows():
            # Get the instance of the Conversation dataitem
            conversation_dataitem = dataset_models.Conversation.objects.get(
                id=row["id"]
            )

            # Get the conversation JSON and iterate through it
            conversation_json = row["conversation_json"]
            translated_conversation_json = []
            for conversation in conversation_json:
                # Get the sentence list, scenario and prompt
                sentences_to_translate = dict(conversation).get("sentences", [])
                speaker_id = dict(conversation).get("speaker_id")

                # Get the translations for the sentences
                translations_output = get_batch_translations(
                    sentences_to_translate=sentences_to_translate,
                    source_lang=row["language"],
                    target_lang=output_language,
                    api_type=api_type,
                    checks_for_particular_languages=checks_for_particular_languages,
                )

                if translations_output["status"] == "success":
                    # Append the translations to the translated conversation JSON
                    translated_conversation_json.append(
                        {
                            "sentences": translations_output["output"],
                            "speaker_id": speaker_id,
                        }
                    )
                else:
                    # Update the task status and raise an exception
                    self.update_state(
                        state="FAILURE",
                        meta={
                            "API Error",
                        },
                    )

                    raise Exception(translations_output["output"])

            # Translate the scenario and prompt
            untranslated_prompt_and_scenario = [row["prompt"], row["scenario"]]
            translations_output = get_batch_translations(
                sentences_to_translate=untranslated_prompt_and_scenario,
                source_lang=row["language"],
                target_lang=output_language,
                api_type=api_type,
                checks_for_particular_languages=checks_for_particular_languages,
            )

            if translations_output["status"] == "failure":
                # Update the task status and raise an exception
                self.update_state(
                    state="FAILURE",
                    meta={
                        "API Error",
                    },
                )

                raise Exception(translations_output["output"])
            else:
                translated_prompt_and_scenario = translations_output["output"]

                # Create the Conversation object
                conversation_object = dataset_models.Conversation(
                    instance_id=output_dataset_instance,
                    parent_data=conversation_dataitem,
                    domain=conversation_dataitem.domain,
                    topic=conversation_dataitem.topic,
                    speaker_count=conversation_dataitem.speaker_count,
                    speakers_json=conversation_dataitem.speakers_json,
                    scenario=translated_prompt_and_scenario[1],
                    prompt=translated_prompt_and_scenario[0],
                    machine_translated_conversation_json=translated_conversation_json,
                    language=output_language,
                )

                # Append the conversation object to the list
                all_translated_conversation_objects.append(conversation_object)

        # Save the Conversation objects in bulk
        multi_inheritance_table_bulk_insert(all_translated_conversation_objects)

    return f"{len(all_translated_conversation_objects)} conversation dataitems created for each of languages: {str(languages)}"


@shared_task(bind=True)
def generate_ocr_prediction_json(
    self, dataset_instance_id, api_type, automate_missing_data_items
):
    """Function to generate OCR prediction data and to save to the same data item.
    Args:
        dataset_instance_id (int): ID of the dataset instance.
        api_type (str): Type of API to be used for translation. (default: google)
            Example - [indic-trans, google, indic-trans-v2, azure, blank]
        automate_missing_data_items (bool): "Boolean to translate only missing data items"
    """
    # Fetching the data items for the given dataset instance.
    success_count, total_count = 0, 0
    try:
        ocr_data_items = dataset_models.OCRDocument.objects.filter(
            instance_id=dataset_instance_id
        ).values_list(
            "id",
            "metadata_json",
            "draft_data_json",
            "file_type",
            "file_url",
            "image_url",
            "page_number",
            "language",
            "ocr_type",
            "ocr_domain",
            "ocr_transcribed_json",
            "ocr_prediction_json",
            "image_details_json",
            "parent_data",
        )
    except Exception as e:
        ocr_data_items = []

    # converting the dataset_instance to pandas dataframe.
    ocr_data_items_df = pd.DataFrame(
        ocr_data_items,
        columns=[
            "id",
            "metadata_json",
            "draft_data_json",
            "file_type",
            "file_url",
            "image_url",
            "page_number",
            "language",
            "ocr_type",
            "ocr_domain",
            "ocr_transcribed_json",
            "ocr_prediction_json",
            "image_details_json",
            "parent_data",
        ],
    )

    # Check if the dataframe is empty
    if ocr_data_items_df.shape[0] == 0:
        raise Exception("The OCR data is empty.")

    required_columns = {
        "id",
        "metadata_json",
        "draft_data_json",
        "file_type",
        "file_url",
        "image_url",
        "page_number",
        "language",
        "ocr_type",
        "ocr_domain",
        "ocr_transcribed_json",
        "ocr_prediction_json",
        "image_details_json",
        "parent_data",
    }
    if not required_columns.issubset(ocr_data_items_df.columns):
        missing_columns = required_columns - set(ocr_data_items_df.columns)
        raise ValueError(
            f"The following required columns are missing: {missing_columns}"
        )

    # Update the ocr_predictions field for each row in the DataFrame
    for index, row in ocr_data_items_df.iterrows():
        curr_id = row["id"]
        if "image_url" not in row:
            print(f"The OCR item with {curr_id} has missing image_url.")
            continue
        image_url = row["image_url"]

        # Considering the case when we should generate predictions for data items
        # which already have ocr_predictions or not.
        if automate_missing_data_items and row["ocr_prediction_json"]:
            continue
        total_count += 1
        ocr_predictions = get_batch_ocr_predictions(curr_id, image_url, api_type)
        if ocr_predictions["status"] == "Success":
            success_count += 1
            ocr_predictions_json = ocr_predictions["output"]

            # Updating the ocr_prediction_json column and saving in OCRDocument dataset with the new ocr predictions
            try:
                ocr_data_items_df.at[
                    index, "ocr_prediction_json"
                ] = ocr_predictions_json
                ocr_document = dataset_models.OCRDocument(
                    instance_id_id=dataset_instance_id,
                    id=curr_id,
                    metadata_json=row["metadata_json"],
                    draft_data_json=row["draft_data_json"],
                    file_type=row["file_type"],
                    file_url=row["file_url"],
                    image_url=image_url,
                    page_number=row["page_number"],
                    language=row["language"],
                    ocr_type=row["ocr_type"],
                    ocr_domain=row["ocr_domain"],
                    ocr_transcribed_json=row["ocr_transcribed_json"],
                    ocr_prediction_json=ocr_predictions_json,
                    image_details_json=row["image_details_json"],
                    parent_data=row["parent_data"],
                )
                with transaction.atomic():
                    ocr_document.save()
            except IntegrityError as e:
                # Handling unique constraint violations or other data integrity issues
                print(f"Error while saving dataset id- {curr_id}, IntegrityError: {e}")
            except DataError as e:
                # Handling data-related issues like incorrect data types, etc.
                print(f"Error while saving dataset id- {curr_id}, DataError: {e}")
            except Exception as e:
                # Handling other unexpected exceptions.
                print(f"Error while saving dataset id- {curr_id}, Error message: {e}")

        else:
            print(
                f"The {api_type} API has not generated predictions for data item with id-{curr_id}"
            )
    return f"{success_count} out of {total_count} populated"


@shared_task(bind=True)
def generate_asr_prediction_json(
    self, dataset_instance_id, api_type, automate_missing_data_items
):
    """Function to generate ASR prediction data and to save to the same data item.
    Args:
        dataset_instance_id (int): ID of the dataset instance.
        api_type (str): Type of API to be used for translation. (default: dhruva_asr)
            Example - [dhruva_asr, indic-trans, google, indic-trans-v2, azure, blank]
        automate_missing_data_items (bool): "Boolean to translate only missing data items"
    """
    # Fetching the data items for the given dataset instance.
    success_count, total_count = 0, 0
    try:
        asr_data_items = dataset_models.SpeechConversation.objects.filter(
            instance_id=dataset_instance_id
        ).values_list(
            "id",
            "metadata_json",
            "draft_data_json",
            "domain",
            "scenario",
            "speaker_count",
            "speakers_json",
            "language",
            "transcribed_json",
            "machine_transcribed_json",
            "audio_url",
            "audio_duration",
            "reference_raw_transcript",
            "prediction_json",
            "parent_data",
        )
    except Exception as e:
        asr_data_items = []

    # converting the dataset_instance to pandas dataframe.
    asr_data_items_df = pd.DataFrame(
        asr_data_items,
        columns=[
            "id",
            "metadata_json",
            "draft_data_json",
            "domain",
            "scenario",
            "speaker_count",
            "speakers_json",
            "language",
            "transcribed_json",
            "machine_transcribed_json",
            "audio_url",
            "audio_duration",
            "reference_raw_transcript",
            "prediction_json",
            "parent_data",
        ],
    )

    # Check if the dataframe is empty
    if asr_data_items_df.shape[0] == 0:
        raise Exception("The ASR data is empty.")

    required_columns = {
        "id",
        "metadata_json",
        "draft_data_json",
        "domain",
        "scenario",
        "speaker_count",
        "speakers_json",
        "language",
        "transcribed_json",
        "machine_transcribed_json",
        "audio_url",
        "audio_duration",
        "reference_raw_transcript",
        "prediction_json",
        "parent_data",
    }
    if not required_columns.issubset(asr_data_items_df.columns):
        missing_columns = required_columns - set(asr_data_items_df.columns)
        raise ValueError(
            f"The following required columns are missing: {missing_columns}"
        )

    # Update the asr_predictions field for each row in the DataFrame
    for index, row in asr_data_items_df.iterrows():
        curr_id = row["id"]
        if "audio_url" not in row:
            print(f"The ASR item with {curr_id} has missing audio_url.")
            continue
        audio_url = row["audio_url"]
        language = row["language"]

        # Considering the case when we should generate predictions for data items
        # which already have asr_predictions or not.
        if automate_missing_data_items and row["prediction_json"]:
            continue
        total_count += 1
        asr_predictions = get_batch_asr_predictions(
            curr_id, audio_url, api_type, language
        )
        if asr_predictions["status"] == "Success":
            success_count += 1
            prediction_json = asr_predictions["output"]

            # Updating the asr_prediction_json column and saving in SpeechConversation dataset with the new asr predictions
            try:
                asr_data_items_df.at[index, "prediction_json"] = prediction_json
                asr_document = dataset_models.SpeechConversation(
                    instance_id_id=dataset_instance_id,
                    id=curr_id,
                    metadata_json=row["metadata_json"],
                    draft_data_json=row["draft_data_json"],
                    domain=row["domain"],
                    scenario=row["scenario"],
                    speaker_count=row["speaker_count"],
                    speakers_json=row["speakers_json"],
                    language=row["language"],
                    transcribed_json=row["transcribed_json"],
                    machine_transcribed_json=row["machine_transcribed_json"],
                    audio_url=audio_url,
                    audio_duration=row["audio_duration"],
                    reference_raw_transcript=row["reference_raw_transcript"],
                    prediction_json=prediction_json,
                    parent_data=row["parent_data"],
                )
                with transaction.atomic():
                    asr_document.save()
            except IntegrityError as e:
                # Handling unique constraint violations or other data integrity issues
                print(f"Error while saving dataset id- {curr_id}, IntegrityError: {e}")
            except DataError as e:
                # Handling data-related issues like incorrect data types, etc.
                print(f"Error while saving dataset id- {curr_id}, DataError: {e}")
            except Exception as e:
                # Handling other unexpected exceptions.
                print(f"Error while saving dataset id- {curr_id}, Error message: {e}")

        else:
            print(
                f"The {api_type} API has not generated predictions for data item with id-{curr_id}"
            )
    print(f"{success_count} out of {total_count} populated")


@shared_task(bind=True)
def populate_draft_data_json(self, pk, fields_list):
    try:
        dataset_instance = DatasetInstance.objects.get(pk=pk)
    except Exception as error:
        return error
    dataset_type = dataset_instance.dataset_type
    dataset_model = apps.get_model("dataset", dataset_type)
    dataset_items = dataset_model.objects.filter(instance_id=dataset_instance)
    cnt = 0
    for dataset_item in dataset_items:
        new_draft_data_json = {}
        for field in fields_list:
            try:
                new_draft_data_json[field] = getattr(dataset_item, field)
                if new_draft_data_json[field] == None:
                    del new_draft_data_json[field]
            except:
                pass

        if new_draft_data_json != {}:
            dataset_item.draft_data_json = new_draft_data_json
            dataset_item.save()
            cnt += 1

    return f"successfully populated {cnt} dataset items with draft_data_json"


# The flow for project_reports- schedule_mail_for_project_reports -> get_proj_objs, get_stats ->
# get_modified_stats_result, get_stats_helper -> update_meta_stats -> calculate_ced_between_two_annotations,
# calculate_wer_between_two_annotations, get_most_recent_annotation.
@shared_task(queue="reports")
def schedule_mail_for_project_reports(
    project_type,
    user_id,
    anno_stats,
    meta_stats,
    complete_stats,
    workspace_level_reports,
    organization_level_reports,
    dataset_level_reports,
    wid,
    oid,
    did,
    language,
):
    proj_objs = get_proj_objs(
        workspace_level_reports,
        organization_level_reports,
        dataset_level_reports,
        project_type,
        wid,
        oid,
        did,
        language,
    )
    if len(proj_objs) == 0:
        print("No projects found")
        return 0
    user = User.objects.get(id=user_id)
    result = get_stats(
        proj_objs, anno_stats, meta_stats, complete_stats, project_type, user
    )
    df = pd.DataFrame.from_dict(result)
    transposed_df = df.transpose()
    content = transposed_df.to_csv(index=True)
    content_type = "text/csv"

    if workspace_level_reports:
        workspace = Workspace.objects.filter(id=wid)
        name = workspace[0].workspace_name
        type = "workspace"
        filename = f"{name}_user_analytics.csv"
    elif dataset_level_reports:
        dataset = DatasetInstance.objects.filter(instance_id=did)
        name = dataset[0].instance_name
        type = "dataset"
        filename = f"{name}_user_analytics.csv"
    else:
        organization = Organization.objects.filter(id=oid)
        name = organization[0].title
        type = "organization"
        filename = f"{name}_user_analytics.csv"

    message = (
        "Dear "
        + str(user.username)
        + f",\nYour project reports for the {type}"
        + f"{name}"
        + " are ready.\n Thanks for contributing on Shoonya!"
        + "\nProject Type: "
        + f"{project_type}"
    )

    email = EmailMessage(
        f"{name}" + " Payment Reports",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        attachments=[(filename, content, content_type)],
    )
    try:
        email.send()
    except Exception as e:
        print(f"An error occurred while sending email: {e}")
    print(f"Email sent successfully - {user_id}")


def get_stats(proj_objs, anno_stats, meta_stats, complete_stats, project_type, user):
    result = {}
    for proj in proj_objs:
        annotations = Annotation.objects.filter(task__project_id=proj.id)
        (
            result_ann_anno_stats,
            result_rev_anno_stats,
            result_sup_anno_stats,
            result_ann_meta_stats,
            result_rev_meta_stats,
            result_sup_meta_stats,
            average_ann_vs_rev_CED,
            average_ann_vs_rev_WER,
            average_rev_vs_sup_CED,
            average_rev_vs_sup_WER,
            average_ann_vs_sup_CED,
            average_ann_vs_sup_WER,
        ) = get_stats_definitions()
        for ann_obj in annotations:
            if ann_obj.annotation_type == ANNOTATOR_ANNOTATION:
                try:
                    get_stats_helper(
                        anno_stats,
                        meta_stats,
                        complete_stats,
                        result_ann_anno_stats,
                        result_ann_meta_stats,
                        ann_obj,
                        project_type,
                        average_ann_vs_rev_CED,
                        average_ann_vs_rev_WER,
                        average_rev_vs_sup_CED,
                        average_rev_vs_sup_WER,
                        average_ann_vs_sup_CED,
                        average_ann_vs_sup_WER,
                    )
                except:
                    continue
            elif ann_obj.annotation_type == REVIEWER_ANNOTATION:
                try:
                    get_stats_helper(
                        anno_stats,
                        meta_stats,
                        complete_stats,
                        result_rev_anno_stats,
                        result_rev_meta_stats,
                        ann_obj,
                        project_type,
                        average_ann_vs_rev_CED,
                        average_ann_vs_rev_WER,
                        average_rev_vs_sup_CED,
                        average_rev_vs_sup_WER,
                        average_ann_vs_sup_CED,
                        average_ann_vs_sup_WER,
                    )
                except:
                    continue
            elif ann_obj.annotation_type == SUPER_CHECKER_ANNOTATION:
                try:
                    get_stats_helper(
                        anno_stats,
                        meta_stats,
                        complete_stats,
                        result_sup_anno_stats,
                        result_sup_meta_stats,
                        ann_obj,
                        project_type,
                        average_ann_vs_rev_CED,
                        average_ann_vs_rev_WER,
                        average_rev_vs_sup_CED,
                        average_rev_vs_sup_WER,
                        average_ann_vs_sup_CED,
                        average_ann_vs_sup_WER,
                    )
                except:
                    continue
        result[f"{proj.id} - {proj.title}"] = get_modified_stats_result(
            result_ann_meta_stats,
            result_rev_meta_stats,
            result_sup_meta_stats,
            result_ann_anno_stats,
            result_rev_anno_stats,
            result_sup_anno_stats,
            anno_stats,
            meta_stats,
            complete_stats,
            average_ann_vs_rev_CED,
            average_ann_vs_rev_WER,
            average_rev_vs_sup_CED,
            average_rev_vs_sup_WER,
            average_ann_vs_sup_CED,
            average_ann_vs_sup_WER,
            proj.id,
            user,
        )

    return result


def get_stats_definitions():
    result_ann_anno_stats = {
        "unlabeled": 0,
        "labeled": 0,
        "skipped": 0,
        "draft": 0,
        "to_be_revised": 0,
    }
    result_rev_anno_stats = {
        "unreviewed": 0,
        "skipped": 0,
        "draft": 0,
        "to_be_revised": 0,
        "accepted": 0,
        "accepted_with_minor_changes": 0,
        "accepted_with_major_changes": 0,
        "rejected": 0,
    }
    result_sup_anno_stats = {
        "unvalidated": 0,
        "skipped": 0,
        "draft": 0,
        "validated": 0,
        "validated_with_changes": 0,
        "rejected": 0,
    }
    result_ann_meta_stats = {
        "unlabeled": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "skipped": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "draft": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "labeled": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "to_be_revised": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
    }
    result_rev_meta_stats = {
        "unreviewed": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "skipped": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "draft": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "to_be_revised": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "accepted": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "accepted_with_minor_changes": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "accepted_with_major_changes": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "rejected": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
    }
    result_sup_meta_stats = {
        "unvalidated": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "skipped": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "draft": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "validated": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "validated_with_changes": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
        "rejected": {
            "Raw Audio Duration": 0,
            "Segment Duration": 0,
            "Not Null Segment Duration": 0,
            "Word Count": 0,
        },
    }
    return (
        result_ann_anno_stats,
        result_rev_anno_stats,
        result_sup_anno_stats,
        result_ann_meta_stats,
        result_rev_meta_stats,
        result_sup_meta_stats,
        [],
        [],
        [],
        [],
        [],
        [],
    )


def get_modified_stats_result(
    result_ann_meta_stats,
    result_rev_meta_stats,
    result_sup_meta_stats,
    result_ann_anno_stats,
    result_rev_anno_stats,
    result_sup_anno_stats,
    anno_stats,
    meta_stats,
    complete_stats,
    average_ann_vs_rev_CED,
    average_ann_vs_rev_WER,
    average_rev_vs_sup_CED,
    average_rev_vs_sup_WER,
    average_ann_vs_sup_CED,
    average_ann_vs_sup_WER,
    proj_id,
    user,
):
    result = {}
    if anno_stats or complete_stats:
        for key, value in result_ann_anno_stats.items():
            result[f"Annotator - {key.replace('_', ' ').title()} Annotations"] = value
        for key, value in result_rev_anno_stats.items():
            result[f"Reviewer - {key.replace('_', ' ').title()} Annotations"] = value
        for key, value in result_sup_anno_stats.items():
            result[
                f"Superchecker - {key.replace('_', ' ').title()} Annotations"
            ] = value
    if meta_stats or complete_stats:
        for key, stats in result_ann_meta_stats.items():
            update_stats(stats)
        for key, stats in result_rev_meta_stats.items():
            update_stats(stats)
        for key, stats in result_sup_meta_stats.items():
            update_stats(stats)
        for key, value in result_ann_meta_stats.items():
            for sub_key in value.keys():
                result[
                    f"Annotator - {key.replace('_', ' ').title()} {sub_key}"
                ] = value[sub_key]
        for key, value in result_rev_meta_stats.items():
            for sub_key in value.keys():
                result[f"Reviewer - {key.replace('_', ' ').title()} {sub_key}"] = value[
                    sub_key
                ]
        for key, value in result_sup_meta_stats.items():
            for sub_key in value.keys():
                result[
                    f"Superchecker - {key.replace('_', ' ').title()} {sub_key}"
                ] = value[sub_key]

        result[
            "Average Annotator VS Reviewer Character Edit Distance"
        ] = "{:.2f}".format(get_average_of_a_list(average_ann_vs_rev_CED))
        result["Average Annotator VS Reviewer Word Error Rate"] = "{:.2f}".format(
            get_average_of_a_list(average_ann_vs_rev_WER)
        )
        result[
            "Average Reviewer VS Superchecker Character Edit Distance"
        ] = "{:.2f}".format(get_average_of_a_list(average_rev_vs_sup_CED))
        result["Average Reviewer VS Superchecker Word Error Rate"] = "{:.2f}".format(
            get_average_of_a_list(average_rev_vs_sup_WER)
        )
        result[
            "Average Annotator VS Superchecker Character Edit Distance"
        ] = "{:.2f}".format(get_average_of_a_list(average_ann_vs_sup_CED))
        result["Average Annotator VS Superchecker Word Error Rate"] = "{:.2f}".format(
            get_average_of_a_list(average_ann_vs_sup_WER)
        )
    # adding unassigned tasks count
    result["Annotator - Unassigned Tasks"] = get_task_count_unassigned(proj_id, user)
    result["Reviewer - Unassigned Tasks"] = (
        Task.objects.filter(project_id=proj_id)
        .filter(task_status=ANNOTATED)
        .filter(review_user__isnull=True)
        .exclude(annotation_users=user.id)
        .count()
    )
    result["Superchecker - Unassigned Tasks"] = (
        Task.objects.filter(project_id=proj_id)
        .filter(task_status=REVIEWED)
        .filter(super_check_user__isnull=True)
        .exclude(annotation_users=user.id)
        .exclude(review_user=user.id)
        .count()
    )
    return result


def update_stats(stats):
    raw_audio_duration = stats["Raw Audio Duration"]
    segment_duration = stats["Segment Duration"]
    not_null_segment_duration = stats["Not Null Segment Duration"]
    converted_duration_rad = convert_seconds_to_hours(raw_audio_duration)
    converted_duration_sd = convert_seconds_to_hours(segment_duration)
    converted_duration_nsd = convert_seconds_to_hours(not_null_segment_duration)
    stats["Raw Audio Duration"] = converted_duration_rad
    stats["Segment Duration"] = converted_duration_sd
    stats["Not Null Segment Duration"] = converted_duration_nsd
    return 0


def get_average_of_a_list(arr):
    if not isinstance(arr, list):
        return 0
    total_sum = 0
    total_length = 0
    for num in arr:
        if isinstance(num, int):
            total_sum += num
            total_length += 1
    return total_sum / total_length if total_length > 0 else 0


def get_proj_objs(
    workspace_level_reports,
    organization_level_reports,
    dataset_level_reports,
    project_type,
    wid,
    oid,
    did,
    language,
):
    if workspace_level_reports:
        if project_type:
            if language != "NULL":
                proj_objs = Project.objects.filter(
                    workspace_id=wid,
                    project_type=project_type,
                    tgt_language=language,
                )
            else:
                proj_objs = Project.objects.filter(
                    workspace_id=wid, project_type=project_type
                )
        else:
            proj_objs = Project.objects.filter(workspace_id=wid)
    elif organization_level_reports:
        if project_type:
            if language != "NULL":
                proj_objs = Project.objects.filter(
                    organization_id=oid,
                    project_type=project_type,
                    tgt_language=language,
                )
            else:
                proj_objs = Project.objects.filter(
                    organization_id=oid, project_type=project_type
                )
        else:
            proj_objs = Project.objects.filter(organization_id=oid)
    elif dataset_level_reports:
        if project_type:
            if language != "NULL":
                proj_objs = Project.objects.filter(
                    dataset_id=did,
                    project_type=project_type,
                    tgt_language=language,
                )
            else:
                proj_objs = Project.objects.filter(
                    dataset_id=did, project_type=project_type
                )
        else:
            proj_objs = Project.objects.filter(dataset_id=did)
    else:
        proj_objs = {}
    return proj_objs


def get_stats_helper(
    anno_stats,
    meta_stats,
    complete_stats,
    result_anno_stats,
    result_meta_stats,
    ann_obj,
    project_type,
    average_ann_vs_rev_CED,
    average_ann_vs_rev_WER,
    average_rev_vs_sup_CED,
    average_rev_vs_sup_WER,
    average_ann_vs_sup_CED,
    average_ann_vs_sup_WER,
):
    ced_project_type_choices = ["ContextualTranslationEditing"]
    task_obj = ann_obj.task
    task_data = task_obj.data

    if anno_stats or complete_stats:
        update_anno_stats(result_anno_stats, ann_obj, anno_stats)
        if anno_stats:
            return 0
    update_meta_stats(
        result_meta_stats,
        ann_obj,
        task_data,
        project_type,
        ced_project_type_choices,
    )
    if task_obj.task_status == REVIEWED:
        if ann_obj.annotation_type == REVIEWER_ANNOTATION:
            if project_type in ced_project_type_choices:
                try:
                    average_ann_vs_rev_CED.append(
                        get_average_of_a_list(
                            calculate_ced_between_two_annotations(
                                get_most_recent_annotation(ann_obj.parent_annotation),
                                get_most_recent_annotation(ann_obj),
                            )
                        )
                    )
                except Exception as error:
                    pass
            elif project_type in get_audio_project_types():
                try:
                    # we pass the reviewer first has the reference sentence and annotator second which
                    # has the hypothesis sentence.
                    # A higher grade has the reference sentence and the lower has the hypothesis sentence
                    average_ann_vs_rev_WER.append(
                        calculate_wer_between_two_annotations(
                            get_most_recent_annotation(ann_obj).result,
                            get_most_recent_annotation(
                                ann_obj.parent_annotation
                            ).result,
                        )
                    )
                except Exception as error:
                    pass
    elif task_obj.task_status == SUPER_CHECKED:
        if ann_obj.annotation_type == SUPER_CHECKER_ANNOTATION:
            if project_type in ced_project_type_choices:
                try:
                    average_ann_vs_rev_CED.append(
                        get_average_of_a_list(
                            calculate_ced_between_two_annotations(
                                get_most_recent_annotation(
                                    ann_obj.parent_annotation.parent_annotation
                                ),
                                get_most_recent_annotation(ann_obj.parent_annotation),
                            )
                        )
                    )
                except Exception as error:
                    pass
                try:
                    average_rev_vs_sup_CED.append(
                        get_average_of_a_list(
                            calculate_ced_between_two_annotations(
                                get_most_recent_annotation(ann_obj.parent_annotation),
                                get_most_recent_annotation(ann_obj),
                            )
                        )
                    )
                except Exception as error:
                    pass
                try:
                    average_ann_vs_sup_CED.append(
                        get_average_of_a_list(
                            calculate_ced_between_two_annotations(
                                get_most_recent_annotation(
                                    ann_obj.parent_annotation.parent_annotation
                                ),
                                get_most_recent_annotation(ann_obj),
                            )
                        )
                    )
                except Exception as error:
                    pass
            elif project_type in get_audio_project_types():
                try:
                    average_ann_vs_rev_WER.append(
                        calculate_wer_between_two_annotations(
                            get_most_recent_annotation(
                                ann_obj.parent_annotation
                            ).result,
                            get_most_recent_annotation(
                                ann_obj.parent_annotation.parent_annotation
                            ).result,
                        )
                    )
                except Exception as error:
                    pass
                try:
                    average_rev_vs_sup_WER.append(
                        calculate_wer_between_two_annotations(
                            get_most_recent_annotation(ann_obj).result,
                            get_most_recent_annotation(
                                ann_obj.parent_annotation
                            ).result,
                        )
                    )
                except Exception as error:
                    pass
                try:
                    average_ann_vs_sup_WER.append(
                        calculate_wer_between_two_annotations(
                            get_most_recent_annotation(ann_obj).result,
                            get_most_recent_annotation(
                                ann_obj.parent_annotation.parent_annotation
                            ).result,
                        )
                    )
                except Exception as error:
                    pass
    return 0


def update_anno_stats(result_anno_stats, ann_obj, anno_stats):
    result_anno_stats[ann_obj.annotation_status] += 1
    return 0 if anno_stats else None


def update_meta_stats(
    result_meta_stats, ann_obj, task_data, project_type, ced_project_type_choices
):
    if project_type in ced_project_type_choices:
        try:
            result_meta_stats[ann_obj.annotation_status]["Word Count"] += task_data[
                "word_count"
            ]
        except Exception as e:
            return 0
    elif "OCRTranscription" in project_type:
        result_meta_stats[ann_obj.annotation_status]["Word Count"] += ocr_word_count(
            ann_obj.result
        )
    elif project_type in get_audio_project_types():
        result_meta_stats[ann_obj.annotation_status]["Raw Audio Duration"] += task_data[
            "audio_duration"
        ]
        result_meta_stats[ann_obj.annotation_status][
            "Segment Duration"
        ] += get_audio_transcription_duration(ann_obj.result)
        result_meta_stats[ann_obj.annotation_status][
            "Not Null Segment Duration"
        ] += get_not_null_audio_transcription_duration(ann_obj.result, ann_obj.id)


def calculate_ced_between_two_annotations(annotation1, annotation2):
    sentence_operation = SentenceOperationViewSet()
    ced_list = []
    for i in range(len(annotation1.result)):
        if "value" in annotation1.result[i]:
            if "text" in annotation1.result[i]["value"]:
                str1 = annotation1.result[i]["value"]["text"]
            else:
                continue
        else:
            continue
        if "value" in annotation2.result[i]:
            if "text" in annotation2.result[i]["value"]:
                str2 = annotation2.result[i]["value"]["text"]
            else:
                continue
        else:
            continue
        data = {"sentence1": str1, "sentence2": str2}
        try:
            char_level_distance = (
                sentence_operation.calculate_normalized_character_level_edit_distance(
                    data
                )
            )
            ced_list.append(
                char_level_distance.data["normalized_character_level_edit_distance"]
            )
        except Exception as e:
            continue
    return ced_list


def calculate_wer_between_two_annotations(annotation1, annotation2):
    try:
        return calculate_word_error_rate_between_two_audio_transcription_annotation(
            annotation1, annotation2
        )
    except Exception as e:
        return 0


def get_most_recent_annotation(annotation):
    duplicate_ann = Annotation.objects.filter(
        task=annotation.task, annotation_type=annotation.annotation_type
    )
    for ann in duplicate_ann:
        if annotation.updated_at < ann.updated_at:
            annotation = ann
    return annotation


@shared_task(bind=True)
def schedule_mail_to_download_all_projects(
    self, workspace_level_projects, dataset_level_projects, wid, did, user_id
):
    download_lock = threading.Lock()
    download_lock.acquire()
    proj_objs = get_proj_objs(
        workspace_level_projects,
        False,
        dataset_level_projects,
        None,
        wid,
        0,
        did,
    )
    if len(proj_objs) == 0 and workspace_level_projects:
        print(f"No projects found for workspace id- {wid}")
        return 0
    elif len(proj_objs) == 0 and dataset_level_projects:
        print(f"No projects found for dataset id- {did}")
        return 0
    user = User.objects.get(id=user_id)
    with tempfile.TemporaryDirectory() as temp_dir:
        for proj in proj_objs:
            proj_view_set_obj = ProjectViewSet()
            factory = APIRequestFactory()
            url = f"/projects/{proj.id}/download"
            query_params = QueryDict(mutable=True)
            query_params["include_input_data_metadata_json"] = "true"
            query_params["export_type"] = "CSV"
            query_params[
                "task_status"
            ] = "incomplete,annotated,reviewed,super_checked,exported"
            custom_request = Request(factory.get(url, data=query_params, timeout=15))
            custom_request.user = user
            try:
                proj_file = proj_view_set_obj.download(custom_request, proj.id)
            except Exception as e:
                print(f"Downloading project timed out, Project id- {proj.id}")
                continue
            file_path = os.path.join(temp_dir, f"{proj.id} - {proj.title}.csv")
            with open(file_path, "wb") as f:
                f.write(proj_file.content)
        url = upload_all_projects_to_blob_and_get_url(temp_dir)
    if url:
        message = (
            "Dear "
            + str(user.username)
            + f",\nYou can download all the projects by clicking on- "
            + f"{url}"
            + " This link is active only for 1 hour.\n Thanks for contributing on Shoonya!"
        )
        email = EmailMessage(
            f"{user.username}" + "- Link to download all projects",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        try:
            email.send()
        except Exception as e:
            print(f"An error occurred while sending email: {e}")
            return 0
        download_lock.release()
        print(f"Email sent successfully - {user_id}")
    else:
        download_lock.release()
        print(url)


def upload_all_projects_to_blob_and_get_url(csv_files_directory):
    date_time_string = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_file_name = f"output_all_projects - {date_time_string}.zip"
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
    CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS = os.getenv(
        "CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS"
    )
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS
        )
    except Exception as e:
        return "Error in connecting to blob_service_client or container_client"
    if not test_container_connection(
        AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS
    ):
        print("Azure Blob Storage connection test failed. Exiting...")
        return "test_container_connection failed"
    blob_url = ""
    if os.path.exists(csv_files_directory):
        zip_file_path_on_disk = csv_files_directory + "/" + f"{zip_file_name}"
        try:
            with zipfile.ZipFile(
                zip_file_path_on_disk, "w", zipfile.ZIP_DEFLATED
            ) as zipf:
                for root, dirs, files in os.walk(csv_files_directory):
                    for file in files:
                        if file.endswith(".csv"):
                            file_path = os.path.join(root, file)
                            zipf.write(
                                file_path,
                                os.path.relpath(file_path, csv_files_directory),
                            )
        except Exception as e:
            return "Error in creating zip file"
        blob_client = container_client.get_blob_client(zip_file_name)
        with open(zip_file_path_on_disk, "rb") as file:
            blob_client.upload_blob(file, blob_type="BlockBlob")
        try:
            expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
            account_name = extract_account_name(AZURE_STORAGE_CONNECTION_STRING)
            endpoint_suffix = extract_endpoint_suffix(AZURE_STORAGE_CONNECTION_STRING)
            sas_token = generate_blob_sas(
                container_name=CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS,
                blob_name=blob_client.blob_name,
                account_name=account_name,
                account_key=extract_account_key(AZURE_STORAGE_CONNECTION_STRING),
                permission=BlobSasPermissions(read=True),
                expiry=expiry,
            )
        except Exception as e:
            return "Error in generating url"
        blob_url = f"https://{account_name}.blob.{endpoint_suffix}/{CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS}/{blob_client.blob_name}?{sas_token}"
    return blob_url
