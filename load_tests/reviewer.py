from locust import HttpUser, task, between

class ReviewerUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        # Login as reviewer
        login_payload = {
            "email": "reviewer@example.com",
            "password": "reviewer123"
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
                response.failure("Reviewer login failed")

    @task
    def reviewer_flow(self):
        # Step 1: Get all projects
        with self.client.get("/projects/projects_list/optimized/", headers=self.auth_headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # You can dynamically parse projects here
                project_id = 2506  # Example static project ID
            else:
                response.failure("Project list failed")
                return

        # Step 2: Get unreviewed tasks
        task_url = f"/task/?project_id={project_id}&page=1&records=10&review_status=[%22unreviewed%22]"
        self.client.get(task_url, headers=self.auth_headers)

        # Step 4: Get analytics with review_reports
        analytics_payload = {
            "from_date": "2024-11-07",
            "to_date": "2025-07-11",
            "reports_type": "review_reports"
        }
        self.client.post(
            f"/projects/{project_id}/get_analytics/",
            json=analytics_payload,
            headers=self.auth_headers
        )

    @task
    def annotation_stage_checks(self):
        project_id = 2486
        annotation_statuses = [
            "skipped",
            "draft",
            "labeled",
            "to_be_revised",
            "unlabeled",
            "accepted_with_major_changes"
        ]

        combinations = [
            {"editable": True, "rejected": True},
            {"editable": True, "rejected": False},
            {"editable": False, "rejected": True},
            {"editable": False, "rejected": False},
            {"editable": None, "rejected": True},   # no editable param
            {"editable": None, "rejected": None},   # base request
        ]

        pages = [1, 2]  # You can extend this if needed
        records_options = [10, 25, 50, 100]

        for status in annotation_statuses:
            for combo in combinations:
                for page_num in pages:
                    for records in records_options:
                        params = {
                            "project_id": project_id,
                            "page": page_num,
                            "records": records,
                            "annotation_status": f'["{status}"]'
                        }

                        if combo["editable"] is not None:
                            params["editable"] = str(combo["editable"]).lower()
                        if combo["rejected"] is not None:
                            params["rejected"] = str(combo["rejected"]).lower()

                        with self.client.get("/task/", params=params, headers=self.auth_headers, catch_response=True) as res:
                            label = (
                                f"{status} | page={page_num} | records={records} | "
                                f"editable={combo['editable']} | rejected={combo['rejected']}"
                            )
                            if res.status_code == 200:
                                res.success()
                                print(f"[✓] {label} → {len(res.json().get('results', []))} tasks")
                            else:
                                res.failure(f"[✗] {label} → Error {res.status_code}")


# https://backend.shoonya.ai4bharat.org/projects/144/
# https://backend.shoonya.ai4bharat.org/task/258556/
# https://backend.shoonya.ai4bharat.org/projects/144/next/
# 