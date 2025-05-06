class project:
    def __init__(self, client, token):
        self.client = client
        self.token = token
        
        
    def get_pro(self):
        """
        Simulates a GET request to the /workspaces/ endpoint to fetch workspace details.
        """
        self.client.get(
            "/projects/projects_list/optimized/?",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_view_pro(self):
        """
        Simulates a GET request to the /organizations/1/users/ endpoint to fetch members
        """
        self.client.get(
            "/projects/2563/", headers={"Authorization": f"JWT {self.token}"}
        )
        
    def get_unlabeled_task(self):
        """/task/?project_id=2563&page=1&records=10&annotation_status=[%22unlabeled%22] endpoint to fetch unlabeled
        """
        self.client.get(
            "/task/?project_id=2563&page=1&records=10&annotation_status=[%22unlabeled%22]", headers={"Authorization": f"JWT {self.token}"}
        )    
    
    def get_unreviewed_task(self):
        """/task/?project_id=2563&page=1&records=10&review_status=[%22unreviewed%22] endpoint to fetch unreviewed
        """
        self.client.get(
            "/task/?project_id=2563&page=1&records=10&review_status=[%22unreviewed%22]", headers={"Authorization": f"JWT {self.token}"}
        )
        
        
    def add_annotator(self):
        """/projects/2563/add_project_annotator endpoint to add_annotator
        """
        payload = {"ids":"[110]"}
        self.client.post(
            "/projects/2563/add_project_annotator", 
            json=payload,
            headers={"Authorization": f"JWT {self.token}"}
        )
    def add_reviewer(self):
        """/projects/2563/add_project_annotator endpoint to add_reviewer
        """
        payload = {"ids":"[1]"}
        self.client.post(
            "/projects/2563/add_project_reviewers/", 
            json=payload,
             headers={"Authorization": f"JWT {self.token}"}
        )

    def get_all_task(self):
        """
        Simulates a get request to the /task/?project_id=2563&page=1&records=10&task_status=[%22incomplete%22] endpoint to fetch all_task
        """
        self.client.get(
            "/task/?project_id=2563&page=1&records=10&task_status=[%22incomplete%22]",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def post_get_analytics(self):
        """
        Simulates a POST request to the /projects/2563/get_analytics/ endpoint
        with required JSON payload.
        """
        payload = {
            "from_date": "2025-04-28",
            "to_date": "2025-04-29"
        }

        self.client.post(
            "/projects/2563/get_analytics/",
            json=payload,
            headers={
                "Authorization": f"JWT {self.token}", 
                "Content-Type": "application/json"
            },
        )

        
        
    def get_report(self):
        """
        Simulates a POST request to the /projects/2563/get_analytics/ endpoint
        with required JSON payload.
        """
        payload = {
            "from_date": "2025-04-28",
            "to_date": "2025-04-29"
        }

        self.client.post(
            "/projects/2563/get_analytics/",
            json=payload,
            headers={
                "Authorization": f"JWT {self.token}", 
                "Content-Type": "application/json"
            },
        )
     
     
     
    # From here Setting Tabs Start :-->   
    
    # Advanced Settings Tab
    def post_project_publish(self):
        """
        Simulates a GET request to the /projects/2563/project_publish/ endpoint to update project_publish
        """
        self.client.post(
            "/projects/2563/project_publish/",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def project_export(self):
        """
        Simulates a POST request to the /projects/2563/project_export/ endpoint to update project_export
        """
        self.client.post(
            "/projects/2563/project_export/",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def pull_new_items(self):
        """
        Simulates a POST request to the /projects/2563/pull_new_items/ endpoint to update pull_new_items
        """
        self.client.post(
            "/projects/2563/pull_new_items/",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def download_export_type_CSV(self):
        """
        Simulates a GET request to the /projects/2563/download_export_type_CSV/ endpoint to update download_export_type_CSV
        """
        self.client.post(
            "/projects/2563/download/?export_type=CSV&task_status=incomplete,annotated,reviewed,super_checked,exported",
            headers={"Authorization": f"JWT {self.token}"},
        )   
        
    def download_export_type_TSV(self):
        """
        Simulates a GET request to the /projects/2563/download_export_type_TSV/ endpoint to update download_export_type_TSV
        """
        self.client.post(
            "/projects/2563/download/?export_type=TSV&task_status=incomplete,annotated,reviewed,super_checked,exported",
            headers={"Authorization": f"JWT {self.token}"},
        )   
     
     
    def download_export_type_JSON(self):
        """
        Simulates a GET request to the /projects/2563/download_export_type_TSV/ endpoint to update download_export_type_JSON
        """
        self.client.post(
            "/projects/2563/download/?export_type=JSON&task_status=incomplete,annotated,reviewed,super_checked,exported",
            headers={"Authorization": f"JWT {self.token}"},
        )   
     
    def change_pro_stage_1(self):
        """
        Simulates a GET request to the /projects/2563/change_project_stage/ endpoint to update change_pro_stage
        """
        payload = {"project_stage": "1"
        }
        self.client.get(
            "/projects/2563/change_project_stage/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        ) 
        
    def change_pro_stage_2(self):
        """
        Simulates a GET request to the /projects/2563/change_project_stage/ endpoint to update change_pro_stage
        """
        payload = {"project_stage": "2"
        }
        self.client.get(
            "/projects/2563/change_project_stage/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        ) 
        
        
    def change_pro_stage_3(self):
        """
        Simulates a GET request to the /projects/2563/change_project_stage/ endpoint to update change_pro_stage
        """
        payload = {"project_stage": "3"
        }
        self.client.get(
            "/projects/2563/change_project_stage/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        ) 
        
    def change_Supercheck_set(self):
        """
        Simulates a PATCH request to the /projects/2563/
        """
        payload = {"k_value": "100",
                "revision_loop_count": "3"
        }
        self.client.patch(
        "/projects/2563/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )     
        
        
     
    # Log Tab   
    def get_logs(self):
        """
        Simulates GET requests to the /projects/2563/get_async_task_results/
        endpoint for multiple task names.
        """        
        self.client.get("/projects/2563/get_async_task_results/?task_name=projects.tasks.create_parameters_for_task_creation",
                headers={
                    "Authorization": f"JWT {self.token}",
                    "Content-Type": "application/json"
                }
        )
        
        
    # Readonly Tab 
    def get_Setting_Readonly(self):
            """
            Simulates GET requests to the /workspaces/{Id}
            endpoint for multiple task names.
            """        
            self.client.get("/workspaces/22",
                    headers={
                        "Authorization": f"JWT {self.token}",
                        "Content-Type": "application/json"
                    }
            ) 
    # Readonly Tab        
    def get_Setting_Readonly_dataset(self):
            """
            Simulates GET requests to the /data/instances/{Id}/
            endpoint for multiple task names.
            """        
            self.client.get("/data/instances/460/",
                    headers={
                        "Authorization": f"JWT {self.token}",
                        "Content-Type": "application/json"
                    }
            )    
            
            
    # Basic Tab
    def basic_pro_set(self):
        """
        Simulates a put request to the /projects/2563/ for basic_pro_setting
        """
        payload = { "description":"-",
                    "max_pending_tasks_per_user":"60",
                    "tasks_pull_count_per_batch":"10",
                    "tgt_language":"Malayalam",
                    "title":"testing audio yt_transcription" }
        self.client.put(
        "/projects/2563/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )    
        
# doen