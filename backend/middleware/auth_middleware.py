# backend/middleware/auth_middleware.py
"""Authentication middleware"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
import jwt
from backend.config.settings import settings

security = HTTPBearer()

async def get_current_user(request: Request):
    """Get current authenticated user from JWT token."""
    # Simplified for demo - implement proper JWT validation
    return {"id": "demo_user", "email": "demo@spinscribe.com"}

async def verify_token(token: str):
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
