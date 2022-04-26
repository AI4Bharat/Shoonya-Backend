from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from tasks.models import *
from tasks.serializers import TaskSerializer, AnnotationSerializer, PredictionSerializer

from users.models import User
from projects.models import Project

# Create your views here.

class TaskViewSet(viewsets.GenericViewSet,
    mixins.ListModelMixin):
    """
        Generic Viewset for Tasks. All Basic CRUD operations are covered here.
    """

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk):
        """
            Assigns users with the given user IDs to the particular task.
        """
        task = self.get_object()
        user_ids = request.data.get('user_ids')
        users = []
        for u_id in user_ids:
            try:
                users.append(User.objects.get(id=u_id))
            except User.DoesNotExist:
                return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        task.assign(users)
        return Response({"message": "Task assigned"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='annotations')
    def annotations(self, request, pk):
        """
            Returns all the annotations associated with a particular task.
        """
        task = self.get_object()
        annotations = Annotation.objects.filter(task=task)
        serializer = AnnotationSerializer(annotations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='predictions')
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
            queryset = Task.objects.filter(project_id__exact=request.query_params["project_id"])
        else:
            queryset = Task.objects.all()
        
        page = request.GET.get('page')
        try: 
            page = self.paginate_queryset(queryset)
        except Exception as e:
            page = []
            data = page
            return Response({
                "status": status.HTTP_200_OK,
                "message": 'No more record.',
                "data" : data
                })

        if page is not None:
            serializer = TaskSerializer(page, many=True)
            data = serializer.data
            return self.get_paginated_response(data)

        #serializer = TaskSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        task_response = super().partial_update(request)
        task_id = task_response.data["id"]
        task = Task.objects.get(pk=task_id)
        task.release_lock(request.user)
        return task_response
        

class AnnotationViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
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
        user_id = int(request.data["completed_by"])
        try:
            # Check if user id does not match with authorized user
            assert user_id == request.user.id
        except AssertionError:
            ret_dict = {"message": "You are trying to impersonate an user :("}
            ret_status = status.HTTP_403_FORBIDDEN
            return Response(ret_dict, status=ret_status)
        if task.project_id.required_annotators_per_task <= task.annotations.count():
            ret_dict = {"message": "Required annotations criteria is already satisfied!"}
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
            task.save()
        return annotation_response


class PredictionViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
        Prediction Viewset with create and update operations.
    """
    queryset = Prediction.objects.all()
    serializer_class = PredictionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def create(self, request):
        prediction_response = super().create(request)
        return prediction_response
