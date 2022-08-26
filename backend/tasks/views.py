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
        users = []
        for u_id in user_ids:
            try:
                users.append(User.objects.get(id=u_id))
            except User.DoesNotExist:
                return Response(
                    {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )
        task.assign(users)
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

        if (
            user.role == User.ANNOTATOR
            and user not in project.annotation_reviewers.all()
        ):
            if user in project.users.all():
                annotations = annotations.filter(completed_by=user)
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
        is_review_mode = (
                "mode" in dict(request.query_params)
                and request.query_params["mode"] == "review"
            )
        if "project_id" in dict(request.query_params):
            # Step 1: get the logged-in user details
            # Step 2: if - he is NOT (superuser, or manager or org owner), filter based on logged in user.
            # Step 3: else - if user_filter passed, filter based on user
            # Step 4: else - else don't filter

            user = request.user
            user_obj = User.objects.get(pk=user.id)


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
                if request.user.role == User.ANNOTATOR and not user_obj.is_superuser:
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
            queryset = Task.objects.all()

        # Handle search query (if any)
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
        if is_review_mode:
            task_status = LABELED
        if "task_status" in dict(request.query_params):
            queryset = queryset.filter(task_status=request.query_params["task_status"])
            task_status = request.query_params["task_status"]
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

        project_details = Project.objects.filter(id=request.query_params["project_id"])
        project_type = project_details[0].project_type
        project_type = project_type.lower()
        is_translation_project = True if "translation" in project_type else False

        user = request.user

        if (
            (is_translation_project)
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
                user.role == User.ANNOTATOR
                and user
                in Project.objects.get(
                    id=request.query_params["project_id"]
                ).users.all()
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
            and (page is not None)
            and (task_status in {ACCEPTED, ACCEPTED_WITH_CHANGES})
        ):
            # Shows annotations for review_mode
            serializer = TaskAnnotationSerializer(page, many=True)
            data = serializer.data
            for index, each_data in enumerate(data):
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
            return self.get_paginated_response(data)

        # serializer = TaskSerializer(queryset, many=True)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        task_response = super().partial_update(request)
        task_id = task_response.data["id"]
        task = Task.objects.get(pk=task_id)
        task.release_lock(request.user)
        return task_response


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
        task.release_lock(request.user)
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

            labeled_annotation_count = Annotation.objects.filter(task=task).filter(annotation_status=LABELED).count()
            if task.project_id.required_annotators_per_task == labeled_annotation_count:
                # if True:
                task.task_status = COMPLETE
                # TODO: Support accepting annotations manually
                # if task.annotations.count() == 1:
                if not task.project_id.enable_task_reviews:
                    task.correct_annotation = annotation
                    task.task_status = ACCEPTED
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
        annotation.annotation_status = UNLABELED
        annotation.result = []
        annotation.save()
        task = annotation.task
        if task.task_status == COMPLETE:
            task.task_status = INCOMPLETE
        task.save()

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
