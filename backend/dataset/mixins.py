import tablib
from django.db.models.query import QuerySet


EXPORT_FIELD_RULES = {
    "SentenceText": {
        "mandatory": ["language", "text", "domain", "quality_status"],
        "shortenfields": ["instruction_data", "output"],
    },
    "TranslationPair": {
        "mandatory": ["input_language", "output_language", "input_text", "domain"],
        "shortenfields": ["input_text", "output_text", "machine_translation", "context"],
    },
    "OCRDocument": {
        "mandatory": ["file_type", "image_url", "page_number", "language", "ocr_type", "ocr_domain"],
        "shortenfields": ["ocr_transcribed_json", "ocr_prediction_json"],
    },
    "BlockText": {
        "mandatory": ["language", "text", "domain"],
        "shortenfields": ["text", "splitted_text_prediction", "splitted_text"],
    },
    "Conversation": {
        "mandatory": ["speaker_count", "language", "conversation_quality_status"],
        "shortenfields": ["prompt", "conversation_json", "machine_translated_conversation_json", "unverified_conversation_json"],
    },
    "SpeechConversation": {
        "mandatory": ["speaker_count", "speakers_json", "language", "audio_url", "audio_duration"],
        "shortenfields": ["transcribed_json", "machine_transcribed_json", "reference_raw_transcript", "prediction_json", "final_transcribed_json"],
    },
}

AUTO_GENERATED_FIELDS = ["id","parent_data", "instance_id"]


class ResourceMixin:
    """
    Resource Mixin for streaming Dataset file
    """

    def _get_field_rule(self, rule_key: str) -> list:
        model_name = self._meta.model.__name__
        return EXPORT_FIELD_RULES.get(model_name, {}).get(rule_key, [])

    def export_sample(self, export_type: str, data_item) -> str:
        """Export a single formatted sample row with marked headers and instruction rows."""
        dataset = self.export([data_item])

        mandatory = set(self._get_field_rule("mandatory")) - set(AUTO_GENERATED_FIELDS)
        dataset.headers = [f"{h}*" if h in mandatory else h for h in dataset.headers]

        auto_gen_indices = [
            i for i, h in enumerate(dataset.headers)
            if h in AUTO_GENERATED_FIELDS
        ]
        row = list(dataset[0])
        for i in auto_gen_indices:
            row[i] = ""
        dataset[0] = tuple(row)

        pad = [""] * (len(dataset.headers) - 1)
        dataset.insert(1, ["Fields marked * are mandatory."] + pad)
        dataset.insert(2, [f"Fields {', '.join(AUTO_GENERATED_FIELDS)} are auto-generated, leave blank."] + pad)

        export_type = export_type.lower()
        if export_type == "tsv":
            return dataset.tsv
        if export_type == "json":
            return dataset.json
        return dataset.csv


    def export_as_generator(self, export_type, queryset=None, *args, **kwargs):
        self.before_export(queryset, *args, **kwargs)
        if queryset is None:
            queryset = self.get_queryset()
        headers = self.get_export_headers()
        data = tablib.Dataset(headers=headers)
        # Return headers
        if export_type == "tsv":
            yield data.tsv
        else:
            yield data.csv

        if isinstance(queryset, QuerySet):
            # Iterate without the queryset cache, to avoid wasting memory when
            # exporting large datasets.
            iterable = queryset.iterator()
        else:
            iterable = queryset
        for obj in iterable:
            # Return subset of the data (one row)
            # This is a simple implementation to fix the tablib library which is missing returning the data as
            # generator
            data = tablib.Dataset()
            data.append(self.export_resource(obj))
            if export_type == "tsv":
                yield data.tsv
            else:
                yield data.csv

        self.after_export(queryset, data, *args, **kwargs)

        yield
