from projects.serializers import ProjectSerializer
from projects.models import Project

"""
This function takes in the project id and the bools corresponding to which users associated with project have to be returned
The return type of the function is list and returns all the required user as mentioned in the parameters
The returned list does not contain any duplicates
"""


def get_userids_from_project_id(
    project_id,
    annotators_bool=False,
    reviewers_bool=False,
    super_checkers_bool=False,
    project_manager_bool=False,
    frozen_users_bool=False,
):
    try:
        project = Project.objects.get(pk=project_id)
        serializer = ProjectSerializer(project, many=False)
        ids = []
        if annotators_bool:
            annotators = serializer.data["annotators"]
            annotators_ids = [a.get("id") for a in annotators]
            ids += annotators_ids
        if reviewers_bool:
            reviewers = serializer.data["annotation_reviewers"]
            reviewers_ids = [r.get("id") for r in reviewers]
            ids += reviewers_ids
        if super_checkers_bool:
            super_checkers = serializer.data["review_supercheckers"]
            super_checkers_ids = [s.get("id") for s in super_checkers]
            ids += super_checkers_ids
        if project_manager_bool:
            project_workspace = project.workspace_id
            project_workspace_managers = project_workspace.managers.all()
            project_workspace_managers_ids = [p.id for p in project_workspace_managers]
            ids += project_workspace_managers_ids
        if frozen_users_bool:
            frozen_users = serializer.data["frozen_users"]
            frozen_users_ids = [s.get("id") for s in frozen_users]
            ids += frozen_users_ids

        return list(set(ids))
    except Project.DoesNotExist:
        print(f"Project with id {project_id} does not exist.")
        return []
    except Exception as e:
        print(f"Error while finding specific userids for - {project_id}")
        return []
