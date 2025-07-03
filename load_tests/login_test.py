# auth_header.py
import requests

def get_auth_headers():
    login_url = "/users/auth/jwt/create"
    payload = {
        "email": "shoonya@ai4bharat.org",
        "password": "password@admin"
    }
    headers = {'Content-Type': 'application/json'}

    response = requests.post(login_url, json=payload, headers=headers)

    if response.status_code == 200:
        token = response.json().get("access")
        if token:
            return {
                "Authorization": f"JWT {token}",
                "Content-Type": "application/json"
            }
        else:
            raise Exception("Token missing in login response")
    else:
        raise Exception(f"Login failed with status {response.status_code}")

# done