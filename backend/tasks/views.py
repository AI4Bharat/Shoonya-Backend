from locale import normalize
from urllib.parse import unquote

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
        user = request.user

        if user != task.review_user:
            if user in project.annotators.all():
                annotations = annotations.filter(completed_by=user)
            elif user.role == User.ANNOTATOR:
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
        if "project_id" in dict(request.query_params):
            # Step 1: get the logged-in user details
            # Step 2: if - he is NOT (superuser, or manager or org owner), filter based on logged in user.
            # Step 3: else - if user_filter passed, filter based on user
            # Step 4: else - else don't filter

            user = request.user
            user_obj = User.objects.get(pk=user.id)
            is_review_mode = (
                "mode" in dict(request.query_params)
                and request.query_params["mode"] == "review"
            )

            if is_review_mode:
                if (
                    request.user
                    in Project.objects.get(
                        id=request.query_params["project_id"]
                    ).annotation_reviewers.all()
                ):
                    queryset = Task.objects.filter(
                        project_id__exact=request.query_params["project_id"]
                    ).filter(review_user=user.id)

                elif (
                    request.user.role == User.WORKSPACE_MANAGER
                    or request.user.role == User.ORGANIZATION_OWNER
                ):
                    if "user_filter" in dict(request.query_params):
                        queryset = Task.objects.filter(
                            project_id__exact=request.query_params["project_id"]
                        ).filter(review_user=request.query_params["user_filter"])
                    else:
                        queryset = Task.objects.filter(
                            project_id__exact=request.query_params["project_id"]
                        )
                else:
                    return Response(
                        {"message": "You do not have access!"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                if (
                    request.user
                    in Project.objects.get(
                        id=request.query_params["project_id"]
                    ).annotators.all()
                ):
                    queryset = Task.objects.filter(
                        project_id__exact=request.query_params["project_id"]
                    ).filter(annotation_users=user.id)
                else:
                    if "user_filter" in dict(request.query_params):
                        queryset = Task.objects.filter(
                            project_id__exact=request.query_params["project_id"]
                        ).filter(annotation_users=request.query_params["user_filter"])
                    else:
                        queryset = Task.objects.filter(
                            project_id__exact=request.query_params["project_id"]
                        )

        else:
            is_review_mode = (
                "mode" in dict(request.query_params)
                and request.query_params["mode"] == "review"
            )
            queryset = Task.objects.all()

        # Handle search query (if any)
        if len(queryset):
            queryset = queryset.filter(
                **process_search_query(
                    request.GET, "data", list(queryset.first().data.keys())
                )
            )

        if "page" in dict(request.query_params):
            page = request.query_params["page"]
            if int(page) == 0:
                queryset = queryset.order_by("id")
                serializer = TaskSerializer(queryset, many=True)
                data = serializer.data
                return Response(data)

        task_status = UNLABELED
        accepted_wt_changes_or_to_be_revised_task = False
        if is_review_mode:
            task_status = LABELED
        if "task_status" in dict(request.query_params):
            queryset = queryset.filter(task_status=request.query_params["task_status"])
            task_status = request.query_params["task_status"]

            if task_status in {ACCEPTED_WITH_CHANGES, TO_BE_REVISED, ACCEPTED}:
                accepted_wt_changes_or_to_be_revised_task = True

        else:
            queryset = queryset.filter(task_status=task_status)

        queryset = queryset.order_by("id")

        page = request.GET.get("page")
        try:
            page = self.paginate_queryset(queryset)
        except Exception:
            page = []
            data = page
            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "message": "No more record.",
                    # TODO: should be results. Needs testing to be sure.
                    "data": data,
                }
            )
        if "project_id" in dict(request.query_params):
            project_details = Project.objects.filter(
                id=request.query_params["project_id"]
            )
            project_type = project_details[0].project_type
            project_type = project_type.lower()
            is_conversation_project = True if "conversation" in project_type else False
            is_translation_project = True if "translation" in project_type else False
        else:

            page = self.paginate_queryset(queryset)
            serializer = TaskAnnotationSerializer(page, many=True)
            data = serializer.data

            for index, each_data in enumerate(data):
                if accepted_wt_changes_or_to_be_revised_task and is_review_mode:
                    ann = Annotation.objects.filter(
                        task_id=data[index]["id"], parent_annotation__isnull=True
                    )
                    email = ann[0].completed_by.email
                    data[index]["email"] = email

            return self.get_paginated_response(data)

        user = request.user

        if (
            (is_translation_project)
            and (not is_conversation_project)
            and (page is not None)
            and (task_status in {DRAFT, LABELED, TO_BE_REVISED})
            and (not is_review_mode)
        ):
            serializer = TaskAnnotationSerializer(page, many=True)
            data = serializer.data
            task_ids = []
            for index, each_data in enumerate(data):
                task_ids.append(each_data["id"])

            if (
                user
                in Project.objects.get(
                    id=request.query_params["project_id"]
                ).annotators.all()
            ):
                annotation_queryset = Annotation.objects.filter(
                    completed_by=request.user
                ).filter(task__id__in=task_ids)

                for index, each_data in enumerate(data):
                    annotation_queryset_instance = annotation_queryset.filter(
                        task__id=each_data["id"]
                    )
                    if len(annotation_queryset_instance) != 0:
                        annotation_queryset_instance = annotation_queryset_instance[0]
                        data[index]["data"][
                            "output_text"
                        ] = annotation_queryset_instance.result[0]["value"]["text"][0]
                        each_data["machine_translation"] = each_data["data"][
                            "machine_translation"
                        ]
                        del each_data["data"]["machine_translation"]
                return self.get_paginated_response(data)

        if (
            (is_translation_project)
            and (not is_conversation_project)
            and (page is not None)
            and (task_status in {ACCEPTED, ACCEPTED_WITH_CHANGES})
        ):
            # Shows annotations for review_mode
            serializer = TaskAnnotationSerializer(page, many=True)
            data = serializer.data
            for index, each_data in enumerate(data):

                if accepted_wt_changes_or_to_be_revised_task and is_review_mode:
                    ann = Annotation.objects.filter(
                        task_id=data[index]["id"], parent_annotation__isnull=True
                    )
                    email = ann[0].completed_by.email
                    data[index]["email"] = email
                data[index]["data"]["output_text"] = each_data["correct_annotation"][
                    "result"
                ][0]["value"]["text"][0]
                each_data["correct_annotation"] = each_data["correct_annotation"]["id"]
                each_data["machine_translation"] = each_data["data"][
                    "machine_translation"
                ]
                del each_data["data"]["machine_translation"]
            return self.get_paginated_response(data)
        elif page is not None:
            serializer = TaskSerializer(page, many=True)
            data = serializer.data

            for index, each_data in enumerate(data):

                if accepted_wt_changes_or_to_be_revised_task and is_review_mode:
                    ann = Annotation.objects.filter(
                        task_id=data[index]["id"], parent_annotation__isnull=True
                    )
                    email = ann[0].completed_by.email
                    data[index]["email"] = email
            return self.get_paginated_response(data)

        # serializer = TaskSerializer(queryset, many=True)
        return Response(status=status.HTTP_400_BAD_REQUEST)

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
            },
            required=["project_task_start_id", "project_task_end_id"],
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

            num_project_tasks = len(project_tasks)

            if num_project_tasks == 0:
                return Response(
                    {
                        "status": status.HTTP_200_OK,
                        "message": "No rows to delete",
                    }
                )

            project_tasks.delete()
            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "message": f"Deleted {num_project_tasks} data items successfully!",
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
        if task.project_id.required_annotators_per_task == task.annotations.count():
            # if True:
            task.task_status = request.data["task_status"]
            # TODO: Support accepting annotations manually
            # if task.annotations.count() == 1:
            if not task.project_id.enable_task_reviews:
                task.correct_annotation = annotation
                if task.task_status == LABELED:
                    task.task_status = ACCEPTED

        else:
            # To-Do : Fix the Labeled for required_annotators_per_task
            task.task_status = request.data["task_status"]
        task.save()
        return annotation_response

    def create_review_annotation(self, request):
        task_id = request.data["task"]
        if "review_status" in dict(request.data) and request.data["review_status"] in [
            ACCEPTED,
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

        if task.task_status == ACCEPTED:
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
        if review_status == ACCEPTED:
            task.correct_annotation = annotation
            is_modified = annotation_result_compare(
                annotation.parent_annotation.result, annotation.result
            )
            if is_modified:
                review_status = ACCEPTED_WITH_CHANGES
        task.task_status = review_status
        task.save()
        parent_annotation.review_notes = annotation.review_notes
        parent_annotation.save()

        return annotation_response

    def partial_update(self, request, pk=None):
        # task_id = request.data["task"]
        # task = Task.objects.get(pk=task_id)
        # if request.user not in task.annotation_users.all():
        #     ret_dict = {"message": "You are trying to impersonate another user :("}
        #     ret_status = status.HTTP_403_FORBIDDEN
        #     return Response(ret_dict, status=ret_status)

        annotation_response = super().partial_update(request)
        annotation_id = annotation_response.data["id"]
        annotation = Annotation.objects.get(pk=annotation_id)
        task = annotation.task

        if not annotation.parent_annotation:
            is_review = False
        else:
            is_review = True

        # Base annotation update
        if not is_review:
            if request.user not in task.annotation_users.all():
                ret_dict = {"message": "You are trying to impersonate another user :("}
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)

            if task.project_id.required_annotators_per_task == task.annotations.count():
                # if True:
                task.task_status = request.data["task_status"]
                # TODO: Support accepting annotations manually
                # if task.annotations.count() == 1:
                if not task.project_id.enable_task_reviews:
                    task.correct_annotation = annotation
                    if task.task_status == LABELED:
                        task.task_status = ACCEPTED
            else:
                task.task_status = request.data["task_status"]
        # Review annotation update
        else:
            if "review_status" in dict(request.data) and request.data[
                "review_status"
            ] in [ACCEPTED, TO_BE_REVISED]:
                review_status = request.data["review_status"]
            else:
                ret_dict = {"message": "Missing param : review_status"}
                ret_status = status.HTTP_400_BAD_REQUEST
                return Response(ret_dict, status=ret_status)

            if request.user != task.review_user:
                ret_dict = {"message": "You are trying to impersonate another user :("}
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)

            if review_status == ACCEPTED:
                task.correct_annotation = annotation
                is_modified = annotation_result_compare(
                    annotation.parent_annotation.result, annotation.result
                )
                if is_modified:
                    review_status = ACCEPTED_WITH_CHANGES
            else:
                task.correct_annotation = None

            task.task_status = review_status

            parent = annotation.parent_annotation
            parent.review_notes = annotation.review_notes
            parent.save()

        task.save()
        return annotation_response

    def destroy(self, request, pk=None):

        instance = self.get_object()
        annotation_id = instance.id
        annotation = Annotation.objects.get(pk=annotation_id)
        task = annotation.task
        task.task_status = UNLABELED
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
