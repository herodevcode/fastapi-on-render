import requests
import json
import subprocess
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in the root directory
root_dir = Path(__file__).parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Configuration with validation
APP_DOMAIN = os.getenv("BUBBLE_APP_DOMAIN")
API_TOKEN = os.getenv("BUBBLE_API_TOKEN")
DATA_TYPE = os.getenv("BUBBLE_DATA_TYPE")
BUBBLE_ENVIRONMENT = os.getenv("BUBBLE_ENVIRONMENT", "production")  # "production" or "version-test"

# Validate required environment variables
def validate_env_vars():
    """Validate that all required environment variables are set"""
    missing_vars = []
    
    if not APP_DOMAIN:
        missing_vars.append("BUBBLE_APP_DOMAIN")
    if not API_TOKEN:
        missing_vars.append("BUBBLE_API_TOKEN")
    if not DATA_TYPE:
        missing_vars.append("BUBBLE_DATA_TYPE")
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables before running the script.")
        print("Example:")
        for var in missing_vars:
            print(f"   export {var}=your_value_here")
        return False
    
    return True

# Base URL for Bubble Data API - adjusted for environment
def get_base_url():
    if BUBBLE_ENVIRONMENT == "version-test":
        return f"https://{APP_DOMAIN}/version-test/api/1.1/obj/{DATA_TYPE}"
    else:
        return f"https://{APP_DOMAIN}/api/1.1/obj/{DATA_TYPE}"

BASE_URL = get_base_url()

# Headers for authentication
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def create_record_with_requests():
    """Create a new record using Python requests library"""
    print("=== Creating record with Python requests ===")
    
    data = {
        "name": "My Test Item",
        "description": "Created via Python requests"
    }
    
    try:
        response = requests.post(BASE_URL, headers=HEADERS, json=data)
        
        if response.status_code == 201:
            print(f"✅ Record created successfully!")
            print(f"Response: {response.json()}")
            return response.json().get('id')
        else:
            print(f"❌ Error creating record: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def update_record_with_requests(record_id):
    """Update an existing record using Python requests library"""
    print(f"\n=== Updating record {record_id} with Python requests ===")
    
    data = {
        "name": "Updated Test Item",
        "description": "Updated via Python requests"
    }
    
    try:
        response = requests.patch(f"{BASE_URL}/{record_id}", headers=HEADERS, json=data)
        
        if response.status_code == 204:
            print(f"✅ Record updated successfully!")
        else:
            print(f"❌ Error updating record: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def create_record_with_curl():
    """Create a new record using curl command"""
    print("\n=== Creating record with curl ===")
    
    curl_command = [
        "curl", "-X", "POST", BASE_URL,
        "-H", f"Authorization: Bearer {API_TOKEN}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "name": "My Test Item (curl)",
            "description": "Created via curl"
        })
    ]
    
    print(f"Curl command: {' '.join(curl_command)}")
    
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Curl request completed!")
            print(f"Response: {result.stdout}")
        else:
            print(f"❌ Curl request failed!")
            print(f"Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Curl execution failed: {e}")

def update_record_with_curl(record_id):
    """Update an existing record using curl command"""
    print(f"\n=== Updating record {record_id} with curl ===")
    
    curl_command = [
        "curl", "-X", "PATCH", f"{BASE_URL}/{record_id}",
        "-H", f"Authorization: Bearer {API_TOKEN}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "name": "Updated Test Item (curl)",
            "description": "Updated via curl"
        })
    ]
    
    print(f"Curl command: {' '.join(curl_command)}")
    
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Curl request completed!")
            print(f"Response: {result.stdout}")
        else:
            print(f"❌ Curl request failed!")
            print(f"Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Curl execution failed: {e}")

def print_example_commands():
    """Print example curl commands for reference"""
    print("\n=== Example curl commands for manual execution ===")
    
    environment_path = "/version-test" if BUBBLE_ENVIRONMENT == "version-test" else ""
    
    print("\n1. Create a new record:")
    print(f"""curl -X POST "https://{APP_DOMAIN}{environment_path}/api/1.1/obj/{DATA_TYPE}" \\
-H "Authorization: Bearer {API_TOKEN}" \\
-H "Content-Type: application/json" \\
-d '{{
  "name": "My Test Item",
  "description": "Created manually"
}}'""")
    
    print("\n2. Update an existing record (replace RECORD_ID with actual ID):")
    print(f"""curl -X PATCH "https://{APP_DOMAIN}{environment_path}/api/1.1/obj/{DATA_TYPE}/RECORD_ID" \\
-H "Authorization: Bearer {API_TOKEN}" \\
-H "Content-Type: application/json" \\
-d '{{
  "name": "Updated Test Item",
  "description": "Updated manually"
}}'""")
    
    print("\n3. Get a specific record:")
    print(f"""curl -X GET "https://{APP_DOMAIN}{environment_path}/api/1.1/obj/{DATA_TYPE}/RECORD_ID" \\
-H "Authorization: Bearer {API_TOKEN}" """)

if __name__ == "__main__":
    print("Bubble API Examples")
    print("==================")
    
    # Validate environment variables first
    if not validate_env_vars():
        sys.exit(1)
    
    print(f"App Domain: {APP_DOMAIN}")
    print(f"Environment: {BUBBLE_ENVIRONMENT}")
    print(f"Data Type: {DATA_TYPE}")
    print(f"Base URL: {BASE_URL}")
    print("\n⚠️  Make sure to update APP_DOMAIN, API_TOKEN, DATA_TYPE, and BUBBLE_ENVIRONMENT variables!")
    
    # Demonstrate Python requests
    record_id = create_record_with_requests()
    
    if record_id:
        update_record_with_requests(record_id)
    
    # Demonstrate curl commands
    create_record_with_curl()
    
    # Print example commands for manual use
    print_example_commands()
