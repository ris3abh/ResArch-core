import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "NexusTalk"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # API Settings
    API_PREFIX: str = "/api/v1"
    
    # AWS Settings
    AWS_REGION: str = "us-east-1"
    
    # Authentication
    SECRET_KEY: str = "your-secret-key-here"  # In production, use a proper secret key
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DYNAMODB_TABLE_PREFIX: str = "nexustalk-"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
