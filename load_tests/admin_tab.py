class AdminAPIs:
    def __init__(self, client, token):
        self.client = client
        self.token = token
    def get_User_details(self):
        """
        Simulates a GET request to the /users/account/user_details/ endpoint to fetch get_User_details.
        """
        self.client.get(
            "/users/account/user_details/",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
        
# below one iss not working as some json responce 500 error is coming
    def get_queued_Tasks(self):
        """
        Simulates a GET request to the /tasks/get_celery_tasks/ endpoint to fetch get_queued_Tasks details.
        """
        self.client.get(
            "/tasks/get_celery_tasks/",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
# get Tasks details

    def get_tasks_annotations(self):
        """
        Simulates a GET request to the /task/3803927/annotations/ endpoint to fetch get_tasks details.
        """
        Id = 3803927
        self.client.get(
            f"/task/{Id}/annotations/",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_task_details(self):
        """
        Simulates a GET request to the /task/3803927/ endpoint to fetch get_task_details.
        """
        Id = 3803927
        with self.client.get(
        f"/task/{Id}/",
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
        ) as response:
            print(f"Status Code: {response.status_code}")

            if response.status_code in (200, 201):
                response.success()
            else:
                response.failure(f"Failed to get task details: {response.status_code}")
                
# get task annotations details:
    def get_task_annotations(self):
        """
        Simulates a GET request to the annotation/{Id} endpoint to fetch get_task_annotations details.
        """
        Id = 2874181
        with self.client.get(
            f"/annotation/{Id}/",
            headers={"Authorization": f"JWT {self.token}"},
            catch_response=True
        ) as response:
            print(f"Status Code: {response.status_code}")

            if response.status_code in (200, 201):
                response.success()
            else:
                response.failure(f"Failed to get task annotations: {response.status_code}")
