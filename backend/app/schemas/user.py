# app/schemas/user.py
"""
Pydantic schemas for User API validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.config.settings import settings

# Request Schemas
class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    
    @field_validator('email')
    @classmethod
    def validate_spinutech_email(cls, v):
        """Validate that email belongs to Spinutech domain."""
        if not v.lower().endswith(settings.SPINUTECH_EMAIL_DOMAIN.lower()):
            raise ValueError(f'Only {settings.SPINUTECH_EMAIL_DOMAIN} emails are allowed')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """Schema for user profile updates."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)


# Response Schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""
    id: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class UserResponse(UserBase):
    """Schema for user profile responses."""
    last_login: Optional[datetime] = None
    full_name: str
    is_spinutech_employee: bool
    
    @field_validator('full_name', mode='before')
    @classmethod
    def compute_full_name(cls, v, info):
        """Compute full name from first_name and last_name."""
        if hasattr(info.data, 'first_name') and hasattr(info.data, 'last_name'):
            return f"{info.data['first_name']} {info.data['last_name']}"
        return v


class UserListResponse(UserBase):
    """Schema for user list responses (minimal data)."""
    full_name: str


# Authentication Response Schemas
class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class TokenData(BaseModel):
    """Schema for token data validation."""
    user_id: str
    email: str