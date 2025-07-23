class user_profileAPI:
    def __init__(self, client, token):
        self.client = client
        self.token = token
    def get_user_profile(self):
        """ 
        Simulates a GET request to the /users/account/user_profile/ endpoint to fetch user profile details.
        """
        self.client.get("/users/account/1/fetch/",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_scheduled_mails(self):
        """
        Simulates a GET request to the /users/1/get_scheduled_mails/ endpoint to fetch user profile update details.
        """
        self.client.get("/users/1/get_scheduled_mails/",
            headers={"Authorization": f"JWT {self.token}"},
        )
    
    
# to Change the schedule of email 

    #  Changing the schedule and schedule_day values to test different scenarios
    def post_schedule_mail(self):
        """
        Simulates a POST request to the /users/1/schedule_mail/ endpoint to fetch user profile update details.
        """
        payload = {"id":1,
                   "report_level":1,
                   "project_type":"AllAudioProjects",
                   "schedule":"Monthly",
                   "schedule_day":2}
        self.client.post("/users/1/schedule_mail/",
                         json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    #  schedule , schedule_day , project_type are changable   
    def post_schedule_mail(self):
        """
        Simulates a POST request to the /users/1/schedule_mail/ endpoint to fetch user profile update details.
        """
        payload =  {"id":1,
                    "report_level":2,
                    "project_type":"AllAudioProjects",
                    "schedule":"Monthly",
                    "schedule_day":2}
        self.client.post("/users/1/schedule_mail/",
                         json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

# user_profile_update  
    def patch_user_profile_update(self):
        """
        Simulates a Patch request to the /users/account/update/ endpoint to fetch user profile update details.
        """
        payload = {"username":"shoonya",
                   "first_name":"Admin",
                   "last_name":"AI4B","languages":["English"],
                   "phone":"12568",
                   "availability_status":1,
                   "participation_type":4}
        self.client.patch("//users/account/update/",
                        json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

# My Progress Tab of profile
    def report_annotation(self):
        """
        Simulates a GET request to the /users/account/report/ endpoint to fetch user profile update details.
        """
        # payload ={page=1&records=10&user_id=1&task_type=annotation}
        self.client.get("/task/annotated_and_reviewed_tasks/get_users_recent_tasks/?page=1&records=10&user_id=1&task_type=annotation",
            headers={"Authorization": f"JWT {self.token}"},
        )
    def report_review(self):
        """
        Simulates a GET request to the /users/account/report/ endpoint to fetch user profile update details.
        """
        # payload ={page=1&records=10&user_id=1&task_type=review}
        self.client.get("/task/annotated_and_reviewed_tasks/get_users_recent_tasks/?page=1&records=10&user_id=1&task_type=review",
            headers={"Authorization": f"JWT {self.token}"},
        )
    def report_superchecker(self):
        """
        Simulates a GET request to the /users/account/report/ endpoint to fetch user profile update details.
        """
        # payload ={page=1&records=10&user_id=1&task_type=transcription}
        self.client.get("/task/annotated_and_reviewed_tasks/get_users_recent_tasks/?page=1&records=10&user_id=1&task_type=supercheck",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
# My Progress Box
    def my_progess_annotation(self):
        """
        Simulates a POST request to the /users/account/report/ endpoint to fetch user profile update details.
        """
        payload = {"user_id":"1",
                   "project_type":"ContextualTranslationEditing",
                   "reports_type":"annotation",
                   "start_date":"2022-04-24",
                   "end_date":"2025-05-05"}
        # payload ={page=1&records=10&user_id=1&task_type=annotation}
        self.client.post("/users/user_analytics/",
                         json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
    def my_progess_review(self):
        """
        Simulates a POST request to the /users/account/report/ endpoint to fetch user profile update details.
        """
        payload = {"user_id":"1",
                   "project_type":"ContextualTranslationEditing",
                   "reports_type":"review",
                   "start_date":"2022-04-24",
                   "end_date":"2025-05-05"}
        # payload ={page=1&records=10&user_id=1&task_type=annotation}
        self.client.post("/users/user_analytics/",
                         json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def my_progess_review(self):
        """
        Simulates a POST request to the /users/account/report/ endpoint to fetch user profile update details.
        """
        payload = {"user_id":"1",
                   "project_type":"ContextualTranslationEditing",
                   "reports_type":"supercheck",
                   "start_date":"2022-04-24",
                   "end_date":"2025-05-05"}
        # payload ={page=1&records=10&user_id=1&task_type=annotation}
        self.client.post("/users/user_analytics/",
                         json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
# /notifications/

    def get_notifications(self):
        """
        Simulates a GET request to the /notifications/ endpoint to fetch user profile update details.
        """
        self.client.get("/notifications/",
            headers={"Authorization": f"JWT {self.token}"},
        )
    def get_unseen_notifications(self):
        """
        Simulates a GET request to the /notifications/ endpoint to fetch user profile update details.
        """
        self.client.get("/notifications/?seen=False",
            headers={"Authorization": f"JWT {self.token}"},
        )


# done