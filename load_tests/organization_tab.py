class OrganisationAPIs:
    def __init__(self, client, token):
        self.client = client
        self.token = token
        
    def get_workspace(self):
        """
        Simulates a GET request to the /workspaces/ endpoint to fetch workspace details.
        """
        self.client.get(
            "/workspaces",
            headers={"Authorization": f"JWT {self.token}"},
        )
        
    def get_members(self):
        """
        Simulates a GET request to the /organizations/1/users/ endpoint to fetch members
        """
        self.client.get(
            "/organizations/1/users/", headers={"Authorization": f"JWT {self.token}"}
        )
        
        
    def get_invites(self):
        """
        Simulates a GET request to the /users/invite/pending_users/?organisation_id=1 endpoint to fetch invites
        """
        self.client.get(
            "/users/invite/pending_users/?organisation_id=1",
            headers={"Authorization": f"JWT {self.token}"},
        )
    def put_organisation_settings(self):
        """
        Simulates a PUT request to the /organizations/1/ endpoint to update organisation
        """
        self.client.put(
            "/organizations/1",
            data={"title": "Anudesh Locust Test"},
            headers={"Authorization": f"JWT {self.token}"},
        )






# Report Sub Tab User Report
# for annotator
def get_report_annotator(self):
    """
    Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report annotator
    """
    
    payload={"project_type":"ContextualTranslationEditing",
             "from_date":"2025-04-24",
             "to_date":"2025-04-30",
             "reports_type":"annotation",
             "send_mail":"false"}
    self.client.get(
        "/organizations/1/user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )        
        
def get_report_annotator_email(self):
        """
        Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report annotator
        """

        payload={"project_type":"ContextualTranslationEditing",
                 "from_date":"2025-04-24",
                 "to_date":"2025-04-30",
                 "reports_type":"annotation",
                 "send_mail":"true"}
        self.client.get(
            "/organizations/1/user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
def get_report_annotator_stage1(self):
        """
        Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report annotator
        """

        payload={"project_type":"ContextualTranslationEditing",
                 "from_date":"2025-04-24",
                 "to_date":"2025-04-30",
                 "project_progress_stage":1,
                 "reports_type":"annotation",
                 "send_mail":"false"}
        self.client.get(
            "/organizations/1/user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
def get_report_annotator_email_stage1(self):
        """
        Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report annotator
        """

        payload={"project_type":"ContextualTranslationEditing",
                 "from_date":"2025-04-24",
                 "to_date":"2025-04-30",
                 "project_progress_stage":1,
                 "reports_type":"annotation",
                 "send_mail":"true"}
        self.client.get(
            "/organizations/1/user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
def get_report_annotator_stage2(self):
        """
        Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report annotator
        """

        payload={"project_type":"ContextualTranslationEditing",
                 "from_date":"2025-04-24",
                 "to_date":"2025-04-30",
                 "project_progress_stage":2,
                 "reports_type":"annotation",
                 "send_mail":"false"}
        self.client.get(
            "/organizations/1/user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
def get_report_annotator_email_stage2(self):
        """
        Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report annotator
        """

        payload={"project_type":"ContextualTranslationEditing",
                 "from_date":"2025-04-24",
                 "to_date":"2025-04-30",
                 "project_progress_stage":2,
                 "reports_type":"annotation",
                 "send_mail":"true"}
        self.client.get(
            "/organizations/1/user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
def get_report_annotator_stage3(self):
        """
        Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report annotator
        """

        payload={"project_type":"ContextualTranslationEditing",
                 "from_date":"2025-04-24",
                 "to_date":"2025-04-30",
                 "project_progress_stage":3,
                 "reports_type":"annotation",
                 "send_mail":"false"}
        self.client.get(
            "/organizations/1/user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
        
def get_report_annotator_email_stage3(self):
        """
        Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report annotator
        """

        payload={"project_type":"ContextualTranslationEditing",
                 "from_date":"2025-04-24",
                 "to_date":"2025-04-30",
                 "project_progress_stage":3,
                 "reports_type":"annotation",
                 "send_mail":"true"}
        self.client.get(
            "/organizations/1/user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

# for reviewer
def get_report_reviewer(self):
    """
    Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report reviewer
    """
    
    payload={"project_type":"ContextualTranslationEditing",
             "from_date":"2025-04-24",
             "to_date":"2025-04-30",
             "reports_type":"review",
             "send_mail":"false"}
    self.client.get(
        "/organizations/1/user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )

def get_report_reviewer_email(self):
    """
    Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report reviewer
    """

    payload={"project_type":"ContextualTranslationEditing",
             "from_date":"2025-04-24",
             "to_date":"2025-04-30",
             "reports_type":"review",
             "send_mail":"true"}
    self.client.get(
        "/organizations/1/user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
def get_report_reviewer_stage2(self):
    """
    Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report reviewer
    """

    payload={"project_type":"ContextualTranslationEditing",
             "from_date":"2025-04-24",
             "to_date":"2025-04-30",
             "project_progress_stage":2,
             "reports_type":"review",
             "send_mail":"false"}
    self.client.get(
        "/organizations/1/user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
def get_report_reviewer_email_stage2(self):
    """
    Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report reviewer
    """

    payload={"project_type":"ContextualTranslationEditing",
             "from_date":"2025-04-24",
             "to_date":"2025-04-30",
             "project_progress_stage":2,
             "reports_type":"review",
             "send_mail":"true"}
    self.client.get(
        "/organizations/1/user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )

def get_report_reviewer_stage3(self):
    """
    Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report reviewer
    """

    payload={"project_type":"ContextualTranslationEditing",
             "from_date":"2025-04-24",
             "to_date":"2025-04-30",
             "project_progress_stage":3,
             "reports_type":"review",
             "send_mail":"false"}
    self.client.get(
        "/organizations/1/user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
def get_report_reviewer_email_stage3(self):
    """
    Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report reviewer
    """

    payload={"project_type":"ContextualTranslationEditing",
             "from_date":"2025-04-24",
             "to_date":"2025-04-30",
             "project_progress_stage":3,
             "reports_type":"review",
             "send_mail":"true"}
    self.client.get(
        "/organizations/1/user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
# for superchecker
def get_report_superchecker(self):
    """
    Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report superchecker
    """
    
    payload={"project_type":"ContextualTranslationEditing",
             "from_date":"2025-04-24",
             "to_date":"2025-04-30",
             "reports_type":"superchecker",
             "send_mail":"false"}
    self.client.get(
        "/organizations/1/user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
def get_report_superchecker_email(self):  
    """
    Simulates a GET request to the /organizations/1/user_analytics/ endpoint to fetch report superchecker
    """

    payload={"project_type":"ContextualTranslationEditing",
             "from_date":"2025-04-24",
             "to_date":"2025-04-30",
             "reports_type":"superchecker",
             "send_mail":"true"}
    self.client.get(
        "/organizations/1/user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
      
        
#  Project Report
def get_report_project(self):
    """
    Simulates a GET request to the /organizations/1/project_analytics/ endpoint to fetch report project
    """
    payload={"project_type":"ContextualTranslationEditing",
             "user_id":1,
             "send_mail":"false"}
    self.client.get(
        "/organizations/1/project_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
def get_report_project_email(self):
    """
    Simulates a GET request to the /organizations/1/project_analytics/ endpoint to fetch report project email
    """
    payload={"project_type":"ContextualTranslationEditing",
             "user_id":1,
             "send_mail":"true"}
    self.client.get(
        "/organizations/1/project_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
# For Detailed Project Report
def get_complete_statistics_detailed_project(self):
    """
    Simulates a GET request to the /functions/schedule_project_reports_email endpoint to fetch report project email complete_statistics
    """
    payload={"organization_id":1,
             "user_id":1,
             "project_type":"ContextualTranslationEditing",
             "complete_statistics":"true"}
    self.client.get(
        "/functions/schedule_project_reports_email",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
def get_meta_info_statistics_detailed_project_email(self):
    """
    Simulates a GET request to the /functions/schedule_project_reports_email endpoint to fetch report project email meta_info_statistics
    """
    payload={"organization_id":1,
             "user_id":1,
             "project_type":"ContextualTranslationEditing",
             "meta-info_statistics":"true",
             "send_mail":"true"}
    self.client.get(
        "/functions/schedule_project_reports_email",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
        
def get_annotation_statistics_detailed_project(self):
    """
    Simulates a GET request to the /functions/schedule_project_reports_email endpoint to fetch report project email annotation_statistics
    """
    payload={"organization_id":1,
             "user_id":1,
             "project_type":"ContextualTranslationEditing",
             "annotation_statistics":"true"}
    self.client.get(
        "/functions/schedule_project_reports_email",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
# for Payment Report
def get_payment_report_full_time(self):
    """
    Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment
    """
    
    payload={"project_type":"AllAudioProjects",
             "participation_types":[1],
             "user_id":1,
             "from_date":"2025-04-26",
             "to_date":"2025-05-02"}
    
    self.client.get(
        "/organizations/1/send_user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
def get_payment_report_part_time(self):
    """
    Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
    """
    
    payload={"project_type":"AllAudioProjects",
             "participation_types":[2],
             "user_id":1,
             "from_date":"2025-04-26",
            "to_date":"2025-05-02"}
    
    self.client.get(
        "/organizations/1/send_user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )

def get_payment_report_contract_basis(self):
    """
    Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
    """
    
    payload={"project_type":"AllAudioProjects",
             "participation_types":[4],
             "user_id":1,
             "from_date":"2025-04-26",
             "to_date":"2025-05-02"}
    
    self.client.get(
        "/organizations/1/send_user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )

def get_payment_report_part_time_full_time_contract_basis(self):
    """
    Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
    """
    
    payload={"project_type":"AllAudioProjects",
             "participation_types":[4, 2, 1],
             "user_id":1,
             "from_date":"2025-04-26",
             "to_date":"2025-05-02"}
    
    self.client.get(
        "/organizations/1/send_user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )   
    
def get_payment_report_part_time_full_time(self):
    """
    Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
    """
    
    payload={"project_type":"AllAudioProjects",
             "participation_types":[1,3],
             "user_id":1,
             "from_date":"2025-04-26",
             "to_date":"2025-05-02",
             }
    
    self.client.get(
        "/organizations/1/send_user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
def get_payment_report_full_time_part_time(self):
    """
    Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
    """
    
    payload={"project_type":"AllAudioProjects",
             "participation_types":[2,1],
             "user_id":1,
             "from_date":"2025-04-26",
             "to_date":"2025-05-02",
             }
    
    self.client.get(
        "/organizations/1/send_user_analytics/",
        json=payload,
        headers={"Authorization": f"JWT {self.token}"},
    )
    
def get_payment_report_full_time_contract_basis(self):
    """
    Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
    """    
    payload={"project_type":"AllAudioProjects",
                "participation_types":[1,4],
                "user_id":1,
                "from_date":"2025-04-26",
                "to_date":"2025-05-02",
                }
        
    self.client.get(
            "/organizations/1/send_user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )

def get_payment_report_part_time_contract_basis(self):
    """
    Simulates a GET request to the /organizations/1/payment_analytics/ endpoint to fetch report payment email
    """    
    payload={"project_type":"AllAudioProjects",
                "participation_types":[2,4],
                "user_id":1,
                "from_date":"2025-04-26",
                "to_date":"2025-05-02",
                }
        
    self.client.get(
            "/organizations/1/send_user_analytics/",
            json=payload,
            headers={"Authorization": f"JWT {self.token}"},
        )
    
# done