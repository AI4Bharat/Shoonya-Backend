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

# change the workspace name
    def change_workspace_name(self):
        """
        Change the name of a workspace.
        """
        workspace_id = 1  # Replace with the actual workspace ID
        payload = {"workspace_name":"Tamil Workspace1",
                   "organization":1,
                   "is_archived":"false",
                   "public_analytics":"true"}
        with self.client.post(
                f"/workspaces/{workspace_id}/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to change workspace name: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
# download workspace projects
    def download_workspace_projects(self):
        """
        Download all projects in a workspace.
        """
        workspace_id = 1
        payload = {"user_id":1}
        with self.client.get(
                f"/functions/download_all_projects?workspace_id={workspace_id}",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to download projects: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging
                
                
                
                
# Members
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

# Add mambers
    def add_members(self):
        """
        Add members to a workspace.
        """
        payload = {"user_id":[313]}  # Replace with the actual user ID of the member to add
        workspace_id = 1  # Replace with the actual workspace ID
        with self.client.post(
                f"/workspaces/{workspace_id}/addmembers/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to add members: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging

# view a specific member
    def view_member(self):
        """
        View a specific member in a workspace.
        """
        member_id = 1  # Replace with the actual member ID you want to view
        with self.client.get(
                f"/users/account/{member_id}/fetch/",
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to view member: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging

# invite members
    def invite_members(self):
        """
        Invite members to a workspace.
        """
        payload = {"organization_id":1,
                   "emails":["munishmangla98@gmail.com"], # Replace with the actual email of the member to invite which is not registered 
                   "role":"1"} # Replace with the actual user ID of the member to invite
        with self.client.post(
                f"/users/invite/generate/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to invite members: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging

# remove members
    def remove_members(self):
        """
        Remove members from a workspace.
        """
        payload = {"user_id":[313]}  # Replace with the actual user ID of the member to remove
        workspace_id = 1  # Replace with the actual workspace ID
        with self.client.post(
                f"/workspaces/{workspace_id}/removemembers/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to remove members: {response.status_code}")
                print(f"Response: {response.json()}")  # Print the response for debugging

# Managers
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
                
# view manager
    def view_manager(self):
        """
        View a specific manager in a workspace.
        """
        manager_id = 1  # Replace with the actual manager ID you want to view
        with self.client.get(
                f"/users/account/{manager_id}/fetch/",
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to view manager: {response.status_code}")
                print(f"Response: {response.json()}")
                
# assign managaer
    def assign_manager(self):
        """
        Assign a manager to a workspace.
        """
        payload = {"ids":[313]} # Replace with the actual Member ID
        workspace_id = 1  # Replace with the actual workspace ID
        with self.client.post(
                f"/workspaces/{workspace_id}/assign_manager/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to assign manager: {response.status_code}")
                print(f"Response: {response.json()}")

# unassign manager
    def unassign_manager(self):
        """
        Unassign a manager from a workspace.
        """
        payload = {"ids":[313]}  # Replace with the actual user ID of the manager to unassign
        workspace_id = 1  # Replace with the actual workspace ID
        with self.client.post(
                f"/workspaces/{workspace_id}/unassign-manager/",
                json=payload,
                headers={'Authorization': f'JWT {self.token}'},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to unassign manager: {response.status_code}")
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
                
# For Detailed Project Report
    def get_complete_statistics_detailed_project(self):
        """
        Simulates a GET request to the /functions/schedule_project_reports_email endpoint to fetch report project email complete_statistics
        """
        payload={"organization_id":1,
                 "user_id":1,
                 "project_type":"ContextualTranslationEditing",
                 "complete_statistics":"true"}
        self.client.get(
            "/functions/schedule_project_reports_email",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

    def get_meta_info_statistics_detailed_project(self):
        """
        Simulates a GET request to the /functions/schedule_project_reports_email endpoint to fetch report project email meta_info_statistics
        """
        payload={"organization_id":1,
                 "user_id":1,
                 "project_type":"ContextualTranslationEditing",
                 "meta-info_statistics":"true",
                 "send_mail":"true"}
        self.client.get(
            "/functions/schedule_project_reports_email",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

    def get_annotation_statistics_detailed_project(self):
        """
        Simulates a GET request to the /functions/schedule_project_reports_email endpoint to fetch report project email annotation_statistics
        """
        payload={"organization_id":1,
                 "user_id":1,
                 "project_type":"ContextualTranslationEditing",
                 "annotation_statistics":"true"}
        self.client.get(
            "/functions/schedule_project_reports_email",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

# for Payment Report
    def get_payment_report_full_time(self):
        """
        Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment
        """

        payload={"project_type":"AllAudioProjects",
                 "participation_types":[1],
                 "user_id":1,
                 "from_date":"2025-04-26",
                 "to_date":"2025-05-02"}

        self.client.get(
            "/organizations/1/send_user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

    def get_payment_report_part_time(self):
        """
        Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
        """

        payload={"project_type":"AllAudioProjects",
                 "participation_types":[2],
                 "user_id":1,
                 "from_date":"2025-04-26",
                "to_date":"2025-05-02"}

        self.client.get(
            "/organizations/1/send_user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

    def get_payment_report_contract_basis(self):
        """
        Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
        """

        payload={"project_type":"AllAudioProjects",
                 "participation_types":[4],
                 "user_id":1,
                 "from_date":"2025-04-26",
                 "to_date":"2025-05-02"}

        self.client.get(
            "/organizations/1/send_user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

    def get_payment_report_part_time_full_time_contract_basis(self):
        """
        Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
        """

        payload={"project_type":"AllAudioProjects",
                 "participation_types":[4, 2, 1],
                 "user_id":1,
                 "from_date":"2025-04-26",
                 "to_date":"2025-05-02"}

        self.client.get(
            "/organizations/1/send_user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )   

    def get_payment_report_part_time_full_time(self):
        """
        Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
        """

        payload={"project_type":"AllAudioProjects",
                 "participation_types":[1,3],
                 "user_id":1,
                 "from_date":"2025-04-26",
                 "to_date":"2025-05-02",
                 }

        self.client.get(
            "/organizations/1/send_user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

    def get_payment_report_full_time_part_time(self):
        """
        Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
        """

        payload={"project_type":"AllAudioProjects",
                 "participation_types":[2,1],
                 "user_id":1,
                 "from_date":"2025-04-26",
                 "to_date":"2025-05-02",
                 }

        self.client.get(
            "/organizations/1/send_user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

    def get_payment_report_full_time_contract_basis(self):
        """
        Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
        """    
        payload={"project_type":"AllAudioProjects",
                    "participation_types":[1,4],
                    "user_id":1,
                    "from_date":"2025-04-26",
                    "to_date":"2025-05-02",
                    }

        self.client.get(
                "/organizations/1/send_user_analytics/",
                json=payload,
                headers={"Authorization": f"JWT {self.token}"},
            )

    def get_payment_report_part_time_contract_basis(self):
        """
        Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
        """    
        payload={"project_type":"AllAudioProjects",
                    "participation_types":[2,4],
                    "user_id":1,
                    "from_date":"2025-04-26",
                    "to_date":"2025-05-02",
                    }

        self.client.get(
                "/organizations/1/send_user_analytics/",
                json=payload,
                headers={"Authorization": f"JWT {self.token}"},
            )
        
# analytics 
    def get_analytics(self):
        """
        Simulates a GET request to the /organizations/1/analytics/ endpoint to fetch analytics details.
        """
        payload = {"project_type_filter":"ContextualTranslationEditing",}
        self.client.get(
            "/workspaces/1/cumulative_tasks_count_all/?project_type_filter=ContextualTranslationEditing",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
    def get_meta_info(self):
        """
        Simulates a GET request to the /organizations/1/analytics/ endpoint to fetch analytics details.
        """
        payload = {"project_type_filter":"ContextualTranslationEditing",}
        self.client.get(
            "/workspaces/1/cumulative_tasks_count_all/?metainfo=true&project_type_filter=ContextualTranslationEditing",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
# performantion
    def get_performance_daily(self):
        """
        Simulates a POST request to the /organizations/1/analytics/ endpoint to fetch analytics details.
        """
        payload = {"project_type":"ContextualTranslationEditing",
                   "periodical_type":"daily",
                   "language":"Hindi",
                   "start_date":"2025-05-06",
                   "end_date":"2025-05-07"}
        self.client.posr(
            "/workspaces/1/performance_analytics_data/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
    def get_performance_weekly(self):
        """
        Simulates a POST request to the /organizations/1/analytics/ endpoint to fetch analytics details.
        """
        payload = {"project_type":"ContextualTranslationEditing",
                   "periodical_type":"weekly",
                   "language":"Hindi",
                   "start_date":"2025-05-06",
                   "end_date":"2025-05-07"}
        self.client.post(
            "/workspaces/1/performance_analytics_data/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
    
    def get_performance_monthly(self):
        """
        Simulates a POST request to the /organizations/1/analytics/ endpoint to fetch analytics details.
        """
        payload = {"project_type":"ContextualTranslationEditing",
                   "periodical_type":"monthly",
                   "language":"Hindi",
                   "start_date":"2025-05-06",
                   "end_date":"2025-05-07"}
        self.client.post(
            "/workspaces/1/performance_analytics_data/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
    
    def get_performance_yearly(self):
        """
        Simulates a POST request to the /organizations/1/analytics/ endpoint to fetch analytics details.
        """
        payload = {"project_type":"ContextualTranslationEditing",
                   "periodical_type":"yearly",
                   "language":"Hindi",
                   "start_date":"2025-05-06",
                   "end_date":"2025-05-07"}
        self.client.post(
            "/workspaces/1/performance_analytics_data/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
