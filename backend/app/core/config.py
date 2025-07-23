from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application
    APP_NAME: str = Field(default="Spinscribe Backend")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=True)
    API_V1_STR: str = Field(default="/api/v1")
    
    # Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:password@localhost:5432/spinscribe")
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://localhost:8080"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    
    # File Upload
    MAX_FILE_SIZE: int = Field(default=52428800)
    UPLOAD_DIR: str = Field(default="./storage/uploads")
    ALLOWED_EXTENSIONS: List[str] = Field(default=[".pdf", ".docx", ".txt", ".md"])
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # This allows extra fields in .env to be ignored

settings = Settings()
