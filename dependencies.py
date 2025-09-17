from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from config import settings
import cloudinary

api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return api_key

# Note: Make sure to install cloudinary package
# pip install cloudinary
