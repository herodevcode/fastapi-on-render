from typing import Optional
import requests
import json
import logging

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Dict, Any, List

from config import settings
from dependencies import get_api_key
from models import (
    AttributeValue, 
    PromptFieldBatchRequest, 
    BubbleRecordCreate, 
    BubbleRecordBatchCreate, 
    BubbleRecordUpdateListField, 
    GeneratedPromptCreate, 
    GeneratedPromptBatchCreate,
    PromptFieldAndGeneratedPromptBatchCreate,
    ApiRequestUpdate,
    ApiRequestProcessAndUpdate
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

def get_bubble_base_url(environment: str = "version-test"):
    """Get the base URL for Bubble API based on environment"""
    if not settings.BUBBLE_APP_DOMAIN or not settings.BUBBLE_SAMPLE_DATA_TYPE:
        return None
    
    if environment == "version-test":
        return f"https://{settings.BUBBLE_APP_DOMAIN}/version-test/api/1.1/obj/{settings.BUBBLE_SAMPLE_DATA_TYPE}"
    else:
        return f"https://{settings.BUBBLE_APP_DOMAIN}/api/1.1/obj/{settings.BUBBLE_SAMPLE_DATA_TYPE}"

def get_bubble_promptfield_base_url(environment: str = "version-test"):
    """Get the base URL for Bubble PromptField API based on environment"""
    if not settings.BUBBLE_APP_DOMAIN or not settings.BUBBLE_PROMPTFIELD_DATA_TYPE:
        return None
    
    if environment == "version-test":
        return f"https://{settings.BUBBLE_APP_DOMAIN}/version-test/api/1.1/obj/{settings.BUBBLE_PROMPTFIELD_DATA_TYPE}"
    else:
        return f"https://{settings.BUBBLE_APP_DOMAIN}/api/1.1/obj/{settings.BUBBLE_PROMPTFIELD_DATA_TYPE}"

def get_bubble_generatedprompt_base_url(environment: str = "version-test"):
    """Get the base URL for Bubble GeneratedPrompt API based on environment"""
    if not settings.BUBBLE_APP_DOMAIN or not settings.BUBBLE_GENERATEDPROMPT_DATA_TYPE:
        return None
    
    if environment == "version-test":
        return f"https://{settings.BUBBLE_APP_DOMAIN}/version-test/api/1.1/obj/{settings.BUBBLE_GENERATEDPROMPT_DATA_TYPE}"
    else:
        return f"https://{settings.BUBBLE_APP_DOMAIN}/api/1.1/obj/{settings.BUBBLE_GENERATEDPROMPT_DATA_TYPE}"

def get_bubble_api_request_base_url(environment: str = "version-test"):
    """Get the base URL for Bubble API Request based on environment"""
    if not settings.BUBBLE_APP_DOMAIN or not settings.BUBBLE_API_REQUEST_DATA_TYPE:
        return None
    
    if environment == "version-test":
        return f"https://{settings.BUBBLE_APP_DOMAIN}/version-test/api/1.1/obj/{settings.BUBBLE_API_REQUEST_DATA_TYPE}"
    else:
        return f"https://{settings.BUBBLE_APP_DOMAIN}/api/1.1/obj/{settings.BUBBLE_API_REQUEST_DATA_TYPE}"

@app.get("/", tags=["basic"])
async def root():
    return RedirectResponse(url="/docs")

@app.get("/items/{item_id}", tags=["basic"])
def read_item(item_id: int, q: Optional[str] = None, api_key: str = Depends(get_api_key)):
    return {"item_id": item_id, "q": q}

@app.get("/bubble/sample-records/search", tags=["bubble"])
async def search_bubble_sample_records_by_name(
    name: str, 
    bubble_environment: str = "version-test",
    limit: Optional[int] = 10,
    api_key: str = Depends(get_api_key)
):
    """Search for sample records in Bubble database by name field. Use query parameter: ?name=Sample Record&bubble_environment=version-test"""
    
    # Validate Bubble configuration
    base_url = get_bubble_base_url(bubble_environment)
    if not base_url or not settings.BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble API configuration is missing. Please check environment variables."
        )
    
    # Prepare request with search constraints
    url = base_url
    headers = {
        "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Build search parameters for Bubble Data API
    params = {
        "constraints": json.dumps([{
            "key": "name",
            "constraint_type": "equals",
            "value": name
        }]),
        "limit": limit
    }
    
    try:
        # Make request to Bubble API
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        logger.info(f"Search request URL: {response.url}")
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            results = response_data.get("response", {}).get("results", [])
            
            return {
                "success": True,
                "search_query": {
                    "field": "name",
                    "value": name,
                    "limit": limit
                },
                "count": len(results),
                "remaining": response_data.get("response", {}).get("remaining", 0),
                "results": results
            }
        elif response.status_code == 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid search parameters: {response.text}"
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

@app.get("/bubble/sample-records/{record_id}", tags=["bubble"])
async def get_bubble_sample_record(
    record_id: str, 
    bubble_environment: str = "version-test",
    api_key: str = Depends(get_api_key)
):
    """Fetch a specific sample record from Bubble database by ID. Use example: 1755912306378x688197843685340200"""
    
    # Validate Bubble configuration
    base_url = get_bubble_base_url(bubble_environment)
    if not base_url or not settings.BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble API configuration is missing. Please check environment variables."
        )
    
    # Prepare request
    url = f"{base_url}/{record_id}"
    headers = {
        "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
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
    base_url = get_bubble_base_url(record_data.bubble_environment)
    if not base_url or not settings.BUBBLE_API_TOKEN:
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
        "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
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
    base_url = get_bubble_base_url(batch_data.bubble_environment)
    if not base_url or not settings.BUBBLE_API_TOKEN:
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
        "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
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

@app.patch("/bubble/sample-records/{record_id}/add-sample2", tags=["bubble"])
async def add_sample2_to_record_list(
    record_id: str, 
    update_data: BubbleRecordUpdateListField, 
    api_key: str = Depends(get_api_key)
):
    """Add a Sample2 record to the list_of_sample2 field of a Sample record. Use 1755917228572x874974032002943500 and 1755919121078x981069894958858800"""
    
    # Validate Bubble configuration
    base_url = get_bubble_base_url(update_data.bubble_environment)
    if not base_url or not settings.BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble API configuration is missing. Please check environment variables."
        )
    
    if not settings.BUBBLE_SAMPLE2_DATA_TYPE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BUBBLE_SAMPLE2_DATA_TYPE is not configured. Please check environment variables."
        )
    
    # Try different payload formats for Bubble list field updates
    # Format 1: Direct assignment with existing values plus new one
    # First, get the current record to see existing list values
    url = f"{base_url}/{record_id}"
    headers = {
        "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    logger.info(f"First, fetching current record {record_id} to get existing list values")
    
    try:
        # Get current record
        get_response = requests.get(url, headers=headers, timeout=30)
        
        if get_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not fetch record {record_id}: {get_response.text}"
            )
        
        current_data = get_response.json()
        logger.info(f"Current record data: {current_data}")
        
        # Get existing list values
        current_list = current_data.get("response", {}).get("list_of_sample2", [])
        logger.info(f"Current list_of_sample2: {current_list}")
        
        # Add new ID to existing list (avoid duplicates)
        if isinstance(current_list, list):
            updated_list = current_list.copy()
            if update_data.sample2_id not in updated_list:
                updated_list.append(update_data.sample2_id)
            else:
                # Item already exists, return success without making update
                return {
                    "success": True,
                    "message": f"Sample2 record {update_data.sample2_id} already exists in Sample record {record_id}",
                    "record_id": record_id,
                    "sample2_id": update_data.sample2_id,
                    "previous_list": current_list,
                    "updated_list": current_list,
                    "already_existed": True
                }
        else:
            updated_list = [update_data.sample2_id]
        
        # Prepare the update payload with the complete updated list
        payload = {
            "list_of_sample2": updated_list
        }
        
        logger.info(f"Updating record {record_id} with payload: {payload}")
        logger.info(f"Request URL: {url}")
        
        # Make PATCH request to Bubble API
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        
        # Handle both 200 (OK with content) and 204 (No Content - successful update)
        if response.status_code in [200, 204]:
            # For 204, there's no response body, so we create our own success response
            if response.status_code == 204:
                response_data = {
                    "status": "success",
                    "message": "Record updated successfully"
                }
            else:
                response_data = response.json()
            
            return {
                "success": True,
                "message": f"Successfully added Sample2 record {update_data.sample2_id} to Sample record {record_id}",
                "record_id": record_id,
                "added_sample2_id": update_data.sample2_id,
                "previous_list": current_list,
                "updated_list": updated_list,
                "http_status": response.status_code,
                "data": response_data
            }
        elif response.status_code == 400:
            # Log the full error response for debugging
            logger.error(f"400 Bad Request details: {response.text}")
            try:
                error_data = response.json()
                error_message = error_data.get("body", {}).get("message", response.text)
            except:
                error_message = response.text
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data provided: {error_message}"
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
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample record with ID {record_id} not found"
            )
        else:
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
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

