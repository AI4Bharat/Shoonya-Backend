# from locust import HttpUser, task, between
# import json

# class ShoonyaUser(HttpUser):
#     wait_time = between(1, 2)

#     def on_start(self):
#         login_payload = {
#             "email": "shoonya@ai4bharat.org",
#             "password": "password@admin"
#         }
#         headers = {"Content-Type": "application/json"}

#         with self.client.post("/users/auth/jwt/create", json=login_payload, headers=headers, catch_response=True) as response:
#             if response.status_code == 200:
#                 self.token = response.json().get("access")
#                 self.auth_headers = {
#                     "Authorization": f"Bearer {self.token}",
#                     "Content-Type": "application/json"
#                 }
#                 response.success()
#             else:
#                 response.failure("Login failed")

#     @task
#     def full_user_flow(self):
#         # Step 1: Get all projects
#         with self.client.get("/projects/projects_list/optimized/", headers=self.auth_headers, catch_response=True) as response:
#             if response.status_code == 200:
#                 response.success()
#                 projects = response.json()
#                 project_id = 4267  # Or dynamically pick from projects
#             else:
#                 response.failure("Failed to fetch projects")
#                 return

#         # Step 2: Get specific project info
#         self.client.get(f"/projects/{project_id}/", headers=self.auth_headers)

#         # Step 3: Get task list for project
#         task_url = f"/task/?project_id={project_id}&page=1&records=10&annotation_status=[%22unlabeled%22]"
#         self.client.get(task_url, headers=self.auth_headers)

#         # Step 4: Get workspace members
#         workspace_id = 69  # Static or dynamic
#         self.client.get(f"/workspaces/{workspace_id}/members/", headers=self.auth_headers)

#         # Step 5: Get project analytics
#         analytics_payload = {
#             "from_date": "2024-07-01",
#             "to_date": "2025-07-10"
#         }
#         self.client.post(f"/projects/{project_id}/get_analytics/", json=analytics_payload, headers=self.auth_headers)
        
#         # check the right no. of tasks are pulled or not 
#         self.client.get(f"/projects/{project_id}/get_num_tasks/", headers=self.auth_headers)
        
#         pull_tasks_payload = {
#             "num_tasks": 10,
#         }
#         self.client.post(f"/projects/{project_id}/assign_new_tasks/", json=pull_tasks_payload, headers=self.auth_headers)
        
        


from locust import HttpUser, task, between
import time

class ShoonyaUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        login_payload = {
            "email": "shoonya@ai4bharat.org",
            "password": "password@admin"
        }
        headers = {"Content-Type": "application/json"}

        with self.client.post("/users/auth/jwt/create", json=login_payload, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                self.token = response.json().get("access")
                self.auth_headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
                response.success()
            else:
                response.failure("Login failed")

    @task
    def full_user_flow(self):
        project_id = 4267
        workspace_id = 69
        pull_count = 10

        # Step 1: Get all projects
        with self.client.get("/projects/projects_list/optimized/", headers=self.auth_headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Failed to fetch projects")
                return

        # Step 2: Get specific project info
        self.client.get(f"/projects/{project_id}/", headers=self.auth_headers)

        # Step 3: Get task list (unlabeled tasks)
        task_url = f"/task/?project_id={project_id}&page=1&records=100&annotation_status=[%22unlabeled%22]"
        with self.client.get(task_url, headers=self.auth_headers, catch_response=True) as task_res:
            if task_res.status_code == 200:
                task_data = task_res.json()
                initial_count = task_data.get("count", 0)
                task_res.success()
            else:
                task_res.failure("Failed to fetch initial task list")
                return

        # Step 4: Get workspace members
        self.client.get(f"/workspaces/{workspace_id}/members/", headers=self.auth_headers)

        # Step 5: Get project analytics
        analytics_payload = {
            "from_date": "2024-07-01",
            "to_date": "2025-07-10"
        }
        self.client.post(f"/projects/{project_id}/get_analytics/", json=analytics_payload, headers=self.auth_headers)

        # Step 6: Pull new tasks
        pull_payload = {"num_tasks": pull_count}
        with self.client.post(f"/projects/{project_id}/assign_new_tasks/", json=pull_payload, headers=self.auth_headers, catch_response=True) as pull_res:
            if pull_res.status_code == 200:
                pull_res.success()
            else:
                pull_res.failure("Failed to assign new tasks")
                return

        # Optional delay to allow backend to update
        time.sleep(2)

        # Step 7: Check new task count
        with self.client.get(task_url, headers=self.auth_headers, catch_response=True) as final_res:
            if final_res.status_code == 200:
                new_count = final_res.json().get("count", 0)
                added = new_count - initial_count
                # Step 3: initial_count from Get task list (unlabeled tasks)
                if added == pull_count:
                    final_res.success()
                    print(f"✅ Successfully pulled {added} new tasks.")
                else:
                    final_res.failure(f"❌ Expected {pull_count} new tasks, got {added}.")
            else:
                final_res.failure("Failed to fetch updated task list")
        
        
        #  Step 8: Check tasks with different editable statuses 
        project_id = 2504
        stages = ["skipped", "draft", "labeled", "to_be_revised", "unlabeled"]

        for stage in stages:
            # Encode status properly
            encoded_status = f"%22{stage}%22"

            # editable=true
            url_true = f"/task/?project_id={project_id}&page=1&records=10&annotation_status=[{encoded_status}]&editable=true"
            with self.client.get(url_true, headers=self.auth_headers, catch_response=True) as res:
                if res.status_code == 200:
                    res.success()
                    print(f"[✓] {stage} + editable=true → {len(res.json().get('results', []))} tasks")
                else:
                    res.failure(f"❌ Failed for stage {stage} editable=true")

            # editable=false
            url_false = f"/task/?project_id={project_id}&page=1&records=10&annotation_status=[{encoded_status}]&editable=false"
            with self.client.get(url_false, headers=self.auth_headers, catch_response=True) as res:
                if res.status_code == 200:
                    res.success()
                    print(f"[✓] {stage} + editable=false → {len(res.json().get('results', []))} tasks")
                else:
                    res.failure(f"❌ Failed for stage {stage} editable=false")
