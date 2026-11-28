import os
import requests
import json
from dotenv import load_dotenv

# Load env vars
load_dotenv(dotenv_path='../.env')

API_KEY = os.getenv("UPSTOX_API_KEY")
API_SECRET = os.getenv("UPSTOX_API_SECRET")
REDIRECT_URI = "https://127.0.0.1"

print("="*60)
print(" UPSTOX LIVE TRADING LOGIN FLOW ")
print("="*60)

if not API_KEY or not API_SECRET:
    print("ERROR: UPSTOX_API_KEY or UPSTOX_API_SECRET is missing in .env")
    exit(1)

# Step 1: Generate Login URL
login_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={API_KEY}&redirect_uri={REDIRECT_URI}"

print("\nSTEP 1: Open the following URL in your browser and log in to Upstox:")
print(f"\n{login_url}\n")
print("After logging in, your browser will try to go to https://127.0.0.1/?code=...")
print("The page will fail to load, WHICH IS NORMAL. Look at the URL bar.")

# Step 2: Ask for code
code = input("\nSTEP 2: Copy the 'code' parameter from the URL bar and paste it here: ").strip()

if not code:
    print("No code provided. Exiting.")
    exit(1)

# Step 3: Get Access Token
print("\nSTEP 3: Exchanging code for Access Token...")

headers = {
    'accept': 'application/json',
    'Api-Version': '2.0',
    'Content-Type': 'application/x-www-form-urlencoded'
}

data = {
    'code': code,
    'client_id': API_KEY,
    'client_secret': API_SECRET,
    'redirect_uri': REDIRECT_URI,
    'grant_type': 'authorization_code'
}

try:
    response = requests.post('https://api.upstox.com/v2/login/authorization/token', headers=headers, data=data)
    response.raise_for_status()
    result = response.json()
    
    access_token = result.get("access_token")
    
    print("\nSUCCESS! You are now connected to the Live Exchange.")
    print("\nHere is your ACCESS TOKEN (Add this to your .env file as UPSTOX_ACCESS_TOKEN):")
    print("-" * 60)
    print(access_token)
    print("-" * 60)
    
except Exception as e:
    print(f"\nFailed to get token: {e}")
    if 'response' in locals():
        print(response.text)
