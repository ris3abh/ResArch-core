# app/api/v1/auth.py
"""
Authentication API routes for user management.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.auth import auth_service
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserUpdate, UserResponse, TokenResponse
from app.api.deps import get_current_active_user
from app.config.settings import settings

router = APIRouter()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new Spinutech user.
    
    - **email**: Must be a valid @spinutech.com email
    - **password**: Must be at least 8 characters with complexity requirements
    - **first_name**: User's first name
    - **last_name**: User's last name
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        password_hash=auth_service.hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Return user response
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        full_name=user.full_name,
        is_spinutech_employee=user.is_spinutech_employee
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access token.
    
    - **email**: Registered Spinutech email
    - **password**: User's password
    """
    # Get user by email
    result = await db.execute(
        select(User).where(User.email == login_data.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    # Verify user and password
    if not user or not auth_service.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create access token
    access_token = auth_service.create_access_token(
        user_id=user.id,
        email=user.email
    )
    
    # Return token response
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,  # Convert hours to seconds
        user=UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
            full_name=user.full_name,
            is_spinutech_employee=user.is_spinutech_employee
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user profile information.
    
    Requires valid authentication token.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        full_name=current_user.full_name,
        is_spinutech_employee=current_user.is_spinutech_employee
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile.
    
    - **first_name**: Update first name (optional)
    - **last_name**: Update last name (optional)
    """
    # Update user fields if provided
    if user_update.first_name is not None:
        current_user.first_name = user_update.first_name
    
    if user_update.last_name is not None:
        current_user.last_name = user_update.last_name
    
    # Save changes
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        full_name=current_user.full_name,
        is_spinutech_employee=current_user.is_spinutech_employee
    )


@router.post("/logout")
async def logout():
    """
    Logout current user.
    
    Note: Since we're using stateless JWT tokens, logout is handled client-side
    by discarding the token. This endpoint exists for API consistency.
    """
    return {"message": "Successfully logged out"}


@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Refresh access token.
    
    Returns a new token with extended expiration time.
    """
    # Create new access token
    access_token = auth_service.create_access_token(
        user_id=current_user.id,
        email=current_user.email
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRATION_HOURS * 3600
    }


@router.get("/verify")
async def verify_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Verify if current token is valid.
    
    Returns user information if token is valid.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "expires_in": settings.JWT_EXPIRATION_HOURS * 3600
    }