from datetime import datetime, timezone
from locale import normalize
from urllib.parse import unquote
import ast
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator

import requests
from tasks.models import *
from tasks.serializers import (
    TaskSerializer,
    AnnotationSerializer,
    PredictionSerializer,
    TaskAnnotationSerializer,
)
from tasks.utils import compute_meta_stats_for_instruction_driven_chat, query_flower
from tasks.utils import Queued_Task_name
from utils.pagination import paginate_queryset
from notifications.views import createNotification
from notifications.utils import get_userids_from_project_id

from users.models import User
from projects.models import Project, REVIEW_STAGE, ANNOTATION_STAGE, SUPERCHECK_STAGE
from users.utils import generate_random_string
from utils.convert_result_to_chitralekha_format import (
    convert_result_to_chitralekha_format,
)
from utils.llm_checks import (
    evaluate_prompt_alignment,
    prompt_lang_check,
    duplicate_check,
)
from utils.llm_interactions import get_model_output

from utils.search import process_search_query

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rapidfuzz.distance import Levenshtein
import sacrebleu

from utils.date_time_conversions import utc_to_ist
from rest_framework.views import APIView


# Create your views here.


def annotation_result_compare(base_annotation_result, review_annotation_result):
    """
    Compares the annotation output of annotator and reviewer, ignores the 'id' field.
    Returns True if output differs
    """
    base_result = [{i: d[i] for i in d if i != "id"} for d in base_annotation_result]
    base_result = sorted(base_result, key=lambda d: d["from_name"])
    review_result = [
        {i: d[i] for i in d if i != "id"} for d in review_annotation_result
    ]
    review_result = sorted(review_result, key=lambda d: d["from_name"])

    is_modified = any(x != y for x, y in zip(base_result, review_result))
    return is_modified


