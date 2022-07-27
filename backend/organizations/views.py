from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework import status
from tasks.models import Task
from datetime import datetime
from .models import Organization
from .serializers import OrganizationSerializer
from .decorators import is_organization_owner, is_particular_organization_owner
from users.serializers import UserFetchSerializer
from users.models import User
from projects.models import Project
from django.db.models import Avg, Count, F, FloatField, Q, Value , Subquery
from django.db.models.functions import Cast, Coalesce
from regex import R
from tasks.models import Annotation
from projects.utils import is_valid_date, no_of_words


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
        users = User.objects.filter(organization=organization).order_by('username')

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
            sort_by_column_name = "Annotator"

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

        if tgt_language == None :

            users_objs_wt_proj_count =   User.objects.filter(organization=organization).order_by('username')\
                .annotate(no_of_projects=Count("project_users", filter = Q(project_users__project_type = project_type),distinct=True))

            users_objs_wt_workspace_count = User.objects.filter(organization=organization).order_by('username')\
                .annotate(no_of_workspaces=Count("organization_users", distinct=True))


            users_objs_all_task_count = User.objects.filter(organization=organization).order_by('username')\
                .annotate(total_tasks=Count("annotation_users" , filter = Q(annotation_users__project_id__project_type = project_type) ))

            
            users_objs_labeled_task_count = User.objects.filter(organization=organization).order_by('username')\
                .annotate(accepted_tasks=Count("annotation",filter=Q(annotation__task__task_status__in=['accepted','rejected','accepted_with_changes','labeled'] )\
                   & Q(annotation__task__project_id__project_type = project_type) & Q(annotation__parent_annotation_id = None) & Q(annotation__updated_at__range = [start_date, end_date]))) 


            users_objs_skipped_task_count  =  User.objects.filter(organization=organization).order_by('username').annotate(skipped_tasks=Count("annotation_users",\
                    filter=Q(annotation_users__task_status="skipped") & Q(annotation_users__project_id__project_type = project_type)))

            users_objs_draft_task_count  =  User.objects.filter(organization=organization).order_by('username')\
                .annotate(draft_tasks=Count("annotation_users",filter=Q(annotation_users__task_status="draft") & Q(annotation_users__project_id__project_type = project_type)))
            users_objs_unlabeled_task_count  =  User.objects.filter(organization=organization).order_by('username')\
                .annotate(unlabeled_task=Count("annotation_users",filter=Q(annotation_users__task_status="unlabeled") & Q(annotation_users__project_id__project_type = project_type)))
            
            time = User.objects.filter(organization=organization).order_by('username').annotate(lead_time=Coalesce(Avg("annotation__lead_time",\
                    filter= Q(annotation__task__task_status__in=['accepted','rejected','accepted_with_changes','labeled']) \
                        & Q(annotation__task__project_id__project_type = project_type) & Q(annotation__parent_annotation_id = None) \
                        & Q(annotation__updated_at__range = [start_date, end_date])),0.0))
            user_word_count =[]
            if is_translation_project:
                for user in users:

                    annotated_tasks = Task.objects.filter(annotation_users =user,\
                        project_id__project_type = project_type ,\
                        task_status__in = ['accepted','rejected','accepted_with_changes','labeled'])

                    annotated_task_ids = list(annotated_tasks.values_list('id',flat = True))
                    annotated_labeled_tasks =Annotation.objects.filter(task_id__in = annotated_task_ids ,parent_annotation_id = None,\
                        updated_at__range = [start_date, end_date])

                    total_word_count_list = [no_of_words(each_task.task.data['input_text']) for  each_task in annotated_labeled_tasks]
                    total_word_count = sum(total_word_count_list)
                    user_word_count.append(total_word_count)

                
            final_result = []
            for i in range(len(users)):
                result=[]
                name = users[i].username
                email = users[i].get_username()

                result.append(("Annotator", name))
                result.append(("Email" ,email))
                result.append(("Language",selected_language))
                result.append(("No. of Workspaces", users_objs_wt_workspace_count[i].no_of_workspaces))
                result.append(("No. of Projects",users_objs_wt_proj_count[i].no_of_projects))
                result.append(("Project Type",project_type))
                result.append(("No.Of Tasks Assigned",users_objs_all_task_count[i].total_tasks))
                result.append(("No. of Annotated Tasks" ,users_objs_labeled_task_count[i].accepted_tasks))
                result.append(("Unlabeled Tasks",users_objs_unlabeled_task_count[i].unlabeled_task))
                result.append(("Skipped Tasks",users_objs_skipped_task_count[i].skipped_tasks))
                result.append(("Draft Tasks" , users_objs_draft_task_count[i].draft_tasks))
                if is_translation_project:
                    result.append(("Word Count Of Annotated Tasks" , user_word_count[i]))
                result.append(("Average Annotation Time (In Seconds)",round(time[i].lead_time ,2)))
                result1 = dict(result)
                final_result.append(result1)

            final_result = sorted(final_result, key=lambda x: x[sort_by_column_name],reverse=descending_order)
            return Response(data=final_result, status=status.HTTP_200_OK)

        else:

            result =[]
            for user in users:
                name = user.username
                email = user.get_username()
                list_of_user_languages = user.languages
                if tgt_language != None and tgt_language not in list_of_user_languages:
                    continue
            
                total_no_of_tasks_assigned = Task.objects.filter(annotation_users =user,\
                    project_id__project_type = project_type,project_id__tgt_language=tgt_language,project_id__organization_id = organization)
                total_no_of_tasks_count = total_no_of_tasks_assigned.count()

                annotated_tasks = Task.objects.filter(annotation_users =user,\
                    project_id__project_type = project_type,project_id__tgt_language=tgt_language,\
                    task_status__in = ['accepted','rejected','accepted_with_changes','labeled'])

                annotated_task_ids = list(annotated_tasks.values_list('id',flat = True))
                annotated_labeled_tasks =Annotation.objects.filter(task_id__in = annotated_task_ids ,parent_annotation_id = None,\
                    updated_at__range = [start_date, end_date])

                annotated_tasks_count = annotated_labeled_tasks.count()

                avg_lead_time = 0
                lead_time_annotated_tasks = [ eachtask.lead_time for eachtask in annotated_labeled_tasks]
                if len(lead_time_annotated_tasks) > 0 :
                    avg_lead_time = sum(lead_time_annotated_tasks) / len(lead_time_annotated_tasks)

                total_skipped_tasks = Task.objects.filter(annotation_users =user,\
                    project_id__project_type = project_type,project_id__tgt_language=tgt_language,\
                    task_status='skipped',project_id__organization_id = organization)
                total_skipped_tasks_count = total_skipped_tasks.count()
            
                total_unlabeled_tasks = Task.objects.filter(annotation_users =user,\
                    project_id__project_type = project_type,project_id__tgt_language=tgt_language,\
                    task_status='unlabeled',project_id__organization_id = organization)
                total_unlabeled_tasks_count = total_unlabeled_tasks.count()
            
                total_draft_tasks = Task.objects.filter(annotation_users =user,\
                    project_id__project_type = project_type,project_id__tgt_language=tgt_language,\
                    task_status='draft',project_id__organization_id = organization)
                total_draft_tasks_count = total_draft_tasks.count()
            
                projects_objs = Project.objects.filter(users = user,project_type = project_type,\
                    tgt_language = tgt_language,organization_id = organization)
                no_of_projects = projects_objs.count()

                no_of_workspaces_objs =len(set([ each_proj.workspace_id.id for each_proj in projects_objs]))

                if is_translation_project:
                    total_word_count_list = [no_of_words(each_task.task.data['input_text']) for  each_task in annotated_labeled_tasks]
                    total_word_count = sum(total_word_count_list)

                    result.append({ "Annotator": name,
                                    'Email' : email,
                                    'Language' : selected_language,
                                    'No. of Workspaces' : no_of_workspaces_objs,
                                    'No. of Projects' :no_of_projects,
                                    'Project Type' :project_type,
                                    'No.Of Tasks Assigned' : total_no_of_tasks_count,
                                    'No. of Annotated Tasks' : annotated_tasks_count,
                                    'Unlabeled Tasks' : total_unlabeled_tasks_count,
                                    'Skipped Tasks' : total_skipped_tasks_count,
                                    'Draft Tasks': total_draft_tasks_count,
                                    'Word Count Of Annotated Tasks' : total_word_count,
                                    'Average Annotation Time (In Seconds)' : round(avg_lead_time,2)
                            } )
                else :
                    result.append({ "Annotator": name,
                                    'Email' : email,
                                    'Language' : selected_language,
                                    'No. of Workspaces' : no_of_workspaces_objs,
                                    'No. of Projects' :no_of_projects,
                                    'Project Type' :project_type,
                                    'No.Of Tasks Assigned' : total_no_of_tasks_count,
                                    'No. of Annotated Tasks' : annotated_tasks_count,
                                    'Unlabeled Tasks' : total_unlabeled_tasks_count,
                                    'Skipped Tasks' : total_skipped_tasks_count,
                                    'Draft Tasks': total_draft_tasks_count,
                                    'Average Annotation Time (In Seconds)' : round(avg_lead_time,2)
                            } )
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
                labeled_count_tasks= Task.objects.filter(Q (project_id = proj.id) & Q(task_status__in = ['accepted','rejected','accepted_with_changes','labeled']))

                labeled_count_tasks_ids = list(labeled_count_tasks.values_list('id',flat = True))
                annotated_labeled_tasks =Annotation.objects.filter(task_id__in = labeled_count_tasks_ids ,parent_annotation_id = None,\
                updated_at__range = [start_date, end_date])

                labeled_count = annotated_labeled_tasks.count()


                skipped_count = Task.objects.filter(project_id = proj.id,task_status = 'skipped').count()
                dropped_tasks = Task.objects.filter(project_id = proj.id,task_status = 'draft').count()
                if total_tasks == 0:
                    project_progress = 0.0
                else :
                    project_progress = (labeled_count / total_tasks) * 100
                result = {
                    "Project Id" : project_id,
                    "Project Name" : project_name,
                    "Project Type" : project_type,
                    "Language" : selected_language,
                    "No.Of Annotators Assigned" : no_of_annotators_assigned,
                    "No.Of Tasks" : total_tasks,
                    "Annotated Tasks" : labeled_count,
                    "Unlabeled Tasks" : un_labeled_count,
                    "Skipped Tasks": skipped_count,
                    "Draft Tasks" : dropped_tasks,
                    "Project Progress" : round(project_progress,3)
                    }
                final_result.append(result)
        return Response(final_result)