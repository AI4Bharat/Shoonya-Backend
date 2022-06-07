from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly

import json
from urllib.parse import unquote

from tasks.models import *
from tasks.serializers import TaskSerializer, AnnotationSerializer, PredictionSerializer

from users.models import User
from projects.models import Project

# Create your views here.


def parse_for_data_types(string: str):
    """
    Convert variables to their appropriate type
    """
    try:  # Try to convert to a int
        return int(string)
    except Exception:
        pass

    try:  # Try to convert to a float
        return float(string)
    except Exception:
        pass

    if string.lower() in ["true", "false"]:
        return bool(string)

    return string  # If none work, return a string


def extract_search_params(query_dict: dict) -> dict:
    new_dict: dict = {}
    for i in query_dict.items():
        if "search_" in i[0]:
            new_dict[i[0][7:]] = unquote(i[1])

    return new_dict


def process_search_query(query_dict: dict) -> dict:
    """
    Extract the query params into a queryset dictionary.
    """
    parsed_value: any = None
    queryset_dict: dict = {}
    terms_not_in_data: list = [
        "id",
        "task_status",
        "metadata_json",
        "project_id",
        "input_data",
        "output_data",
        "correct_annotation",
        "annotation_users",
        "review_user",
    ]

    try:
        for i, j in extract_search_params(query_dict).items():
            parsed_value = parse_for_data_types(j)
            print({i:j})
            if i not in terms_not_in_data:
                if type(parsed_value) == str:
                    queryset_dict[f"data__{i}__unaccent__icontains"] = parsed_value  # Unaccent doesn't work as intended.
                else:
                    queryset_dict[f"data__{i}"] = parsed_value
            else:
                if type(parsed_value) != str:
                    queryset_dict[i] = parse_for_data_types(j)
                else:
                    queryset_dict[f"{i}__icontains"] = parsed_value  # Unaccent is not supported for CharField
    except Exception as e:
        print(f"\033[1mError found while processing query dictionary. In: {e}\033[0m")

    return queryset_dict


class TaskViewSet(viewsets.ModelViewSet, mixins.ListModelMixin):
    """
    Model Viewset for Tasks. All Basic CRUD operations are covered here.
    """

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

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
            userRole = user.role
            user_obj = User.objects.get(pk=user.id)

            if userRole == 1 and not user_obj.is_superuser:
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
        queryset = queryset.filter(**process_search_query(request.GET))

        if "task_status" in dict(request.query_params):
            queryset = queryset.filter(task_status=request.query_params["task_status"])
        else:
            queryset = queryset.filter(task_status=UNLABELED)

        queryset = queryset.order_by("id")

        page = request.GET.get("page")
        try:
            page = self.paginate_queryset(queryset)
        except Exception as e:
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

        if page is not None:
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
    permission_classes = [IsAuthenticatedOrReadOnly]

    def create(self, request):
        # TODO: Correction annotation to be filled by validator
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
            task.task_status = LABELED
            # TODO: Support accepting annotations manually
            if task.annotations.count() == 1:
                task.correct_annotation = annotation
                task.task_status = ACCEPTED
        else:
            task.task_status = UNLABELED
        task.save()
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

        if request.user not in task.annotation_users.all():
            ret_dict = {"message": "You are trying to impersonate another user :("}
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)

        if task.project_id.required_annotators_per_task == task.annotations.count():
            # if True:
            task.task_status = LABELED
            # TODO: Support accepting annotations manually
            if task.annotations.count() == 1:
                task.correct_annotation = annotation
                task.task_status = ACCEPTED
        else:
            task.task_status = UNLABELED

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
    permission_classes = [IsAuthenticatedOrReadOnly]

    def create(self, request):
        prediction_response = super().create(request)
        return prediction_response
