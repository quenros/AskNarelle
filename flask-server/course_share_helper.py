import msal
from dotenv import load_dotenv
import os


load_dotenv()

tenant_id = os.environ.get('TENANT_ID')
authority_url = f'https://login.microsoftonline.com/{tenant_id}'
scope = ["https://graph.microsoft.com/.default"]

graph_url = 'https://graph.microsoft.com/v1.0/'

def get_access_token():
    app = msal.ConfidentialClientApplication(
        os.environ.get('CLIENT_ID'), authority=authority_url, client_credential=os.environ.get('CLIENT_SECRET')
    )
    result = app.acquire_token_for_client(scopes=scope)
    return result.get("access_token")





