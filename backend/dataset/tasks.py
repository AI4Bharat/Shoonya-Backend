import io
import json
import os
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from celery import shared_task
from django.apps import apps
from django.db.models import Max
from minio import Minio
from tablib import Dataset

from .pipeline_utils import (
    TASK_LIMITS,
    build_project_title,
    build_shoonya_csv_string,
    build_shoonya_row,
    build_target_object_key,
    build_unassigned_filter_string,
    get_audio_folder_name,
    get_latest_project_for_group,
    get_project_config_for_language,
    get_row_part,
    get_row_type,
    parse_domain,
    parse_input_csv,
    validate_input_csv,
)
from .resources import RESOURCE_MAP

from dataset.models import DatasetInstance
from tasks.models import Task, Annotation

#### CELERY SHARED TASKS


@shared_task(
    bind=True,
)
def upload_data_to_data_instance(
    self, dataset_string, pk, dataset_type, content_type, deduplicate=False
):
    # sourcery skip: raise-specific-error
    """Celery background task to upload the data to the dataset instance through file upload.
    First perform a batch upload and if that fails then move on to an iterative format to find rows with errors.


    Args:
        dataset_string (str): The data to be uploaded in string format
        pk (int): Primary key of the dataset instance
        dataset_type (str): The type of the dataset instance
        content_type (str): The file format of the uploaded file
        deduplicate (bool): Whether to deduplicate the data or not
    """

    # Create a new tablib Dataset and load the data into this dataset
    if content_type in ["xls", "xlsx"]:
        imported_data = Dataset().load(b64decode(dataset_string), format=content_type)
    else:
        imported_data = Dataset().load(dataset_string, format=content_type)

    # If deduplicate is True then remove duplicate rows from the imported data
    if deduplicate:
        imported_data.remove_duplicates()

    # Add the instance_id column to all rows in the dataset
    imported_data.append_col([pk] * len(imported_data), header="instance_id")

    try:
        data_headers = imported_data.dict[0].keys()
    except Exception as e:
        raise Exception("Empty Dataset Uploaded.") from e

    # Declare the appropriate resource map based on dataset type
    resource = RESOURCE_MAP[dataset_type]()

    # Perform a full batch upload of the data and return success if all checks are passed
    try:
        resource.import_data(imported_data, raise_errors=True)
        return f"All {len(imported_data.dict)} rows uploaded together."

    # If checks are failed, check which lines have an issue
    except:
        # Add row numbers to the dataset
        imported_data.append_col(range(1, len(imported_data) + 1), header="row_number")

        # List with row numbers that couldn't be uploaded, and why
        failed_rows = []
        error_details = {}

        # Iterate through the dataset and upload each row to the database
        for row in imported_data.dict:
            # Remove row number column from the row being uploaded
            row_number = row["row_number"]
            del row["row_number"]

            # Convert row to a tablib dataset
            row_dataset = Dataset()
            row_dataset.headers = data_headers

            # Add the row to the dataset
            row_dataset.append(tuple(row.values()))

            upload_result = resource.import_data(
                row_dataset, raise_errors=False, dry_run=True
            )

            # check if the upload result has errors
            if upload_result.has_errors() or upload_result.has_validation_errors():
                failed_rows.append(row_number)
                for _, row_errors in upload_result.row_errors():
                    for error in row_errors:
                        error_details.setdefault(row_number, []).append(str(error.error))
                for invalid_row in upload_result.invalid_rows:
                    error_details.setdefault(row_number, []).append(str(invalid_row.error_dict))

        raise Exception(
            f"Upload failed for lines: {failed_rows}. Details: {error_details}"
        )


