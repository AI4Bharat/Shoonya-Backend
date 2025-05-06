from locust import HttpUser, task, between
from datetime import datetime
# Get current date and time as a formatted string
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
import traceback
from django.http import JsonResponse

class SequentialUser(HttpUser):
    wait_time = between(1, 2)  # optional wait between tasks
 
    @task
    def full_flow(self):
        # Step 1: Login
        login_payload = {
            "email": "shoonya@ai4bharat.org",
            "password": "password@admin"
        }
        login_headers = {'Content-Type': 'application/json'}

        with self.client.post("/users/auth/jwt/create", json=login_payload, headers=login_headers, catch_response=True) as response:
            if response.status_code == 200:
                access_token = response.json().get("access")
                if access_token:
                    auth_headers = {
                        "Authorization": f"JWT {access_token}",
                        "Content-Type": "application/json"
                    }
                    response.success()
                else:
                    response.failure("Login succeeded but token missing")
                    return
            else:
                response.failure(f"Login failed: {response.status_code}")
                return
            
            
            
        payload = {"organization":"1",
                   "workspace_name":f"test - {current_time}",
                   "is_archived":"false",
                   "public_analytics":"true"}
        with self.client.post(
                "/workspaces/",
                json=payload,
                headers=auth_headers,
                catch_response=True
            ) as response:
            if response.status_code == 201:
                return response.json()
            else:
                raise Exception(f"Failed to create workspace: {response.text}")
            
            
        # Id = 3803927
        # with self.client.get(
        #     f"/task/{Id}/annotations/",
        #     headers=auth_headers,
        #     catch_response=True
        # ) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Get task annotations failed: {response.status_code}")
        # print(f"Response annotations: {response.json()}")  # Print the response for debugging
        
        # Id = 3803927
        # with self.client.get(
        #     f"/task/{Id}/",
        #     headers=auth_headers,
        #     catch_response=True
        # ) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Get task annotations failed: {response.status_code}")
        # print(f"Response T: {response.json()}")  # Print the response for debugging
        
        # with self.client.get("/task/annotated_and_reviewed_tasks/get_users_recent_tasks/?page=1&records=10&user_id=1&task_type=supercheck",
        #     headers=auth_headers,
        #     catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Get user recent tasks failed: {response.status_code}")
        
        # with self.client.get("/task/annotated_and_reviewed_tasks/get_users_recent_tasks/?page=1&records=10&user_id=1&task_type=review",
        #     headers=auth_headers,
        #     catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Get user recent tasks failed: {response.status_code}")
                
        # with self.client.get("/task/annotated_and_reviewed_tasks/get_users_recent_tasks/?page=1&records=10&user_id=1&task_type=annotation",
        #     headers=auth_headers,
        #     catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Get user recent tasks failed: {response.status_code}")
                
                
        # payload = {"user_id":"1",
        #            "project_type":"ContextualTranslationEditing",
        #            "reports_type":"supercheck",
        #            "start_date":"2022-04-24",
        #            "end_date":"2025-05-05"}
        # with self.client.post("/users/user_analytics/",
        #                  json=payload,
        #     headers=auth_headers,
        #     catch_response=True) as response:
        #     if response.status_code == 200:
        #             response.success()
        #     else:
        #             response.failure(f"Get user recent tasks failed: {response.status_code}")
        # print(f"Response mY: {response.json()}")  # Print the response for debugging
       
       
        # # get_queued_Tasks
        # try:
        #     with self.client.get(
        #             "/tasks/get_celery_tasks",
        #             headers=auth_headers,
        #             catch_response=True
        #         ) as response:

        #         try:
        #             if response.status_code in (200, 201):
        #                 data = response.json()
        #                 response.success()
        #                 for task_id, task_info in data.items():
        #                     print(f"Task ID: {task_id}, Info: {task_info}")
        #             else:
        #                 response.failure(f"Request failed: {response.status_code}")
        #                 print(f"Non-JSON Response: {response.text}")
        #         except ValueError:
        #             response.failure("Response was not valid JSON")
        #             print(f"Invalid JSON Response: {response.text}")
        # except Exception as e:
        #     traceback.print_exc()
        #     return JsonResponse({'error': str(e)}, status=500)




            
            
        #     """
        # Simulates a GET request to fetch performance analytics data with query parameters.
        # """
        # params = {
        #     "end_date": "2025-05-02",
        #     "language": "Hindi",
        #     "periodical_type": "daily",
        #     "project_type": "ContextualTranslationEditing",
        #     "reviewer_reports": "true",
        #     "start_date": "2025-05-01",
        # }

        # with self.client.get(
        #     "/organizations/1/performance_analytics_data/",
        #     params=params,
        #     headers=auth_headers,
        #     catch_response=True
        # ) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Analytics fetch failed: {response.status_code}")

        #     print(f"Response: {response.json()}")

        # # Step 2: Call /projects/2563/
        # with self.client.get("/projects/2563/", headers=auth_headers, catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Project 2563 failed: {response.status_code}")
                
        #     print(f"Response: {response.json()}")
        
        
        #  # Step 3: Call /projects/2563/
        # with self.client.get("/workspaces/1", headers=auth_headers, catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Project 2563 failed: {response.status_code}")
                
        #     print(f"Response: {response.json()}")
        
        # # Step 4: Call /projects/
        # with self.client.get("/workspaces/", headers=auth_headers, catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Projects List failed: {response.status_code}")
                
        #     print(f"Response: {response.json()}")  # Print the response for debugging
            
            
            
        # # Step 5: Call /projects/2563/get_analytics/
        # analytics_payload = {
        #     "from_date": "2025-04-28",
        #     "to_date": "2025-04-29"
        # }

        # with self.client.post("/projects/2563/get_analytics/", json=analytics_payload, headers=auth_headers, catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Analytics failed: {response.status_code}")

        #     print(f"Response_analytics_payload: {response.text}")  # Changed to .text in case response is not JSON

        
        # # Step 6: Call /projects/2563/get_async_task_results/
        # """
        # Simulates GET requests to the /projects/2563/get_async_task_results/
        # endpoint for multiple task names.
        # """
    
        # with self.client.get( "/projects/2563/get_async_task_results/?task_name=projects.tasks.create_parameters_for_task_creation",
        #         headers=auth_headers, 
        #     ) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Get async task results failed: {response.status_code}")  
                
        # print(f"Response: {response.json()}")     
        
        
        # # Step 4: Call //workspaces/22 under Readonly
        # with self.client.get("/workspaces/22", headers=auth_headers, catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Projects List failed: {response.status_code}")
                
        #     print(f"Response: {response.json()}")  # Print the response for debugging
        
        # # Step 4: Call //data/instances/460/ under Readonly
        # with self.client.get("/data/instances/460/", headers=auth_headers, catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Projects List failed: {response.status_code}")
                
        #     print(f"Response: {response.json()}")  # Print the response for debugging
            
            
        # # Step 4: Call //data/instances/460/ under Readonly
        # with self.client.get("/data/instances/dataset_types/", headers=auth_headers, catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Projects List failed: {response.status_code}")
                
        #     print(f"Response: {response.json()}")  # Print the response for debugging
        
        # # Step 4: Call //data/instances/460/ under Readonly
        # with self.client.get("/data/instances/?", headers=auth_headers, catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Projects List failed: {response.status_code}")
                
        #     print(f"Response: {response.json()}")  # Print the response for debugging
    
    
        # """
        # Simulates a POST request to the /data/instances/ endpoint to create a new dataset instance.
        # """
        # payload = {
        #     "dataset_type": "SentenceText",
        #     "instance_description": f"Data2 - {current_time}",
        #     "instance_name": f"Data2 - {current_time}",
        #     "organisation_id": "1",
        #     "parent_instance_id": "1",
        #     "users": [1]
        # }
        
        # # payload={"instance_name":"Data2 - 2025-05-02 11:59:31",
        # #          "parent_instance_id":"1",
        # #          "instance_description":"Data2 - 2025-05-02 11:59:31",
        # #          "dataset_type":"SentenceText",
        # #          "organisation_id":"1",
        # #          "users":[1]}
            

        # with self.client.post(
        #     "/data/instances/",
        #     json=payload,
        #     headers=auth_headers,
        #     catch_response=True
        # ) as response:
        #     if response.status_code == 200 or response.status_code == 201:
        #         response.success()
        #     else:
        #         response.failure(f"Dataset creation failed: {response.status_code}")
        #     print(f"Response: {response.json()}")  # Print the response for debugging  
            
            
        # # # Step 5: Call /analytic/ for basic_pro_setting
        # with self.client.get("/organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation", headers=auth_headers, catch_response=True) as response:
        #     if response.status_code == 200:
        #         response.success()
        #     else:
        #         response.failure(f"Projects List failed: {response.status_code}")
                
        #     print(f"Response: {response.json()}")  # Print the response for debugging
            
            
#         payload = {"end_date":"2025-05-02",
# "language":"Hindi",
# "periodical_type":"daily",
# "project_type":"ContextualTranslationEditing",
# "reviewer_reports":"true",
# "start_date":"2025-05-01",
#         }
#         with self.client.get(
#             "/organizations/1/performance_analytics_data/",
#             json=payload,
#             headers=auth_headers,
#         ) as response:
#             if response.status_code == 200:
#                 response.success()
#             else:
#                 response.failure(f"Projects List failed: {response.status_code}")
                
#             print(f"Response: {response.json()}")
        