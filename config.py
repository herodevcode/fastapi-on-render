from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Model config to load from .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Your API Key
    API_KEY: str = "your-secret-api-key"

    # Bubble API Configuration
    BUBBLE_APP_DOMAIN: str
    BUBBLE_API_TOKEN: str
    BUBBLE_SAMPLE_DATA_TYPE: str = "sample"
    BUBBLE_SAMPLE2_DATA_TYPE: str = "sample2"
    BUBBLE_PROMPTFIELD_DATA_TYPE: str = "promptfield"
    BUBBLE_GENERATEDPROMPT_DATA_TYPE: str = "generatedprompt"
    BUBBLE_API_REQUEST_DATA_TYPE: str = "api_request"
    BUBBLE_PROMPTTEMPLATE_DATA_TYPE: str = "prompttemplate"
    BUBBLE_ENVIRONMENT: str = "production"
    BUBBLE_PROMPTTEMPLATECUSTOM_DATA_TYPE: str = "prompttemplatecustom"

    # Cloudinary configuration
    CLOUDINARY_CLOUD_NAME: str = None
    CLOUDINARY_API_KEY: str = None
    CLOUDINARY_API_SECRET: str = None

# Create a single instance to be imported in other files
settings = Settings()
