from locustfile import auth_headers, current_time
from datetime import datetime
# Get current date and time as a formatted string
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class OrganisationAPIs:
    def __init__(self, client, token):
        self.client = client
        self.token = token
    def get_dataset_instances(self):
        """
        Simulates a GET request to the /data/instances/? endpoint to fetch /data/instances/? details.
        """
        with self.client.get("/data/instances/?", headers={"Authorization": f"JWT {self.token}"}, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Projects List failed: {response.status_code}")
                
            print(f"Response: {response.json()}")  # Print the response for debugging
            
            
    def get_dataset_instances(self):
        """
        Simulates a GET request to the /data/instances/dataset_types/ endpoint to fetch /data/instances/dataset_types/ details.
        """
        with self.client.get("/data/instances/dataset_types/", headers={"Authorization": f"JWT {self.token}"}, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Projects List failed: {response.status_code}")
                
            print(f"Response: {response.json()}")  # Print the response for debugging
        
    def create_New_dataset(self):
        """
        Simulates a POST request to the /data/instances/ endpoint to create a new dataset instance.
        """
        payload = {
            "dataset_type": "SentenceText",
            "instance_description": f"Data2 - {current_time}",
            "instance_name": f"Data2 - {current_time}",
            "organisation_id": "1",
            "parent_instance_id": "1",
            "users": [1]
        }       

        with self.client.post(
            "/data/instances/",
            json=payload,
            headers= {"Authorization": f"JWT {self.token}"},
            catch_response=True
        ) as response:
            if response.status_code == 200 or response.status_code == 201:
                response.success()
            else:
                response.failure(f"Dataset creation failed: {response.status_code}")
            print(f"Response: {response.json()}")  # Print the response for debugging     
    
#  Automate Dataset Creation

# Inter Automate Dataset Creation
def create_inter_dataset(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new inter dataset instance.
    """
    payload = {"input_dataset_instance_id":49,
               "languages":"[\"Bengali\"]",
               "output_dataset_instance_id":48,
               "organization_id":1,
               "checks_for_particular_languages":"True",
               "api_type":"indic-trans",
               "automate_missing_data_items":"true"}     

    with self.client.post(
        "/functions/automated_sentence_text_translation_job",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Inter Dataset creation failed: {response.status_code}")
        print(f"Response Inter Dataset creation: {response.json()}")  # Print the response for debugging