@app.post("/bubble/promptfields/batch-process", tags=["bubble"])
async def process_promptfield_attributes(
    request_data: PromptFieldBatchRequest,
    api_key: str = Depends(get_api_key)
):
    """Process a list of attribute-value pairs and return PromptField record IDs"""
    
    if not settings.BUBBLE_PROMPTFIELD_DATA_TYPE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BUBBLE_PROMPTFIELD_DATA_TYPE is not configured. Please check environment variables."
        )
    
    results = []
    errors = []
    
    logger.info(f"Processing {len(request_data.attributes)} PromptField attributes")
    
    for i, attr_value in enumerate(request_data.attributes):
        try:
            record_id = await search_or_create_promptfield(attr_value.attribute, request_data.bubble_environment)
            results.append({
                "attribute": attr_value.attribute,
                "value": attr_value.value,
                "promptfield_id": record_id,
                "index": i
            })
            
        except Exception as e:
            error_detail = {
                "attribute": attr_value.attribute,
                "value": attr_value.value,
                "index": i,
                "error": str(e)
            }
            errors.append(error_detail)
            logger.error(f"Error processing attribute '{attr_value.attribute}': {str(e)}")
    
    # Extract just the IDs for the main response
    promptfield_ids = [result["promptfield_id"] for result in results]
    
    response = {
        "success": len(errors) == 0,
        "message": f"Processed {len(results)} attributes successfully" + (f", {len(errors)} errors" if errors else ""),
        "total_processed": len(request_data.attributes),
        "successful_count": len(results),
        "error_count": len(errors),
        "promptfield_ids": promptfield_ids,
        "detailed_results": results
    }
    
    if errors:
        response["errors"] = errors
    
    return response

