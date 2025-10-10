# api/config.py
"""
Configuration Management for Spinscribe API

Loads configuration from:
1. AWS Secrets Manager (production)
2. .env file (local development)

Priority: Secrets Manager > .env > defaults
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application Settings with AWS Secrets Manager + .env fallback"""
    
    # =========================================================================
    # ENVIRONMENT
    # =========================================================================
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    DEBUG: bool = Field(default=False, description="Debug mode")
    APP_NAME: str = Field(default="Spinscribe API", description="Application name")
    
    # =========================================================================
    # AWS
    # =========================================================================
    AWS_REGION: str = Field(default="us-east-1", description="AWS region")
    AWS_SECRETS_NAME: Optional[str] = Field(
        default=None, 
        description="Secrets Manager secret name (e.g., spinscribe/production/secrets)"
    )
    
    # =========================================================================
    # DATABASE
    # =========================================================================
    DATABASE_URL: str = Field(
        default="postgresql://spinscribe_admin:password@localhost:5432/spinscribe",
        description="PostgreSQL connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    
    # =========================================================================
    # REDIS
    # =========================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=50, description="Redis max connections")
    
    # =========================================================================
    # S3 BUCKETS
    # =========================================================================
    DOCUMENTS_BUCKET: str = Field(
        default="spinscribe-dev-documents",
        description="S3 bucket for client documents"
    )
    OUTPUTS_BUCKET: str = Field(
        default="spinscribe-dev-outputs",
        description="S3 bucket for content outputs"
    )
    
    # =========================================================================
    # CREWAI
    # =========================================================================
    CREWAI_API_URL: str = Field(
        default="https://api.crewai.com/v1",
        description="CrewAI API base URL"
    )
    CREWAI_BEARER_TOKEN: str = Field(
        default="",
        description="CrewAI API Bearer token"
    )
    CREWAI_USER_BEARER_TOKEN: str = Field(
        default="",
        description="CrewAI User Bearer token"
    )
    CREWAI_BASE_URL: Optional[str] = Field(
        default=None,
        description="Alternative CrewAI base URL (alias)"
    )
    
    @field_validator('CREWAI_BASE_URL')
    @classmethod
    def set_crewai_base_url(cls, v, info):
        """Use CREWAI_API_URL if CREWAI_BASE_URL not set"""
        return v or info.data.get('CREWAI_API_URL')
    
    # =========================================================================
    # OPENAI
    # =========================================================================
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_MODEL_NAME: str = Field(default="gpt-4o", description="OpenAI model name")
    MODEL: Optional[str] = Field(default=None, description="Model alias")
    OPENAI_TEMPERATURE: float = Field(default=0.7, description="OpenAI temperature")
    
    @field_validator('MODEL')
    @classmethod
    def set_model(cls, v, info):
        """Use OPENAI_MODEL_NAME if MODEL not set"""
        return v or info.data.get('OPENAI_MODEL_NAME')
    
    # =========================================================================
    # SERPER (Web Search)
    # =========================================================================
    SERPER_API_KEY: str = Field(default="", description="Serper API key for web search")
    ENABLE_WEB_RESEARCH: bool = Field(default=True, description="Enable web research tools")
    
    # =========================================================================
    # COGNITO
    # =========================================================================
    COGNITO_USER_POOL_ID: str = Field(
        default="",
        description="AWS Cognito User Pool ID"
    )
    COGNITO_CLIENT_ID: str = Field(
        default="",
        description="AWS Cognito App Client ID"
    )
    COGNITO_REGION: Optional[str] = Field(
        default=None,
        description="Cognito region (defaults to AWS_REGION)"
    )
    
    @field_validator('COGNITO_REGION')
    @classmethod
    def set_cognito_region(cls, v, info):
        """Use AWS_REGION if COGNITO_REGION not set"""
        return v or info.data.get('AWS_REGION')
    
    # =========================================================================
    # SECURITY
    # =========================================================================
    JWT_SECRET: str = Field(
        default="your-secret-key-min-32-characters-please-change-in-production",
        description="JWT signing secret (min 32 chars)"
    )
    WEBHOOK_SECRET_TOKEN: str = Field(
        default="your-webhook-secret-token-please-change-in-production",
        description="Webhook authentication token"
    )
    
    # =========================================================================
    # API CONFIGURATION
    # =========================================================================
    API_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="API base URL (for webhook callbacks)"
    )
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated CORS origins"
    )
    
    @property
    def cors_origins_list(self) -> list:
        """Parse CORS origins into list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]
    
    # =========================================================================
    # CONTENT CREATION SETTINGS
    # =========================================================================
    DEFAULT_CONTENT_MIN_LENGTH: int = Field(
        default=1000,
        description="Minimum content length in words"
    )
    SUPPORTED_CONTENT_TYPES: str = Field(
        default="blog,landing_page,local_article",
        description="Comma-separated content types"
    )
    
    @property
    def supported_content_types_list(self) -> list:
        """Parse content types into list"""
        return [ct.strip() for ct in self.SUPPORTED_CONTENT_TYPES.split(',')]
    
    # =========================================================================
    # HITL (Human-in-the-Loop) SETTINGS
    # =========================================================================
    ENABLE_HITL_BRAND_VOICE_REVIEW: bool = Field(
        default=True,
        description="Enable brand voice checkpoint"
    )
    ENABLE_HITL_STYLE_COMPLIANCE_REVIEW: bool = Field(
        default=True,
        description="Enable style compliance checkpoint"
    )
    ENABLE_HITL_FINAL_APPROVAL: bool = Field(
        default=True,
        description="Enable final approval checkpoint"
    )
    
    # =========================================================================
    # LOGGING
    # =========================================================================
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"  # Allow extra fields from .env
    )


def load_secrets_from_aws(secret_name: str, region: str = "us-east-1") -> Dict[str, Any]:
    """
    Load secrets from AWS Secrets Manager
    
    Args:
        secret_name: Name of the secret in Secrets Manager
        region: AWS region
        
    Returns:
        Dictionary of secret key-value pairs
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        client = boto3.client('secretsmanager', region_name=region)
        
        logger.info(f"Loading secrets from AWS Secrets Manager: {secret_name}")
        response = client.get_secret_value(SecretId=secret_name)
        
        secret_string = response.get('SecretString')
        if secret_string:
            secrets = json.loads(secret_string)
            logger.info(f"✅ Successfully loaded {len(secrets)} secrets from AWS")
            return secrets
        else:
            logger.warning("Secret string is empty")
            return {}
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            logger.warning(f"Secret {secret_name} not found in AWS Secrets Manager")
        elif error_code == 'AccessDeniedException':
            logger.warning("Access denied to AWS Secrets Manager")
        else:
            logger.error(f"Error loading secrets from AWS: {e}")
        return {}
    except ImportError:
        logger.warning("boto3 not installed, skipping AWS Secrets Manager")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error loading secrets from AWS: {e}")
        return {}


