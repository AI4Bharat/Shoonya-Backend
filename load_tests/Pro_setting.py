class Pro_setting:

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