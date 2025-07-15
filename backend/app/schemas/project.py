# app/schemas/project.py
"""
Pydantic schemas for Project API validation.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.schemas.user import UserListResponse

# Request Schemas
class ProjectCreate(BaseModel):
    """Schema for project creation."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    client_name: Optional[str] = Field(None, max_length=200)
    project_type: str = Field(default="personal")
    
    @field_validator('project_type')
    @classmethod
    def validate_project_type(cls, v):
        """Validate project type."""
        allowed_types = ['personal', 'shared']
        if v not in allowed_types:
            raise ValueError(f'Project type must be one of: {allowed_types}')
        return v


class ProjectUpdate(BaseModel):
    """Schema for project updates."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    client_name: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate project status."""
        if v is not None:
            allowed_statuses = ['active', 'archived', 'completed']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v


class ProjectMemberAdd(BaseModel):
    """Schema for adding project members."""
    user_email: EmailStr
    role: str = Field(default="member")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Validate member role."""
        allowed_roles = ['owner', 'admin', 'member', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {allowed_roles}')
        return v


class ProjectMemberUpdate(BaseModel):
    """Schema for updating project member roles."""
    role: str
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Validate member role."""
        allowed_roles = ['owner', 'admin', 'member', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {allowed_roles}')
        return v


# Response Schemas
class ProjectBase(BaseModel):
    """Base project schema."""
    id: str
    name: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    project_type: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ProjectResponse(ProjectBase):
    """Schema for project responses."""
    project_metadata: Optional[Dict[str, Any]] = None
    is_personal: bool
    is_shared: bool
    is_active: bool
    
    # Expose metadata with the expected field name
    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        return self.project_metadata


class ProjectListResponse(ProjectBase):
    """Schema for project list responses (minimal data)."""
    is_personal: bool
    is_shared: bool
    is_active: bool


class ProjectMemberResponse(BaseModel):
    """Schema for project member responses."""
    id: str
    project_id: str
    user_id: str
    role: str
    created_at: datetime
    is_owner: bool
    is_admin: bool
    can_manage_project: bool
    can_edit_content: bool
    user: Optional[UserListResponse] = None  # User details if included
    
    model_config = {"from_attributes": True}


class ProjectWithMembersResponse(ProjectResponse):
    """Schema for project with members."""
    members: list[ProjectMemberResponse] = []
    member_count: int = 0


class ProjectStatsResponse(BaseModel):
    """Schema for project statistics."""
    total_projects: int
    personal_projects: int
    shared_projects: int
    active_projects: int
    archived_projects: int
    total_documents: int
    total_chats: int
    total_drafts: int