async def search_or_create_promptfield(attribute_name: str, environment: str = "version-test") -> str:
    """Search for PromptField by name, create if not found, return record ID"""
    
    # Validate Bubble configuration
    base_url = get_bubble_promptfield_base_url(environment)
    if not base_url or not settings.BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble PromptField API configuration is missing. Please check environment variables."
        )
    
    headers = {
        "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # First, search for existing record
    search_params = {
        "constraints": json.dumps([{
            "key": "Name",
            "constraint_type": "equals",
            "value": attribute_name
        }]),
        "limit": 1
    }
    
    try:
        # Search for existing record
        search_response = requests.get(base_url, headers=headers, params=search_params, timeout=30)
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            results = search_data.get("response", {}).get("results", [])
            
            if results:
                # Record found, return its ID
                record_id = results[0].get("_id")
                logger.info(f"Found existing PromptField record for '{attribute_name}': {record_id}")
                return record_id
        
        # No existing record found, create new one
        logger.info(f"No existing PromptField found for '{attribute_name}', creating new record")
        
        create_payload = {
            "Name": attribute_name
        }
        
        create_response = requests.post(base_url, headers=headers, json=create_payload, timeout=30)
        
        if create_response.status_code == 201:
            create_data = create_response.json()
            new_record_id = create_data.get("id")
            logger.info(f"Created new PromptField record for '{attribute_name}': {new_record_id}")
            return new_record_id
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create PromptField record: {create_response.status_code} - {create_response.text}"
            )
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Bubble API: {str(e)}"
        )

