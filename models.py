from pydantic import BaseModel
from typing import List

class AttributeValue(BaseModel):
    """Model for attribute-value pair"""
    attribute: str
    value: str
    
    class Config:
        schema_extra = {
            "example": {
                "attribute": "subject",
                "value": "A complete description of the primary and secondary subjects, including their appearance, attire, and actions."
            }
        }

class PromptFieldBatchRequest(BaseModel):
    """Model for batch processing PromptField attributes"""
    attributes: List[AttributeValue]
    
    class Config:
        schema_extra = {
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
                ]
            }
        }
