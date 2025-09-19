from typing import Optional
import requests
import json
import logging
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Dict, Any, List

from config import settings
from dependencies import get_api_key
from models import (
    AttributeValue, 
    PromptFieldBatchRequest, 
    GeneratedPromptCreate, 
    GeneratedPromptBatchCreate,
    PromptFieldAndGeneratedPromptBatchCreate,
    ApiRequestUpdate,
    ApiRequestProcessAndUpdate,
    PromptResponse,
    PromptListItem,
    PromptListResponse,
    PromptTemplateProcessedResponse
)

# Import routers
from routers.sample_records import router as sample_records_router
from routers.cloudinary_video import router as cloudinary_video_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Include routers
app.include_router(sample_records_router)
app.include_router(cloudinary_video_router)

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

def get_bubble_generic_base_url(data_type: str, environment: str = "version-test"):
    """Get the base URL for any Bubble data type based on environment"""
    if not settings.BUBBLE_APP_DOMAIN or not data_type:
        return None
    
    if environment == "version-test":
        return f"https://{settings.BUBBLE_APP_DOMAIN}/version-test/api/1.1/obj/{data_type}"
    else:
        return f"https://{settings.BUBBLE_APP_DOMAIN}/api/1.1/obj/{data_type}"

@app.get("/", tags=["basic"])
async def root():
    return RedirectResponse(url="/docs")

@app.get("/items/{item_id}", tags=["basic"])
def read_item(item_id: int, q: Optional[str] = None, api_key: str = Depends(get_api_key)):
    return {"item_id": item_id, "q": q}

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

