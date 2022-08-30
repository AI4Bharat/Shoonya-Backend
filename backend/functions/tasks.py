import pandas as pd
from celery import shared_task
from dataset import models as dataset_models

from utils.custom_bulk_create import multi_inheritance_table_bulk_insert

from .utils import (
    get_batch_translations_using_google_translate,
    get_batch_translations_using_indictrans_nmt_api,
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

    # Iterate through the languages
    for output_language in languages:
        
        # Create a TranslationPair object list
        translation_pair_objects = []
        
        # Loop through all the sentences to be translated in batch format
        for i in range(0, len(all_sentences_to_be_translated), batch_size):

            batch_of_input_sentences = all_sentences_to_be_translated[
                i : i + batch_size
            ]

            # Check the API type
            if api_type == "indic-trans":

                # Get the translation using the Indictrans NMT API
                translations_output = get_batch_translations_using_indictrans_nmt_api(
                    sentence_list=batch_of_input_sentences,
                    source_language=input_sentences_df["input_language"].iloc[0],
                    target_language=output_language,
                    checks_for_particular_languages=checks_for_particular_languages,
                )

                # Check if the translations output is a string or a list
                if isinstance(translations_output, str):

                    # Update the task status and raise an exception
                    self.update_state(
                        state="FAILURE",
                        meta={
                            "Error: {}".format(translations_output),
                        },
                    )

                    raise Exception(translations_output)
                else:
                    translated_sentences = translations_output

            elif api_type == "google":
                # Get the translation using the Indictrans NMT API
                translations_output = get_batch_translations_using_google_translate(
                    sentence_list=batch_of_input_sentences,
                    source_language=input_sentences_df["input_language"].iloc[0],
                    target_language=output_language,
                    checks_for_particular_languages=checks_for_particular_languages,
                )
                # Check if translation output returned a list or a string
                if type(translations_output) != list:
                    # Update the task status and raise an exception
                    self.update_state(
                        state="FAILURE",
                        meta={
                            "Google API Error",
                        },
                    )

                    raise Exception("Google API Error")
                else:
                    translated_sentences = translations_output

            else:
                # Update the task status and raise an exception
                self.update_state(
                    state="FAILURE",
                    meta={
                        "Invalid API type. Allowed - [indic-trans, google]",
                    },
                )

                raise Exception("Invalid API type. Allowed - [indic-trans, google]")

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

    return f"{len(translation_pair_objects)} translation pairs created for languages: {str(languages)}"
