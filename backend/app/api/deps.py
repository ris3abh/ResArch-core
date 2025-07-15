# app/api/deps.py
"""
API dependencies for authentication and common functionality.
"""
from typing import Optional, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.auth import auth_service
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.schemas.user import TokenData

# Security scheme
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Verify and decode token
    token_data = auth_service.verify_token(credentials.credentials)
    user_id = token_data.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional check for active status).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated"
        )
    return current_user


async def get_current_spinutech_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Ensure current user is a Spinutech employee.
    
    Args:
        current_user: Current active user
        
    Returns:
        User: Current Spinutech user
        
    Raises:
        HTTPException: If user is not a Spinutech employee
    """
    if not current_user.is_spinutech_employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Spinutech employees"
        )
    return current_user


async def get_project_with_access_check(
    project_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    required_role: str = "viewer"
) -> Project:
    """
    Get project and verify user has access with required role.
    
    Args:
        project_id: Project ID
        user: Current user
        db: Database session
        required_role: Minimum required role (viewer, member, admin, owner)
        
    Returns:
        Project: Project if user has access
        
    Raises:
        HTTPException: If project not found or access denied
    """
    # Get project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Owner always has access
    if project.created_by == user.id:
        return project
    
    # For personal projects, only owner has access
    if project.project_type == "personal":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to personal project"
        )
    
    # For shared projects, check membership
    if project.project_type == "shared":
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id
            )
        )
        member = result.scalar_one_or_none()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - not a project member"
            )
        
        # Check role hierarchy: owner > admin > member > viewer
        role_hierarchy = {"viewer": 1, "member": 2, "admin": 3, "owner": 4}
        user_role_level = role_hierarchy.get(member.role, 0)
        required_role_level = role_hierarchy.get(required_role, 0)
        
        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions - {required_role} role required"
            )
    
    return project


async def get_project_with_member_access(
    project_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Project:
    """Get project with member-level access."""
    return await get_project_with_access_check(project_id, user, db, "member")


async def get_project_with_admin_access(
    project_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Project:
    """Get project with admin-level access."""
    return await get_project_with_access_check(project_id, user, db, "admin")


async def get_project_with_owner_access(
    project_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Project:
    """Get project with owner-level access."""
    return await get_project_with_access_check(project_id, user, db, "owner")


def get_pagination_params(
    page: int = 1,
    limit: int = 50,
    max_limit: int = 100
) -> dict:
    """
    Get pagination parameters with validation.
    
    Args:
        page: Page number (1-based)
        limit: Items per page
        max_limit: Maximum allowed limit
        
    Returns:
        dict: Pagination parameters
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be 1 or greater"
        )
    
    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be 1 or greater"
        )
    
    if limit > max_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limit cannot exceed {max_limit}"
        )
    
    offset = (page - 1) * limit
    
    return {
        "limit": limit,
        "offset": offset,
        "page": page
    }