@shared_task(bind=True)
def deduplicate_dataset_instance_items(self, pk, deduplicate_field_list):
    if len(deduplicate_field_list) == 0:
        return "Field list cannot be empty"
    try:
        dataset_instance = DatasetInstance.objects.get(pk=pk)
    except Exception as error:
        return error
    dataset_type = dataset_instance.dataset_type
    dataset_model = apps.get_model("dataset", dataset_type)
    dataset_items = dataset_model.objects.filter(instance_id=dataset_instance)
    duplicate_data_tracking_dict = {}
    tasks_count = 0
    annotations_count = 0
    dataset_items_count = 0
    for dataset_item in dataset_items:
        dataset_item_field_value = []
        for field in deduplicate_field_list:
            dataset_item_field_value.append(getattr(dataset_item, field))
        dict_key = tuple(dataset_item_field_value)
        if dict_key not in duplicate_data_tracking_dict:
            related_tasks = Task.objects.filter(input_data__id=dataset_item.id)
            related_tasks_ids = [task.id for task in related_tasks]
            related_annos = Annotation.objects.filter(
                task__id__in=related_tasks_ids
            ).order_by("-id")
            duplicate_data_tracking_dict[dict_key] = [
                related_annos,
                dataset_item,
                len(related_tasks_ids),
            ]
        else:
            print(duplicate_data_tracking_dict[dict_key])
            related_tasks = Task.objects.filter(input_data=dataset_item.id)
            related_tasks_ids = [task.id for task in related_tasks]
            related_annos1 = Annotation.objects.filter(
                task__id__in=related_tasks_ids
            ).order_by("-id")
            related_annos2 = duplicate_data_tracking_dict[dict_key][0]
            if related_annos1.count() <= related_annos2.count():
                annotations_count += related_annos1.count()
                tasks_count += len(related_tasks_ids)
                for anno in related_annos1:
                    anno.delete()
                dataset_item.delete()
                dataset_items_count += 1
            else:
                dataset_item2 = duplicate_data_tracking_dict[dict_key][1]
                annotations_count += related_annos2.count()
                tasks_count += duplicate_data_tracking_dict[dict_key][2]
                for anno in related_annos2:
                    anno.delete()
                dataset_item2.delete()
                dataset_items_count += 1
                duplicate_data_tracking_dict[dict_key] = [
                    related_annos1,
                    dataset_item,
                    len(related_tasks_ids),
                ]

    return f"Deleted {dataset_items_count} duplicate dataset items and {tasks_count} related tasks and {annotations_count} related annotations"


#### CREATE DATASET & PROJECT PIPELINE
#
# ShaktiCloud/MinIO credentials for the "JT" child-speech audio bucket. These are
# separate from the main MINIO_* deployment used elsewhere in the backend.
MINIO_JT_ENDPOINT_ENV = "MINIO_IITM_ENDPOINT"
MINIO_JT_ACCESS_KEY_ENV = "MINIO_IITM_ACCESS_KEY"
MINIO_JT_SECRET_KEY_ENV = "MINIO_IITM_SECRET_KEY"
MINIO_JT_BUCKET_ENV = "MINIO_IITM_BUCKET"


def _get_jt_minio_client():
    return Minio(
        endpoint=os.getenv(MINIO_JT_ENDPOINT_ENV),
        access_key=os.getenv(MINIO_JT_ACCESS_KEY_ENV),
        secret_key=os.getenv(MINIO_JT_SECRET_KEY_ENV),
        secure=True,
    )


def _upload_one_audio_file(minio_client, bucket, source_url, object_key):
    """Downloads one audio file from its source URL and uploads it to MinIO,
    skipping the download entirely if the object already exists at the target key."""
    try:
        minio_client.stat_object(bucket, object_key)
        return {"status": "skipped", "object_key": object_key}
    except Exception:
        pass

    try:
        response = requests.get(source_url, stream=True, timeout=120)
        response.raise_for_status()
    except Exception as e:
        return {
            "status": "failed",
            "object_key": object_key,
            "reason": f"Failed to download from source: {e}",
        }

    try:
        data = response.content
        minio_client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=response.headers.get("Content-Type", "audio/wav"),
        )
        return {"status": "uploaded", "object_key": object_key}
    except Exception as e:
        return {
            "status": "failed",
            "object_key": object_key,
            "reason": f"Failed to upload to ShaktiCloud: {e}",
        }


