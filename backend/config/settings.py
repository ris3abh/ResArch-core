# backend/config/settings.py
"""
Backend-specific settings that integrate with core Spinscribe configuration.
FIXED: Now properly allows all SpinScribe environment variables.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Any

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
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
    DEFAULT_WORKFLOW_TIMEOUT = int(os.getenv("DEFAULT_WORKFLOW_TIMEOUT", "600"))
    ENABLE_HUMAN_CHECKPOINTS = os.getenv("ENABLE_HUMAN_CHECKPOINTS", "true").lower() == "true"

class Settings(BaseSettings):
    """Backend application settings with full SpinScribe support."""
    
    # ==========================================
    # CORE APPLICATION SETTINGS
    # ==========================================
    APP_NAME: str = Field(default="Spinscribe Backend")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=True)
    API_V1_STR: str = Field(default="/api/v1")
    ENVIRONMENT: str = Field(default="development")
    
    # ==========================================
    # DATABASE CONFIGURATION  
    # ==========================================
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:password@localhost:5432/spinscribe")
    
    # ==========================================
    # SECURITY CONFIGURATION
    # ==========================================
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # ==========================================
    # CORS CONFIGURATION
    # ==========================================
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://localhost:8080"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    
    # ==========================================
    # FILE UPLOAD CONFIGURATION
    # ==========================================
    MAX_FILE_SIZE: int = Field(default=52428800)
    UPLOAD_DIR: str = Field(default="./storage/uploads")
    ALLOWED_EXTENSIONS: List[str] = Field(default=[".pdf", ".docx", ".txt", ".md"])
    
    # ==========================================
    # SPINSCRIBE CONFIGURATION
    # ==========================================
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    MODEL_PLATFORM: str = Field(default="openai")
    MODEL_TYPE: str = Field(default="gpt-4o-mini")
    MODEL_TEMPERATURE: float = Field(default=0.7)
    MODEL_MAX_TOKENS: int = Field(default=4096)
    MODEL_TOP_P: float = Field(default=1.0)
    
    # Workflow Configuration
    DEFAULT_TASK_ID: str = Field(default="spinscribe-content-task")
    AGENT_TIMEOUT: int = Field(default=300)
    MAX_WORKFLOW_RETRIES: int = Field(default=3)
    MAX_CONCURRENT_AGENTS: int = Field(default=2)
    
    # Memory Configuration
    MEMORY_TYPE: str = Field(default="contextual")
    ENABLE_MEMORY_PERSISTENCE: bool = Field(default=True)
    
    # Human Layer Integration
    ENABLE_HUMAN_TOOLKIT: bool = Field(default=True)
    HUMAN_INPUT_TIMEOUT: int = Field(default=600)
    HUMAN_INTERACTION_MODE: str = Field(default="console")
    
    # Vector Database Configuration (Qdrant)
    QDRANT_HOST: str = Field(default="localhost")
    QDRANT_PORT: int = Field(default=6333)
    QDRANT_COLLECTION_NAME: str = Field(default="spinscribe_knowledge")
    QDRANT_VECTOR_DIM: int = Field(default=1536)
    
    # Document Processing
    ENABLE_RAG: bool = Field(default=True)
    DOCUMENT_PROCESSING_TIMEOUT: int = Field(default=300)
    MAX_DOCUMENT_SIZE: int = Field(default=10485760)  # 10MB
    MAX_DOCUMENTS_PER_PROJECT: int = Field(default=50)
    
    # Logging Configuration
    ENABLE_FILE_LOGGING: bool = Field(default=True)
    VERBOSE_LOGGING: bool = Field(default=False)
    DEBUG_MODE: bool = Field(default=False)
    
    # Performance Configuration
    ENABLE_CACHING: bool = Field(default=True)
    CACHE_TTL: int = Field(default=3600)
    ENABLE_OUTPUT_PERSISTENCE: bool = Field(default=True)
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # ✅ FIXED: Now allows extra environment variables
        
        # Custom field validation
        @staticmethod
        def parse_env_var(field_name: str, raw_value: Any) -> Any:
            """Custom parsing for environment variables."""
            if field_name == "ALLOWED_EXTENSIONS" and isinstance(raw_value, str):
                # Parse JSON-like string for extensions
                import json
                try:
                    return json.loads(raw_value)
                except json.JSONDecodeError:
                    # Fallback to comma-separated
                    return [ext.strip() for ext in raw_value.split(",")]
            
            if field_name == "CORS_ORIGINS" and isinstance(raw_value, str):
                # Parse comma-separated origins
                return [origin.strip() for origin in raw_value.split(",")]
            
            # Boolean parsing
            if raw_value == "true":
                return True
            elif raw_value == "false":
                return False
            
            # Try to convert to appropriate type
            try:
                # Try integer first
                if isinstance(raw_value, str) and raw_value.isdigit():
                    return int(raw_value)
                
                # Try float
                if isinstance(raw_value, str) and "." in raw_value:
                    return float(raw_value)
                    
            except ValueError:
                pass
            
            return raw_value

# Create settings instance
settings = Settings()

# Validate critical settings
def validate_settings():
    """Validate that critical settings are properly configured."""
    
    print("🔍 Validating SpinScribe configuration...")
    
    # Check OpenAI API key
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-dummy"):
        print("⚠️ WARNING: No valid OpenAI API key found. SpinScribe will run in mock mode.")
    else:
        print("✅ OpenAI API key configured")
    
    # Check database URL
    if "postgresql" not in settings.DATABASE_URL:
        print("⚠️ WARNING: Non-PostgreSQL database detected. Some features may not work.")
    else:
        print("✅ PostgreSQL database configured")
    
    # Check upload directory
    upload_path = Path(settings.UPLOAD_DIR)
    try:
        upload_path.mkdir(parents=True, exist_ok=True)
        print("✅ Upload directory configured")
    except Exception as e:
        print(f"⚠️ WARNING: Could not create upload directory: {e}")
    
    print("🎉 SpinScribe configuration validation complete!")

# Auto-validate on import
if __name__ != "__main__":
    validate_settings()