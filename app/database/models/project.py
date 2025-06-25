# app/database/models/project.py - UPDATED FOR SQLAlchemy 2.0
"""
Project model with proper SQLAlchemy 2.0 syntax using Mapped annotations.
Updated to follow modern best practices and fix relationship issues.
"""
from sqlalchemy import String, DateTime, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.database.connection import Base

def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())

class Project(Base):
    """
    Project model representing a client's workspace in SpinScribe.
    Each project is isolated and contains its own knowledge base, chats, and workflows.
    """
    __tablename__ = "projects"

    # Primary key using UUID with proper Mapped annotation
    project_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Basic project information with proper type annotations
    client_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String, default="active", index=True)
    
    # Project-specific configuration stored as JSON
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Timestamps with proper Mapped annotations
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    
    # Relationships with proper forward references and back_populates
    knowledge_items: Mapped[List["KnowledgeItem"]] = relationship(
        "KnowledgeItem", 
        back_populates="project", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    chat_instances: Mapped[List["ChatInstance"]] = relationship(
        "ChatInstance", 
        back_populates="project", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    human_checkpoints: Mapped[List["HumanCheckpoint"]] = relationship(
        "HumanCheckpoint", 
        back_populates="project", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<Project(id={self.project_id}, client={self.client_name}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary for API responses"""
        return {
            "project_id": self.project_id,
            "client_name": self.client_name,
            "description": self.description,
            "status": self.status,
            "configuration": self.configuration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
        }
    
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity_at = datetime.utcnow()
    
    @classmethod
    def create_new(cls, client_name: str, description: str = None, configuration: dict = None):
        """Create a new project instance"""
        return cls(
            client_name=client_name,
            description=description,
            configuration=configuration or {},
        )
    
    def is_active(self) -> bool:
        """Check if project is active"""
        return self.status == "active"
    
    def archive(self):
        """Archive the project"""
        self.status = "archived"
        self.update_activity()
    
    def activate(self):
        """Activate the project"""
        self.status = "active"
        self.update_activity()