class TaskViewSet(viewsets.ModelViewSet, mixins.ListModelMixin):
    """
    Model Viewset for Tasks. All Basic CRUD operations are covered here.
    """

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING, format="email"),
                    description="List of emails",
                )
            },
            required=["user_ids"],
        ),
        responses={200: "Task assigned", 404: "User not found"},
    )
    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk):
        """
        Assigns users with the given user IDs to the particular task.
        """
        task = self.get_object()
        user_ids = request.data.get("user_ids")
        annotators = []
        for u_id in user_ids:
            try:
                annotators.append(User.objects.get(id=u_id))
            except User.DoesNotExist:
                return Response(
                    {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )
        task.assign(annotators)
        return Response({"message": "Task assigned"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="annotations")
    def annotations(self, request, pk):
        """
        Returns all the annotations associated with a particular task.
        """
        task = self.get_object()
        annotations = Annotation.objects.filter(task=task)
        project = Project.objects.get(id=task.project_id.id)
        annotator = request.user
        annotators_of_this_project = project.annotators.all()
        if (annotator.role == User.ANNOTATOR) or (
            (
                annotator.role == User.REVIEWER
                or annotator.role == User.SUPER_CHECKER
                or annotator.role == User.WORKSPACE_MANAGER
                or annotator.role == User.ORGANIZATION_OWNER
                or annotator.role == User.ADMIN
            )
            and (annotator in annotators_of_this_project)
        ):
            if annotator != task.review_user and annotator != task.super_check_user:
                if annotator in annotators_of_this_project:
                    ann_annotations = annotations.filter(completed_by=annotator)
                    annotations1 = list(ann_annotations)
                    if len(ann_annotations) > 0:
                        review_annotation = annotations.filter(
                            parent_annotation_id__isnull=False
                        )

                        annotations1.extend(list(review_annotation))
                    annotations = annotations1
                else:
                    return Response(
                        {"message": "You are not a part of this project"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # modifications for integrations of chitralekha UI
        if "enable_chitralekha_UI" in dict(request.query_params):
            for ann in annotations:
                ann.result = convert_result_to_chitralekha_format(
                    ann.result, ann.id, project.project_type
                )

        serializer = AnnotationSerializer(annotations, many=True)
        for i in serializer.data:
            if len(i["result"]) > 0:
                if type(i["result"]) == type([]):
                    if "output" in i["result"][0] and type(
                        i["result"][0]["output"]
                    ) == type([]):
                        i["result"][0]["output"] = i["result"][0]["output"][0]["value"]
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="predictions")
    def predictions(self, request, pk):
        """
        Returns all the predictions associated with a particular task.
        """
        task = self.get_object()
        predictions = Prediction.objects.filter(task=task)
        serializer = PredictionSerializer(predictions, many=True)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        user_id = request.user.id
        user = request.user
        page_number = None
        if "page" in dict(request.query_params):
            page_number = request.query_params["page"]
        records = 10
        if "records" in dict(request.query_params):
            records = request.query_params["records"]

        if "project_id" in dict(request.query_params):
            proj_id = request.query_params["project_id"]
            proj_objs = Project.objects.filter(id=proj_id)
            if len(proj_objs) == 0:
                return Response(
                    {"message": " this project not  exist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            proj_annotators = proj_objs[0].annotators.all()
            proj_reviewers = proj_objs[0].annotation_reviewers.all()
            proj_supercheckers = proj_objs[0].review_supercheckers.all()

            view = "user_view"
            exist_req_user = 0
            if (
                user.role == User.ORGANIZATION_OWNER
                or user.role == User.WORKSPACE_MANAGER
                or user.is_superuser
            ):
                if not (
                    (user in proj_annotators)
                    or (user in proj_reviewers)
                    or (user in proj_supercheckers)
                ):
                    view = "managerial_view"

                    if "req_user" in dict(request.query_params):
                        exist_req_user = 1
                        req_user = request.query_params["req_user"]

            if exist_req_user:
                user_id = int(req_user)
            required_annotators_per_task = proj_objs[0].required_annotators_per_task
            if "annotation_status" in dict(request.query_params):
                ann_status = request.query_params["annotation_status"]
                ann_status = ast.literal_eval(ann_status)

                if view == "managerial_view":
                    if not ("req_user" in dict(request.query_params)):
                        ann = Annotation.objects.filter(
                            task__project_id_id=proj_id,
                            annotation_status__in=ann_status,
                            annotation_type=ANNOTATOR_ANNOTATION,
                        )

                        tasks = Task.objects.filter(annotations__in=ann)
                        tasks = tasks.distinct()
                        # Handle search query (if any)
                        if len(tasks):
                            tasks = tasks.filter(
                                **process_search_query(
                                    request.GET, "data", list(tasks.first().data.keys())
                                )
                            )
                        ann_filter1 = ann.filter(task__in=tasks).order_by("id")

                        task_objs = []
                        for an in ann_filter1:
                            task_obj = {}
                            task_obj["id"] = an.task_id
                            task_obj["annotation_status"] = an.annotation_status
                            task_obj["user_mail"] = an.completed_by.email
                            task_objs.append(task_obj)
                        task_objs.sort(key=lambda x: x["id"])
                        final_dict = {}
                        ordered_tasks = []
                        for task_obj in task_objs:
                            tas = Task.objects.filter(id=task_obj["id"])
                            tas = tas.values()[0]
                            tas["annotation_status"] = task_obj["annotation_status"]
                            tas["user_mail"] = task_obj["user_mail"]
                            ordered_tasks.append(tas)
                        if page_number is not None:
                            page_object = Paginator(ordered_tasks, records)
                            try:
                                final_dict["total_count"] = len(ordered_tasks)
                                page_items = page_object.page(page_number)
                                ordered_tasks = page_items.object_list
                                final_dict["result"] = ordered_tasks
                                return Response(final_dict)
                            except:
                                return Response(
                                    {"message": "page not available"},
                                    status=status.HTTP_400_BAD_REQUEST,
                                )

                        final_dict["total_count"] = len(ordered_tasks)
                        final_dict["result"] = ordered_tasks
                        return Response(final_dict)
                ann = Annotation.objects.filter(
                    task__project_id_id=proj_id,
                    annotation_status__in=ann_status,
                    annotation_type=ANNOTATOR_ANNOTATION,
                    completed_by=user_id,
                )

                tasks = Task.objects.filter(annotations__in=ann)
                tasks = tasks.distinct()
                # Handle search query (if any)
                if len(tasks):
                    tasks = tasks.filter(
                        **process_search_query(
                            request.GET, "data", list(tasks.first().data.keys())
                        )
                    )
                # editable filter
                if "editable" in dict(request.query_params):
                    editable = False
                    if request.query_params["editable"] in ["true", "True"]:
                        editable = True
                    tasks_editable_filter_list = []
                    for task in tasks:
                        annos = Annotation.objects.filter(
                            task=task,
                            annotation_type=REVIEWER_ANNOTATION,
                        )
                        if len(annos) == 0:
                            tasks_editable_filter_list.append(task.id)
                    if editable:
                        tasks = tasks.filter(id__in=tasks_editable_filter_list)
                    else:
                        tasks = tasks.exclude(id__in=tasks_editable_filter_list)

                ann_filter1 = ann.filter(task__in=tasks).order_by("id")

                task_objs = []
                for an in ann_filter1:
                    task_obj = {}
                    task_obj["id"] = an.task_id
                    task_obj["annotation_status"] = an.annotation_status
                    task_obj["user_mail"] = an.completed_by.email
                    task_obj["annotation_result_json"] = an.result
                    task_objs.append(task_obj)
                task_objs.sort(key=lambda x: x["id"])
                final_dict = {}
                ordered_tasks = []
                proj_type = proj_objs[0].project_type
                for task_obj in task_objs:
                    tas = Task.objects.filter(id=task_obj["id"])
                    tas = tas.values()[0]
                    tas["annotation_status"] = task_obj["annotation_status"]
                    tas["user_mail"] = task_obj["user_mail"]
                    if (ann_status[0] in ["labeled", "draft", "to_be_revised"]) and (
                        proj_type == "ContextualTranslationEditing"
                    ):
                        try:
                            tas["data"]["output_text"] = task_obj[
                                "annotation_result_json"
                            ][0]["value"]["text"][0]
                        except:
                            tas["data"]["output_text"] = "-"
                        del tas["data"]["machine_translation"]
                    ordered_tasks.append(tas)

                if page_number is not None:
                    page_object = Paginator(ordered_tasks, records)

                    try:
                        final_dict["total_count"] = len(ordered_tasks)
                        page_items = page_object.page(page_number)
                        ordered_tasks = page_items.object_list
                        final_dict["result"] = ordered_tasks
                        return Response(final_dict)
                    except:
                        return Response(
                            {"message": "page not available"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                final_dict["total_count"] = len(ordered_tasks)
                final_dict["result"] = ordered_tasks
                return Response(final_dict)

            if "review_status" in dict(request.query_params):
                rew_status = request.query_params["review_status"]
                rew_status = ast.literal_eval(rew_status)

                if view == "managerial_view":
                    if not ("req_user" in dict(request.query_params)):
                        ann = Annotation.objects.filter(
                            task__project_id_id=proj_id,
                            annotation_status__in=rew_status,
                            annotation_type=REVIEWER_ANNOTATION,
                        )
                        tasks = Task.objects.filter(annotations__in=ann)
                        tasks = tasks.distinct()
                        # Handle search query (if any)
                        if len(tasks):
                            tasks = tasks.filter(
                                **process_search_query(
                                    request.GET, "data", list(tasks.first().data.keys())
                                )
                            )
                        ann_filter1 = ann.filter(task__in=tasks).order_by("id")

                        task_objs = []
                        for an in ann_filter1:
                            task_obj = {}
                            task_obj["id"] = an.task_id
                            task_obj["annotation_status"] = an.annotation_status
                            task_obj["user_mail"] = an.completed_by.email
                            task_objs.append(task_obj)
                        task_objs.sort(key=lambda x: x["id"])
                        ordered_tasks = []
                        final_dict = {}
                        seen = set()
                        for task_obj in task_objs:
                            if task_obj["id"] in seen:
                                continue
                            seen.add(task_obj["id"])
                            tas = Task.objects.filter(id=task_obj["id"])
                            tas = tas.values()[0]
                            tas["review_status"] = task_obj["annotation_status"]
                            tas["user_mail"] = task_obj["user_mail"]
                            if required_annotators_per_task > 1:
                                review_ann = [
                                    a
                                    for a in Annotation.objects.filter(
                                        task_id=tas["id"]
                                    ).order_by("id")
                                    if a.annotation_type == REVIEWER_ANNOTATION
                                ]
                                if len(review_ann) > 1:
                                    for r in review_ann:
                                        tas_copy = deepcopy(tas)
                                        tas_copy["correct_annotation_id"] = r.id
                                        tas_copy[
                                            "annotator_mail"
                                        ] = r.parent_annotation.completed_by.email
                                        ordered_tasks.append(tas_copy)
                                    continue
                            ordered_tasks.append(tas)

                        if page_number is not None:
                            page_object = Paginator(ordered_tasks, records)

                            try:
                                final_dict["total_count"] = len(ordered_tasks)
                                page_items = page_object.page(page_number)
                                ordered_tasks = page_items.object_list
                                final_dict["result"] = ordered_tasks
                                return Response(final_dict)
                            except:
                                return Response(
                                    {"message": "page not available"},
                                    status=status.HTTP_400_BAD_REQUEST,
                                )

                        final_dict["total_count"] = len(ordered_tasks)
                        final_dict["result"] = ordered_tasks
                        return Response(final_dict)

                ann = Annotation.objects.filter(
                    task__project_id_id=proj_id,
                    annotation_status__in=rew_status,
                    annotation_type=REVIEWER_ANNOTATION,
                    completed_by=user_id,
                )
                tasks = Task.objects.filter(annotations__in=ann)
                tasks = tasks.distinct()
                tasks = tasks.order_by("id")
                # Handle search query (if any)
                if len(tasks):
                    tasks = tasks.filter(
                        **process_search_query(
                            request.GET, "data", list(tasks.first().data.keys())
                        )
                    )

                # editable filter
                if "editable" in dict(request.query_params):
                    editable = False
                    if request.query_params["editable"] in ["true", "True"]:
                        editable = True
                    tasks_editable_filter_list = []
                    for task in tasks:
                        annos = Annotation.objects.filter(
                            task=task,
                            annotation_type=SUPER_CHECKER_ANNOTATION,
                        )
                        if len(annos) == 0:
                            tasks_editable_filter_list.append(task.id)
                    if editable:
                        tasks = tasks.filter(id__in=tasks_editable_filter_list)
                    else:
                        tasks = tasks.exclude(id__in=tasks_editable_filter_list)

                ann_filter1 = ann.filter(task__in=tasks).order_by("id")
                proj_type = proj_objs[0].project_type

                task_objs = []
                for an in ann_filter1:
                    task_obj = {}
                    parent_annotator_object = Annotation.objects.filter(
                        id=an.parent_annotation_id
                    )
                    first_annotator_object = Annotation.objects.filter(
                        task=an.task,
                        annotation_type=ANNOTATOR_ANNOTATION,
                    )
                    task_obj["id"] = an.task_id
                    task_obj["annotation_status"] = an.annotation_status
                    task_obj["user_mail"] = an.completed_by.email
                    task_obj["reviewer_annotation"] = an.result
                    task_obj["first_annotator_annotation"] = (
                        parent_annotator_object[0].result
                        if first_annotator_object
                        else "-"
                    )
                    task_obj["parent_annotator_annotation"] = (
                        parent_annotator_object[0].result
                        if parent_annotator_object
                        else "-"
                    )
                    task_obj["parent_annotator_mail"] = (
                        parent_annotator_object[0].completed_by.email
                        if parent_annotator_object
                        else "-"
                    )
                    task_objs.append(task_obj)
                task_objs.sort(key=lambda x: x["id"])
                ordered_tasks = []
                final_dict = {}
                seen = set()
                for task_obj in task_objs:
                    if task_obj["id"] in seen:
                        continue
                    seen.add(task_obj["id"])
                    tas = Task.objects.filter(id=task_obj["id"])
                    tas = tas.values()[0]
                    tas["review_status"] = task_obj["annotation_status"]
                    tas["user_mail"] = task_obj["user_mail"]
                    tas["annotator_mail"] = task_obj["parent_annotator_mail"]
                    if proj_type == "ContextualTranslationEditing":
                        if rew_status[0] in [
                            "draft",
                            "accepted",
                            "accepted_with_major_changes",
                            "accepted_with_minor_changes",
                        ]:
                            if task_obj["reviewer_annotation"] is not None:
                                try:
                                    tas["data"]["output_text"] = task_obj[
                                        "reviewer_annotation"
                                    ][0]["value"]["text"][0]
                                except:
                                    tas["data"]["output_text"] = "-"
                            else:
                                tas["data"]["output_text"] = "-"
                        elif rew_status[0] in [
                            "unreviewed",
                            "skipped",
                        ]:
                            if task_obj["parent_annotator_annotation"] != "-":
                                try:
                                    tas["data"]["output_text"] = task_obj[
                                        "parent_annotator_annotation"
                                    ][0]["value"]["text"][0]
                                except:
                                    tas["data"]["output_text"] = "-"
                            else:
                                tas["data"]["output_text"] = task_obj[
                                    "first_annotator_annotation"
                                ][0]["value"]["text"][0]
                        else:
                            if task_obj["parent_annotator_annotation"] != "-":
                                try:
                                    tas["data"]["output_text"] = task_obj[
                                        "parent_annotator_annotation"
                                    ][0]["value"]["text"][0]
                                except:
                                    tas["data"]["output_text"] = "-"
                            else:
                                tas["data"]["output_text"] = "-"
                        del tas["data"]["machine_translation"]
                    if required_annotators_per_task > 1:
                        review_ann = [
                            a
                            for a in Annotation.objects.filter(
                                task_id=tas["id"]
                            ).order_by("id")
                            if a.annotation_type == REVIEWER_ANNOTATION
                        ]
                        if len(review_ann) > 1:
                            for r in review_ann:
                                tas_copy = deepcopy(tas)
                                tas_copy["correct_annotation_id"] = r.id
                                tas_copy[
                                    "annotator_mail"
                                ] = r.parent_annotation.completed_by.email
                                ordered_tasks.append(tas_copy)
                            continue
                    ordered_tasks.append(tas)
                if page_number is not None:
                    page_object = Paginator(ordered_tasks, records)

                    try:
                        final_dict["total_count"] = len(ordered_tasks)
                        page_items = page_object.page(page_number)
                        ordered_tasks = page_items.object_list
                        final_dict["result"] = ordered_tasks
                        return Response(final_dict)
                    except:
                        return Response(
                            {"message": "page not available"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                final_dict["total_count"] = len(ordered_tasks)
                final_dict["result"] = ordered_tasks
                return Response(final_dict)

            if "supercheck_status" in dict(request.query_params):
                supercheck_status = request.query_params["supercheck_status"]
                supercheck_status = ast.literal_eval(supercheck_status)

                if view == "managerial_view":
                    if not ("req_user" in dict(request.query_params)):
                        ann = Annotation.objects.filter(
                            task__project_id_id=proj_id,
                            annotation_status__in=supercheck_status,
                            annotation_type=SUPER_CHECKER_ANNOTATION,
                        )
                        tasks = Task.objects.filter(annotations__in=ann)
                        tasks = tasks.distinct()
                        # Handle search query (if any)
                        if len(tasks):
                            tasks = tasks.filter(
                                **process_search_query(
                                    request.GET, "data", list(tasks.first().data.keys())
                                )
                            )
                        ann_filter1 = ann.filter(task__in=tasks)
                        task_objs = []
                        for an in ann_filter1:
                            task_obj = {}
                            task_obj["id"] = an.task_id
                            task_obj["annotation_status"] = an.annotation_status
                            task_obj["user_mail"] = an.completed_by.email
                            task_objs.append(task_obj)
                        task_objs.sort(key=lambda x: x["id"])
                        ordered_tasks = []
                        final_dict = {}
                        for task_obj in task_objs:
                            tas = Task.objects.filter(id=task_obj["id"])
                            tas = tas.values()[0]
                            tas["supercheck_status"] = task_obj["annotation_status"]
                            tas["user_mail"] = task_obj["user_mail"]
                            ordered_tasks.append(tas)

                        if page_number is not None:
                            page_object = Paginator(ordered_tasks, records)

                            try:
                                final_dict["total_count"] = len(ordered_tasks)
                                page_items = page_object.page(page_number)
                                ordered_tasks = page_items.object_list
                                final_dict["result"] = ordered_tasks
                                return Response(final_dict)
                            except:
                                return Response(
                                    {"message": "page not available"},
                                    status=status.HTTP_400_BAD_REQUEST,
                                )

                        final_dict["total_count"] = len(ordered_tasks)
                        final_dict["result"] = ordered_tasks
                        return Response(final_dict)

                ann = Annotation.objects.filter(
                    task__project_id_id=proj_id,
                    annotation_status__in=supercheck_status,
                    annotation_type=SUPER_CHECKER_ANNOTATION,
                    completed_by=user_id,
                )
                tasks = Task.objects.filter(annotations__in=ann)
                tasks = tasks.distinct()
                # Handle search query (if any)
                if len(tasks):
                    tasks = tasks.filter(
                        **process_search_query(
                            request.GET, "data", list(tasks.first().data.keys())
                        )
                    )
                ann_filter1 = ann.filter(task__in=tasks).order_by("id")

                task_objs = []
                for an in ann_filter1:
                    task_obj = {}
                    reviewer_object = Annotation.objects.filter(
                        id=an.parent_annotation_id
                    )
                    annotator_object = Annotation.objects.filter(
                        id=an.parent_annotation.parent_annotation_id
                    )
                    task_obj["id"] = an.task_id
                    task_obj["annotation_status"] = an.annotation_status
                    task_obj["user_mail"] = an.completed_by.email
                    task_obj["superchecker_annotation"] = an.result
                    task_obj["reviewer_mail"] = (
                        reviewer_object[0].completed_by.email
                        if reviewer_object
                        else "-"
                    )
                    task_obj["reviewer_annotation"] = (
                        reviewer_object[0].result if reviewer_object else "-"
                    )
                    task_obj["annotator_mail"] = (
                        annotator_object[0].completed_by.email
                        if annotator_object
                        else "-"
                    )
                    task_objs.append(task_obj)

                task_objs.sort(key=lambda x: x["id"])
                ordered_tasks = []
                final_dict = {}
                proj_type = proj_objs[0].project_type
                for task_obj in task_objs:
                    tas = Task.objects.filter(id=task_obj["id"])
                    tas = tas.values()[0]
                    tas["supercheck_status"] = task_obj["annotation_status"]
                    tas["user_mail"] = task_obj["user_mail"]
                    tas["reviewer_mail"] = task_obj["reviewer_mail"]
                    tas["annotator_mail"] = task_obj["annotator_mail"]
                    if proj_type == "ContextualTranslationEditing":
                        if supercheck_status[0] in [
                            "draft",
                            "validated",
                            "Validated_with_changes",
                        ]:
                            if task_obj["superchecker_annotation"] is not None:
                                tas["data"]["output_text"] = task_obj[
                                    "superchecker_annotation"
                                ][0]["value"]["text"][0]
                            else:
                                tas["data"]["output_text"] = "-"
                        else:
                            if task_obj["reviewer_annotation"] != "-":
                                tas["data"]["output_text"] = task_obj[
                                    "reviewer_annotation"
                                ][0]["value"]["text"][0]
                            else:
                                tas["data"]["output_text"] = "-"
                        del tas["data"]["machine_translation"]
                    ordered_tasks.append(tas)
                if page_number is not None:
                    page_object = Paginator(ordered_tasks, records)

                    try:
                        final_dict["total_count"] = len(ordered_tasks)
                        page_items = page_object.page(page_number)
                        ordered_tasks = page_items.object_list
                        final_dict["result"] = ordered_tasks
                        return Response(final_dict)
                    except:
                        return Response(
                            {"message": "page not available"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                final_dict["total_count"] = len(ordered_tasks)
                final_dict["result"] = ordered_tasks
                return Response(final_dict)

            tas_status = ["incomplete"]
            if "task_status" in dict(request.query_params):
                tas_status = request.query_params["task_status"]
                tas_status = ast.literal_eval(tas_status)

            if (
                user.role == User.ORGANIZATION_OWNER
                or user.role == User.WORKSPACE_MANAGER
                or user.is_superuser
            ):
                if not ("req_user" in dict(request.query_params)):
                    tasks = Task.objects.filter(
                        project_id__exact=proj_id,
                        task_status__in=tas_status,
                    )

                    # Handle search query (if any)
                    if len(tasks):
                        tasks = tasks.filter(
                            **process_search_query(
                                request.GET, "data", list(tasks.first().data.keys())
                            )
                        )

                    ordered_tasks = list(tasks.values())
                    final_dict = {}
                    if page_number is not None:
                        page_object = Paginator(ordered_tasks, records)

                        try:
                            final_dict["total_count"] = len(ordered_tasks)
                            page_items = page_object.page(page_number)
                            ordered_tasks = page_items.object_list
                            final_dict["result"] = ordered_tasks
                            return Response(final_dict)
                        except:
                            return Response(
                                {"message": "page not available"},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                    final_dict["total_count"] = len(ordered_tasks)
                    final_dict["result"] = ordered_tasks
                    return Response(final_dict)
            proj_annotators_ids = [an.id for an in proj_annotators]
            proj_reviewers_ids = [an.id for an in proj_reviewers]
            proj_superchecker_ids = [an.id for an in proj_supercheckers]

            if user_id in proj_annotators_ids:
                tasks = Task.objects.filter(
                    project_id__exact=proj_id,
                    task_status__in=tas_status,
                    annotation_users=user_id,
                )

                # Handle search query (if any)
                if len(tasks):
                    tasks = tasks.filter(
                        **process_search_query(
                            request.GET, "data", list(tasks.first().data.keys())
                        )
                    )

                ordered_tasks = list(tasks.values())
                final_dict = {}
                if page_number is not None:
                    page_object = Paginator(ordered_tasks, records)

                    try:
                        final_dict["total_count"] = len(ordered_tasks)
                        page_items = page_object.page(page_number)
                        ordered_tasks = page_items.object_list
                        final_dict["result"] = ordered_tasks
                        return Response(final_dict)
                    except:
                        return Response(
                            {"message": "page not available"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                final_dict["total_count"] = len(ordered_tasks)
                final_dict["result"] = ordered_tasks
                return Response(final_dict)

            if user_id in proj_reviewers_ids:
                tasks = Task.objects.filter(
                    project_id__exact=proj_id,
                    task_status__in=tas_status,
                    review_user_id=user_id,
                )

                # Handle search query (if any)
                if len(tasks):
                    tasks = tasks.filter(
                        **process_search_query(
                            request.GET, "data", list(tasks.first().data.keys())
                        )
                    )

                ordered_tasks = list(tasks.values())
                final_dict = {}
                if page_number is not None:
                    page_object = Paginator(ordered_tasks, records)

                    try:
                        final_dict["total_count"] = len(ordered_tasks)
                        page_items = page_object.page(page_number)
                        ordered_tasks = page_items.object_list
                        final_dict["result"] = ordered_tasks
                        return Response(final_dict)
                    except:
                        return Response(
                            {"message": "page not available"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                final_dict["total_count"] = len(ordered_tasks)
                final_dict["result"] = ordered_tasks
                return Response(final_dict)

            if user_id in proj_superchecker_ids:
                tasks = Task.objects.filter(
                    project_id__exact=proj_id,
                    task_status__in=tas_status,
                    super_checker_user_id=user_id,
                )
                tasks = tasks.order_by("id")

                # Handle search query (if any)
                if len(tasks):
                    tasks = tasks.filter(
                        **process_search_query(
                            request.GET, "data", list(tasks.first().data.keys())
                        )
                    )

                ordered_tasks = list(tasks.values())
                final_dict = {}
                if page_number is not None:
                    page_object = Paginator(ordered_tasks, records)

                    try:
                        final_dict["total_count"] = len(ordered_tasks)
                        page_items = page_object.page(page_number)
                        ordered_tasks = page_items.object_list
                        final_dict["result"] = ordered_tasks
                        return Response(final_dict)
                    except:
                        return Response(
                            {"message": "page not available"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                final_dict["total_count"] = len(ordered_tasks)
                final_dict["result"] = ordered_tasks
                return Response(final_dict)

            return Response(
                {"message": " this user not part of this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            return Response(
                {"message": "please provide project_id as a query_params "},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def partial_update(self, request, pk=None):
        task_response = super().partial_update(request)
        task_id = task_response.data["id"]
        task = Task.objects.get(pk=task_id)
        return task_response

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "project_task_start_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "project_task_end_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "project_task_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                ),
            },
            description="Either pass the project_task_start_id and project_task_end_id or the project_task_ids in request body",
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the project"),
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "Deleted successfully! or No rows to delete",
            403: "Not authorized!",
            400: "Invalid parameters in the request body!",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="delete_project_tasks",
        url_name="delete_project_tasks",
    )
    def delete_project_tasks(self, request, pk=None):
        project = Project.objects.get(pk=pk)
        try:
            if (
                (
                    request.user.role == User.ORGANIZATION_OWNER
                    or request.user.is_superuser
                )
                and (request.user.organization == project.organization_id)
            ) == False:
                return Response(
                    {
                        "status": status.HTTP_403_FORBIDDEN,
                        "message": "You are not authorized to access the endpoint.",
                    }
                )

            if "project_task_ids" in request.data:
                project_task_ids = request.data.get("project_task_ids")
                if len(project_task_ids) == 0:
                    return Response(
                        {
                            "status": status.HTTP_400_BAD_REQUEST,
                            "message": "Please enter valid values",
                        }
                    )
            else:
                project_task_start_id = request.data.get("project_task_start_id")
                project_task_end_id = request.data.get("project_task_end_id")

                if (
                    project_task_start_id == ""
                    or project_task_end_id == ""
                    or project_task_start_id == None
                    or project_task_end_id == None
                ):
                    return Response(
                        {
                            "status": status.HTTP_400_BAD_REQUEST,
                            "message": "Please enter valid values",
                        }
                    )

                project_task_ids = [
                    id for id in range(project_task_start_id, project_task_end_id + 1)
                ]

            project_tasks = Task.objects.filter(project_id=project).filter(
                id__in=project_task_ids
            )

            related_annotation_task_ids = [
                project_task.id for project_task in project_tasks
            ]
            related_annotations = Annotation.objects.filter(
                task__id__in=related_annotation_task_ids
            ).order_by("-id")

            num_project_tasks = len(project_tasks)
            num_related_annotations = len(related_annotations)

            if num_project_tasks == 0:
                return Response(
                    {
                        "status": status.HTTP_200_OK,
                        "message": "No rows to delete",
                    }
                )

            for related_annotation in related_annotations:
                related_annotation.delete()
            project_tasks.delete()
            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "message": f"Deleted {num_project_tasks} project tasks and {num_related_annotations} related annotations successfully!",
                }
            )

        except Exception as error:
            return Response(
                {
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": str(error),
                }
            )

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description=(
                    "A integer refering to the user id for which tasks are to be fetched"
                ),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "task_type",
                openapi.IN_QUERY,
                description=(
                    "A string refering to the task type for which tasks are to be fetched"
                ),
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "search_Project ID",
                openapi.IN_QUERY,
                description=(
                    "A integer refering to the project id for which tasks are to be fetched"
                ),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "search_Task ID",
                openapi.IN_QUERY,
                description=(
                    "A integer refering to the task id for which tasks are to be fetched"
                ),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "search_Updated at",
                openapi.IN_QUERY,
                description=(
                    "A integer refering to the updated at time for which tasks are to be fetched"
                ),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "search_Annotated at",
                openapi.IN_QUERY,
                description=(
                    "A integer refering to the annotated at time for which tasks are to be fetched"
                ),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "search_Created at",
                openapi.IN_QUERY,
                description=(
                    "A integer refering to the created at time for which tasks are to be fetched"
                ),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description=("A integer refering to page no of paginated response"),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "records",
                openapi.IN_QUERY,
                description=(
                    "A integer refering to no of records in single page of a paginated response"
                ),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: "Returns a paginated list of recent tasks annotated/reviewed by a user",
            403: "Not authorized!",
            400: "Invalid parameters in the request body!",
        },
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="annotated_and_reviewed_tasks/get_users_recent_tasks",
        url_name="get_users_recent_tasks",
    )
    def get_users_recent_tasks(self, request):
        try:
            try:
                user_id = request.query_params.get("user_id")
                user = User.objects.filter(id=user_id)[0]
            except Exception as e:
                user = request.user

            task_type = request.query_params.get("task_type", "annotation")
            project_id = request.query_params.get("search_Project ID", "")
            task_id = request.query_params.get("search_Task ID", "")
            updated_at = request.query_params.get("search_Updated at", "")
            annotated_at = request.query_params.get("search_Annotated at", "")
            created_at = request.query_params.get("search_Created at", "")

            error_list = []

            annotations = Annotation.objects.filter(completed_by=user)
            if task_type == "review":
                annotations = annotations.filter(annotation_type=REVIEWER_ANNOTATION)
            elif task_type == "supercheck":
                annotations = annotations.filter(
                    annotation_type=SUPER_CHECKER_ANNOTATION
                )
            else:
                annotations = annotations.filter(annotation_type=ANNOTATOR_ANNOTATION)

            if project_id:
                try:
                    annotations = annotations.filter(task__project_id=project_id)
                except Exception as e:
                    error_list.append(f"Error filtering by Project ID")
                    pass

            if task_id:
                try:
                    annotations = annotations.filter(task__id=task_id)
                except Exception as e:
                    error_list.append(f"Error filtering by Task ID")
                    pass

            if updated_at:
                try:
                    date_obj = datetime.strptime(updated_at, "%d-%m-%Y")
                    annotations = annotations.filter(updated_at__date=date_obj.date())
                except Exception as e:
                    error_list.append(f"Error filtering by updated at date")
                    pass

            if annotated_at:
                try:
                    date_obj = datetime.strptime(annotated_at, "%d-%m-%Y")
                    annotations = annotations.filter(annotated_at__date=date_obj.date())
                except Exception as e:
                    error_list.append(f"Error filtering by annotated at date")
                    pass

            if created_at:
                try:
                    date_obj = datetime.strptime(created_at, "%d-%m-%Y")
                    annotations = annotations.filter(created_at__date=date_obj.date())
                except Exception as e:
                    error_list.append(f"Error filtering by created at date")
                    pass

            annotations = annotations.order_by("-updated_at")
            annotations = self.paginate_queryset(annotations)

            response = []

            for annotation in annotations:
                data = {
                    "Project ID": annotation.task.project_id.id,
                    "Task ID": annotation.task.id,
                    "Updated at": utc_to_ist(annotation.updated_at),
                    "Annotated at": utc_to_ist(annotation.annotated_at)
                    if annotation.annotated_at
                    else None,
                    "Created at": utc_to_ist(annotation.created_at)
                    if annotation.created_at
                    else None,
                }

                response.append(data)
            if len(error_list) == 0:
                return self.get_paginated_response({"results": response})
            else:
                return self.get_paginated_response(
                    {"results": response, "errors": error_list}
                )

        except:
            return Response(
                {
                    "message": "Invalid Parameters in the request body!",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "task_status": openapi.Schema(type=openapi.TYPE_STRING),
                "annotation_type": openapi.Schema(type=openapi.TYPE_STRING),
                "find_words": openapi.Schema(type=openapi.TYPE_STRING),
                "replace_words": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["task_status", "annotation_type", "find_words", "replace_words"],
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description=("A unique integer identifying the project"),
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            200: "Returns the no of annotations modified.",
            400: "Invalid parameters in the request body!",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="find_and_replace_words_in_annotation",
        url_name="find_and_replace_words_in_annotation",
    )
    def find_and_replace_words_in_annotation(self, request, pk=None):
        try:
            project = Project.objects.get(pk=pk)
            task_status = request.data.get("task_status")
            project_tasks = Task.objects.filter(project_id=project).filter(
                task_status=task_status
            )

            task_annotations = Annotation.objects.filter(task__in=project_tasks).filter(
                completed_by=request.user
            )
            annotation_type = request.data.get("annotation_type")
            # print(task_status)
            if annotation_type == "review":
                task_annotations = task_annotations.filter(
                    parent_annotation__isnull=False
                )
            else:
                task_annotations = task_annotations.filter(
                    parent_annotation__isnull=True
                )

            find_words = request.data.get("find_words")
            replace_words = request.data.get("replace_words")

            num_annotations_modified = 0
            for annotation in task_annotations:
                text = annotation.result[0]["value"]["text"][0]
                prev_text = text
                text = text.replace(find_words, replace_words)
                annotation.result[0]["value"]["text"][0] = text
                annotation.save()
                if prev_text != text:
                    num_annotations_modified += 1

            return Response(
                {"message": f"{num_annotations_modified} annotations are modified."},
                status=status.HTTP_200_OK,
            )
        except:
            return Response(
                {"message": "Invalid parameters in request body!"},
                status=status.HTTP_400_BAD_REQUEST,
            )


def update_notification(annotation_obj, task):
    project_id = task.project_id.id
    project_name = task.project_id
    notification_type = "task_update"

    if annotation_obj.annotation_status == TO_BE_REVISED:
        title = f"{project_name} : {project_id} Some tasks annotated by you in this project have been sent back for revision"
        try:
            notification_ids = get_userids_from_project_id(
                project_id=project_id,
                reviewers_bool=True,
                project_manager_bool=True,
            )
            notification_ids_set = list(set(notification_ids))
            createNotification(
                title, notification_type, notification_ids_set, project_id, task.id
            )
        except Exception as e:
            print(f"Error in creating notification: {e}")

    elif annotation_obj.annotation_status == REJECTED:
        title = f"{project_name} : {project_id} Some tasks reviewed by you in this project have been rejected by superchecker"
        try:
            notification_ids = get_userids_from_project_id(
                project_id=project_id,
                reviewers_bool=True,
                project_manager_bool=True,
            )
            notification_type = "rejected task"
            notification_ids_set = list(set(notification_ids))
            createNotification(title, notification_type, notification_ids_set)
        except Exception as e:
            print(f"Error in creating notification: {e}")


class AnnotationViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Annotation Viewset with create and update operations.
    """

    queryset = Annotation.objects.all()
    serializer_class = AnnotationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        # TODO: Correction annotation to be filled by validator
        if "mode" in dict(request.data):
            if request.data["mode"] == "review":
                return self.create_review_annotation(request)

        return self.create_base_annotation(request)

    def create_base_annotation(self, request):
        task_id = request.data["task"]
        task = Task.objects.get(pk=task_id)
        if request.user not in task.annotation_users.all():
            ret_dict = {"message": "You are trying to impersonate another user :("}
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)

        user_id = int(request.data["completed_by"])
        try:
            # Check if user id does not match with authorized user
            assert user_id == request.user.id
        except AssertionError:
            ret_dict = {"message": "You are trying to impersonate another user :("}
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)
        if task.project_id.required_annotators_per_task <= task.annotations.count():
            ret_dict = {
                "message": "Required annotations criteria is already satisfied!"
            }
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)
        if task.task_status == FREEZED:
            ret_dict = {"message": "Task is freezed!"}
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)

        if len(task.annotations.filter(completed_by__exact=request.user.id)) > 0:
            ret_dict = {"message": "Cannot add more than one annotation per user!"}
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)
        annotation_response = super().create(request)
        annotation_id = annotation_response.data["id"]
        annotation = Annotation.objects.get(pk=annotation_id)
        # project = Project.objects.get(pk=task.project_id.id)
        no_of_annotations = task.annotations.filter(
            parent_annotation_id=None, annotation_status="labeled"
        ).count()
        if task.project_id.required_annotators_per_task == no_of_annotations:
            # if True:
            task.task_status = ANNOTATED
            if not (task.project_id.project_stage == REVIEW_STAGE):
                if no_of_annotations == 1:
                    task.correct_annotation = annotation
                else:
                    task.correct_annotation = None

            task.save()
        return annotation_response

    def create_review_annotation(self, request):
        task_id = request.data["task"]
        if "review_status" in dict(request.data) and request.data["review_status"] in [
            ACCEPTED,
            UNREVIEWED,
            ACCEPTED_WITH_MINOR_CHANGES,
            ACCEPTED_WITH_MAJOR_CHANGES,
            DRAFT,
            SKIPPED,
            TO_BE_REVISED,
        ]:
            review_status = request.data["review_status"]
        else:
            ret_dict = {"message": "Missing param : review_status"}
            ret_status = status.HTTP_400_BAD_REQUEST
            return Response(ret_dict, status=ret_status)

        try:
            task = Task.objects.get(pk=task_id)
        except Task.DoesNotExist:
            ret_dict = {"message": "Task does not exist"}
            ret_status = status.HTTP_404_NOT_FOUND
            return Response(ret_dict, status=ret_status)

        if request.user != task.review_user:
            ret_dict = {"message": "You are trying to impersonate another user :("}
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)

        user_id = int(request.data["completed_by"])
        try:
            # Check if user id does not match with authorized user
            assert user_id == request.user.id
        except AssertionError:
            ret_dict = {"message": "You are trying to impersonate another user :("}
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)

        if task.task_status == REVIEWED:
            ret_dict = {"message": "Task is already reviewed and accepted!"}
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)

        parent_annotation_id = request.data["parent_annotation"]
        parent_annotation = Annotation.objects.get(pk=parent_annotation_id)
        # Verify that parent annotation is one of the task annotations
        if not parent_annotation or parent_annotation not in task.annotations.all():
            ret_dict = {"message": "Parent annotation Invalid/Null"}
            ret_status = status.HTTP_404_NOT_FOUND
            return Response(ret_dict, status=ret_status)

        annotation_response = super().create(request)
        annotation_id = annotation_response.data["id"]
        annotation = Annotation.objects.get(pk=annotation_id)
        if (
            review_status == ACCEPTED
            or review_status == ACCEPTED_WITH_MINOR_CHANGES
            or review_status == ACCEPTED_WITH_MAJOR_CHANGES
            or review_status == TO_BE_REVISED
        ):
            if review_status != TO_BE_REVISED:
                task.correct_annotation = annotation
                parent_annotation.review_notes = annotation.review_notes
                parent_annotation.save()
            task.task_status = REVIEWED
            task.save()

        return annotation_response

    def partial_update(self, request, pk=None):
        try:
            annotation_obj = Annotation.objects.get(id=pk)
            task = annotation_obj.task
        except:
            final_result = {"message": "annotation object does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
            return Response(final_result, status=ret_status)
        try:
            if str(task.id) != str(request.data["task_id"]):
                return Response(
                    {"message": "Task Id does not match the annotation's task id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except:
            return Response(
                {"message": "Missing parameter task_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            task = Task.objects.get(pk=request.data["task_id"])
        except:
            print("task not found")

        auto_save = False
        if "auto_save" in request.data:
            if request.data["auto_save"] == True:
                auto_save = True

        if annotation_obj.annotation_type == REVIEWER_ANNOTATION:
            is_revised = False
            if annotation_obj.annotation_status == TO_BE_REVISED:
                update_notification(annotation_obj, task)
                is_revised = True
                print(annotation_obj)
                if "ids" in dict(request.data):
                    pass

                else:
                    return Response(
                        {"message": "key doesnot match"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        elif annotation_obj.annotation_type == SUPER_CHECKER_ANNOTATION:
            is_rejected = False
            if annotation_obj.annotation_type == REJECTED:
                update_notification(annotation_obj, task)
                is_rejected = True

        is_acoustic_project_type = (
            True
            if annotation_obj.task.project_id.project_type
            == "AcousticNormalisedTranscriptionEditing"
            else False
        )
        # Base annotation update
        if annotation_obj.annotation_type == ANNOTATOR_ANNOTATION:
            if request.user not in task.annotation_users.all():
                ret_dict = {"message": "You are trying to impersonate another user :("}
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)
            # need to add few filters here
            is_IDC, output_result = False, ""
            if auto_save:
                update_fields_list = ["result", "lead_time", "updated_at", "meta_stats"]

                if (
                    annotation_obj.task.project_id.project_type
                    == "InstructionDrivenChat"
                ):
                    if isinstance(request.data["result"], str):
                        output_result = get_llm_output(
                            request.data["result"],
                            annotation_obj.task,
                            annotation_obj,
                            annotation_obj.task.project_id.metadata_json,
                        )
                        if output_result == -1:
                            ret_dict = {
                                "message": "Please make sure you have entered a prompt and the system has responded with an answer"
                            }
                            ret_status = status.HTTP_403_FORBIDDEN
                            return Response(ret_dict, status=ret_status)
                        # store the result of all checks as well
                        annotation_obj.result.append(
                            {
                                "prompt": request.data["result"],
                                "output": output_result,
                            }
                        )
                    # to handle the delete last chat case
                    else:
                        annotation_obj.result = request.data["result"]
                    annotation_obj.meta_stats = (
                        compute_meta_stats_for_instruction_driven_chat(
                            annotation_obj.result
                        )
                    )
                    is_IDC = True
                else:
                    annotation_obj.result = request.data["result"]
                if "annotation_notes" in dict(request.data):
                    annotation_obj.annotation_notes = request.data["annotation_notes"]
                    update_fields_list.append("annotation_notes")
                annotation_obj.lead_time = request.data["lead_time"]
                annotation_obj.save(update_fields=update_fields_list)
                annotation_response = Response(
                    AnnotationSerializer(annotation_obj).data
                )
                if is_IDC:
                    annotation_response.data["output"] = output_result
                response_message = "Success"
            else:
                if "annotation_status" in dict(request.data) and request.data[
                    "annotation_status"
                ] in [
                    UNLABELED,
                    LABELED,
                    DRAFT,
                    SKIPPED,
                ]:
                    annotation_status = request.data["annotation_status"]
                    if annotation_status == LABELED:
                        response_message = "Task Successfully Submitted"
                    elif annotation_status == DRAFT:
                        response_message = "Task Saved as Draft"
                    else:
                        response_message = "Success"
                    update_annotated_at = (
                        True
                        if annotation_status == LABELED
                        and annotation_obj.annotated_at is None
                        else False
                    )

                else:
                    ret_dict = {"message": "Missing param : annotation_status!"}
                    ret_status = status.HTTP_400_BAD_REQUEST
                    return Response(ret_dict, status=ret_status)

                if update_annotated_at:
                    annotation_obj.annotated_at = datetime.now(timezone.utc)
                    annotation_obj.save(update_fields=["annotated_at"])
                if (
                    annotation_obj.task.project_id.project_type
                    == "InstructionDrivenChat"
                ):
                    if isinstance(request.data["result"], str):
                        ret_dict = {
                            "message": "Please send the result as list when you are not auto-saving."
                        }
                        ret_status = status.HTTP_400_BAD_REQUEST
                        return Response(ret_dict, status=ret_status)
                    if (
                        isinstance(request.data["result"], list)
                        and isinstance(annotation_obj.result, list)
                        and len(annotation_obj.result) > len(request.data["result"])
                    ):
                        request.data["result"] = annotation_obj.result
                        request.data[
                            "meta_stats"
                        ] = compute_meta_stats_for_instruction_driven_chat(
                            annotation_obj.result
                        )
                    else:
                        request.data[
                            "meta_stats"
                        ] = compute_meta_stats_for_instruction_driven_chat(
                            request.data["result"]
                        )
                annotation_response = super().partial_update(request)
                if is_IDC:
                    annotation_response.data["output"] = output_result
                annotation_id = annotation_response.data["id"]
                annotation = Annotation.objects.get(pk=annotation_id)
                task = annotation.task

                if annotation_status in [DRAFT, SKIPPED]:
                    task.task_status = INCOMPLETE
                    task.save()

                if annotation_status == LABELED:
                    try:
                        review_annotation = Annotation.objects.get(
                            task=task, annotation_type=REVIEWER_ANNOTATION
                        )
                        if review_annotation.annotation_status == TO_BE_REVISED:
                            review_annotation.annotation_status = UNREVIEWED
                            review_annotation.save()
                    except:
                        pass

                no_of_annotations = task.annotations.filter(
                    annotation_type=ANNOTATOR_ANNOTATION, annotation_status="labeled"
                ).count()
                if task.project_id.required_annotators_per_task == no_of_annotations:
                    # if True:
                    task.task_status = ANNOTATED
                    if not (
                        task.project_id.project_stage == REVIEW_STAGE
                        or task.project_id.project_stage == SUPERCHECK_STAGE
                    ):
                        if no_of_annotations == 1:
                            task.correct_annotation = annotation

                    task.save()

        # Review annotation update
        elif annotation_obj.annotation_type == REVIEWER_ANNOTATION:
            if request.user != task.review_user:
                ret_dict = {"message": "You are trying to impersonate another user :("}
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)
            is_IDC, output_result = False, ""
            if auto_save:
                update_fields_list = ["result", "lead_time", "updated_at", "meta_stats"]
                if (
                    annotation_obj.task.project_id.project_type
                    == "InstructionDrivenChat"
                ):
                    if isinstance(request.data["result"], str):
                        output_result = get_llm_output(
                            request.data["result"],
                            annotation_obj.task,
                            annotation_obj,
                            annotation_obj.task.project_id.metadata_json,
                        )
                        if output_result == -1:
                            ret_dict = {
                                "message": "Please make sure you have entered a prompt and the system has responded with an answer"
                            }
                            ret_status = status.HTTP_403_FORBIDDEN
                            return Response(ret_dict, status=ret_status)
                        # store the result of all checks as well
                        annotation_obj.result.append(
                            {
                                "prompt": request.data["result"],
                                "output": output_result,
                            }
                        )
                    # to handle the delete last chat case
                    else:
                        annotation_obj.result = request.data["result"]
                    annotation_obj.meta_stats = (
                        compute_meta_stats_for_instruction_driven_chat(
                            annotation_obj.result
                        )
                    )
                    is_IDC = True
                else:
                    annotation_obj.result = request.data["result"]
                if "review_notes" in dict(request.data):
                    annotation_obj.review_notes = request.data["review_notes"]
                    update_fields_list.append("review_notes")
                annotation_obj.lead_time = request.data["lead_time"]
                annotation_obj.save(update_fields=update_fields_list)
                annotation_response = Response(
                    AnnotationSerializer(annotation_obj).data
                )
                if is_IDC:
                    annotation_response.data["output"] = output_result
                response_message = "Success"

            else:
                if "annotation_status" in dict(request.data) and request.data[
                    "annotation_status"
                ] in [
                    ACCEPTED,
                    UNREVIEWED,
                    ACCEPTED_WITH_MINOR_CHANGES,
                    ACCEPTED_WITH_MAJOR_CHANGES,
                    DRAFT,
                    SKIPPED,
                    TO_BE_REVISED,
                ]:
                    review_status = request.data["annotation_status"]
                    if review_status in [
                        ACCEPTED,
                        ACCEPTED_WITH_MINOR_CHANGES,
                        ACCEPTED_WITH_MAJOR_CHANGES,
                    ]:
                        response_message = "Task Successfully Accepted"
                    elif review_status == DRAFT:
                        response_message = "Task Saved as Draft"
                    elif review_status == TO_BE_REVISED:
                        response_message = "Task Saved as 'To Be Revised'"
                    else:
                        response_message = "Success"
                    update_annotated_at = (
                        True
                        if review_status
                        in [
                            ACCEPTED,
                            ACCEPTED_WITH_MINOR_CHANGES,
                            ACCEPTED_WITH_MAJOR_CHANGES,
                            TO_BE_REVISED,
                        ]
                        and annotation_obj.annotated_at is None
                        else False
                    )

                else:
                    ret_dict = {"message": "Missing param : annotation_status!"}
                    ret_status = status.HTTP_400_BAD_REQUEST
                    return Response(ret_dict, status=ret_status)

                if (
                    review_status == ACCEPTED
                    or review_status == ACCEPTED_WITH_MINOR_CHANGES
                    or review_status == ACCEPTED_WITH_MAJOR_CHANGES
                    or review_status == TO_BE_REVISED
                ):
                    if not "parent_annotation" in dict(request.data):
                        ret_dict = {"message": "Missing param : parent_annotation!"}
                        ret_status = status.HTTP_400_BAD_REQUEST
                        return Response(ret_dict, status=ret_status)

                    if review_status == TO_BE_REVISED:
                        rev_loop_count = task.revision_loop_count
                        if (
                            rev_loop_count["review_count"]
                            >= task.project_id.revision_loop_count
                        ):
                            ret_dict = {
                                "message": "Maximum revision loop count for task reached!"
                            }
                            ret_status = status.HTTP_403_FORBIDDEN
                            return Response(ret_dict, status=ret_status)

                if update_annotated_at:
                    annotation_obj.annotated_at = datetime.now(timezone.utc)
                    annotation_obj.save(update_fields=["annotated_at"])
                if (
                    annotation_obj.task.project_id.project_type
                    == "InstructionDrivenChat"
                ):
                    if isinstance(request.data["result"], str):
                        ret_dict = {
                            "message": "Please send the result as list when you are not auto-saving."
                        }
                        ret_status = status.HTTP_400_BAD_REQUEST
                        return Response(ret_dict, status=ret_status)
                    if (
                        isinstance(request.data["result"], list)
                        and isinstance(annotation_obj.result, list)
                        and len(annotation_obj.result) > len(request.data["result"])
                    ):
                        request.data["result"] = annotation_obj.result
                        request.data[
                            "meta_stats"
                        ] = compute_meta_stats_for_instruction_driven_chat(
                            annotation_obj.result
                        )
                    else:
                        request.data[
                            "meta_stats"
                        ] = compute_meta_stats_for_instruction_driven_chat(
                            request.data["result"]
                        )
                annotation_response = super().partial_update(request)
                if is_IDC:
                    annotation_response.data["output"] = output_result
                annotation_id = annotation_response.data["id"]
                annotation = Annotation.objects.get(pk=annotation_id)
                task = annotation.task

                if review_status in [DRAFT, SKIPPED]:
                    task.task_status = ANNOTATED
                    task.save()

                if (
                    review_status == ACCEPTED
                    or review_status == ACCEPTED_WITH_MINOR_CHANGES
                    or review_status == ACCEPTED_WITH_MAJOR_CHANGES
                    or review_status == TO_BE_REVISED
                ):
                    if not (task.project_id.project_stage == SUPERCHECK_STAGE):
                        task.correct_annotation = annotation
                    else:
                        task.correct_annotation = None
                    parent = annotation.parent_annotation
                    parent.review_notes = annotation.review_notes
                    if review_status == TO_BE_REVISED:
                        parent.annotation_status = TO_BE_REVISED
                        task.task_status = INCOMPLETE
                        rev_loop_count = task.revision_loop_count
                        if not is_revised:
                            rev_loop_count["review_count"] = (
                                1 + rev_loop_count["review_count"]
                            )
                        task.revision_loop_count = rev_loop_count
                    else:
                        task.task_status = REVIEWED
                        try:
                            supercheck_annotation = Annotation.objects.get(
                                task=task, annotation_type=SUPER_CHECKER_ANNOTATION
                            )
                            if supercheck_annotation.annotation_status == REJECTED:
                                supercheck_annotation.annotation_status = UNVALIDATED
                                supercheck_annotation.save()
                        except:
                            pass
                    parent.save(update_fields=["review_notes", "annotation_status"])
                    task.save()

                if review_status in [
                    ACCEPTED,
                    ACCEPTED_WITH_MAJOR_CHANGES,
                    ACCEPTED_WITH_MINOR_CHANGES,
                    SKIPPED,
                    DRAFT,
                ]:
                    parent = annotation.parent_annotation
                    if (parent.annotation_status) not in [LABELED]:
                        if parent.annotated_at is None:
                            parent.annotated_at = datetime.now(timezone.utc)
                            parent.save(update_fields=["annotated_at"])
                        parent.annotation_status = LABELED
                        parent.save(update_fields=["annotation_status"])

                if review_status in [UNREVIEWED, DRAFT, SKIPPED, TO_BE_REVISED]:
                    task.correct_annotation = None
                    task.save()
        # supercheck annotation update
        else:
            if request.user != task.super_check_user:
                ret_dict = {"message": "You are trying to impersonate another user :("}
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)
            is_IDC, output_result = False, ""
            if auto_save:
                update_fields_list = ["result", "lead_time", "updated_at", "meta_stats"]
                if (
                    annotation_obj.task.project_id.project_type
                    == "InstructionDrivenChat"
                ):
                    if isinstance(request.data["result"], str):
                        output_result = get_llm_output(
                            request.data["result"],
                            annotation_obj.task,
                            annotation_obj,
                            annotation_obj.task.project_id.metadata_json,
                        )
                        if output_result == -1:
                            ret_dict = {
                                "message": "Please make sure you have entered a prompt and the system has responded with an answer"
                            }
                            ret_status = status.HTTP_403_FORBIDDEN
                            return Response(ret_dict, status=ret_status)
                        # store the result of all checks as well
                        annotation_obj.result.append(
                            {
                                "prompt": request.data["result"],
                                "output": output_result,
                            }
                        )
                    # to handle the delete last chat case
                    else:
                        annotation_obj.result = request.data["result"]
                    annotation_obj.meta_stats = (
                        compute_meta_stats_for_instruction_driven_chat(
                            annotation_obj.result
                        )
                    )
                    is_IDC = True
                else:
                    annotation_obj.result = request.data["result"]
                if "supercheck_notes" in dict(request.data):
                    annotation_obj.supercheck_notes = request.data["supercheck_notes"]
                    update_fields_list.append("supercheck_notes")
                annotation_obj.lead_time = request.data["lead_time"]
                annotation_obj.save(update_fields=update_fields_list)
                annotation_response = Response(
                    AnnotationSerializer(annotation_obj).data
                )
                if is_IDC:
                    annotation_response.data["output"] = output_result
                response_message = "Success"

            else:
                if "annotation_status" in dict(request.data) and request.data[
                    "annotation_status"
                ] in [
                    UNVALIDATED,
                    VALIDATED,
                    VALIDATED_WITH_CHANGES,
                    REJECTED,
                    DRAFT,
                    SKIPPED,
                ]:
                    supercheck_status = request.data["annotation_status"]
                    if supercheck_status in [VALIDATED, VALIDATED_WITH_CHANGES]:
                        response_message = "Task Successfully Validated"
                    elif supercheck_status == DRAFT:
                        response_message = "Task Saved as Draft"
                    elif supercheck_status == REJECTED:
                        response_message = "Task Rejected"
                    else:
                        response_message = "Success"
                    update_annotated_at = (
                        True
                        if supercheck_status
                        in [
                            VALIDATED,
                            VALIDATED_WITH_CHANGES,
                            REJECTED,
                        ]
                        and annotation_obj.annotated_at is None
                        else False
                    )
                else:
                    ret_dict = {"message": "Missing param : annotation_status!"}
                    ret_status = status.HTTP_400_BAD_REQUEST
                    return Response(ret_dict, status=ret_status)

                if (
                    supercheck_status == VALIDATED
                    or supercheck_status == VALIDATED_WITH_CHANGES
                    or supercheck_status == REJECTED
                ):
                    if not "parent_annotation" in dict(request.data):
                        ret_dict = {"message": "Missing param : parent_annotation!"}
                        ret_status = status.HTTP_400_BAD_REQUEST
                        return Response(ret_dict, status=ret_status)
                    if supercheck_status == REJECTED:
                        rev_loop_count = task.revision_loop_count
                        if (
                            rev_loop_count["super_check_count"]
                            >= task.project_id.revision_loop_count
                        ):
                            ret_dict = {
                                "message": "Maximum revision loop count for task reached!"
                            }
                            ret_status = status.HTTP_403_FORBIDDEN
                            return Response(ret_dict, status=ret_status)

                if update_annotated_at:
                    annotation_obj.annotated_at = datetime.now(timezone.utc)
                    annotation_obj.save(update_fields=["annotated_at"])
                if (
                    annotation_obj.task.project_id.project_type
                    == "InstructionDrivenChat"
                ):
                    if isinstance(request.data["result"], str):
                        ret_dict = {
                            "message": "Please send the result as list when you are not auto-saving."
                        }
                        ret_status = status.HTTP_400_BAD_REQUEST
                        return Response(ret_dict, status=ret_status)
                    if (
                        isinstance(request.data["result"], list)
                        and isinstance(annotation_obj.result, list)
                        and len(annotation_obj.result) > len(request.data["result"])
                    ):
                        request.data["result"] = annotation_obj.result
                        request.data[
                            "meta_stats"
                        ] = compute_meta_stats_for_instruction_driven_chat(
                            annotation_obj.result
                        )
                    else:
                        request.data[
                            "meta_stats"
                        ] = compute_meta_stats_for_instruction_driven_chat(
                            request.data["result"]
                        )
                annotation_response = super().partial_update(request)
                if is_IDC:
                    annotation_response.data["output"] = output_result
                annotation_id = annotation_response.data["id"]
                annotation = Annotation.objects.get(pk=annotation_id)

                task = annotation.task

                if supercheck_status in [DRAFT, SKIPPED]:
                    task.task_status = REVIEWED
                    task.save()

                if (
                    supercheck_status == VALIDATED
                    or supercheck_status == VALIDATED_WITH_CHANGES
                    or supercheck_status == REJECTED
                ):
                    task.correct_annotation = annotation
                    parent = annotation.parent_annotation
                    parent.supercheck_notes = annotation.supercheck_notes
                    if supercheck_status == REJECTED:
                        parent.annotation_status = REJECTED
                        task.task_status = ANNOTATED
                        rev_loop_count = task.revision_loop_count
                        if not is_rejected:
                            rev_loop_count["super_check_count"] = (
                                1 + rev_loop_count["super_check_count"]
                            )
                        task.revision_loop_count = rev_loop_count
                    else:
                        task.task_status = SUPER_CHECKED
                    parent.save(update_fields=["supercheck_notes", "annotation_status"])
                    task.save()

                if supercheck_status in [
                    VALIDATED,
                    VALIDATED_WITH_CHANGES,
                    SKIPPED,
                    DRAFT,
                ]:
                    parent = annotation.parent_annotation
                    grand_parent = parent.parent_annotation
                    if (parent.annotation_status) not in [
                        ACCEPTED,
                        ACCEPTED_WITH_MAJOR_CHANGES,
                        ACCEPTED_WITH_MINOR_CHANGES,
                    ]:
                        if parent.annotated_at is None:
                            parent.annotated_at = datetime.now(timezone.utc)
                            parent.save(update_fields=["annotated_at"])
                        parent.annotation_status = ACCEPTED
                        parent.save(update_fields=["annotation_status"])
                    if (grand_parent.annotation_status) not in [LABELED]:
                        if grand_parent.annotated_at is None:
                            grand_parent.annotated_at = datetime.now(timezone.utc)
                            grand_parent.save(update_fields=["annotated_at"])
                        grand_parent.annotation_status = LABELED
                        grand_parent.save(update_fields=["annotation_status"])

                if supercheck_status in [UNVALIDATED, REJECTED, DRAFT, SKIPPED]:
                    task.correct_annotation = None
                    task.save()
        annotation_response.data["message"] = response_message
        return annotation_response

    def destroy(self, request, pk=None):
        instance = self.get_object()
        annotation_id = instance.id
        annotation = Annotation.objects.get(pk=annotation_id)
        task = annotation.task
        task.task_status = INCOMPLETE
        task.save()

        annotation_response = super().destroy(request)

        return Response({"message": "Annotation Deleted"}, status=status.HTTP_200_OK)

    # def update(self, request, pk=None):
    #     annotation_response = super().partial_update(request)
    #     task_id = request.data["task"]
    #     task = Task.objects.get(pk=task_id)
    #     annotation_id = annotation_response.data["id"]
    #     annotation = Annotation.objects.get(pk=annotation_id)
    #     if task.project_id.required_annotators_per_task == task.annotations.count():
    #     # if True:
    #         task.task_status = LABELED
    #         # TODO: Support accepting annotations manually
    #         if task.annotations.count() == 1:
    #             task.correct_annotation = annotation
    #             task.task_status = ACCEPTED
    #     else:
    #         task.task_status = UNLABELED

    #     task.save()
    #     return annotation_response

    # convert chitralekha_format to LSF
    def convert_chitralekha_format_to_LSF(
        self, result, task, is_acoustic=False, acoustic_enabled=False
    ):
        modified_result = []
        audio_duration = task.data["audio_duration"]
        if result == None or len(result) == 0:
            return modified_result
        for idx, val in enumerate(result):
            if "standardised_transcription" in val:
                if acoustic_enabled:
                    standardised_dict = {
                        "id": f"chitralekha_{idx}s{generate_random_string(13 - len(str(idx)))}",
                        "origin": "manual",
                        "to_name": "audio_url",
                        "from_name": "standardised_transcription",
                        "original_length": audio_duration,
                        "type": "textarea",
                        "value": {
                            "text": [val["standardised_transcription"]],
                        },
                    }
                    modified_result.append(standardised_dict)
                continue
            if "type" in val or "value" in val:
                print(f"The item number {idx} is already in LSF")
                modified_result.append(val)
                continue
            label_dict = {
                "origin": "manual",
                "to_name": "audio_url",
                "from_name": "labels",
                "original_length": audio_duration,
            }
            text_dict = {
                "origin": "manual",
                "to_name": "audio_url",
                "from_name": "transcribed_json"
                if not is_acoustic
                else "verbatim_transcribed_json",
                "original_length": audio_duration,
            }

            id = f"chitralekha_{idx}s{generate_random_string(13 - len(str(idx)))}"
            label_dict["id"] = id
            text_dict["id"] = id
            label_dict["type"] = "labels"
            text_dict["type"] = "textarea"

            value_labels = {
                "start": self.convert_formatted_time_to_fractional(val["start_time"]),
                "end": self.convert_formatted_time_to_fractional(val["end_time"]),
                "labels": [val["speaker_id"]],
            }
            value_text = {
                "start": self.convert_formatted_time_to_fractional(val["start_time"]),
                "end": self.convert_formatted_time_to_fractional(val["end_time"]),
                "text": [val["text"]],
            }

            label_dict["value"] = value_labels
            text_dict["value"] = value_text

            if acoustic_enabled:
                acoustic_dict = {
                    "origin": "manual",
                    "to_name": "audio_url",
                    "from_name": "acoustic_normalised_transcribed_json",
                    "original_length": audio_duration,
                    "id": id,
                    "type": "textarea",
                    "value": {
                        "start": self.convert_formatted_time_to_fractional(
                            val["start_time"]
                        ),
                        "end": self.convert_formatted_time_to_fractional(
                            val["end_time"]
                        ),
                        "text": [val["acoustic_normalised_text"]],
                    },
                }
                modified_result.append(acoustic_dict)

            modified_result.append(label_dict)
            modified_result.append(text_dict)

        return modified_result

    def convert_formatted_time_to_fractional(self, formatted_time):
        hours, minutes, seconds = map(float, formatted_time.split(":"))
        total_seconds = (hours * 3600) + (minutes * 60) + seconds
        return total_seconds


class PredictionViewSet(
    mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Prediction Viewset with create and update operations.
    """

    queryset = Prediction.objects.all()
    serializer_class = PredictionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        prediction_response = super().create(request)
        return prediction_response


class SentenceOperationViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "sentence1": openapi.Schema(type=openapi.TYPE_STRING),
                "sentence2": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["sentence1", "sentence2"],
        ),
        responses={
            200: "Character level edit distance calculated successfully.",
            400: "Invalid parameters in the request body!",
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="calculate_normalized_character_level_edit_distance",
        url_name="calculate_normalized_character_level_edit_distance",
    )
    def calculate_normalized_character_level_edit_distance(self, request):
        try:
            sentence1 = request.data.get("sentence1")
            sentence2 = request.data.get("sentence2")
        except:
            try:
                sentence1 = request["sentence1"]
                sentence2 = request["sentence2"]
            except:
                return Response(
                    {"message": "Invalid parameters in request body!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            character_level_edit_distance = Levenshtein.distance(sentence1, sentence2)
            normalized_character_level_edit_distance = (
                character_level_edit_distance / len(sentence1)
            )

            return Response(
                {
                    "normalized_character_level_edit_distance": normalized_character_level_edit_distance
                },
                status=status.HTTP_200_OK,
            )
        except:
            return Response(
                {"message": "Invalid parameters in request body!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "sentence1": openapi.Schema(type=openapi.TYPE_STRING),
                "sentence2": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["sentence1", "sentence2"],
        ),
        responses={
            200: "Bleu calculated successfully.",
            400: "Invalid parameters in the request body!",
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="calculate_bleu_score",
        url_name="calculate_bleu_score",
    )
    def calculate_bleu_score(self, request):
        try:
            sentence1 = request.data.get("sentence1")
            sentence2 = request.data.get("sentence2")
        except:
            try:
                sentence1 = request["sentence1"]
                sentence2 = request["sentence2"]
            except:
                return Response(
                    {"message": "Invalid parameters in request body!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            sentence1 = [sentence1]
            sentence2 = [[sentence2]]

            bleu = sacrebleu.corpus_bleu(sentence1, sentence2)

            bleu_score = bleu.score

            return Response(
                {"bleu_score": str(bleu_score)},
                status=status.HTTP_200_OK,
            )
        except:
            return Response(
                {"message": "Invalid parameters in request body!"},
                status=status.HTTP_400_BAD_REQUEST,
            )


def get_llm_output(prompt, task, annotation, project_metadata_json):
    # CHECKS
    intent = task.data["meta_info_intent"]
    domain = task.data["meta_info_domain"]
    lang_type = task.data["meta_info_language"]
    ann_result = (
        json.loads(annotation.result)
        if isinstance(annotation.result, str)
        else annotation.result
    )
    project_metadata = (
        json.loads(project_metadata_json)
        if isinstance(project_metadata_json, str)
        else project_metadata_json
    )
    if prompt in [None, "Null", 0, "None", "", " "]:
        return -1
    intentDomain_test, lang_test, duplicate_test = False, False, False
    if project_metadata:
        if (
            "intentDomain_test" in project_metadata
            and project_metadata["intentDomain_test"] == "True"
        ):
            intentDomain_test = True
        if (
            "lang_check" in project_metadata
            and project_metadata["lang_check"] == "True"
        ):
            lang_test = True
        if (
            "duplicate_check" in project_metadata
            and project_metadata["duplicate_check"] == "True"
        ):
            duplicate_test = True

    if len(ann_result) == 0 and intentDomain_test and intent and domain:
        intent_check, domain_check, reason = evaluate_prompt_alignment(
            prompt, domain, intent
        )
    # if lang_type and lang_test:
    #     lang_check = prompt_lang_check(prompt, lang_type)
    if len(ann_result) > 0 and duplicate_test:
        dup_check = duplicate_check(ann_result, prompt)

    # GET MODEL OUTPUT
    history = ann_result
    model = task.data["model"]
    model_output = get_model_output(
        "We will be rendering your response on a frontend. so please add spaces or indentation or nextline chars or "
        "bullet or numberings etc. suitably for code or the text. wherever required.",
        prompt,
        history,
        model,
    )
    res = format_model_output(model_output)
    if res in [None, "Null", 0, "None", "", " "]:
        return -1
    return res


def format_model_output(model_output):
    result = ""
    if isinstance(model_output, list):
        for o in model_output:
            try:
                result += o["value"]
            except KeyError as k:
                continue
        return result
    else:
        return model_output


@swagger_auto_schema(
    method="get",
    operation_description="Get a list of Celery tasks with an optional filter by task state. use State = 'FAILURE' for retrieving failed tasks, State = 'SUCCESS' for retrieving successful tasks, State = 'STARTED' for retrieving active tasks and State = None for all retrieving tasks",
    responses={
        200: "Success",
        400: "Bad Request",
    },
    manual_parameters=[
        openapi.Parameter(
            name="state",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Filter tasks by state",
            required=False,
        ),
    ],
)
@api_view(["GET"])
def get_celery_tasks(request):
    filters = request.GET
    filtered_tasks = query_flower(filters)
    for i in filtered_tasks:
        if filtered_tasks[i]["name"] in Queued_Task_name:
            filtered_tasks[i]["name"] = Queued_Task_name[filtered_tasks[i]["name"]]
    for i in filtered_tasks:
        if filtered_tasks[i]["succeeded"] is not None:
            filtered_tasks[i]["succeeded"] = datetime.fromtimestamp(
                filtered_tasks[i]["succeeded"], tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if filtered_tasks[i]["failed"] is not None:
            filtered_tasks[i]["failed"] = datetime.fromtimestamp(
                filtered_tasks[i]["failed"], tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if filtered_tasks[i]["started"] is not None:
            filtered_tasks[i]["started"] = datetime.fromtimestamp(
                filtered_tasks[i]["started"], tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if filtered_tasks[i]["received"] is not None:
            filtered_tasks[i]["received"] = datetime.fromtimestamp(
                filtered_tasks[i]["received"], tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    if "error" in filtered_tasks:
        return JsonResponse({"message": filtered_tasks["error"]}, status=503)
    page_number = request.GET.get("page")
    page_size = int(request.GET.get("page_size", 10))
    data = paginate_queryset(filtered_tasks, page_number, page_size)
    return JsonResponse(data["results"], safe=False)


class TransliterationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, target_language, data, *args, **kwargs):
        response_transliteration = requests.get(
            os.getenv("TRANSLITERATION_URL") + target_language + "/" + data,
            headers={"Authorization": "Bearer " + os.getenv("TRANSLITERATION_KEY")},
        )

        transliteration_output = response_transliteration.json()
        return Response(transliteration_output, status=status.HTTP_200_OK)
