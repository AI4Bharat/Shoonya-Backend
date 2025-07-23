from locust import HttpUser, task, between

class SupercheckerUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        # Login as superchecker
        login_payload = {
            "email": "superchecker@example.com",
            "password": "superchecker123"
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
                response.failure("Superchecker login failed")

    @task
    def superchecker_flow(self):
        # Step 1: Get all projects
        with self.client.get("/projects/projects_list/optimized/", headers=self.auth_headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                project_id = 2504  # Hardcoded; can be extracted dynamically
            else:
                response.failure("Failed to fetch project list")
                return

        # Step 2: Get tasks for annotation_status=unlabeled
        task_url = f"/task/?project_id={project_id}&page=1&records=10&annotation_status=[%22unlabeled%22]"
        self.client.get(task_url, headers=self.auth_headers)

        # Step 3: Get analytics
        analytics_payload = {
            "from_date": "2024-09-10",
            "to_date": "2025-07-11"
        }
        self.client.post(
            f"/projects/{project_id}/get_analytics/",
            json=analytics_payload,
            headers=self.auth_headers
        )

    
    @task
    def superchecker_stage_checks(self):
        project_id = 1645
        supercheck_statuses = [
            "validated_with_changes",
            "validated",
            "unvalidated",
            "draft",
            "skipped"
        ]
    
        pages = [1, 2]  # Add more pages if needed
        records_options = [10, 25, 50, 100]
    
        for status in supercheck_statuses:
            for page_num in pages:
                for records in records_options:
                    params = {
                        "project_id": project_id,
                        "page": page_num,
                        "records": records,
                        "supercheck_status": f'["{status}"]'
                    }
    
                    with self.client.get("/task/", params=params, headers=self.auth_headers, catch_response=True) as res:
                        label = f"{status} | page={page_num} | records={records}"
                        if res.status_code == 200:
                            res.success()
                            print(f"[✓] Superchecker: {label} → {len(res.json().get('results', []))} tasks")
                        else:
                            res.failure(f"[✗] Superchecker: {label} → Error {res.status_code}")
    