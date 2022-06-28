from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework import status
from projects.utils import no_of_words
from tasks.models import Task
from datetime import datetime
from projects.utils import is_valid_date
from .models import Organization
from .serializers import OrganizationSerializer
from .decorators import is_organization_owner, is_particular_organization_owner
from users.serializers import UserFetchSerializer
from users.models import User


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    A viewset for Organization CRUD, access limited only to organization Managers and Superuser.
    """

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @is_organization_owner
    def create(self, request, pk=None, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @is_particular_organization_owner
    def update(self, request, pk=None, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @is_particular_organization_owner
    def partial_update(self, request, pk=None, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"message": "Deleting of Organizations is not supported!"},
            status=status.HTTP_403_FORBIDDEN,
        )

    @is_particular_organization_owner
    @action(
        detail=True, methods=["GET"], name="Get Organization users", url_name="users"
    )
    def users(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        users = User.objects.filter(organization=organization)
        serializer = UserFetchSerializer(users, many=True)
        return Response(serializer.data)


    @is_organization_owner
    @action(
        detail=True, methods=["POST"], name="Get Organization level  users analytics ", url_name="analytics"
    )
    def analytics(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        users = User.objects.filter(organization=organization)

        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        from_date = from_date + ' 00:00'
        to_date = to_date + ' 23:59'
        tgt_language = request.data.get('tgt_language')
        project_type = request.data.get("project_type")
        project_type_lower =  project_type.lower()
        is_translation_project = True if  "translation" in  project_type_lower  else False



        cond, invalid_message = is_valid_date(from_date)
        if not cond:
            return Response({"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST)
        
        cond, invalid_message = is_valid_date(to_date)
        if not cond:
            return Response({"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST)

        start_date = datetime.strptime(from_date, '%Y-%m-%d %H:%M')
        end_date = datetime.strptime(to_date, '%Y-%m-%d %H:%M')

        if start_date > end_date:
            return Response({"message": "'To' Date should be after 'From' Date"}, status=status.HTTP_400_BAD_REQUEST)


        result =[]
        for user in users:
            name = user.username
            email = user.get_username()
            # total_no_of_tasks_assigned = Task.objects.filter(annotation_users =user)
            # total_no_of_tasks_count = total_no_of_tasks_assigned.count()

            annotated_tasks = Task.objects.filter(annotation_users =user,project_id__project_type = project_type,project_id__tgt_language=tgt_language,task_status='accepted',correct_annotation__created_at__range = [start_date, end_date])
            annotated_tasks_count = annotated_tasks.count()

            if is_translation_project:
                total_word_count_list = [no_of_words(each_task.data['input_text']) for  each_task in annotated_tasks]
                total_word_count = sum(total_word_count_list)
                result.append({ 'User Name' : name,
                                'Email' : email,
                                'Language' : tgt_language,
                                'No. of Annotated Tasks' : annotated_tasks_count,
                                'No. of Words' : total_word_count
                        } )
            else :
                result.append({ 'User Name' : name,
                                'Email' : email,
                                'Language' : tgt_language,
                                'No. of Annotated Tasks' : annotated_tasks_count
                        } )
        if is_translation_project:
            final_result = sorted(result, key=lambda x: x['No. of Words'])
            return Response(final_result)
        else:
            return Response(result)