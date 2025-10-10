# api/config.py
import os
import json
import boto3
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Spinscribe API"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # AWS
    AWS_REGION: str = "us-east-1"
    
    # Database
    DATABASE_URL: str = ""
    
    # Redis
    REDIS_URL: str = ""
    
    # S3
    DOCUMENTS_BUCKET: str = ""
    OUTPUTS_BUCKET: str = ""
    
    # CrewAI
    CREWAI_API_URL: str = ""
    CREWAI_BEARER_TOKEN: str = ""
    CREWAI_USER_BEARER_TOKEN: str = ""
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    
    # Auth
    JWT_SECRET: str = ""
    WEBHOOK_SECRET_TOKEN: str = ""
    
    # Load Balancer URL (for webhook callbacks)
    API_BASE_URL: str = "http://spinscribe-production-alb-1661012357.us-east-1.elb.amazonaws.com"
    
    class Config:
        env_file = ".env"

def load_secrets_from_aws():
    """Load secrets from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    
    try:
        response = client.get_secret_value(
            SecretId='spinscribe/production/secrets'
        )
        secrets = json.loads(response['SecretString'])
        
        # Set environment variables
        os.environ['DATABASE_URL'] = secrets['database_url']
        os.environ['REDIS_URL'] = secrets['redis_url']
        os.environ['DOCUMENTS_BUCKET'] = secrets['documents_bucket']
        os.environ['OUTPUTS_BUCKET'] = secrets['outputs_bucket']
        os.environ['CREWAI_API_URL'] = secrets['crewai_api_url']
        os.environ['CREWAI_BEARER_TOKEN'] = secrets['crewai_bearer_token']
        os.environ['CREWAI_USER_BEARER_TOKEN'] = secrets['crewai_user_bearer_token']
        os.environ['OPENAI_API_KEY'] = secrets['openai_api_key']
        os.environ['SERPER_API_KEY'] = secrets['serper_api_key']
        
        # Get JWT and webhook secrets
        jwt_secret_arn = secrets['jwt_secret']
        webhook_token_arn = secrets['webhook_token']
        
        # Fetch the actual secret values
        jwt_response = client.get_secret_value(SecretId=jwt_secret_arn)
        jwt_data = json.loads(jwt_response['SecretString'])
        os.environ['JWT_SECRET'] = list(jwt_data.values())[0]
        
        webhook_response = client.get_secret_value(SecretId=webhook_token_arn)
        webhook_data = json.loads(webhook_response['SecretString'])
        os.environ['WEBHOOK_SECRET_TOKEN'] = list(webhook_data.values())[0]
        
        print("✅ Secrets loaded from AWS Secrets Manager")
        
    except Exception as e:
        print(f"⚠️  Could not load secrets from AWS: {e}")
        print("   Using environment variables instead")

# Load secrets on module import
load_secrets_from_aws()

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()