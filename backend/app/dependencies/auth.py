# backend/app/dependencies/auth.py (CLEAN VERSION)
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import verify_token
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    email = verify_token(token)
    
    if email is None:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_websocket_user(token: str, db: AsyncSession) -> Optional[User]:
    """Get user from JWT token for WebSocket authentication."""
    try:
        email = verify_token(token)
        if email is None:
            return None
        
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        return user
    except Exception:
        return None

# END OF FILE - NOTHING ELSE SHOULD BE HERE