async def search_promptfield_only(attribute_name: str, environment: str = "version-test") -> Optional[str]:
    """Search for PromptField by name, return record ID if found, None if not found (no creation)"""
    
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
    
    # Search for existing record
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
        
        # No existing record found, return None
        logger.info(f"No existing PromptField found for '{attribute_name}', skipping creation")
        return None
            
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
    """Search for existing PromptFields (no creation) and create corresponding GeneratedPrompts for found ones only"""
    
    if not settings.BUBBLE_PROMPTFIELD_DATA_TYPE or not settings.BUBBLE_GENERATEDPROMPT_DATA_TYPE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BUBBLE_PROMPTFIELD_DATA_TYPE or BUBBLE_GENERATEDPROMPT_DATA_TYPE is not configured. Please check environment variables."
        )
    
    generated_prompt_records = []
    results = []
    skipped = []
    errors = []
    
    logger.info(f"Processing {len(request_data.attributes)} attributes for PromptField search and GeneratedPrompt creation")
    
    # Step 1: Process each attribute to search for existing PromptField and prepare GeneratedPrompt data
    for i, attr_value in enumerate(request_data.attributes):
        try:
            # Search for existing PromptField only (no creation)
            promptfield_id = await search_promptfield_only(attr_value.attribute, request_data.bubble_environment)
            
            if promptfield_id:
                # PromptField found, prepare GeneratedPrompt record
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
            else:
                # PromptField not found, skip this attribute
                skipped.append({
                    "attribute": attr_value.attribute,
                    "value": attr_value.value,
                    "index": i,
                    "reason": "PromptField not found"
                })
                logger.info(f"Skipping attribute '{attr_value.attribute}' - PromptField not found")
            
        except Exception as e:
            error_detail = {
                "attribute": attr_value.attribute,
                "value": attr_value.value,
                "index": i,
                "error": str(e)
            }
            errors.append(error_detail)
            logger.error(f"Error processing attribute '{attr_value.attribute}': {str(e)}")
    
    # If we have no PromptFields found and no errors, return early
    if not generated_prompt_records and not errors:
        return {
            "success": True,
            "message": f"No existing PromptFields found for any of the {len(request_data.attributes)} attributes",
            "total_processed": len(request_data.attributes),
            "found_promptfields": 0,
            "skipped_count": len(skipped),
            "error_count": 0,
            "generated_prompt_ids": [],
            "skipped": skipped
        }
    
    # If we have errors in PromptField processing, include them in response
    if errors:
        response = {
            "success": len(generated_prompt_records) > 0,
            "message": f"Found {len(results)} PromptFields, skipped {len(skipped)}, {len(errors)} errors",
            "total_processed": len(request_data.attributes),
            "found_promptfields": len(results),
            "skipped_count": len(skipped),
            "error_count": len(errors),
            "errors": errors,
            "skipped": skipped,
            "generated_prompt_ids": []
        }
        
        if not generated_prompt_records:
            return response
    
    # Step 2: Batch create GeneratedPrompts for found PromptFields
    try:
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
                    "message": f"Found {len(results)} PromptFields, skipped {len(skipped)}, successfully created {successful_count} GeneratedPrompt records",
                    "total_attributes": len(request_data.attributes),
                    "found_promptfields": len(results),
                    "skipped_count": len(skipped),
                    "generated_prompt_creation_successful": successful_count,
                    "generated_prompt_ids": generated_prompt_ids,
                    "detailed_results": results,
                    "skipped": skipped,
                    "creation_errors": creation_errors if creation_errors else None,
                    "errors": errors if errors else None
                }
                
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {json_err}")
                return {
                    "success": False,
                    "message": "GeneratedPrompt batch creation completed but response parsing failed",
                    "generated_prompt_ids": [],
                    "raw_response": response.text,
                    "error": str(json_err),
                    "skipped": skipped,
                    "found_promptfields": len(results)
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
    """Search for existing PromptFields (no creation) and create GeneratedPrompts, then update the API Request record with the results"""
    
    try:
        # Step 1: Search for existing PromptFields and create GeneratedPrompts
        logger.info(f"Processing {len(request_data.attributes)} attributes for API Request {request_data.request_id}")
        
        if not settings.BUBBLE_PROMPTFIELD_DATA_TYPE or not settings.BUBBLE_GENERATEDPROMPT_DATA_TYPE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="BUBBLE_PROMPTFIELD_DATA_TYPE or BUBBLE_GENERATEDPROMPT_DATA_TYPE is not configured."
            )
        
        generated_prompt_records = []
        promptfield_results = []
        skipped_attributes = []
        promptfield_errors = []
        
        # Process each attribute to search for existing PromptField and prepare GeneratedPrompt data
        for i, attr_value in enumerate(request_data.attributes):
            try:
                # Search for existing PromptField only (no creation)
                promptfield_id = await search_promptfield_only(attr_value.attribute, request_data.bubble_environment)
                
                if promptfield_id:
                    # PromptField found, prepare GeneratedPrompt record
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
                else:
                    # PromptField not found, skip this attribute
                    skipped_attributes.append({
                        "attribute": attr_value.attribute,
                        "value": attr_value.value,
                        "index": i,
                        "reason": "PromptField not found"
                    })
                    logger.info(f"Skipping attribute '{attr_value.attribute}' - PromptField not found")
                
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
                "found_promptfields": len(promptfield_results),
                "skipped_count": len(skipped_attributes),
                "error_count": len(promptfield_errors),
                "errors": promptfield_errors,
                "skipped": skipped_attributes
            }
        
        # If no PromptFields were found, update API Request with empty results
        if not generated_prompt_records:
            logger.info(f"No existing PromptFields found for any attributes, updating API Request {request_data.request_id} with empty results")
            
            # Get API Request base URL
            api_request_base_url = get_bubble_api_request_base_url(request_data.bubble_environment)
            if not api_request_base_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Bubble API Request configuration is missing."
                )
            
            # Format JSON prompt field for Bubble (empty since no PromptFields found)
            json_prompt_formatted = []
            
            # Prepare update payload
            update_payload = {
                "jsonPrompt": json.dumps(json_prompt_formatted),
                "GeneratedPrompts": [],
                "Request Status": "Completed - No Matching PromptFields"
            }
            
            # URL for the specific API Request record
            update_url = f"{api_request_base_url}/{request_data.request_id}"
            update_headers = {
                "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Make PATCH request to update API Request
            update_response = requests.patch(update_url, headers=update_headers, json=update_payload, timeout=30)
            
            if update_response.status_code not in [200, 204]:
                logger.error(f"Failed to update API Request: {update_response.text}")
                return {
                    "success": False,
                    "message": f"No PromptFields found and failed to update API Request: {update_response.status_code}",
                    "step": "api_request_update",
                    "update_error": update_response.text
                }
            
            return {
                "success": True,
                "message": f"No existing PromptFields found for any of {len(request_data.attributes)} attributes, API Request updated with empty results",
                "request_id": request_data.request_id,
                "total_attributes": len(request_data.attributes),
                "found_promptfields": 0,
                "skipped_count": len(skipped_attributes),
                "generated_prompt_ids": [],
                "skipped": skipped_attributes,
                "api_request_update_status": update_response.status_code
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
                "generated_prompt_creation_errors": gp_creation_errors,
                "skipped": skipped_attributes
            }
        
        # Step 3: Update API Request record with the results
        logger.info(f"Updating API Request {request_data.request_id} with {len(generated_prompt_ids)} GeneratedPrompt IDs")
        
        # Get API Request base URL
        api_request_base_url = get_bubble_api_request_base_url(request_data.bubble_environment)
        if not api_request_base_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bubble API Request configuration is missing."
            )
        
        # Format JSON prompt field for Bubble (include ALL attributes that were processed)
        json_prompt_formatted = []
        for item in request_data.attributes:
            json_prompt_formatted.append({
                "attribute": item.attribute,
                "value": item.value
            })
        
        # Prepare update payload with GeneratedPrompts and Request Status
        update_payload = {
            "jsonPrompt": json.dumps(json_prompt_formatted),
            "GeneratedPrompts": generated_prompt_ids,
            "Request Status": "Completed"
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
                "message": f"Successfully created GeneratedPrompts, but failed to update API Request: {update_response.status_code}",
                "step": "api_request_update",
                "generated_prompt_ids": generated_prompt_ids,
                "update_error": update_response.text,
                "partial_success": True,
                "promptfield_results": promptfield_results,
                "skipped": skipped_attributes
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
            "found_promptfields": len(promptfield_results),
            "skipped_count": len(skipped_attributes),
            "promptfield_processing_successful": len(promptfield_results),
            "generated_prompt_creation_successful": successful_gp_count,
            "generated_prompt_ids": generated_prompt_ids,
            "api_request_update_status": update_response.status_code,
            "detailed_results": promptfield_results,
            "skipped": skipped_attributes,
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

@app.get("/prompts/{prompt_name}", tags=["prompts"], response_model=PromptResponse)
async def get_prompt(prompt_name: str, api_key: str = Depends(get_api_key)):
    """Get a prompt by name from stored text files"""
    
    # Define the prompts directory
    prompts_dir = Path("prompts")
    
    # Sanitize the prompt name to prevent directory traversal
    safe_prompt_name = "".join(c for c in prompt_name if c.isalnum() or c in ('-', '_', '.'))
    
    # Look for the prompt file with .txt extension
    prompt_file = prompts_dir / f"{safe_prompt_name}.txt"
    
    # Check if file exists
    if not prompt_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{prompt_name}' not found"
        )
    
    try:
        # Read the prompt content
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        
        return PromptResponse(
            success=True,
            prompt_name=prompt_name,
            content=prompt_content,
            file_path=str(prompt_file)
        )
        
    except Exception as e:
        logger.error(f"Error reading prompt file '{prompt_file}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read prompt file: {str(e)}"
        )

@app.get("/prompts", tags=["prompts"], response_model=PromptListResponse)
async def list_prompts(api_key: str = Depends(get_api_key)):
    """List all available prompts"""
    
    prompts_dir = Path("prompts")
    
    # Create prompts directory if it doesn't exist
    prompts_dir.mkdir(exist_ok=True)
    
    try:
        # Get all .txt files in the prompts directory
        prompt_files = list(prompts_dir.glob("*.txt"))
        
        prompts = []
        for prompt_file in prompt_files:
            prompt_name = prompt_file.stem  # filename without extension
            try:
                # Get basic info about each prompt
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    preview = content[:100] + "..." if len(content) > 100 else content
                
                prompts.append(PromptListItem(
                    name=prompt_name,
                    file_path=str(prompt_file),
                    size_chars=len(content),
                    preview=preview
                ))
            except Exception as e:
                logger.warning(f"Could not read prompt file '{prompt_file}': {str(e)}")
                prompts.append(PromptListItem(
                    name=prompt_name,
                    file_path=str(prompt_file),
                    error=str(e)
                ))
        
        return PromptListResponse(
            success=True,
            total_prompts=len(prompts),
            prompts=prompts
        )
        
    except Exception as e:
        logger.error(f"Error listing prompts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list prompts: {str(e)}"
        )

@app.get("/bubble/{data_type}/{record_id}", tags=["bubble"])
async def get_bubble_record(
    data_type: str,
    record_id: str,
    environment: str = "version-test",
    api_key: str = Depends(get_api_key)
):
    """Get a Bubble record by data type and record ID"""
    
    # Validate Bubble configuration
    base_url = get_bubble_generic_base_url(data_type, environment)
    if not base_url or not settings.BUBBLE_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bubble API configuration is missing. Please check environment variables."
        )
    
    # Sanitize data_type to prevent potential issues
    safe_data_type = "".join(c for c in data_type if c.isalnum() or c in ('-', '_'))
    if safe_data_type != data_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data type format. Only alphanumeric characters, hyphens, and underscores are allowed."
        )
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # URL for the specific record
    url = f"{base_url}/{record_id}"
    
    logger.info(f"Fetching {data_type} record with ID: {record_id} from environment: {environment}")
    
    try:
        # Make GET request to Bubble API
        response = requests.get(url, headers=headers, timeout=30)
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                record_data = response.json()
                
                return {
                    "success": True,
                    "message": f"Successfully retrieved {data_type} record",
                    "data_type": data_type,
                    "record_id": record_id,
                    "environment": environment,
                    "record": record_data.get("response", record_data)
                }
                
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {json_err}")
                logger.error(f"Raw response: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to parse Bubble API response: {str(json_err)}"
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
                detail=f"Record with ID '{record_id}' not found in data type '{data_type}'"
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
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/prompts/{prompt_name}/process-template/{template_id}", tags=["prompts"], response_model=PromptTemplateProcessedResponse)
async def get_processed_prompt_with_template(
    prompt_name: str, 
    template_id: str,
    prompttemplatecustom_id: Optional[str] = None,
    environment: str = "version-test",
    api_key: str = Depends(get_api_key)
):
    """Get a prompt by name and process it with JSON template from PromptTemplate or PromptTemplateCustom record"""
    
    try:
        # Step 1: Get the prompt file content
        prompts_dir = Path("prompts")
        safe_prompt_name = "".join(c for c in prompt_name if c.isalnum() or c in ('-', '_', '.'))
        prompt_file = prompts_dir / f"{safe_prompt_name}.txt"
        
        if not prompt_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt '{prompt_name}' not found"
            )
        
        # Read the prompt content
        with open(prompt_file, 'r', encoding='utf-8') as f:
            original_prompt_content = f.read()
        
        # Step 2: Determine which data type and record ID to use
        if prompttemplatecustom_id:
            # Use PromptTemplateCustom data type
            data_type = settings.BUBBLE_PROMPTTEMPLATECUSTOM_DATA_TYPE
            record_id = prompttemplatecustom_id
            template_source = "PromptTemplateCustom"
            
            if not data_type:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="BUBBLE_PROMPTTEMPLATECUSTOM_DATA_TYPE is not configured. Please check environment variables."
                )
        else:
            # Use regular PromptTemplate data type
            data_type = settings.BUBBLE_PROMPTTEMPLATE_DATA_TYPE
            record_id = template_id
            template_source = "PromptTemplate"
            
            if not data_type:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="BUBBLE_PROMPTTEMPLATE_DATA_TYPE is not configured. Please check environment variables."
                )
        
        # Step 3: Get the template record from Bubble
        base_url = get_bubble_generic_base_url(data_type, environment)
        if not base_url or not settings.BUBBLE_API_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bubble API configuration is missing. Please check environment variables."
            )
        
        headers = {
            "Authorization": f"Bearer {settings.BUBBLE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # URL for the specific template record
        url = f"{base_url}/{record_id}"
        
        logger.info(f"Fetching {template_source} record with ID: {record_id} from environment: {environment}")
        
        # Make GET request to Bubble API
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            try:
                template_data = response.json()
                template_record = template_data.get("response", template_data)
                
                # Extract the json_template field
                json_template = template_record.get("json_template", "")
                
                if not json_template:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{template_source} record '{record_id}' does not have a json_template field or it's empty"
                    )
                
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {json_err}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to parse Bubble API response: {str(json_err)}"
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
                detail=f"{template_source} record with ID '{record_id}' not found"
            )
        else:
            logger.error(f"Unexpected status code: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Bubble API error: {response.status_code} - {response.text}"
            )
        
        # Step 4: Replace {{JSON_STRUCTURE}} placeholder in the prompt
        processed_content = original_prompt_content.replace("{{JSON_STRUCTURE}}", json_template)
        
        logger.info(f"Successfully processed prompt '{prompt_name}' with {template_source} '{record_id}'")
        
        return PromptTemplateProcessedResponse(
            success=True,
            prompt_name=prompt_name,
            template_id=record_id,  # This will be either template_id or prompttemplatecustom_id
            original_content=original_prompt_content,
            processed_content=processed_content,
            json_template=json_template,
            file_path=str(prompt_file)
        )
        
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
        logger.error(f"Error processing prompt with template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process prompt with template: {str(e)}"
        )