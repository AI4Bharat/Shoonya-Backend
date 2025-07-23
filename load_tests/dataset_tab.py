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
        
# done

# Intra Automate Dataset Creation
def create_intra_dataset_id(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"id",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
def create_intra_dataset_metadata_json(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"metadata_json",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
def create_intra_dataset_draft_data_json(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"draft_data_json",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
def create_intra_dataset_language(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"language",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
def create_intra_dataset_language(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"language",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
def create_intra_dataset_text(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"text",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
def create_intra_dataset_context(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"context",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
    
def create_intra_dataset_corrected_text(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"corrected_text",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
def create_intra_dataset_domain(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"domain",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging


def create_intra_dataset_quality_status(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"quality_status",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
                
def create_intra_dataset_parent_data(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"parent_data",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging


def create_intra_dataset_instance_id(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":77,
               "fields_list":"instance_id",
               "organization_id":1}     

    with self.client.post(
        "/functions/schedule_draft_data_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging

        
# populate Prediction ASR AI Model
def populate_prediction_asr_ai_model_true(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":166,"api_type":"dhruva_asr","organization_id":1,"automate_missing_data_items":"true"} 
    # check that the "true" will work with "" or Not 

    with self.client.post(
        "/functions/schedule_asr_prediction_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging
        
        
def populate_prediction_asr_ai_model_false(self):
    """
    Simulates a POST request to the /data/instances/ endpoint to create a new intra dataset instance.
    """
    payload = {"dataset_instance_id":166,"api_type":"dhruva_asr","organization_id":1,"automate_missing_data_items":"false"} 
    # check that the "false" will work with "" or Not 

    with self.client.post(
        "/functions/schedule_asr_prediction_json_population",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
        catch_response=True
    ) as response:
        if response.status_code == 200 or response.status_code == 201:
            response.success()
        else:
            response.failure(f" Intra Dataset creation failed: {response.status_code}")
        print(f"Response Intra Dataset creation: {response.json()}")  # Print the response for debugging 
