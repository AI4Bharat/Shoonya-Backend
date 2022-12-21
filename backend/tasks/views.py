from locale import normalize
from urllib.parse import unquote
import ast

from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated


from tasks.models import *
from tasks.serializers import (
    TaskSerializer,
    AnnotationSerializer,
    PredictionSerializer,
    TaskAnnotationSerializer,
)

from users.models import User
from projects.models import Project

from utils.search import process_search_query

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rapidfuzz.distance import Levenshtein
import sacrebleu

from utils.date_time_conversions import utc_to_ist

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
        if (annotator.role == 1) or (
            (annotator.role == 2 or annotator.role == 3)
            and (annotator in annotators_of_this_project)
        ):
            if annotator != task.review_user:
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
        serializer = AnnotationSerializer(annotations, many=True)
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

            view = "user_view"
            exist_req_user = 0
            if user.role == 3 or user.role == 2:
                if not ((user in proj_annotators) or (user in proj_reviewers)):
                    view = "managerial_view"

                    if "req_user" in dict(request.query_params):
                        exist_req_user = 1
                        req_user = request.query_params["req_user"]

            if exist_req_user:
                user_id = int(req_user)

            if "annotation_status" in dict(request.query_params):
                ann_status = request.query_params["annotation_status"]
                ann_status = ast.literal_eval(ann_status)

                if view == "managerial_view":
                    if not ("req_user" in dict(request.query_params)):
                        ann = Annotation.objects.filter(
                            task__project_id_id=proj_id,
                            annotation_status__in=ann_status,
                            parent_annotation_id__isnull=True,
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

                        task_ids = [an.task_id for an in ann_filter1]
                        annotation_status = [an.annotation_status for an in ann_filter1]
                        user_mail = [an.completed_by.email for an in ann_filter1]

                        ordered_tasks = []

                        for idx, ids in enumerate(task_ids):
                            tas = Task.objects.filter(id=ids)
                            tas = tas.values()[0]
                            tas["annotation_status"] = annotation_status[idx]
                            tas["user_mail"] = user_mail[idx]
                            ordered_tasks.append(tas)

                        return Response(ordered_tasks)
                ann = Annotation.objects.filter(
                    task__project_id_id=proj_id,
                    annotation_status__in=ann_status,
                    parent_annotation_id__isnull=True,
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
                ann_filter1 = ann.filter(task__in=tasks)

                task_ids = [an.task_id for an in ann_filter1]
                annotation_status = [an.annotation_status for an in ann_filter1]
                user_mail = [an.completed_by.email for an in ann_filter1]

                ordered_tasks = []

                for idx, ids in enumerate(task_ids):
                    tas = Task.objects.filter(id=ids)
                    tas = tas.values()[0]
                    tas["annotation_status"] = annotation_status[idx]
                    tas["user_mail"] = user_mail[idx]
                    ordered_tasks.append(tas)

                return Response(ordered_tasks)

            if "review_status" in dict(request.query_params):
                rew_status = request.query_params["review_status"]
                rew_status = ast.literal_eval(rew_status)

                if view == "managerial_view":
                    if not ("req_user" in dict(request.query_params)):

                        ann = Annotation.objects.filter(
                            task__project_id_id=proj_id,
                            annotation_status__in=rew_status,
                            parent_annotation_id__isnull=False,
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

                        task_ids = [an.task_id for an in ann_filter1]
                        annotation_status = [an.annotation_status for an in ann_filter1]
                        user_mail = [an.completed_by.email for an in ann_filter1]
                        ordered_tasks = []

                        for idx, ids in enumerate(task_ids):
                            tas = Task.objects.filter(id=ids)
                            tas = tas.values()[0]
                            tas["review_status"] = annotation_status[idx]
                            tas["user_mail"] = user_mail[idx]
                            ordered_tasks.append(tas)

                        return Response(ordered_tasks)

                ann = Annotation.objects.filter(
                    task__project_id_id=proj_id,
                    annotation_status__in=rew_status,
                    parent_annotation_id__isnull=False,
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
                ann_filter1 = ann.filter(task__in=tasks)

                task_ids = [an.task_id for an in ann_filter1]
                annotation_status = [an.annotation_status for an in ann_filter1]
                user_mail = [an.completed_by.email for an in ann_filter1]
                annotator_mail = [
                    Annotation.objects.filter(id=an.parent_annotation_id)[
                        0
                    ].completed_by.email
                    for an in ann_filter1
                ]

                ordered_tasks = []

                for idx, ids in enumerate(task_ids):
                    tas = Task.objects.filter(id=ids)
                    tas = tas.values()[0]
                    tas["review_status"] = annotation_status[idx]
                    tas["user_mail"] = user_mail[idx]
                    tas["annotator_mail"] = annotator_mail[idx]
                    ordered_tasks.append(tas)
                return Response(ordered_tasks)

            tas_status = ["incomplete"]
            if "task_status" in dict(request.query_params):
                tas_status = request.query_params["task_status"]
                tas_status = ast.literal_eval(tas_status)

            if view == "managerial_view":
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

                    tasks = tasks.values()
                    return Response(tasks)

            proj_annotators_ids = [an.id for an in proj_annotators]
            proj_reviewers_ids = [an.id for an in proj_reviewers]

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

                tasks = tasks.values()
                return Response(tasks)

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

                tasks = tasks.values()
                return Response(tasks)

            return Response(
                {"message": " this user not part of this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            return Response(
                {"message": "please provide project_id as a query_param "},
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
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "task_type": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["user_id"],
        ),
        manual_parameters=[
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
        methods=["POST"],
        url_path="annotated_and_reviewed_tasks/get_users_recent_tasks",
        url_name="get_users_recent_tasks",
    )
    def get_users_recent_tasks(self, request):
        try:
            user_id = request.data.get("user_id")
            task_type = request.data.get("task_type", "annotation")

            user = User.objects.get(pk=user_id)

            annotations = Annotation.objects.filter(completed_by=user)
            if task_type == "review":
                annotations = annotations.filter(parent_annotation__isnull=False)
            else:
                annotations = annotations.filter(parent_annotation__isnull=True)

            annotations = annotations.order_by("-updated_at")
            annotations = self.paginate_queryset(annotations)

            response = []

            for annotation in annotations:
                data = {
                    "Project ID": annotation.task.project_id.id,
                    "Task ID": annotation.task.id,
                    "Updated at": utc_to_ist(annotation.updated_at),
                }

                response.append(data)

            return self.get_paginated_response(response)
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
            if not task.project_id.enable_task_reviews:
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

        if not annotation_obj.parent_annotation:
            is_review = False
        else:
            is_review = True

        # Base annotation update
        if not is_review:
            if request.user not in task.annotation_users.all():
                ret_dict = {"message": "You are trying to impersonate another user :("}
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)
            # need to add few filters here

            if "annotation_status" in dict(request.data) and request.data[
                "annotation_status"
            ] in [
                UNLABELED,
                LABELED,
                DRAFT,
                SKIPPED,
            ]:
                annotation_status = request.data["annotation_status"]
            else:
                ret_dict = {"message": "Missing param : annotation_status!"}
                ret_status = status.HTTP_400_BAD_REQUEST
                return Response(ret_dict, status=ret_status)

            annotation_response = super().partial_update(request)
            annotation_id = annotation_response.data["id"]
            annotation = Annotation.objects.get(pk=annotation_id)
            task = annotation.task

            no_of_annotations = task.annotations.filter(
                parent_annotation_id=None, annotation_status="labeled"
            ).count()
            if task.project_id.required_annotators_per_task == no_of_annotations:
                # if True:
                task.task_status = ANNOTATED
                if not task.project_id.enable_task_reviews:
                    if no_of_annotations == 1:
                        task.correct_annotation = annotation

                task.save()

        # Review annotation update
        else:

            if request.user != task.review_user:
                ret_dict = {"message": "You are trying to impersonate another user :("}
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)

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

            annotation_response = super().partial_update(request)
            annotation_id = annotation_response.data["id"]
            annotation = Annotation.objects.get(pk=annotation_id)
            task = annotation.task

            if (
                review_status == ACCEPTED
                or review_status == ACCEPTED_WITH_MINOR_CHANGES
                or review_status == ACCEPTED_WITH_MAJOR_CHANGES
                or review_status == TO_BE_REVISED
            ):
                if review_status != TO_BE_REVISED:
                    task.correct_annotation = annotation
                    parent = annotation.parent_annotation
                    parent.review_notes = annotation.review_notes
                    parent.save()
                task.task_status = REVIEWED
                task.save()

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