@app.post("/bubble/generated-prompts/batch", tags=["bubble"])
async def create_generated_prompts_batch(
    batch_data: GeneratedPromptBatchCreate, 
    api_key: str = Depends(get_api_key)
):
    """Create multiple GeneratedPrompt records in Bubble database using bulk API"""
    
    # Validate Bubble configuration
    base_url = get_bubble_generatedprompt_base_url(batch_data.bubble_environment)
    if not base_url or not settings.BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble GeneratedPrompt API configuration is missing. Please check environment variables."
        )
    
    # Format data as newline-separated JSON objects
    bulk_data_lines = []
    for record in batch_data.records:
        record_json = {
            "PromptField": record.promptfield_id,
            "Value": record.value
        }
        bulk_data_lines.append(json.dumps(record_json))
    
    bulk_data = "\n".join(bulk_data_lines)
    
    # Debug logging
    logger.info(f"GeneratedPrompt batch request data count: {len(batch_data.records)}")
    logger.info(f"Bulk data lines: {bulk_data_lines}")
    logger.info(f"Final bulk data: {repr(bulk_data)}")
    
    # Prepare request to bulk endpoint
    url = f"{base_url}/bulk"
    headers = {
        "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
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
                    "message": f"Batch created {successful_count} out of {len(batch_data.records)} GeneratedPrompt records successfully",
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
                    "message": "GeneratedPrompt batch request completed but response parsing failed",
                    "generated_prompt_ids": [],
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

@app.post("/bubble/promptfields-and-generated-prompts/batch", tags=["bubble"])
async def create_promptfields_and_generated_prompts_batch(
    request_data: PromptFieldAndGeneratedPromptBatchCreate,
    api_key: str = Depends(get_api_key)
):
    """Process attributes to create/find PromptFields and create corresponding GeneratedPrompts, returning GeneratedPrompt IDs"""
    
    if not settings.BUBBLE_PROMPTFIELD_DATA_TYPE or not settings.BUBBLE_GENERATEDPROMPT_DATA_TYPE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BUBBLE_PROMPTFIELD_DATA_TYPE or BUBBLE_GENERATEDPROMPT_DATA_TYPE is not configured. Please check environment variables."
        )
    
    generated_prompt_records = []
    results = []
    errors = []
    
    logger.info(f"Processing {len(request_data.attributes)} attributes for PromptField and GeneratedPrompt creation")
    
    # Step 1: Process each attribute to get/create PromptField and prepare GeneratedPrompt data
    for i, attr_value in enumerate(request_data.attributes):
        try:
            # Get or create PromptField
            promptfield_id = await search_or_create_promptfield(attr_value.attribute, request_data.bubble_environment)
            
            # Prepare GeneratedPrompt record
            generated_prompt_records.append(GeneratedPromptCreate(
                promptfield_id=promptfield_id,
                value=attr_value.value
            ))
            
            results.append({
                "attribute": attr_value.attribute,
                "value": attr_value.value,
                "promptfield_id": promptfield_id,
                "index": i
            })
            
        except Exception as e:
            error_detail = {
                "attribute": attr_value.attribute,
                "value": attr_value.value,
                "index": i,
                "error": str(e)
            }
            errors.append(error_detail)
            logger.error(f"Error processing attribute '{attr_value.attribute}': {str(e)}")
    
    # If we have errors in PromptField processing, return early
    if errors:
        return {
            "success": False,
            "message": f"Failed to process {len(errors)} out of {len(request_data.attributes)} attributes",
            "total_processed": len(request_data.attributes),
            "successful_promptfield_count": len(results),
            "error_count": len(errors),
            "errors": errors,
            "generated_prompt_ids": []
        }
    
    # Step 2: Batch create GeneratedPrompts
    try:
        batch_create_data = GeneratedPromptBatchCreate(
            records=generated_prompt_records,
            bubble_environment=request_data.bubble_environment
        )
        
        # Use the existing batch create logic
        base_url = get_bubble_generatedprompt_base_url(request_data.bubble_environment)
        if not base_url or not settings.BUBBLE_API_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bubble GeneratedPrompt API configuration is missing. Please check environment variables."
            )
        
        # Format data as newline-separated JSON objects
        bulk_data_lines = []
        for record in generated_prompt_records:
            record_json = {
                "PromptField": record.promptfield_id,
                "Value": record.value
            }
            bulk_data_lines.append(json.dumps(record_json))
        
        bulk_data = "\n".join(bulk_data_lines)
        
        # Prepare request to bulk endpoint
        url = f"{base_url}/bulk"
        headers = {
            "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
            "Content-Type": "text/plain"
        }
        
        logger.info(f"Creating {len(generated_prompt_records)} GeneratedPrompt records")
        
        # Make request to Bubble API
        response = requests.post(url, headers=headers, data=bulk_data, timeout=30)
        
        if response.status_code == 200:
            try:
                # Parse multi-line JSON response
                response_lines = response.text.strip().split('\n')
                parsed_responses = []
                
                for line in response_lines:
                    if line.strip():
                        parsed_responses.append(json.loads(line))
                
                # Extract created GeneratedPrompt IDs
                generated_prompt_ids = []
                successful_count = 0
                creation_errors = []
                
                for i, resp in enumerate(parsed_responses):
                    if resp.get("status") == "success":
                        successful_count += 1
                        if "id" in resp:
                            generated_prompt_ids.append(resp["id"])
                            # Add the generated_prompt_id to our results
                            if i < len(results):
                                results[i]["generated_prompt_id"] = resp["id"]
                    else:
                        creation_errors.append({
                            "index": i,
                            "error": resp,
                            "attribute": results[i]["attribute"] if i < len(results) else "unknown"
                        })
                
                return {
                    "success": successful_count == len(generated_prompt_records),
                    "message": f"Successfully created {successful_count} out of {len(generated_prompt_records)} GeneratedPrompt records",
                    "total_attributes": len(request_data.attributes),
                    "promptfield_processing_successful": len(results),
                    "generated_prompt_creation_successful": successful_count,
                    "generated_prompt_ids": generated_prompt_ids,
                    "detailed_results": results,
                    "creation_errors": creation_errors if creation_errors else None
                }
                
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {json_err}")
                return {
                    "success": False,
                    "message": "GeneratedPrompt batch creation completed but response parsing failed",
                    "generated_prompt_ids": [],
                    "raw_response": response.text,
                    "error": str(json_err)
                }
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create GeneratedPrompts: {response.status_code} - {response.text}"
            )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception during GeneratedPrompt creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Bubble API for GeneratedPrompt creation: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during GeneratedPrompt creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during GeneratedPrompt creation: {str(e)}"
        )

