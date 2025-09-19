"""
Basic authentication module for WebSocket connections
"""
import jwt
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Configuration - replace with your actual secret
JWT_SECRET = "MvtiOdzu-Atqulon2xSDmRSAA_a-uDJT9wox5dZosZTYw3dcP0ThATNmn3dP_xGohoILKULzVIk4ag2O9ImW-A"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


async def verify_token(token: str) -> Optional[Dict]:
    """
    Verify JWT token and return user information.
    
    Args:
        token: JWT token string
        
    Returns:
        User information dict if valid, None otherwise
    """
    if not token:
        return None
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        
        # Check expiration
        if 'exp' in payload:
            if datetime.fromtimestamp(payload['exp']) < datetime.utcnow():
                logger.warning("Token expired")
                return None
        
        # Return user info
        return {
            "email": payload.get("sub", "unknown@example.com"),
            "id": payload.get("user_id", "unknown"),
            "name": payload.get("name", "User")
        }
        
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


def create_access_token(user_email: str, user_id: str = None) -> str:
    """
    Create a new JWT access token.
    
    Args:
        user_email: User's email address
        user_id: Optional user ID
        
    Returns:
        JWT token string
    """
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "sub": user_email,
        "user_id": user_id or user_email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


# For development/testing - simple API key verification
async def verify_api_key(api_key: str) -> bool:
    """
    Simple API key verification for development.
    
    Args:
        api_key: API key to verify
        
    Returns:
        True if valid, False otherwise
    """
    # In production, check against database or service
    VALID_API_KEYS = {
        "dev-key-123",
        "test-key-456"
    }
    
    return api_key in VALID_API_KEYS