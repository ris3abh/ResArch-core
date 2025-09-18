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
    MAX_FILE_SIZE: int = Field(default=52428800)  # 50MB
    UPLOAD_DIR: str = Field(default="./storage/uploads")
    ALLOWED_EXTENSIONS: List[str] = Field(default=[".pdf", ".docx", ".txt", ".md"])
    
    # WebSocket Configuration
    WEBSOCKET_PING_INTERVAL: int = Field(default=25)  # seconds - Send ping every 25 seconds
    WEBSOCKET_PING_TIMEOUT: int = Field(default=60)   # seconds - Wait 60 seconds for pong response
    WEBSOCKET_CONNECTION_TIMEOUT: int = Field(default=30)  # seconds - Connection establishment timeout
    WEBSOCKET_MAX_SIZE: int = Field(default=16777216)  # 16MB message size limit
    WEBSOCKET_MAX_QUEUE: int = Field(default=32)  # Maximum number of queued messages
    WEBSOCKET_KEEPALIVE_TIMEOUT: int = Field(default=30)  # Keep connection alive for 30 seconds
    
    # Workflow Configuration
    WORKFLOW_DEFAULT_TIMEOUT: int = Field(default=600)  # 10 minutes default workflow timeout
    WORKFLOW_CHECKPOINT_TIMEOUT: int = Field(default=300)  # 5 minutes checkpoint timeout
    WORKFLOW_MAX_RETRIES: int = Field(default=3)  # Maximum workflow retry attempts
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # This allows extra fields in .env to be ignored

settings = Settings()