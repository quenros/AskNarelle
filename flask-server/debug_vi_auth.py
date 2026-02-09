# debug_vi_auth.py
import os
import requests
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# 1. Load your variables
load_dotenv()

SUB_ID = os.environ.get("VIDEO_INDEXER_SUBSCRIPTION_ID")
RG = os.environ.get("VIDEO_INDEXER_RESOURCE_GROUP")
ACCOUNT = os.environ.get("VIDEO_INDEXER_ACCOUNT_NAME")

print(f"--- Debugging VI Auth ---")
print(f"Target Subscription: {SUB_ID}")
print(f"Using Client ID:     {os.environ.get('AZURE_CLIENT_ID')}")
print(f"Using Tenant ID:     {os.environ.get('AZURE_TENANT_ID')}")

try:
    # 2. Get the Token
    print("\n1. Attempting to get ARM Token...")
    cred = DefaultAzureCredential()
    token_obj = cred.get_token("https://management.azure.com/.default")
    token = token_obj.token
    print("   SUCCESS: Token acquired!")

    # 3. Test the exact URL that is failing
    print("\n2. Testing ARM Permission...")
    url = (
        f"https://management.azure.com/subscriptions/{SUB_ID}"
        f"/resourceGroups/{RG}"
        f"/providers/Microsoft.VideoIndexer/accounts/{ACCOUNT}"
        f"?api-version=2022-08-01"
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        print("\n   SUCCESS! The code has access to Video Indexer.")
        print(f"   Account Location: {resp.json().get('location')}")
        print("   If the script works but the app fails, RESTART your app container/service.")
    else:
        print(f"\n   FAILURE: Azure returned {resp.status_code}")
        print(f"   Error Details: {resp.text}")
        
        if resp.status_code == 401:
            print("\n   [DIAGNOSIS]: 401 usually means a Tenant Mismatch.")
            print("   Check: Does your AZURE_TENANT_ID match the Tenant where the Subscription currently lives?")
            print("   Check: Did you create the App Registration in the NEW tenant?")
        elif resp.status_code == 403:
            print("\n   [DIAGNOSIS]: 403 means the App exists, but has no permissions.")
            print("   Check: Did you assign the 'Contributor' role to this specific App?")

except Exception as e:
    print(f"\n   CRITICAL FAILURE: {e}")