@shared_task(bind=True, queue="functions")
def create_dataset_and_project_pipeline(self, input_csv_string, config):
    """Runs Phase 1 of the "Create Dataset & Project" automation pipeline.

    Steps:
    1. Parse + validate the input CSV
    2. Upload audio to MinIO/ShaktiCloud (concurrent, skip-if-exists)
    3. Generate the Shoonya-format CSV (only rows whose audio upload succeeded)
    4. Create or reuse the DatasetInstance for the CSV's language
    5. Upload the generated CSV to that dataset instance

    Project creation is a deliberate second phase, triggered separately once the
    user picks Vendor(workspace), Language, and Category on the frontend — see
    `create_projects_for_dataset_category` below.

    Args:
        input_csv_string (str): Raw contents of the uploaded input CSV
        config (dict): {
            "dataset_name": str,           # used only when creating a new instance
            "existing_instance_id": int | None,
            "organisation_id": int,
            "user_id": int,                # user who triggered the pipeline
            "deduplicate": bool,           # remove duplicate rows on CSV upload
        }
    """
    steps = []

    def report(step_name, step_status, **extra):
        steps[:] = [s for s in steps if s["name"] != step_name]
        steps.append({"name": step_name, "status": step_status, **extra})
        self.update_state(
            state="PROGRESS", meta={"current_step": step_name, "steps": steps}
        )

    # Step 1: parse + validate
    rows, fieldnames = parse_input_csv(input_csv_string)
    validation = validate_input_csv(rows, fieldnames)
    report(
        "validate_csv",
        "completed" if validation["valid"] else "failed",
        details=validation,
    )
    if not validation["valid"]:
        raise ValueError(f"CSV validation failed: {validation['errors']}")

    language = validation["languages"][0]

    # Step 2: upload audio to MinIO
    bucket = os.getenv(MINIO_JT_BUCKET_ENV)
    endpoint = os.getenv(MINIO_JT_ENDPOINT_ENV)
    minio_client = _get_jt_minio_client()

    upload_jobs = []
    for row in rows:
        source_url = (row.get("Audio Link") or "").strip()
        if not source_url:
            continue
        folder_name = get_audio_folder_name(source_url)
        filename = os.path.basename(source_url)
        object_key = build_target_object_key(folder_name, filename)
        upload_jobs.append(
            {
                "row": row,
                "source_url": source_url,
                "object_key": object_key,
                "audio_url": f"https://{endpoint}/{bucket}/{object_key}",
            }
        )

    total_jobs = len(upload_jobs)
    report("audio_upload", "in_progress", progress={"done": 0, "total": total_jobs})

    upload_results = {}
    done_count = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                _upload_one_audio_file,
                minio_client,
                bucket,
                job["source_url"],
                job["object_key"],
            ): idx
            for idx, job in enumerate(upload_jobs)
        }
        for future in as_completed(futures):
            idx = futures[future]
            upload_results[idx] = future.result()
            done_count += 1
            if done_count % 5 == 0 or done_count == total_jobs:
                report(
                    "audio_upload",
                    "in_progress",
                    progress={"done": done_count, "total": total_jobs},
                )

    failed_uploads = []
    successful_jobs = []
    for idx, job in enumerate(upload_jobs):
        result = upload_results.get(
            idx, {"status": "failed", "reason": "Upload did not complete"}
        )
        if result["status"] == "failed":
            failed_uploads.append(
                {"audio_link": job["source_url"], "reason": result["reason"]}
            )
        else:
            successful_jobs.append(job)

    report(
        "audio_upload",
        "completed",
        progress={"done": total_jobs, "total": total_jobs},
        uploaded=len(successful_jobs),
        failures=failed_uploads,
    )

    if not successful_jobs:
        raise ValueError(
            "No audio files were uploaded successfully; aborting before dataset creation."
        )

    # Step 3: generate the Shoonya-format CSV rows for successful uploads only
    shoonya_rows = [
        build_shoonya_row(job["row"], job["audio_url"]) for job in successful_jobs
    ]

    # Step 4: create or reuse the DatasetInstance for this language
    existing_instance_id = config.get("existing_instance_id")
    organisation_id = config["organisation_id"]
    user_id = config["user_id"]
    deduplicate = config.get("deduplicate", False)

    if existing_instance_id:
        dataset_instance = DatasetInstance.objects.get(pk=existing_instance_id)
    else:
        dataset_instance = DatasetInstance.objects.create(
            instance_name=config.get("dataset_name") or language,
            dataset_type="SpeechConversation",
            organisation_id_id=organisation_id,
        )
    dataset_instance.users.add(user_id)

    report(
        "create_dataset",
        "completed",
        details={
            "instance_id": dataset_instance.instance_id,
            "instance_name": dataset_instance.instance_name,
        },
    )

    SpeechConversation = apps.get_model("dataset", "SpeechConversation")

    # Skip rows whose audio_url is already present in this dataset instance
    # (e.g. re-uploading the same CSV) -- but only when the user asked for
    # it via "Delete Duplicate Records". `remove_duplicates()` inside
    # upload_data_to_data_instance only dedupes within the current batch, it
    # never checks against rows already sitting in the dataset from a prior
    # upload, so that check has to happen here instead.
    duplicate_rows = []
    if deduplicate:
        # Starts with what's already in the dataset, then grows as rows are
        # kept -- catches duplicates against the existing dataset AND
        # duplicates within this same CSV batch (two rows sharing an
        # audio_url), keeping only the first occurrence of each.
        seen_audio_urls = set(
            SpeechConversation.objects.filter(instance_id=dataset_instance).values_list(
                "audio_url", flat=True
            )
        )
        deduped_rows = []
        for row in shoonya_rows:
            if row["audio_url"] in seen_audio_urls:
                duplicate_rows.append({"audio_url": row["audio_url"]})
            else:
                deduped_rows.append(row)
                seen_audio_urls.add(row["audio_url"])
        shoonya_rows = deduped_rows

    # Tag each row actually being inserted with a sequence_id (1, 2, 3, ...)
    # tracked separately per category (Read / Extempore each have their own
    # counter, continuing from the highest sequence_id already used *for
    # that category* in this dataset instance) -- matches how their task
    # limits/batches are already independent of each other. E.g. if Read
    # has 1-12 and Extempore has 1-8, a further Read upload continues at
    # 13, and a further Extempore upload continues at 9. Assigned after
    # dedup so skipped duplicates don't consume a number. Rows preserve
    # their upload/CSV order.
    #
    # Stored in metadata_json: process_task() (projects/utils.py) now always
    # copies the dataset item's metadata_json into the downloaded project
    # CSV as its own "input_data_metadata_json" column, so this flows
    # through there without needing speakers_json's special-cased export.
    max_sequence_id_by_category = {}
    for category, metadata in SpeechConversation.objects.filter(
        instance_id=dataset_instance
    ).values_list("scenario", "metadata_json"):
        if not metadata:
            continue
        sequence_id = metadata.get("sequence_id", 0)
        max_sequence_id_by_category[category] = max(
            max_sequence_id_by_category.get(category, 0), sequence_id
        )

    next_sequence_id_by_category = {
        category: max_sequence_id_by_category.get(category, 0) + 1
        for category in TASK_LIMITS
    }
    for row in shoonya_rows:
        category = row["scenario"]
        metadata_dict = json.loads(row["metadata_json"])
        metadata_dict["sequence_id"] = next_sequence_id_by_category.get(category, 1)
        row["metadata_json"] = json.dumps(metadata_dict, ensure_ascii=False)
        next_sequence_id_by_category[category] = (
            next_sequence_id_by_category.get(category, 1) + 1
        )

    csv_string = build_shoonya_csv_string(shoonya_rows)
    report(
        "generate_csv",
        "completed",
        details={"row_count": len(shoonya_rows), "duplicate_count": len(duplicate_rows)},
        csv_content=csv_string,
        duplicate_rows=duplicate_rows,
    )

    # Step 5: upload the generated CSV to the dataset instance (only if
    # there's anything left to upload once duplicates are filtered out)
    if shoonya_rows:
        upload_data_to_data_instance(
            dataset_string=csv_string,
            pk=dataset_instance.instance_id,
            dataset_type="SpeechConversation",
            content_type="csv",
            deduplicate=deduplicate,
        )

    categories_present = sorted({get_row_type(job["row"]) for job in successful_jobs})

    report(
        "upload_csv",
        "completed" if shoonya_rows else "skipped",
        details={"row_count": len(shoonya_rows)},
        categories_present=categories_present,
    )

    return {
        "dataset_instance_id": dataset_instance.instance_id,
        "dataset_instance_name": dataset_instance.instance_name,
        "language": language,
        "categories_present": categories_present,
        "total_input_rows": len(rows),
        "uploaded_count": len(successful_jobs),
        "inserted_count": len(shoonya_rows),
        "duplicate_count": len(duplicate_rows),
        "duplicate_rows": duplicate_rows,
        "failed_uploads": failed_uploads,
        "generated_csv": csv_string,
    }


