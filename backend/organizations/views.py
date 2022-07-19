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
from projects.models import Project
from django.db.models import Q


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
        detail=True, methods=["POST"], name="Get Organization level  users analytics ", url_name="user_analytics"
    )
    def user_analytics(self, request, pk=None):
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
        sort_by_column_name = request.data.get('sort_by_column_name')
        descending_order = request.data.get('descending_order')
        if sort_by_column_name == None :
            sort_by_column_name = "User Name"

        if descending_order == None :
            descending_order = False

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

        if tgt_language == None :
            selected_language = '-'
        else :
            selected_language = tgt_language

        result =[]
        for user in users:
            name = user.username
            email = user.get_username()
            list_of_user_languages = user.languages

            if tgt_language != None and tgt_language not in list_of_user_languages:
                continue
            if tgt_language == None :
                
                total_no_of_tasks_assigned = Task.objects.filter(annotation_users =user,\
                    project_id__project_type = project_type,project_id__organization_id = organization)
                total_no_of_tasks_count = total_no_of_tasks_assigned.count()
               
                projects_objs = Project.objects.filter(users = user,project_type = project_type,organization_id = organization)
                no_of_projects = projects_objs.count()

            else :
                total_no_of_tasks_assigned = Task.objects.filter(annotation_users =user,\
                    project_id__project_type = project_type,project_id__tgt_language=tgt_language,project_id__organization_id = organization)
                total_no_of_tasks_count = total_no_of_tasks_assigned.count()

                projects_objs = Project.objects.filter(users = user,project_type = project_type,\
                    tgt_language = tgt_language,organization_id = organization)
                no_of_projects = projects_objs.count()


            annotated_tasks = total_no_of_tasks_assigned.filter(task_status='accepted',correct_annotation__created_at__range = [start_date, end_date])
            annotated_tasks_count = annotated_tasks.count()

            avg_lead_time = 0
            lead_time_annotated_tasks = [ eachtask.correct_annotation.lead_time for eachtask in annotated_tasks]
            if len(lead_time_annotated_tasks) > 0 :
                avg_lead_time = sum(lead_time_annotated_tasks) / len(lead_time_annotated_tasks)

            total_skipped_tasks = total_no_of_tasks_assigned.filter(task_status='skipped')
            total_skipped_tasks_count = total_skipped_tasks.count()
        
            total_unlabeled_tasks = total_no_of_tasks_assigned.filter(task_status='unlabeled')
            total_unlabeled_tasks_count = total_unlabeled_tasks.count()
        
            total_draft_tasks = total_no_of_tasks_assigned.filter(task_status='draft')
            total_draft_tasks_count = total_draft_tasks.count()
        

            no_of_workspaces_objs =len(set([ each_proj.workspace_id.id for each_proj in projects_objs]))


            if is_translation_project:
                total_word_count_list = [no_of_words(each_task.data['input_text']) for  each_task in annotated_tasks]
                total_word_count = sum(total_word_count_list)

                result.append({ 'User Name' : name,
                                'Email' : email,
                                'Language' : selected_language,
                                'Project Type' :project_type,
                                'No.Of Tasks Assigned' : total_no_of_tasks_count,
                                'No. of Annotated Tasks in Given Date Range' : annotated_tasks_count,
                                'Average Annotation Time (In Seconds)' : round(avg_lead_time,2),
                                'Skipped Tasks' : total_skipped_tasks_count,
                                'Unlabeled Tasks' : total_unlabeled_tasks_count,
                                'Draft Tasks': total_draft_tasks_count,
                                'No. of Projects' :no_of_projects,
                                'No. of Workspaces' : no_of_workspaces_objs,
                                'Word Count Of Annotated Tasks' : total_word_count
                        } )
            else :
                result.append({ 'User Name' : name,
                                'Email' : email,
                                'Language' : selected_language,
                                'Project Type' :project_type,
                                'No.Of Tasks Assigned' : total_no_of_tasks_count,
                                'No. of Annotated Tasks in Given Date Range' : annotated_tasks_count,
                                'Average Annotation Time (In Seconds)' : round(avg_lead_time,2),
                                'Skipped Tasks' : total_skipped_tasks_count,
                                'Unlabeled Tasks' : total_unlabeled_tasks_count,
                                'Draft Tasks': total_draft_tasks_count,
                                'No. of Projects' :no_of_projects,
                                'No. of Workspaces' : no_of_workspaces_objs
                        } )
        if not is_translation_project and sort_by_column_name == 'Word Count Of Annotated Tasks' :
            return Response({'message' : 'presently sort by word count for non translation projects not activated '})
        else :
            final_result = sorted(result, key=lambda x: x[sort_by_column_name],reverse=descending_order)
            return Response(final_result)


    @is_organization_owner
    @action(
        detail=True, methods=["POST"], name="Get Organization level  Project analytics ", url_name="project_analytics"
    )
    def project_analytics(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        from_date = from_date + ' 00:00'
        to_date = to_date + ' 23:59'
        tgt_language = request.data.get('tgt_language')
        project_type = request.data.get("project_type")
        

        sort_by_column_name = request.data.get('sort_by_column_name')
        descending_order = request.data.get('descending_order')
        if sort_by_column_name == None :
            sort_by_column_name = "User Name"

        if descending_order == None :
            descending_order = False

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

        if tgt_language == None :
            selected_language = '-'
            projects_obj  = Project.objects.filter(organization_id = organization,project_type = project_type)
        else :
            selected_language = tgt_language
            projects_obj  = Project.objects.filter(organization_id = organization,tgt_language = tgt_language,project_type = project_type)
        final_result = []
        if projects_obj.count() !=0:
            for proj in projects_obj:
                proj_manager = [manager.get_username() for manager in proj.workspace_id.managers.all()]
                try :
                    org_owner = proj.organization_id.created_by.get_username()
                    proj_manager.append(org_owner)
                except:
                    pass
                project_id = proj.id
                project_name = proj.title
                project_type = proj.project_type
                all_tasks = Task.objects.filter(project_id = proj.id)
                total_tasks = all_tasks.count()
                annotators_list = [ user_.get_username()  for user_ in   proj.users.all()]
                no_of_annotators_assigned = len( [annotator for annotator in annotators_list if annotator not in proj_manager ])
                un_labeled_task = Task.objects.filter(project_id = proj.id,task_status = 'unlabeled')
                un_labeled_count = un_labeled_task.count()
                labeled_count = Task.objects.filter(Q (project_id = proj.id) & Q(task_status = 'accepted') & Q (correct_annotation__created_at__range = [start_date, end_date])).count()
                skipped_count = Task.objects.filter(project_id = proj.id,task_status = 'skipped').count()
                dropped_tasks = Task.objects.filter(project_id = proj.id,task_status = 'draft').count()
                if total_tasks == 0:
                    project_progress = 0.0
                else :
                    project_progress = (labeled_count / total_tasks) * 100
                result = {
                    "Project Id" : project_id,
                    "Project Name" : project_name,
                    "Language" : selected_language,
                    "Project Type" : project_type,
                    "Total No.Of Tasks" : total_tasks,
                    "Total No.Of Annotators Assigned" : no_of_annotators_assigned,
                    "Annotated Tasks In Given Date Range" : labeled_count,
                    "Unlabeled Tasks" : un_labeled_count,
                    "Skipped Tasks": skipped_count,
                    "Draft Tasks" : dropped_tasks,
                    "Project Progress" : round(project_progress,3)
                    }
                final_result.append(result)
        return Response(final_result)