import requests
import json
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

CONTROLLER_URL = "https://192.168.180.45:8443"
USERNAME = "abandomar"
PASSWORD = "1Nformat1ca"
SITE_NAME = "default"


def login(session):
    login_url = f"{CONTROLLER_URL}/api/login"
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    response = session.post(login_url, json=login_data, verify=False)
    
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.text}")
    
    print("Login successful")
    return session


def get_api_key(session):
    api_key_url = f"{CONTROLLER_URL}/api/s/{SITE_NAME}/cmd/sitemgr"
    api_key_payload = {"cmd": "get-api-key"}
    
    response = session.post(api_key_url, json=api_key_payload, verify=False)
    
    if response.status_code == 200:
        try:
            return response.json()["data"]["api_key"]
        except:
            return None
    return None


def get_clients_active(session, api_key=None):
    active_url = f"{CONTROLLER_URL}/api/site/{SITE_NAME}/stat/sta"

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = session.get(active_url, headers=headers, verify=False)
    
    if response.status_code != 200:
        raise Exception(f"No se pudo obtener clientes activos : {response.status_code} - {response.text}")
    
    return response.json()["data"]
