from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Model config to load from .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Your API Key
    API_KEY: str = "your-secret-api-key"

    # Bubble API Configuration
    BUBBLE_APP_DOMAIN: str
    BUBBLE_API_TOKEN: str
    BUBBLE_SAMPLE_DATA_TYPE: str
    BUBBLE_SAMPLE2_DATA_TYPE: str
    BUBBLE_PROMPTFIELD_DATA_TYPE: str
    BUBBLE_GENERATEDPROMPT_DATA_TYPE: str
    BUBBLE_API_REQUEST_DATA_TYPE: str
    BUBBLE_ENVIRONMENT: str = "production"

# Create a single instance to be imported in other files
settings = Settings()
