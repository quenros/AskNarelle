import os
import requests
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# Configuration
SUB_ID = os.environ.get("VIDEO_INDEXER_SUBSCRIPTION_ID")
RG = os.environ.get("VIDEO_INDEXER_RESOURCE_GROUP")
ACCOUNT_NAME = os.environ.get("VIDEO_INDEXER_ACCOUNT_NAME")
API_VER = os.environ.get("VIDEO_INDEXER_API_VERSION", "2022-08-01") # Defaults if not found

print("--- Debugging Video Indexer Access Token ---")
print(f"Subscription:   {SUB_ID}")
print(f"Resource Group: {RG}")
print(f"Account Name:   {ACCOUNT_NAME}")
print(f"API Version:    {API_VER}")
print("-" * 30)

try:
    # 2. Authenticate with Azure (Service Principal)
    print("\n[1/2] Getting Azure ARM Token...")
    credential = DefaultAzureCredential()
    arm_token = credential.get_token("https://management.azure.com/.default")
    print("✅ Success! Azure ARM Token acquired.")

    # 3. Request Video Indexer Access Token
    print(f"\n[2/2] Generating VI Access Token (using version {API_VER})...")
    
    url = (
        f"https://management.azure.com/subscriptions/{SUB_ID}"
        f"/resourceGroups/{RG}"
        f"/providers/Microsoft.VideoIndexer/accounts/{ACCOUNT_NAME}"
        f"/generateAccessToken?api-version={API_VER}"
    )
    
    headers = {"Authorization": f"Bearer {arm_token.token}"}
    body = {"permissionType": "Contributor", "scope": "Account"}
    
    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 200:
        token = response.json().get("accessToken")
        print("\n🎉 SUCCESS! Token generated.")
        print(f"Token preview: {token[:20]}...")
        print("\n👉 If this script works but your app fails, you MUST RESTART your app server/container.")
    else:
        print(f"\n❌ FAILED. Status Code: {response.status_code}")
        print(f"URL Used: {url}")
        print(f"Error Response: {response.text}")
        
        if response.status_code == 404:
            print("\n[Diagnosis] 404 means the API Version is likely too old for this new account.")
            print("Try changing VIDEO_INDEXER_API_VERSION in .env to '2024-01-01'")

except Exception as e:
    print(f"\n⛔ CRITICAL ERROR: {str(e)}")