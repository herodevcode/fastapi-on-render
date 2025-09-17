import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary import CloudinaryVideo
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Cloudinary credentials from environment variables
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

def upload_and_trim_video():
    """
    Upload a video from URL and trim it to 0-5 seconds
    """
    # Source video URL
    video_url = "https://dd55e155247f83b96954043c82c5bcb6.cdn.bubble.io/f1758076647592x506015112424890400/10%20seconds%201920x1080.mp4"
    
    try:
        # Upload video with trimming transformation
        # start_offset: 0 seconds, end_offset: 5 seconds (duration: 5 seconds)
        result = cloudinary.uploader.upload(
            video_url,
            resource_type="video",
            public_id="trimmed_video_sample",
            video_codec="h264",
            start_offset="0",
            end_offset="5"
        )
        
        print("Upload successful!")
        print(f"Public ID: {result['public_id']}")
        print(f"Original URL: {result['url']}")
        print(f"Secure URL: {result['secure_url']}")
        print(f"Duration: {result.get('duration', 'N/A')} seconds")
        
        # Generate URL with additional transformations if needed
        trimmed_video_url = CloudinaryVideo("trimmed_video_sample").build_url(
            start_offset="0",
            end_offset="5",
            quality="auto",
            format="mp4"
        )
        
        print(f"Trimmed video URL: {trimmed_video_url}")
        
        return result
        
    except Exception as e:
        print(f"Error uploading video: {str(e)}")
        return None

def alternative_trim_method():
    """
    Alternative method: Upload first, then apply trimming transformation
    """
    video_url = "https://dd55e155247f83b96954043c82c5bcb6.cdn.bubble.io/f1758076647592x506015112424890400/10%20seconds%201920x1080.mp4"
    
    try:
        # First upload the original video
        upload_result = cloudinary.uploader.upload(
            video_url,
            resource_type="video",
            public_id="original_video_sample"
        )
        
        print("Original video uploaded!")
        
        # Create trimmed version using transformation URL
        trimmed_url = CloudinaryVideo("original_video_sample").build_url(
            start_offset="0",
            end_offset="5",
            video_codec="h264",
            quality="auto",
            format="mp4"
        )
        
        print(f"Trimmed video URL: {trimmed_url}")
        
        return trimmed_url
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    print("Cloudinary Video Trimming Sample")
    print("=" * 40)
    
    # Check if credentials are loaded
    if not all([os.getenv('CLOUDINARY_CLOUD_NAME'), os.getenv('CLOUDINARY_API_KEY'), os.getenv('CLOUDINARY_API_SECRET')]):
        print("Error: Missing Cloudinary credentials in .env file")
        print("Please create a .env file with:")
        print("CLOUDINARY_CLOUD_NAME=your_cloud_name")
        print("CLOUDINARY_API_KEY=your_api_key")
        print("CLOUDINARY_API_SECRET=your_api_secret")
        exit(1)
    
    # Method 1: Upload with trimming
    print("\nMethod 1: Upload with trimming transformation")
    result1 = upload_and_trim_video()
    
    print("\n" + "=" * 40)
    
    # Method 2: Upload then transform
    print("\nMethod 2: Upload then apply trimming transformation")
    result2 = alternative_trim_method()
