# app/core/config.py - Fixed for CAMEL compatibility
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional, Union
from functools import lru_cache
import os
import json
from pathlib import Path

class Settings(BaseSettings):
    """SpinScribe application settings with CAMEL integration"""
    
    # Application Settings
    app_name: str = "SpinScribe"
    debug: bool = True
    environment: str = "development"
    log_level: str = "INFO"
    
    # API Settings
    api_v1_str: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database Settings - Use 127.0.0.1 instead of localhost
    database_url: str = "postgresql://spinscribe:spinscribe123@127.0.0.1:5432/spinscribe"
    echo_sql: bool = False  # Set to True for SQL debugging
    
    # Redis Settings (for caching and sessions)
    redis_url: str = "redis://127.0.0.1:6379/0"
    
    # Vector Database Settings (Qdrant)
    qdrant_host: str = "127.0.0.1"
    qdrant_port: int = 6333
    qdrant_collection_prefix: str = "spinscribe_"
    vector_db_url: Optional[str] = None  # If using cloud Qdrant
    vector_db_api_key: Optional[str] = None
    
    # CAMEL / AI Model Settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_model_platform: str = "openai"
    default_model_type: str = "gpt-4o-mini"
    
    # Alternative model settings
    mistral_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Content Settings
    max_content_length: int = 10000  # Max characters for content generation
    default_language: str = "en"
    
    # Security Settings
    secret_key: str = "your-super-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # CORS Settings - Handle as Union to accept both string and list
    backend_cors_origins: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://localhost:8080", "http://localhost:8000"]
    )
    
    # Storage Settings
    storage_root_dir: str = "./storage"
    documents_dir: str = "documents"
    chat_attachments_dir: str = "chat_attachments"
    vector_db_local_dir: str = "vector_db"
    
    # Agent Settings
    max_agent_retries: int = 3
    agent_timeout_seconds: int = 30
    max_concurrent_agents: int = 5
    
    # Workflow Settings
    max_workflow_steps: int = 20
    human_checkpoint_timeout_hours: int = 24
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    
    @field_validator('backend_cors_origins')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or return list as-is"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If it's a simple comma-separated string
                return [origin.strip() for origin in v.split(',')]
        elif isinstance(v, list):
            return v
        else:
            return ["http://localhost:3000", "http://localhost:8080", "http://localhost:8000"]
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra fields from environment
    }
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        base_path = Path(self.storage_root_dir)
        directories = [
            base_path,
            base_path / "database",
            base_path / self.documents_dir,
            base_path / self.chat_attachments_dir,
            base_path / self.vector_db_local_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Create .keep files to ensure directories are tracked in git
        for directory in directories[1:]:  # Skip root storage dir
            keep_file = directory / ".keep"
            if not keep_file.exists():
                keep_file.touch()
    
    @property
    def database_path(self) -> Path:
        """Get the database file path"""
        if self.database_url.startswith("sqlite"):
            # Extract path from sqlite URL
            return Path(self.database_url.replace("sqlite:///", ""))
        return None
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() in ["development", "dev"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() in ["production", "prod"]
    
    def get_model_config(self) -> dict:
        """
        Get configuration for CAMEL model factory.
        NOTE: API keys are NOT included here - CAMEL gets them from environment variables.
        """
        config = {
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        
        # Add platform-specific configurations (no API keys)
        if self.default_model_platform == "openai":
            config.update({
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            })
        elif self.default_model_platform == "anthropic":
            config.update({
                "top_p": 1.0,
            })
        elif self.default_model_platform == "mistral":
            config.update({
                "top_p": 1.0,
                "safe_prompt": False,
            })
            
        return config
    
    def get_vector_db_config(self) -> dict:
        """Get vector database configuration"""
        if self.vector_db_url:
            return {
                "url": self.vector_db_url,
                "api_key": self.vector_db_api_key,
            }
        else:
            return {
                "host": self.qdrant_host,
                "port": self.qdrant_port,
            }
    
    def get_api_key_status(self) -> dict:
        """Check status of API keys without exposing them"""
        return {
            "openai": bool(self.openai_api_key and self.openai_api_key != "your_openai_api_key_here"),
            "anthropic": bool(self.anthropic_api_key and self.anthropic_api_key != "your_anthropic_api_key_here"),
            "mistral": bool(self.mistral_api_key and self.mistral_api_key != "your_mistral_api_key_here"),
            "google": bool(self.google_api_key and self.google_api_key != "your_google_api_key_here"),
        }
    
    def setup_environment_variables(self):
        """Ensure API keys are set as environment variables for CAMEL"""
        # Set OpenAI API key
        if self.openai_api_key and self.openai_api_key != "your_openai_api_key_here":
            os.environ['OPENAI_API_KEY'] = self.openai_api_key
        
        # Set Anthropic API key
        if self.anthropic_api_key and self.anthropic_api_key != "your_anthropic_api_key_here":
            os.environ['ANTHROPIC_API_KEY'] = self.anthropic_api_key
        
        # Set Mistral API key
        if self.mistral_api_key and self.mistral_api_key != "your_mistral_api_key_here":
            os.environ['MISTRAL_API_KEY'] = self.mistral_api_key
        
        # Set Google API key
        if self.google_api_key and self.google_api_key != "your_google_api_key_here":
            os.environ['GOOGLE_API_KEY'] = self.google_api_key

# Global settings instance
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    # Ensure environment variables are set for CAMEL
    settings.setup_environment_variables()
    return settings

# Export settings for easy import
settings = get_settings()