def merge_configs(base_config: Settings, aws_secrets: Dict[str, Any]) -> Settings:
    """
    Merge AWS secrets into base configuration
    
    Priority: AWS Secrets > .env > defaults
    
    Args:
        base_config: Base settings from .env
        aws_secrets: Secrets from AWS Secrets Manager
        
    Returns:
        Updated Settings object
    """
    if not aws_secrets:
        return base_config
    
    # Map AWS secret keys to Settings field names
    key_mapping = {
        'database_url': 'DATABASE_URL',
        'database_host': None,  # Not directly used (part of URL)
        'database_port': None,  # Not directly used
        'database_name': None,  # Not directly used
        'database_user': None,  # Not directly used
        'database_password': None,  # Not directly used
        'redis_url': 'REDIS_URL',
        'redis_host': None,  # Not directly used
        'redis_port': None,  # Not directly used
        'crewai_api_url': 'CREWAI_API_URL',
        'crewai_bearer_token': 'CREWAI_BEARER_TOKEN',
        'crewai_user_bearer_token': 'CREWAI_USER_BEARER_TOKEN',
        'crewai_base_url': 'CREWAI_BASE_URL',
        'openai_api_key': 'OPENAI_API_KEY',
        'openai_model_name': 'OPENAI_MODEL_NAME',
        'model': 'MODEL',
        'openai_temperature': 'OPENAI_TEMPERATURE',
        'serper_api_key': 'SERPER_API_KEY',
        'documents_bucket': 'DOCUMENTS_BUCKET',
        'outputs_bucket': 'OUTPUTS_BUCKET',
        'jwt_secret': 'JWT_SECRET',
        'webhook_token': 'WEBHOOK_SECRET_TOKEN',
        'aws_region': 'AWS_REGION',
        'environment': 'ENVIRONMENT',
        'log_level': 'LOG_LEVEL',
        'enable_web_research': 'ENABLE_WEB_RESEARCH',
        'default_content_min_length': 'DEFAULT_CONTENT_MIN_LENGTH',
        'supported_content_types': 'SUPPORTED_CONTENT_TYPES',
        'enable_hitl_brand_voice_review': 'ENABLE_HITL_BRAND_VOICE_REVIEW',
        'enable_hitl_style_compliance_review': 'ENABLE_HITL_STYLE_COMPLIANCE_REVIEW',
        'enable_hitl_final_approval': 'ENABLE_HITL_FINAL_APPROVAL',
    }
    
    # Update config with AWS secrets
    updates = {}
    for aws_key, settings_key in key_mapping.items():
        if settings_key and aws_key in aws_secrets:
            value = aws_secrets[aws_key]
            # Convert string booleans to actual booleans
            if isinstance(value, str):
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
            updates[settings_key] = value
    
    if updates:
        logger.info(f"Overriding {len(updates)} settings with AWS Secrets Manager values")
        # Create new Settings instance with merged values
        return Settings(**{**base_config.model_dump(), **updates})
    
    return base_config


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached)
    
    Loading priority:
    1. AWS Secrets Manager (if AWS_SECRETS_NAME is set)
    2. .env file
    3. Default values
    
    Returns:
        Settings instance
    """
    # Load base config from .env
    base_settings = Settings()
    
    # Try to load from AWS Secrets Manager if configured
    if base_settings.AWS_SECRETS_NAME:
        logger.info(f"AWS_SECRETS_NAME detected: {base_settings.AWS_SECRETS_NAME}")
        aws_secrets = load_secrets_from_aws(
            base_settings.AWS_SECRETS_NAME,
            base_settings.AWS_REGION
        )
        
        if aws_secrets:
            return merge_configs(base_settings, aws_secrets)
        else:
            logger.warning("Failed to load AWS secrets, using .env configuration")
    else:
        logger.info("AWS_SECRETS_NAME not set, using .env configuration only")
    
    return base_settings


# Create settings instance
settings = get_settings()


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


if __name__ == "__main__":
    """Test configuration loading"""
    print("=" * 80)
    print("SPINSCRIBE CONFIGURATION")
    print("=" * 80)
    print(f"\nEnvironment: {settings.ENVIRONMENT}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"API Base URL: {settings.API_BASE_URL}")
    print(f"\nDatabase: {settings.DATABASE_URL[:50]}...")
    print(f"Redis: {settings.REDIS_URL}")
    print(f"\nCrewAI URL: {settings.CREWAI_API_URL}")
    print(f"CrewAI Token: {'*' * 20}{settings.CREWAI_BEARER_TOKEN[-8:] if settings.CREWAI_BEARER_TOKEN else 'NOT SET'}")
    print(f"\nOpenAI Model: {settings.OPENAI_MODEL_NAME}")
    print(f"OpenAI Key: {'*' * 20}{settings.OPENAI_API_KEY[-8:] if settings.OPENAI_API_KEY else 'NOT SET'}")
    print(f"\nDocuments Bucket: {settings.DOCUMENTS_BUCKET}")
    print(f"Outputs Bucket: {settings.OUTPUTS_BUCKET}")
    print(f"\nCORS Origins: {settings.cors_origins_list}")
    print(f"\nHITL Checkpoints Enabled:")
    print(f"  - Brand Voice: {settings.ENABLE_HITL_BRAND_VOICE_REVIEW}")
    print(f"  - Style Compliance: {settings.ENABLE_HITL_STYLE_COMPLIANCE_REVIEW}")
    print(f"  - Final Approval: {settings.ENABLE_HITL_FINAL_APPROVAL}")
    print(f"\nExtra fields: {[k for k in settings.model_dump() if k.lower() not in [f.lower() for f in settings.model_fields]]}")
    print("\n" + "=" * 80)