@app.patch("/bubble/api-requests/{request_id}", tags=["bubble"])
async def update_api_request(
    request_id: str,
    update_data: ApiRequestUpdate,
    api_key: str = Depends(get_api_key)
):
    """Update an API Request record with JSON prompt and generated prompts"""
    
    # Validate Bubble configuration
    base_url = get_bubble_api_request_base_url(update_data.bubble_environment)
    if not base_url or not settings.BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble API Request configuration is missing. Please check environment variables."
        )
    
    # Format JSON prompt field for Bubble
    json_prompt_formatted = []
    for item in update_data.json_prompt:
        json_prompt_formatted.append({
            "attribute": item.attribute,
            "value": item.value
        })
    
    # Prepare update payload - convert JSON prompt to string as expected by Bubble
    payload = {
        "jsonPrompt": json.dumps(json_prompt_formatted),
        "GeneratedPrompts": update_data.generated_prompts
    }
    
    # URL for the specific record
    url = f"{base_url}/{request_id}"
    headers = {
        "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    logger.info(f"Updating API Request record {request_id} with payload: {payload}")
    
    try:
        # Make PATCH request to Bubble API
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        
        if response.status_code in [200, 204]:
            # Handle both 200 (OK with content) and 204 (No Content - successful update)
            if response.status_code == 204:
                response_data = {
                    "status": "success",
                    "message": "API Request record updated successfully"
                }
            else:
                response_data = response.json()
            
            return {
                "success": True,
                "message": f"Successfully updated API Request record {request_id}",
                "request_id": request_id,
                "json_prompt_count": len(update_data.json_prompt),
                "GeneratedPrompts_count": len(update_data.generated_prompts),
                "http_status": response.status_code,
                "data": response_data
            }
        elif response.status_code == 400:
            logger.error(f"400 Bad Request details: {response.text}")
            try:
                error_data = response.json()
                error_message = error_data.get("body", {}).get("message", response.text)
            except:
                error_message = response.text
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data provided: {error_message}"
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
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API Request record with ID {request_id} not found"
            )
        else:
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
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

