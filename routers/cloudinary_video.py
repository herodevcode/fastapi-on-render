import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary import CloudinaryVideo
import os
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from dependencies import get_api_key
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cloudinary", tags=["cloudinary"])

# Configure Cloudinary credentials from environment variables
def configure_cloudinary():
    """Configure Cloudinary with environment variables"""
    if not all([settings.CLOUDINARY_CLOUD_NAME, settings.CLOUDINARY_API_KEY, settings.CLOUDINARY_API_SECRET]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary credentials not configured. Please check environment variables."
        )
    
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )

class VideoTrimRequest(BaseModel):
    video_url: HttpUrl
    public_id: str
    start_offset: str = "0"
    end_offset: str = "5"
    video_codec: str = "h264"
    quality: str = "auto"
    format: str = "mp4"

class VideoTrimResponse(BaseModel):
    success: bool
    message: str
    public_id: str
    original_url: str
    secure_url: str
    trimmed_url: str
    duration: Optional[float] = None

class VideoTransformRequest(BaseModel):
    public_id: str
    start_offset: str = "0"
    end_offset: str = "5"
    video_codec: str = "h264"
    quality: str = "auto"
    format: str = "mp4"

class VideoTransformResponse(BaseModel):
    success: bool
    message: str
    public_id: str
    trimmed_url: str

@router.post("/video/upload-and-trim", response_model=VideoTrimResponse)
async def upload_and_trim_video(
    request: VideoTrimRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Upload a video from URL and trim it to specified duration
    """
    configure_cloudinary()
    
    try:
        logger.info(f"Uploading and trimming video from: {request.video_url}")
        
        # Upload video with trimming transformation
        result = cloudinary.uploader.upload(
            str(request.video_url),
            resource_type="video",
            public_id=request.public_id,
            video_codec=request.video_codec,
            start_offset=request.start_offset,
            end_offset=request.end_offset
        )
        
        logger.info(f"Upload successful for public_id: {result['public_id']}")
        
        # Generate URL with additional transformations
        trimmed_video_url = CloudinaryVideo(request.public_id).build_url(
            start_offset=request.start_offset,
            end_offset=request.end_offset,
            quality=request.quality,
            format=request.format
        )
        
        return VideoTrimResponse(
            success=True,
            message="Video uploaded and trimmed successfully",
            public_id=result['public_id'],
            original_url=result['url'],
            secure_url=result['secure_url'],
            trimmed_url=trimmed_video_url,
            duration=result.get('duration')
        )
        
    except Exception as e:
        logger.error(f"Error uploading and trimming video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload and trim video: {str(e)}"
        )

@router.post("/video/upload", response_model=dict)
async def upload_video(
    video_url: HttpUrl,
    public_id: str,
    api_key: str = Depends(get_api_key)
):
    """
    Upload a video from URL without trimming
    """
    configure_cloudinary()
    
    try:
        logger.info(f"Uploading video from: {video_url}")
        
        # Upload the original video
        upload_result = cloudinary.uploader.upload(
            str(video_url),
            resource_type="video",
            public_id=public_id
        )
        
        logger.info(f"Upload successful for public_id: {upload_result['public_id']}")
        
        return {
            "success": True,
            "message": "Video uploaded successfully",
            "public_id": upload_result['public_id'],
            "original_url": upload_result['url'],
            "secure_url": upload_result['secure_url'],
            "duration": upload_result.get('duration')
        }
        
    except Exception as e:
        logger.error(f"Error uploading video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )

@router.post("/video/transform", response_model=VideoTransformResponse)
async def transform_video(
    request: VideoTransformRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Apply trimming transformation to an already uploaded video
    """
    configure_cloudinary()
    
    try:
        logger.info(f"Applying transformation to video: {request.public_id}")
        
        # Create trimmed version using transformation URL
        trimmed_url = CloudinaryVideo(request.public_id).build_url(
            start_offset=request.start_offset,
            end_offset=request.end_offset,
            video_codec=request.video_codec,
            quality=request.quality,
            format=request.format
        )
        
        logger.info(f"Transformation URL generated: {trimmed_url}")
        
        return VideoTransformResponse(
            success=True,
            message="Video transformation URL generated successfully",
            public_id=request.public_id,
            trimmed_url=trimmed_url
        )
        
    except Exception as e:
        logger.error(f"Error generating transformation URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate transformation URL: {str(e)}"
        )

@router.get("/video/info/{public_id}")
async def get_video_info(
    public_id: str,
    api_key: str = Depends(get_api_key)
):
    """
    Get information about an uploaded video
    """
    configure_cloudinary()
    
    try:
        logger.info(f"Getting video info for: {public_id}")
        
        # Get video resource information
        result = cloudinary.api.resource(public_id, resource_type="video")
        
        return {
            "success": True,
            "message": "Video information retrieved successfully",
            "public_id": result['public_id'],
            "format": result.get('format'),
            "duration": result.get('duration'),
            "width": result.get('width'),
            "height": result.get('height'),
            "bytes": result.get('bytes'),
            "url": result.get('url'),
            "secure_url": result.get('secure_url'),
            "created_at": result.get('created_at')
        }
        
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get video information: {str(e)}"
        )
