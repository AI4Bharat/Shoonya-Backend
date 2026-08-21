"""
Utility functions for the "Create Dataset & Project" automation pipeline.

These helpers are pure functions (no DB/network access, except where noted)
so that CSV validation can be reused both for the synchronous
`validate_pipeline_csv` preview endpoint and inside the Celery pipeline task.
"""
import csv
import io
import json
import os
import re
from urllib.parse import urlencode, urlparse

READ = "Read"
EXTEMPORE = "Extempore"

TASK_LIMITS = {
    READ: 1000,
    EXTEMPORE: 1200,
}

REQUIRED_COLUMNS = [
    "Language",
    "Audio ID",
    "Audio Link",
    "Audio Duration",
    "Reference Transcript",
    "Verbatim Transcription",
    "Metadata",
]

# Rule 1
TAMIL_LANGUAGES = {"Tamil"}
# Rule 2
BLANK_ACOUSTIC_LANGUAGES = {"Marathi", "English", "Sindhi", "Urdu", "Malayalam"}

REVIEW_ACOUSTIC_STAGE = 2


def parse_input_csv(csv_string):
    """Parses the raw input CSV string into a list of row dicts + fieldnames."""
    reader = csv.DictReader(io.StringIO(csv_string))
    rows = list(reader)
    return rows, list(reader.fieldnames or [])


def get_row_type(row):
    """Determines Read vs Extempore from the CSV `Type` column (e.g. 'Part A-READ')."""
    type_str = (row.get("Type") or "").strip().upper()
    return EXTEMPORE if "EXTEMPORE" in type_str else READ


def get_row_part(row):
    """Determines Part A / Part B from the CSV `Part A/ Part B` column."""
    part = (row.get("Part A/ Part B") or "").strip()
    return part if part in ("Part A", "Part B") else "Part A"


def get_domain(row_type, part):
    return f"[{row_type}][{part}]"


_DOMAIN_RE = re.compile(r"^\[(?P<type>[^\]]+)\]\[(?P<part>[^\]]+)\]$")


def parse_domain(domain):
    """Parses a domain string like '[Read][Part A]' back into (type, part)."""
    match = _DOMAIN_RE.match(domain or "")
    if not match:
        return None, None
    return match.group("type"), match.group("part")


def validate_input_csv(rows, fieldnames):
    """Validates parsed CSV rows and returns a preview/validation summary."""
    errors = []

    missing_columns = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")

    if not rows:
        errors.append("CSV has no data rows.")

    languages, types, parts, speakers = set(), set(), set(), set()
    seen_audio_ids, duplicate_audio_ids = set(), set()

    for idx, row in enumerate(rows, start=1):
        language = (row.get("Language") or "").strip()
        audio_link = (row.get("Audio Link") or "").strip()
        audio_id = (row.get("Audio ID") or "").strip()

        if not language:
            errors.append(f"Row {idx}: missing Language")
        if not audio_link:
            errors.append(f"Row {idx}: missing Audio Link")

        if audio_id:
            if audio_id in seen_audio_ids:
                duplicate_audio_ids.add(audio_id)
            seen_audio_ids.add(audio_id)

        if language:
            languages.add(language)
        types.add(get_row_type(row))
        parts.add(get_row_part(row))

        raw_metadata = (row.get("Metadata") or "").strip()
        if raw_metadata:
            try:
                metadata = json.loads(raw_metadata)
                if isinstance(metadata, dict) and metadata.get("Name"):
                    speakers.add(metadata["Name"])
            except Exception:
                errors.append(f"Row {idx}: invalid Metadata JSON")

        raw_verbatim = (row.get("Verbatim Transcription") or "").strip()
        if raw_verbatim:
            try:
                json.loads(raw_verbatim)
            except Exception:
                errors.append(f"Row {idx}: invalid Verbatim Transcription JSON")

    if duplicate_audio_ids:
        errors.append(
            f"Duplicate Audio IDs found: {', '.join(sorted(duplicate_audio_ids))}"
        )
    if len(languages) > 1:
        errors.append(
            f"CSV contains multiple languages ({', '.join(sorted(languages))}). "
            "Each upload must contain a single language."
        )
    if len(parts) > 1:
        errors.append(
            f"CSV contains multiple parts ({', '.join(sorted(parts))}). "
            "Each upload must contain a single part."
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "row_count": len(rows),
        "languages": sorted(languages),
        "types": sorted(types),
        "parts": sorted(parts),
        "speakers": sorted(speakers),
        "preview_rows": rows[:5],
    }


def get_audio_folder_name(source_url):
    """Extracts the MinIO/ShaktiCloud target folder name from the source Audio Link.

    e.g. 'https://storage.googleapis.com/delivery_team_data/hindi_bodhan_batch1/139335.wav'
    -> 'hindi_bodhan_batch1'
    """
    path = urlparse(source_url).path
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 2:
        return segments[-2]
    return "misc"


def build_target_object_key(folder_name, filename):
    return f"asr/sakshi/JT/{folder_name}/{filename}"


