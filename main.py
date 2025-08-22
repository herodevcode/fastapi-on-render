from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader

app = FastAPI()

# Define the API key header
api_key_header = APIKeyHeader(name="X-API-Key")

# Define the expected API key (in production, use environment variables)
API_KEY = "your-secret-api-key"

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return api_key

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None, api_key: str = Depends(get_api_key)):
    return {"item_id": item_id, "q": q}