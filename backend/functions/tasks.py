import pandas as pd
from celery import shared_task
from dataset import models as dataset_models
from utils.custom_bulk_create import multi_inheritance_table_bulk_insert

from .utils import (
    get_batch_translations,
)


## CELERY SHARED TASKS
@shared_task(bind=True)
def sentence_text_translate_and_save_translation_pairs(
    self,
    languages,
    input_dataset_instance_id,
    output_dataset_instance_id,
    batch_size,
    api_type="indic-trans",
    checks_for_particular_languages=False,
):  # sourcery skip: raise-specific-error
    """Function to translate SentenceTexts and to save the TranslationPairs in the database.

    Args:
        languages (list): List of output languages for the translations.
        input_dataset_instance_id (int): ID of the input dataset instance.
        output_dataset_instance_id (int): ID of the output dataset instance.
        batch_size (int): Number of sentences to be translated in a single batch.
        api_type (str): Type of API to be used for translation. (default: indic-trans)
            Allowed - [indic-trans, google]
        checks_for_particular_languages (bool): If True, checks for the particular languages in the translations.
    """

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
    input_sentences_df = pd.DataFrame(
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
    input_sentences_df = input_sentences_df[
        (input_sentences_df["quality_status"] == "Clean")
    ].reset_index(drop=True)

    # Check if the dataframe is empty
    if input_sentences_df.shape[0] == 0:

        # Update the task status
        self.update_state(
            state="FAILURE",
            meta={
                "No sentences to upload.",
            },
        )

        raise Exception("No clean sentences found. Perform project export first.")

    # Make a sentence list for valid sentences to be translated
    all_sentences_to_be_translated = input_sentences_df["corrected_text"].tolist()

    # Get the output dataset instance
    output_dataset_instance = dataset_models.DatasetInstance.objects.get(
        instance_id=output_dataset_instance_id
    )

    # Keep count of the number of sentences translated
    translated_sentences_count = 0

    # Iterate through the languages
    for output_language in languages:

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
            Allowed - [indic-trans, google]
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
