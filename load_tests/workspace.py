from datetime import datetime
# Get current date and time as a formatted string
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class WorkspaceAPIs:
    def __init__(self, client, token):
        self.client = client
        self.token = token
        
    def create_workspace(self, workspace_name):
        """
        Create a new workspace with the given name.
        """
        payload = {"organization":"1",
                   "workspace_name":f"test - {current_time}",
                   "is_archived":"false",
                   "public_analytics":"true"}
        with self.client.post(
                "/workspaces/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200 or response.status_code == 201:
                    response.success()
                else:
                    response.failure(f"Dataset creation failed: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
# get workspace projects
    def get_workspace_projects(self):
        """
        Get all projects in a workspace.
        """
        workspace_id = 1
        with self.client.get(
                f"/workspaces/{workspace_id}/projects",
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get projects: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging

#  get workspace Members
    def get_workspace_members(self):
        """
        Get all members in a workspace.
        """
        workspace_id = 1
        with self.client.get(
                f"/workspaces/{workspace_id}/members",
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get members: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging

# get workspace Managers
    def get_workspace_managers(self):
        """
        Get all managers in a workspace.
        """
        workspace_id = 1
        with self.client.get(
                f"/workspaces/{workspace_id}/list-managers/",
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get managers: {response.status_code}")
                print(f"Response: {response.json()}")
        
# Reprts

# for Annotaotr
    def get_report_annotaotr(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"annotation",
                  "send_mail":"false"}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
    def get_report_annotaotr_email(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"annotation",
                  "send_mail":"true"}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
    def get_report_annotaotr_annotaotr(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"annotation",
                  "send_mail":"false",
                  "project_progress_stage":1}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
    def get_report_annotaotr_annotaotr_email(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"annotation",
                  "project_progress_stage":1,
                  "send_mail":"true"}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
    def get_report_annotaotr_reviewer(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"annotation",
                  "send_mail":"false",
                  "project_progress_stage":2}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
    def get_report_annotaotr_reviewer_email(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"annotation",
                  "project_progress_stage":2,
                  "send_mail":"true"}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
    def get_report_annotaotr_superchecker(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"annotation",
                  "send_mail":"false",
                  "project_progress_stage":3}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
    def get_report_annotaotr_superchecker_email(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"annotation",
                  "project_progress_stage":3,
                  "send_mail":"true"}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                

# for Reviewer
    def get_report_reviewer_reviewer(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"review",
                  "send_mail":"false",
                  "project_progress_stage":2}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
    def get_report_reviewer_reviewer_email(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"review",
                  "send_mail":"true",
                  "project_progress_stage":2}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
    
    def get_report_reviewer_superchecker(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing","from_date":"2022-04-24","to_date":"2025-05-06","reports_type":"review","send_mail":"false","project_progress_stage":3}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")
                
    def get_report_reviewer_superchecker_email(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"review",
                  "send_mail":"true",
                  "project_progress_stage":3}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")
    
    def get_report_reviewer_allstage(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"review",
                  "send_mail":"false"}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
    def get_report_reviewer_allstage_email(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"review",
                  "send_mail":"false"}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
# for Superchecker
    def get_report_superchecker_allstage(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"supercheck",
                  "send_mail":"false"}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")
                
    def get_report_superchecker_allstage_email(self):
        """
        Get all reports in a workspace.
        """
        payload ={"project_type":"ContextualTranslationEditing",
                  "from_date":"2022-04-24",
                  "to_date":"2025-05-06",
                  "reports_type":"supercheck",
                  "send_mail":"true"}
        workspace_id = 1
        with self.client.post(
                f"/workspaces/{workspace_id}/user_analytics/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get reports: {response.status_code}")
                print(f"Response: {response.json()}")