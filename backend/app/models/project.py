# app/models/project.py
"""
Project and ProjectMember models for project management.
"""
from sqlalchemy import Column, String, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Project(BaseModel):
    """Project model for organizing work."""
    
    __tablename__ = "projects"
    
    # Project Information
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    client_name = Column(String(200), nullable=True)
    
    # Project Configuration
    project_type = Column(String(50), default='personal', nullable=False)  # 'personal' or 'shared'
    status = Column(String(50), default='active', nullable=False)  # 'active', 'archived', 'completed'
    
    # Ownership
    created_by = Column(String, ForeignKey('users.id'), nullable=False)
    
    # Metadata (renamed to avoid SQLAlchemy reserved word)
    project_metadata = Column(JSON, default=dict, nullable=True)
    
    # Relationships (we'll add these when we create related models)
    # creator = relationship("User", back_populates="created_projects")
    # members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    # documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    # chat_instances = relationship("ChatInstance", back_populates="project", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_project_created_by', 'created_by'),
        Index('idx_project_type_status', 'project_type', 'status'),
    )
    
    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, type={self.project_type})>"
    
    @property
    def is_personal(self) -> bool:
        """Check if project is personal."""
        return self.project_type == 'personal'
    
    @property
    def is_shared(self) -> bool:
        """Check if project is shared."""
        return self.project_type == 'shared'
    
    @property
    def is_active(self) -> bool:
        """Check if project is active."""
        return self.status == 'active'


class ProjectMember(BaseModel):
    """Project membership model for shared projects."""
    
    __tablename__ = "project_members"
    
    # Relationship Fields
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Membership Details
    role = Column(String(50), default='member', nullable=False)  # 'owner', 'admin', 'member', 'viewer'
    
    # Relationships
    # project = relationship("Project", back_populates="members")
    # user = relationship("User", back_populates="project_memberships")
    
    # Indexes
    __table_args__ = (
        Index('idx_project_member_unique', 'project_id', 'user_id', unique=True),
        Index('idx_project_member_project', 'project_id'),
        Index('idx_project_member_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<ProjectMember(project_id={self.project_id}, user_id={self.user_id}, role={self.role})>"
    
    @property
    def is_owner(self) -> bool:
        """Check if member is owner."""
        return self.role == 'owner'
    
    @property
    def is_admin(self) -> bool:
        """Check if member is admin."""
        return self.role == 'admin'
    
    @property
    def can_manage_project(self) -> bool:
        """Check if member can manage project."""
        return self.role in ['owner', 'admin']
    
    @property
    def can_edit_content(self) -> bool:
        """Check if member can edit content."""
        return self.role in ['owner', 'admin', 'member']