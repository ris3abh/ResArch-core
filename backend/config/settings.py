"""
Backend-specific settings that integrate with core Spinscribe configuration.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings

# Add parent directory to Python path for shared config
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from config.loader import load_environment
    from config.shared import (
        OPENAI_MODEL, 
        OPENAI_MAX_TOKENS, 
        DEFAULT_WORKFLOW_TIMEOUT,
        ENABLE_HUMAN_CHECKPOINTS
    )
    
    # Load environment variables
    load_environment()
    
except ImportError as e:
    print(f"Warning: Could not import shared config: {e}")
    # Fallback to environment variables
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
    DEFAULT_WORKFLOW_TIMEOUT = int(os.getenv("DEFAULT_WORKFLOW_TIMEOUT", "600"))
    ENABLE_HUMAN_CHECKPOINTS = os.getenv("ENABLE_HUMAN_CHECKPOINTS", "true").lower() == "true"

class Settings(BaseSettings):
    """Backend application settings."""
    
    # Application
    APP_NAME: str = Field(default="Spinscribe Backend")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    API_V1_STR: str = Field(default="/api/v1")
    
    # Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:password@localhost:5432/spinscribe")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379")
    
    # Security
    SECRET_KEY: str = Field(default="change-this-secret-key")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    
    # File Upload
    MAX_FILE_SIZE: int = Field(default=52428800)  # 50MB
    UPLOAD_DIR: str = Field(default="./storage/uploads")
    
    # Shared Configuration (from core Spinscribe)
    OPENAI_MODEL: str = Field(default=OPENAI_MODEL)
    OPENAI_MAX_TOKENS: int = Field(default=OPENAI_MAX_TOKENS)
    DEFAULT_WORKFLOW_TIMEOUT: int = Field(default=DEFAULT_WORKFLOW_TIMEOUT)
    ENABLE_HUMAN_CHECKPOINTS: bool = Field(default=ENABLE_HUMAN_CHECKPOINTS)
    
    # CAMEL Integration
    SPINSCRIBE_ROOT_DIR: str = Field(default="../")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings instance
settings = Settings()