def build_shoonya_row(input_row, audio_url):
    """Transforms one input CSV row into a Shoonya SpeechConversation CSV row dict."""
    raw_audio_id = (input_row.get("Audio ID") or "").strip()
    audio_id = int(raw_audio_id) if raw_audio_id.isdigit() else raw_audio_id

    raw_user_id = (input_row.get("User ID") or "").strip()
    raw_class = (input_row.get("Class") or "").strip()
    class_val = int(raw_class) if raw_class.isdigit() else raw_class
    delivery_date = (input_row.get("Date of delivery") or "").strip()
    others = (input_row.get("Others") or "").strip()

    raw_metadata = (input_row.get("Metadata") or "").strip()
    metadata_dict = {}
    if raw_metadata:
        try:
            metadata_dict = json.loads(raw_metadata)
        except Exception:
            metadata_dict = {}
    metadata_dict["audio_id"] = audio_id
    metadata_dict["user_id"] = raw_user_id
    metadata_dict["class"] = class_val
    metadata_dict["delivery_date"] = delivery_date
    if others:
        metadata_dict["others"] = others

    raw_verbatim = (input_row.get("Verbatim Transcription") or "").strip()
    segments = []
    if raw_verbatim:
        try:
            segments = json.loads(raw_verbatim)
        except Exception:
            segments = []
    for segment in segments:
        if isinstance(segment, dict) and "start" in segment and "end" in segment:
            segment["speaker_id"] = 0
    draft_data_json = {"transcribed_json": {"verbatim_transcribed_json": segments}}

    name = metadata_dict.get("Name", "Speaker 0")
    gender = metadata_dict.get("Gender", "U")
    speakers_json = [{"name": name, "gender": gender, "speaker_id": 0}]

    row_type = get_row_type(input_row)
    part = get_row_part(input_row)

    raw_duration = (input_row.get("Audio Duration") or "").strip()
    try:
        audio_duration = float(raw_duration)
    except ValueError:
        audio_duration = 0

    return {
        "id": "",
        "parent_data": "",
        "instance_id": "",
        "metadata_json": json.dumps(metadata_dict, ensure_ascii=False),
        "draft_data_json": json.dumps(draft_data_json, ensure_ascii=False),
        "domain": get_domain(row_type, part),
        "scenario": row_type,
        "speaker_count": 1,
        "speakers_json": json.dumps(speakers_json, ensure_ascii=False),
        "language": (input_row.get("Language") or "").strip(),
        "transcribed_json": "",
        "machine_transcribed_json": "",
        "audio_url": audio_url,
        "audio_duration": audio_duration,
        "reference_raw_transcript": (input_row.get("Reference Transcript") or "").strip(),
        "prediction_json": "",
        "freeze_task": 0,
    }


SHOONYA_CSV_HEADERS = [
    "id", "parent_data", "instance_id", "metadata_json", "draft_data_json",
    "domain", "scenario", "speaker_count", "speakers_json", "language",
    "transcribed_json", "machine_transcribed_json", "audio_url",
    "audio_duration", "reference_raw_transcript", "prediction_json",
    "freeze_task",
]


def build_shoonya_csv_string(shoonya_rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=SHOONYA_CSV_HEADERS)
    writer.writeheader()
    writer.writerows(shoonya_rows)
    return buffer.getvalue()


def get_project_config_for_language(language):
    """Returns {project_type, acoustic_enabled_stage} per the language-based rules.

    acoustic_enabled_stage must be None (-> JSON null) for "blank", not "" --
    the frontend's `showAcousticText` check (TranscriptionRightPanel.jsx) does
    `acoustic_enabled_stage !== null && acoustic_enabled_stage <= stage`. An
    empty string passes `!== null` and coerces to 0 in `<= stage`, which is
    true for virtually every stage -- the opposite of "blank"/hidden.
    """
    if language in TAMIL_LANGUAGES:
        return {
            "project_type": "VerbatimTranscriptionCharacterTagging",
            "acoustic_enabled_stage": REVIEW_ACOUSTIC_STAGE,
        }
    if language in BLANK_ACOUSTIC_LANGUAGES:
        return {
            "project_type": "VerbatimTranscriptionCharacterTagging",
            "acoustic_enabled_stage": None,
        }
    return {
        "project_type": "AcousticNormalisedTranscriptionEditing",
        "acoustic_enabled_stage": None,
    }


def build_project_title(language, part, row_type, batch_number):
    part_token = part.replace(" ", "")
    return f"JT-{part_token}-{language}-[{row_type}]-[B{batch_number}]"


def get_latest_project_for_group(dataset_instance, language, part, row_type):
    """Returns (latest_project_or_None, next_batch_number) for this dataset
    instance's (language, part, row_type) group.

    Used to decide whether a new batch should wait for the task-limit
    threshold: any project created via the threshold-met path always has
    exactly `limit` tasks by construction (see create_projects_for_dataset_
    category), so the *only* way an existing project can be under capacity
    is if it was created as the very first batch for its group with fewer
    than `limit` tasks available at the time. So "is there an existing
    under-capacity project to fill first" is the right question -- not
    "is this batch number 1" -- since once every existing project for a
    group is already full, the next batch should be created immediately
    just like a first-ever one would be, regardless of its count.

    Matches group membership via `filter_string` (which always starts with
    the exact `domain=...` this group's items are filtered by) rather than
    parsing `title` -- title is user-editable (renaming a project is a
    normal action), so keying off it made batch tracking silently break the
    moment someone renamed a project.
    """
    from projects.models import BATCH, Project

    domain = get_domain(row_type, part)
    domain_prefix = urlencode({"domain": domain})

    group_projects = Project.objects.filter(
        dataset_id=dataset_instance,
        sampling_mode=BATCH,
        filter_string__startswith=domain_prefix,
    ).order_by("-id")

    latest_project = group_projects.first()
    next_batch_number = group_projects.count() + 1
    return latest_project, next_batch_number


def build_unassigned_filter_string(domain, last_assigned_id):
    """Builds a `filter_string` (as consumed by projects.tasks.filter_data_items)
    that matches dataset items of the given domain that have not yet been pulled
    into any project (i.e. id greater than the highest id already assigned)."""
    params = {"domain": domain}
    if last_assigned_id:
        params["id__gt"] = str(last_assigned_id)
    return urlencode(params)
