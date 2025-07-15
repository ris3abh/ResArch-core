# app/core/auth.py
"""
Authentication utilities and JWT token management.
"""
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from app.config.settings import settings

class AuthService:
    """Authentication service for user management."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password
            hashed: Hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def create_access_token(user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            user_id: User ID
            email: User email
            expires_delta: Token expiration time
            
        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        
        payload = {
            "user_id": str(user_id),
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def validate_spinutech_email(email: str) -> bool:
        """
        Validate that email belongs to Spinutech domain.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid Spinutech email, False otherwise
        """
        return email.lower().endswith(settings.SPINUTECH_EMAIL_DOMAIN.lower())
    
    @staticmethod
    def extract_user_info_from_token(token: str) -> Dict[str, Any]:
        """
        Extract user information from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with user_id and email
        """
        payload = AuthService.verify_token(token)
        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email")
        }

# Create singleton instance
auth_service = AuthService()