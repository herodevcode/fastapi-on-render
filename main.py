from typing import Optional
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, Any

# Load environment variables
root_dir = Path(__file__).parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI()

# Define the API key header
api_key_header = APIKeyHeader(name="X-API-Key")

# Define the expected API key (in production, use environment variables)
API_KEY = "your-secret-api-key"

# Bubble API configuration
BUBBLE_APP_DOMAIN = os.getenv("BUBBLE_APP_DOMAIN")
BUBBLE_API_TOKEN = os.getenv("BUBBLE_API_TOKEN")
BUBBLE_DATA_TYPE = os.getenv("BUBBLE_DATA_TYPE")
BUBBLE_ENVIRONMENT = os.getenv("BUBBLE_ENVIRONMENT", "production")

def get_bubble_base_url():
    """Get the base URL for Bubble API based on environment"""
    if not BUBBLE_APP_DOMAIN or not BUBBLE_DATA_TYPE:
        return None
    
    if BUBBLE_ENVIRONMENT == "version-test":
        return f"https://{BUBBLE_APP_DOMAIN}/version-test/api/1.1/obj/{BUBBLE_DATA_TYPE}"
    else:
        return f"https://{BUBBLE_APP_DOMAIN}/api/1.1/obj/{BUBBLE_DATA_TYPE}"

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return api_key

class BubbleRecordCreate(BaseModel):
    """Model for creating a new record in Bubble database"""
    name: str
    description: str
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Sample Record",
                "description": "This is a sample description for the record"
            }
        }

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None, api_key: str = Depends(get_api_key)):
    return {"item_id": item_id, "q": q}

@app.get("/bubble/records/{record_id}")
async def get_bubble_record(record_id: str, api_key: str = Depends(get_api_key)):
    """Fetch a specific record from Bubble database by ID. Use example: 1755912306378x688197843685340200"""
    
    # Validate Bubble configuration
    base_url = get_bubble_base_url()
    if not base_url or not BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble API configuration is missing. Please check environment variables."
        )
    
    # Prepare request
    url = f"{base_url}/{record_id}"
    headers = {
        "Authorization": f"Bearer {BUBBLE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Make request to Bubble API
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return {
                "success": True,
                "record_id": record_id,
                "data": response.json()
            }
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record with ID {record_id} not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Bubble API error: {response.status_code} - {response.text}"
            )
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Bubble API: {str(e)}"
        )

@app.post("/bubble/records")
async def create_bubble_record(record_data: BubbleRecordCreate, api_key: str = Depends(get_api_key)):
    """Create a new record in Bubble database"""
    
    # Validate Bubble configuration
    base_url = get_bubble_base_url()
    if not base_url or not BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble API configuration is missing. Please check environment variables."
        )
    
    # Prepare request payload
    payload = {
        "name": record_data.name,
        "description": record_data.description
    }
    
    # Prepare request
    url = base_url
    headers = {
        "Authorization": f"Bearer {BUBBLE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Make request to Bubble API
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 201:
            response_data = response.json()
            return {
                "success": True,
                "message": "Record created successfully",
                "record_id": response_data.get("id"),
                "data": response_data
            }
        elif response.status_code == 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data provided: {response.text}"
            )
        elif response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Bubble API token"
            )
        elif response.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Check Bubble privacy rules and API settings."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Bubble API error: {response.status_code} - {response.text}"
            )
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Bubble API: {str(e)}"
        )