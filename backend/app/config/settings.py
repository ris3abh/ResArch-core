# app/config/settings.py
"""
SpinScribe Configuration Settings
Centralized configuration management for the application.
"""
import os
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """Application settings."""
    
    # Project Information
    PROJECT_NAME: str = "SpinScribe API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Multi-Agent Content Creation System for Spinutech"
    
    # Environment
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./spinscribe.db"
    
    # JWT Configuration
    JWT_SECRET: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # File Upload Configuration
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_FILES_PER_PROJECT: int = 500
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md", ".json"]
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # OpenAI Configuration (for CAMEL-AI)
    OPENAI_API_KEY: Optional[str] = None
    
    # Redis Configuration (for production)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Email Configuration
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Vector Database Configuration
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    
    # Monitoring Configuration
    PROMETHEUS_PORT: int = 8001
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Security Configuration
    SPINUTECH_EMAIL_DOMAIN: str = "@spinutech.com"
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("UPLOAD_DIR")
    @classmethod
    def create_upload_dir(cls, v):
        """Ensure upload directory exists."""
        Path(v).mkdir(exist_ok=True)
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for migrations."""
        return self.DATABASE_URL.replace("+aiosqlite", "")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

# Create settings instance
settings = Settings()

# Development overrides
if settings.is_development:
    settings.DEBUG = True
    settings.LOG_LEVEL = "DEBUG"

# Production overrides
if settings.is_production:
    settings.DEBUG = False
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required in production")