def create_projects_for_dataset_category(
    dataset_instance, category, workspace_id, organisation_id, user_id
):
    """Phase 2 of the pipeline: creates a project for every part (Part A / Part B)
    of the given category that has reached its task-limit threshold of unassigned
    dataset items. Runs synchronously (fast, DB-only) from the view; the actual
    Task creation for each new project is still delegated asynchronously to the
    existing `create_parameters_for_task_creation` Celery task, exactly like the
    normal manual project-creation flow.

    Args:
        dataset_instance (DatasetInstance): The dataset to pull tasks from
        category (str): "Read" or "Extempore"
        workspace_id (int): Vendor/workspace the new project(s) should belong to
        organisation_id (int): Organisation the new project(s) should belong to
        user_id (int): User triggering creation; set as creator/annotator/reviewer
    """
    from projects.models import BATCH, REVIEW_STAGE, Project
    from projects.tasks import (
        add_new_data_items_into_project,
        create_parameters_for_task_creation,
        filter_data_items,
    )

    SpeechConversation = apps.get_model("dataset", "SpeechConversation")

    language = (
        SpeechConversation.objects.filter(instance_id=dataset_instance)
        .values_list("language", flat=True)
        .first()
    )
    if not language:
        raise ValueError("This dataset has no data items yet.")

    limit = TASK_LIMITS[category]
    project_config = get_project_config_for_language(language)

    domains = (
        SpeechConversation.objects.filter(instance_id=dataset_instance, scenario=category)
        .values_list("domain", flat=True)
        .distinct()
    )

    created_projects = []
    topped_up_projects = []

    for domain in sorted(domains):
        _, part = parse_domain(domain)
        if not part:
            continue

        last_assigned_id = (
            Task.objects.filter(
                project_id__dataset_id=dataset_instance,
                input_data__speechconversation__domain=domain,
            ).aggregate(Max("input_data_id"))["input_data_id__max"]
            or 0
        )
        unassigned_count = SpeechConversation.objects.filter(
            instance_id=dataset_instance, domain=domain, id__gt=last_assigned_id
        ).count()

        if unassigned_count == 0:
            continue

        latest_project, next_batch_number = get_latest_project_for_group(
            dataset_instance, language, part, category
        )

        # Top up the latest existing project first if it's under capacity --
        # using only as many of the newly-unassigned items as needed to fill
        # it (not more), so any surplus still goes toward a new batch below.
        # Runs synchronously (not .delay()) so the just-created Task rows
        # are visible to the unassigned-count recompute that follows,
        # instead of racing an async pull.
        if latest_project is not None:
            deficit = limit - Task.objects.filter(project_id=latest_project).count()
            if deficit > 0:
                topup_filter_string = build_unassigned_filter_string(domain, last_assigned_id)
                available_items = filter_data_items(
                    latest_project.project_type,
                    [dataset_instance.instance_id],
                    topup_filter_string,
                )
                items_to_pull = available_items[:deficit]
                if items_to_pull:
                    # Captured before add_new_data_items_into_project runs --
                    # it calls create_tasks_from_dataitems, which mutates
                    # each item dict in place (`del item["id"]`) once it's
                    # used to build the Task, so reading item["id"] after
                    # that call would raise KeyError.
                    pulled_ids = [item["id"] for item in items_to_pull]
                    add_new_data_items_into_project(
                        project_id=latest_project.id, items=items_to_pull
                    )
                    topped_up_projects.append(
                        {
                            "project_id": latest_project.id,
                            "title": latest_project.title,
                            "pulled_count": len(items_to_pull),
                        }
                    )
                    last_assigned_id = max(pulled_ids)
                    unassigned_count -= len(items_to_pull)

        if unassigned_count == 0:
            continue

        # Whatever's left after the top-up above always becomes a new batch
        # immediately, however small -- by this point the latest existing
        # project (if any) is guaranteed either full or completely out of
        # data to give it, so there's nothing left to wait on.
        task_count = min(unassigned_count, limit)
        batch_number = next_batch_number
        title = build_project_title(language, part, category, batch_number)
        filter_string = build_unassigned_filter_string(domain, last_assigned_id)
        sampling_parameters = {"batch_size": task_count, "batch_number": [1]}

        project = Project.objects.create(
            title=title,
            description="Child speech data",
            created_by_id=user_id,
            organization_id_id=organisation_id,
            workspace_id_id=workspace_id,
            project_type=project_config["project_type"],
            project_mode="Annotation",
            sampling_mode=BATCH,
            sampling_parameters_json=sampling_parameters,
            filter_string=filter_string,
            project_stage=REVIEW_STAGE,
            # Transcription, not translation -- src/tgt are both the
            # dataset's own language. Set explicitly since this pipeline
            # builds the Project directly via the ORM, bypassing
            # ProjectSerializer (which is what normally saves these when a
            # project is created through the standard UI form).
            src_language=language,
            tgt_language=language,
            metadata_json={
                "acoustic_enabled_stage": project_config["acoustic_enabled_stage"],
                "automatic_annotation_creation_mode": "annotation",
            },
        )
        project.annotators.add(user_id)
        project.annotation_reviewers.add(user_id)
        project.dataset_id.add(dataset_instance)

        create_parameters_for_task_creation.delay(
            project_type=project_config["project_type"],
            dataset_instance_ids=[dataset_instance.instance_id],
            filter_string=filter_string,
            sampling_mode=BATCH,
            sampling_parameters=sampling_parameters,
            variable_parameters=None,
            project_id=project.id,
            automatic_annotation_creation_mode="annotation",
        )
        created_projects.append(
            {
                "project_id": project.id,
                "title": title,
                "task_count": task_count,
                "batch_number": batch_number,
                "part": part,
            }
        )

    return {
        "language": language,
        "created_projects": created_projects,
        "topped_up_projects": topped_up_projects,
    }