@app.post("/bubble/api-requests/process-and-update", tags=["bubble"])
async def process_and_update_api_request(
    request_data: ApiRequestProcessAndUpdate,
    api_key: str = Depends(get_api_key)
):
    """Process attributes to create PromptFields and GeneratedPrompts, then update the API Request record with the results"""
    
    try:
        # Step 1: Process attributes to create PromptFields and GeneratedPrompts
        logger.info(f"Processing {len(request_data.attributes)} attributes for API Request {request_data.request_id}")
        
        # Create the batch request data for PromptFields and GeneratedPrompts
        batch_request = PromptFieldAndGeneratedPromptBatchCreate(
            attributes=request_data.attributes,
            bubble_environment=request_data.bubble_environment
        )
        
        # Call the existing logic for creating PromptFields and GeneratedPrompts
        if not settings.BUBBLE_PROMPTFIELD_DATA_TYPE or not settings.BUBBLE_GENERATEDPROMPT_DATA_TYPE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="BUBBLE_PROMPTFIELD_DATA_TYPE or BUBBLE_GENERATEDPROMPT_DATA_TYPE is not configured."
            )
        
        generated_prompt_records = []
        promptfield_results = []
        promptfield_errors = []
        
        # Process each attribute to get/create PromptField and prepare GeneratedPrompt data
        for i, attr_value in enumerate(request_data.attributes):
            try:
                # Get or create PromptField
                promptfield_id = await search_or_create_promptfield(attr_value.attribute, request_data.bubble_environment)
                
                # Prepare GeneratedPrompt record
                generated_prompt_records.append(GeneratedPromptCreate(
                    promptfield_id=promptfield_id,
                    value=attr_value.value
                ))
                
                promptfield_results.append({
                    "attribute": attr_value.attribute,
                    "value": attr_value.value,
                    "promptfield_id": promptfield_id,
                    "index": i
                })
                
            except Exception as e:
                error_detail = {
                    "attribute": attr_value.attribute,
                    "value": attr_value.value,
                    "index": i,
                    "error": str(e)
                }
                promptfield_errors.append(error_detail)
                logger.error(f"Error processing attribute '{attr_value.attribute}': {str(e)}")
        
        # If we have errors in PromptField processing, return early
        if promptfield_errors:
            return {
                "success": False,
                "message": f"Failed to process {len(promptfield_errors)} out of {len(request_data.attributes)} attributes",
                "step": "promptfield_processing",
                "total_processed": len(request_data.attributes),
                "successful_promptfield_count": len(promptfield_results),
                "error_count": len(promptfield_errors),
                "errors": promptfield_errors
            }
        
        # Step 2: Batch create GeneratedPrompts
        logger.info(f"Creating {len(generated_prompt_records)} GeneratedPrompt records")
        
        base_url = get_bubble_generatedprompt_base_url(request_data.bubble_environment)
        if not base_url or not settings.BUBBLE_API_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bubble GeneratedPrompt API configuration is missing."
            )
        
        # Format data as newline-separated JSON objects
        bulk_data_lines = []
        for record in generated_prompt_records:
            record_json = {
                "PromptField": record.promptfield_id,
                "Value": record.value
            }
            bulk_data_lines.append(json.dumps(record_json))
        
        bulk_data = "\n".join(bulk_data_lines)
        
        # Prepare request to bulk endpoint
        url = f"{base_url}/bulk"
        headers = {
            "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
            "Content-Type": "text/plain"
        }
        
        # Make request to Bubble API for GeneratedPrompts
        response = requests.post(url, headers=headers, data=bulk_data, timeout=30)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create GeneratedPrompts: {response.status_code} - {response.text}"
            )
        
        # Parse GeneratedPrompt creation response
        response_lines = response.text.strip().split('\n')
        parsed_responses = []
        
        for line in response_lines:
            if line.strip():
                parsed_responses.append(json.loads(line))
        
        # Extract created GeneratedPrompt IDs
        generated_prompt_ids = []
        successful_gp_count = 0
        gp_creation_errors = []
        
        for i, resp in enumerate(parsed_responses):
            if resp.get("status") == "success":
                successful_gp_count += 1
                if "id" in resp:
                    generated_prompt_ids.append(resp["id"])
                    # Add the generated_prompt_id to our results
                    if i < len(promptfield_results):
                        promptfield_results[i]["generated_prompt_id"] = resp["id"]
            else:
                gp_creation_errors.append({
                    "index": i,
                    "error": resp,
                    "attribute": promptfield_results[i]["attribute"] if i < len(promptfield_results) else "unknown"
                })
        
        if gp_creation_errors:
            return {
                "success": False,
                "message": f"Failed to create {len(gp_creation_errors)} GeneratedPrompt records",
                "step": "generatedprompt_creation",
                "total_attributes": len(request_data.attributes),
                "promptfield_processing_successful": len(promptfield_results),
                "generated_prompt_creation_successful": successful_gp_count,
                "generated_prompt_creation_errors": gp_creation_errors
            }
        
        # Step 3: Update API Request record with the results
        logger.info(f"Updating API Request {request_data.request_id} with {len(generated_prompt_ids)} GeneratedPrompt IDs")
        
        # Prepare update data for API Request
        api_update_data = ApiRequestUpdate(
            json_prompt=request_data.attributes,
            generated_prompts=generated_prompt_ids,
            bubble_environment=request_data.bubble_environment
        )
        
        # Get API Request base URL
        api_request_base_url = get_bubble_api_request_base_url(request_data.bubble_environment)
        if not api_request_base_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bubble API Request configuration is missing."
            )
        
        # Format JSON prompt field for Bubble
        json_prompt_formatted = []
        for item in api_update_data.json_prompt:
            json_prompt_formatted.append({
                "attribute": item.attribute,
                "value": item.value
            })
        
        # Prepare update payload
        update_payload = {
            "jsonPrompt": json.dumps(json_prompt_formatted),
            "GeneratedPrompts": api_update_data.generated_prompts
        }
        
        # URL for the specific API Request record
        update_url = f"{api_request_base_url}/{request_data.request_id}"
        update_headers = {
            "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Make PATCH request to update API Request
        update_response = requests.patch(update_url, headers=update_headers, json=update_payload, timeout=30)
        
        logger.info(f"API Request update response status: {update_response.status_code}")
        
        if update_response.status_code not in [200, 204]:
            logger.error(f"Failed to update API Request: {update_response.text}")
            return {
                "success": False,
                "message": f"Successfully created PromptFields and GeneratedPrompts, but failed to update API Request: {update_response.status_code}",
                "step": "api_request_update",
                "generated_prompt_ids": generated_prompt_ids,
                "update_error": update_response.text,
                "partial_success": True
            }
        
        # Parse API Request update response
        if update_response.status_code == 204:
            api_response_data = {
                "status": "success",
                "message": "API Request record updated successfully"
            }
        else:
            api_response_data = update_response.json()
        
        # Return comprehensive success response
        return {
            "success": True,
            "message": f"Successfully processed {len(request_data.attributes)} attributes and updated API Request {request_data.request_id}",
            "request_id": request_data.request_id,
            "total_attributes": len(request_data.attributes),
            "promptfield_processing_successful": len(promptfield_results),
            "generated_prompt_creation_successful": successful_gp_count,
            "generated_prompt_ids": generated_prompt_ids,
            "api_request_update_status": update_response.status_code,
            "detailed_results": promptfield_results,
            "api_request_response": api_response_data
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Bubble API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )