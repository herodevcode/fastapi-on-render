from typing import Optional
import os
import requests
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
BUBBLE_SAMPLE_DATA_TYPE = os.getenv("BUBBLE_SAMPLE_DATA_TYPE")
BUBBLE_ENVIRONMENT = os.getenv("BUBBLE_ENVIRONMENT", "production")

def get_bubble_base_url():
    """Get the base URL for Bubble API based on environment"""
    if not BUBBLE_APP_DOMAIN or not BUBBLE_SAMPLE_DATA_TYPE:
        return None
    
    if BUBBLE_ENVIRONMENT == "version-test":
        return f"https://{BUBBLE_APP_DOMAIN}/version-test/api/1.1/obj/{BUBBLE_SAMPLE_DATA_TYPE}"
    else:
        return f"https://{BUBBLE_APP_DOMAIN}/api/1.1/obj/{BUBBLE_SAMPLE_DATA_TYPE}"

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

class BubbleRecordBatchCreate(BaseModel):
    """Model for batch creating records in Bubble database"""
    records: List[BubbleRecordCreate]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "records": [
                    {
                        "name": "string",
                        "description": "string"
                    },
                    {
                        "name": "string",
                        "description": "string"
                    }
                ]
            }
        }
    }

@app.get("/", tags=["basic"])
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}", tags=["basic"])
def read_item(item_id: int, q: Optional[str] = None, api_key: str = Depends(get_api_key)):
    return {"item_id": item_id, "q": q}

@app.get("/bubble/sample-records/{record_id}", tags=["bubble"])
async def get_bubble_sample_record(record_id: str, api_key: str = Depends(get_api_key)):
    """Fetch a specific sample record from Bubble database by ID. Use example: 1755912306378x688197843685340200"""
    
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

@app.post("/bubble/sample-records", tags=["bubble"])
async def create_bubble_sample_record(record_data: BubbleRecordCreate, api_key: str = Depends(get_api_key)):
    """Create a new sample record in Bubble database"""
    
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
                "message": "Sample record created successfully",
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

@app.post("/bubble/sample-records/batch", tags=["bubble"])
async def create_bubble_sample_records_batch(batch_data: BubbleRecordBatchCreate, api_key: str = Depends(get_api_key)):
    """Create multiple sample records in Bubble database using bulk API"""
    
    # Validate Bubble configuration
    base_url = get_bubble_base_url()
    if not base_url or not BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble API configuration is missing. Please check environment variables."
        )
    
    # Format data as newline-separated JSON objects
    bulk_data_lines = []
    for record in batch_data.records:
        record_json = {
            "name": record.name,
            "description": record.description
        }
        bulk_data_lines.append(json.dumps(record_json))
    
    bulk_data = "\n".join(bulk_data_lines)
    
    # Debug logging
    logger.info(f"Batch request data count: {len(batch_data.records)}")
    logger.info(f"Bulk data lines: {bulk_data_lines}")
    logger.info(f"Final bulk data: {repr(bulk_data)}")
    
    # Prepare request to bulk endpoint
    url = f"{base_url}/bulk"
    headers = {
        "Authorization": f"Bearer {BUBBLE_API_TOKEN}",
        "Content-Type": "text/plain"
    }
    
    logger.info(f"Making request to: {url}")
    logger.info(f"Request headers: {headers}")
    
    try:
        # Make request to Bubble API
        response = requests.post(url, headers=headers, data=bulk_data, timeout=30)
        
        # Debug response
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response content: {repr(response.content)}")
        logger.info(f"Response text: {repr(response.text)}")
        
        if response.status_code == 200:
            try:
                # Parse multi-line JSON response (one JSON object per line)
                response_lines = response.text.strip().split('\n')
                parsed_responses = []
                
                for line in response_lines:
                    if line.strip():  # Skip empty lines
                        parsed_responses.append(json.loads(line))
                
                logger.info(f"Successfully parsed {len(parsed_responses)} JSON responses: {parsed_responses}")
                
                # Extract created record IDs
                created_ids = []
                successful_count = 0
                errors = []
                
                for resp in parsed_responses:
                    if resp.get("status") == "success":
                        successful_count += 1
                        if "id" in resp:
                            created_ids.append(resp["id"])
                    else:
                        errors.append(resp)
                
                return {
                    "success": True,
                    "message": f"Batch created {successful_count} out of {len(batch_data.records)} records successfully",
                    "requested_count": len(batch_data.records),
                    "successful_count": successful_count,
                    "created_ids": created_ids,
                    "errors": errors,
                    "detailed_responses": parsed_responses
                }
                
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {json_err}")
                logger.error(f"Raw response: {response.text}")
                return {
                    "success": False,
                    "message": f"Batch request completed but response parsing failed",
                    "requested_count": len(batch_data.records),
                    "raw_response": response.text,
                    "error": str(json_err)
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
            logger.error(f"Unexpected status code: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Bubble API error: {response.status_code} - {response.text}"
            )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Bubble API: {str(e)}"
        )
    except json.JSONDecodeError as json_err:
        logger.error(f"JSON decode error in exception handler: {json_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse Bubble API response: {str(json_err)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )