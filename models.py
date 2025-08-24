from pydantic import BaseModel
from typing import List, Literal, Optional

class AttributeValue(BaseModel):
    """Model for attribute-value pair"""
    attribute: str
    value: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "attribute": "subject",
                "value": "A complete description of the primary and secondary subjects, including their appearance, attire, and actions."
            }
        }
    }

class PromptFieldBatchRequest(BaseModel):
    """Model for batch processing PromptField attributes"""
    attributes: List[AttributeValue]
    bubble_environment: Literal["production", "version-test"] = "version-test"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "attributes": [
                    {
                        "attribute": "subject",
                        "value": "A complete description of the primary and secondary subjects, including their appearance, attire, and actions."
                    },
                    {
                        "attribute": "composition", 
                        "value": "A description of the shot type, camera angle, and framing, including layout details like foreground/background and use of compositional rules."
                    },
                    {
                        "attribute": "environment",
                        "value": "A description of the location, time of day, weather, and overall atmosphere."
                    },
                    {
                        "attribute": "style",
                        "value": "A description of the medium (e.g., photo, painting), artistic look, lighting, color palette, and any technical details like depth of field or film grain."
                    }
                ],
                "bubble_environment": "version-test"
            }
        }
    }

class BubbleRecordCreate(BaseModel):
    """Model for creating a new record in Bubble database"""
    name: str
    description: str
    bubble_environment: Literal["production", "version-test"] = "version-test"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Sample Record",
                "description": "This is a sample description for the record",
                "bubble_environment": "version-test"
            }
        }
    }

class BubbleRecordBatchCreate(BaseModel):
    """Model for batch creating records in Bubble database"""
    records: List[BubbleRecordCreate]
    bubble_environment: Literal["production", "version-test"] = "version-test"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "records": [
                    {
                        "name": "Sample Record 1",
                        "description": "First sample record description",
                        "bubble_environment": "version-test"
                    },
                    {
                        "name": "Sample Record 2", 
                        "description": "Second sample record description",
                        "bubble_environment": "version-test"
                    }
                ],
                "bubble_environment": "version-test"
            }
        }
    }

class BubbleRecordUpdateListField(BaseModel):
    """Model for updating a list field in a Bubble record"""
    sample2_id: str
    bubble_environment: Literal["production", "version-test"] = "version-test"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sample2_id": "1755912306378x688197843685340200",
                "bubble_environment": "version-test"
            }
        }
    }

class GeneratedPromptCreate(BaseModel):
    """Model for creating a new GeneratedPrompt record"""
    promptfield_id: str
    value: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "promptfield_id": "1755923027740x713483466029849500",
                "value": "subject is here"
            }
        }
    }

class GeneratedPromptBatchCreate(BaseModel):
    """Model for batch creating GeneratedPrompt records"""
    records: List[GeneratedPromptCreate]
    bubble_environment: Literal["production", "version-test"] = "version-test"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "records": [
                    {
                        "promptfield_id": "1755923027740x713483466029849500",
                        "value": "subject is here"
                    },
                    {
                        "promptfield_id": "1755923028308x655772690012022000",
                        "value": "composition is here"
                    }
                ],
                "bubble_environment": "version-test"
            }
        }
    }

class PromptFieldAndGeneratedPromptBatchCreate(BaseModel):
    """Model for batch creating PromptFields and corresponding GeneratedPrompts"""
    attributes: List[AttributeValue]
    bubble_environment: Literal["production", "version-test"] = "version-test"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "attributes": [
                    {
                        "attribute": "subject",
                        "value": "A complete description of the primary and secondary subjects, including their appearance, attire, and actions."
                    },
                    {
                        "attribute": "composition", 
                        "value": "A description of the shot type, camera angle, and framing, including layout details like foreground/background and use of compositional rules."
                    },
                    {
                        "attribute": "environment",
                        "value": "A description of the location, time of day, weather, and overall atmosphere."
                    },
                    {
                        "attribute": "style",
                        "value": "A description of the medium (e.g., photo, painting), artistic look, lighting, color palette, and any technical details like depth of field or film grain."
                    }
                ],
                "bubble_environment": "version-test"
            }
        }
    }

class ApiRequestUpdate(BaseModel):
    """Model for updating an API request record. Use: 1755878226412x138224706807443800"""
    json_prompt: List[AttributeValue]
    generated_prompts: List[str]
    bubble_environment: Literal["production", "version-test"] = "version-test"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "json_prompt": [
                    {
                        "attribute": "subject",
                        "value": "A complete description of the primary and secondary subjects, including their appearance, attire, and actions."
                    },
                    {
                        "attribute": "composition",
                        "value": "A description of the shot type, camera angle, and framing, including layout details like foreground/background and use of compositional rules."
                    },
                    {
                        "attribute": "environment",
                        "value": "A description of the location, time of day, weather, and overall atmosphere."
                    },
                    {
                        "attribute": "style",
                        "value": "A description of the medium (e.g., photo, painting), artistic look, lighting, color palette, and any technical details like depth of field or film grain."
                    }
                ],
                "generated_prompts": [
                    "1755929474459x247733095409041760",
                    "1755929474457x665050477953099000",
                    "1755929474456x950032919292906900",
                    "1755929474454x672506176960183700"
                ],
                "bubble_environment": "version-test"
            }
        }
    }

class ApiRequestProcessAndUpdate(BaseModel):
    """Model for processing attributes to create PromptFields/GeneratedPrompts and updating an API request record"""
    request_id: str
    attributes: List[AttributeValue]
    bubble_environment: Literal["production", "version-test"] = "version-test"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "request_id": "1755878226412x138224706807443800",
                "attributes": [
                    {
                        "attribute": "subject",
                        "value": "A complete description of the primary and secondary subjects, including their appearance, attire, and actions."
                    },
                    {
                        "attribute": "composition",
                        "value": "A description of the shot type, camera angle, and framing, including layout details like foreground/background and use of compositional rules."
                    },
                    {
                        "attribute": "environment",
                        "value": "A description of the location, time of day, weather, and overall atmosphere."
                    },
                    {
                        "attribute": "style",
                        "value": "A description of the medium (e.g., photo, painting), artistic look, lighting, color palette, and any technical details like depth of field or film grain."
                    }
                ],
                "bubble_environment": "version-test"
            }
        }
    }

class PromptResponse(BaseModel):
    """Model for prompt file response"""
    success: bool
    prompt_name: str
    content: str
    file_path: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "prompt_name": "short",
                "content": "You are a world-class visual analysis engine.\n\nYour task is to deconstruct a provided image or video and return a structured JSON object describing its visual characteristics...",
                "file_path": "prompts/short.txt"
            }
        }
    }

class PromptListItem(BaseModel):
    """Model for individual prompt item in list"""
    name: str
    file_path: str
    size_chars: Optional[int] = None
    preview: Optional[str] = None
    error: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "detailed",
                "file_path": "prompts/detailed.txt",
                "size_chars": 542,
                "preview": "You are a world-class visual analysis engine.\n\nYour task is to meticulously deconstruct a provided image..."
            }
        }
    }

class PromptListResponse(BaseModel):
    """Model for listing all available prompts"""
    success: bool
    total_prompts: int
    prompts: List[PromptListItem]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "total_prompts": 2,
                "prompts": [
                    {
                        "name": "short",
                        "file_path": "prompts/short.txt",
                        "size_chars": 498,
                        "preview": "You are a world-class visual analysis engine.\n\nYour task is to deconstruct a provided image or video..."
                    },
                    {
                        "name": "detailed",
                        "file_path": "prompts/detailed.txt",
                        "size_chars": 542,
                        "preview": "You are a world-class visual analysis engine.\n\nYour task is to meticulously deconstruct a provided image..."
                    }
                ]
            }
        }
    }

class PromptTemplateProcessedResponse(BaseModel):
    """Model for processed prompt response with template substitution"""
    success: bool
    prompt_name: str
    template_id: str
    original_content: str
    processed_content: str
    json_template: str
    file_path: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "prompt_name": "short",
                "template_id": "1755923027740x713483466029849500",
                "original_content": "You are a visual analysis engine. Return a JSON object with this structure: {{JSON_STRUCTURE}}",
                "processed_content": "You are a visual analysis engine. Return a JSON object with this structure: {\"subject\": \"string\", \"composition\": \"string\"}",
                "json_template": "{\"subject\": \"string\", \"composition\": \"string\"}",
                "file_path": "prompts/short.txt"
            }
        }
    }
