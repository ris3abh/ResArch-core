# api/dependencies.py
"""
Dependency Injection for FastAPI

Provides reusable dependencies for:
- Database sessions
- Authentication (Cognito JWT validation)
- Current user retrieval
- Service instances
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import logging

from api.database import SessionLocal
from api.config import settings
from api.models.user import User

logger = logging.getLogger(__name__)

# Security scheme for JWT bearer tokens
security = HTTPBearer()


# =============================================================================
# DATABASE SESSION
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    
    Yields:
        SQLAlchemy Session
        
    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# AUTHENTICATION
# =============================================================================

def decode_cognito_token(token: str) -> dict:
    """
    Decode and validate Cognito JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        # For Cognito, we should verify the token signature
        # In production, you'd fetch Cognito public keys and verify
        # For now, we'll decode without verification (development only)
        
        # TODO: Implement proper Cognito token verification
        # See: https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html
        
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_signature": False}  # TODO: Enable in production
        )
        return payload
        
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_cognito_sub(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract Cognito sub (user ID) from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Cognito sub (unique user identifier)
        
    Raises:
        HTTPException: If token is invalid or sub not found
    """
    token = credentials.credentials
    payload = decode_cognito_token(token)
    
    cognito_sub = payload.get("sub")
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return cognito_sub


async def get_current_user(
    cognito_sub: str = Depends(get_current_user_cognito_sub),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from database.
    
    Args:
        cognito_sub: Cognito sub from JWT token
        db: Database session
        
    Returns:
        User model instance
        
    Raises:
        HTTPException: If user not found or inactive
    """
    user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please complete signup."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    
    Useful for endpoints that have optional authentication.
    
    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session
        
    Returns:
        User instance if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_cognito_token(token)
        cognito_sub = payload.get("sub")
        
        if cognito_sub:
            user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
            if user and user.is_active:
                return user
    except Exception as e:
        logger.warning(f"Optional auth failed: {e}")
    
    return None


# =============================================================================
# WEBHOOK AUTHENTICATION
# =============================================================================

async def verify_webhook_token(
    authorization: Optional[str] = Header(None)
) -> bool:
    """
    Verify webhook request is from CrewAI.
    
    Checks the Authorization header for bearer token.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        True if valid
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        logger.error("Webhook request missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        logger.error(f"Invalid Authorization header format: {authorization}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    # Verify token matches our webhook secret
    if token != settings.WEBHOOK_SECRET_TOKEN:
        logger.error("Invalid webhook token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook token"
        )
    
    return True


# =============================================================================
# SERVICE DEPENDENCIES
# =============================================================================

def get_s3_service():
    """
    Get S3 service instance.
    
    Returns:
        S3Service instance
    """
    from api.services.s3 import S3Service
    return S3Service()


def get_crewai_service():
    """
    Get CrewAI service instance.
    
    Returns:
        CrewAIService instance
    """
    from api.services.crewai import CrewAIService
    return CrewAIService()


def get_cognito_service():
    """
    Get Cognito service instance.
    
    Returns:
        CognitoService instance
    """
    from api.services.cognito import CognitoService
    return CognitoService()


# =============================================================================
# PAGINATION
# =============================================================================

class PaginationParams:
    """
    Reusable pagination parameters.
    
    Example:
        @app.get("/items")
        def get_items(pagination: PaginationParams = Depends()):
            skip = pagination.skip
            limit = pagination.limit
    """
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
    ):
        self.page = max(1, page)
        self.page_size = min(100, max(1, page_size))  # Max 100 items per page
        self.skip = (self.page - 1) * self.page_size
        self.limit = self.page_size


# =============================================================================
# ROLE-BASED ACCESS CONTROL (Future Enhancement)
# =============================================================================

class RoleChecker:
    """
    Dependency to check user roles.
    
    Example:
        require_admin = RoleChecker(['admin'])
        
        @app.delete("/users/{id}")
        def delete_user(user: User = Depends(require_admin)):
            ...
    """
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user.role}' not authorized for this action"
            )
        return user


# Predefined role checkers
require_admin = RoleChecker(['admin'])
require_client = RoleChecker(['client', 'admin'])