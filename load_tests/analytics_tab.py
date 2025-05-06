class AnalyticsAPIs:
    def __init__(self, client, token):
        self.client = client
        self.token = token
    def get_Analytics_Meta(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        self.client.get(
            "/organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation",
            headers={"Authorization": f"JWT {self.token}"},
        )

# must be changed all project_type
        
# This is for the advanced analytics tab for Supercheck reports   
    def get_Andanced_Analytics_Monthly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        
        payload = {"end_date":"2025-05-02",
"periodical_type":"monthly",
"project_type":"ContextualTranslationEditing",
"start_date":"2025-05-01",
"supercheck_reports":"true",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
        
    def get_Andanced_Analytics_Yearly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        
        payload = {"end_date":"2025-05-02",
"periodical_type":"monthly",
"project_type":"ContextualTranslationEditing",
"start_date":"2025-05-01",
"supercheck_reports":"true",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_Andanced_Analytics_Weekly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        
        payload = {"end_date":"2025-05-02",
"periodical_type":"weekly",
"project_type":"ContextualTranslationEditing",
"start_date":"2025-05-01",
"supercheck_reports":"true",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_Andanced_Analytics_Weekly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        
        payload = {
"project_type":"ContextualTranslationEditing",
"supercheck_reports":"true",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
        
# This is for the advanced analytics tab for reviewer reports   
    def get_Andanced_Analytics_Monthly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        payload = {"end_date":"2025-05-02",
                   "periodical_type":"monthly",
                   "project_type":"ContextualTranslationEditing",
                   "start_date":"2025-05-01",
                   "reviewer_reports":"true",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
        
    def get_Andanced_Analytics_Yearly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        payload = {"end_date":"2025-05-02",
                   "periodical_type":"monthly",
                   "project_type":"ContextualTranslationEditing",
                   "start_date":"2025-05-01",
                   "reviewer_reports":"true",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_Andanced_Analytics_Weekly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        payload = {"end_date":"2025-05-02",
                   "periodical_type":"weekly",
                   "project_type":"ContextualTranslationEditing",
                   "start_date":"2025-05-01",
                   "reviewer_reports":"true",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_Andanced_Analytics_Weekly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        payload = {
"project_type":"ContextualTranslationEditing",
"reviewer_reports":"true",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
        
# This is for the advanced analytics tab for annotator reports   
    def get_Andanced_Analytics_Monthly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        payload = {"end_date":"2025-05-02",
"periodical_type":"monthly",
"project_type":"ContextualTranslationEditing",
"start_date":"2025-05-01",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
        
    def get_Andanced_Analytics_Yearly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        payload = {"end_date":"2025-05-02",
"periodical_type":"monthly",
"project_type":"ContextualTranslationEditing",
"start_date":"2025-05-01",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_Andanced_Analytics_Weekly(self):
        """
        Simulates a GET request to the /organizations/public/1/cumulative_tasks_count/?metainfo=true&project_type_filter=AudioSegmentation endpoint to fetch cumulative_tasks_count details.
        """
        payload = {"end_date":"2025-05-02",
"periodical_type":"weekly",
"project_type":"ContextualTranslationEditing",
"start_date":"2025-05-01",
        }
        self.client.get(
            "/organizations/1/periodical_tasks_count/?metainfo=true",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
   
   
# This is for the Performance analytics tab for annotator reports  
    def get_Andanced_Analytics_Daily(self):
        """
        Simulates a POST request to the /organizations/1/performance_analytics_data/ endpoint to fetch performance_analytics_data details.
        """
        payload = {"end_date":"2025-05-02",
"language":"Hindi",
"periodical_type":"daily",
"project_type":"ContextualTranslationEditing",# must be changed all project_type
"start_date":"2025-05-01",
        }
        self.client.post(
            "/organizations/1/performance_analytics_data/",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_Andanced_Analytics_Weekly(self):
        """
        Simulates a POST request to the /organizations/1/performance_analytics_data/ endpoint to fetch performance_analytics_data details.
        """
        payload = {"end_date":"2025-05-02",
"language":"Hindi",
"periodical_type":"weekly",
"project_type":"ContextualTranslationEditing", # must be changed
"start_date":"2025-05-01",
        }
        self.client.post(
            "/organizations/1/performance_analytics_data/",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_Andanced_Analytics_Monthly(self):
        """
        Simulates a POST request to the /organizations/1/performance_analytics_data/ endpoint to fetch performance_analytics_data details.
        """
        payload = {"end_date":"2025-05-02",
"language":"Hindi",
"periodical_type":"monthly",
"project_type":"ContextualTranslationEditing",
"start_date":"2025-05-01",
        }
        self.client.post(
            "/organizations/1/performance_analytics_data/",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
        
    def get_Andanced_Analytics_Monthly(self):
        """
        Simulates a POST request to the /organizations/1/performance_analytics_data/ endpoint to fetch performance_analytics_data details.
        """
        payload = {"end_date":"2025-05-02",
"language":"Hindi",
"periodical_type":"yearly",
"project_type":"ContextualTranslationEditing",
"start_date":"2025-05-01",
        }
        self.client.post(
            "/organizations/1/performance_analytics_data/",
            JSON=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        

#     
        
