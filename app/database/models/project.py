# app/database/models/project.py
from sqlalchemy import Column, String, DateTime, JSON, func, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

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

    # Primary key using UUID
    project_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Basic project information
    client_name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Status tracking (e.g., "active", "archived", "completed", "paused")
    status = Column(String, default="active", index=True)
    
    # Project-specific configuration stored as JSON
    # This can include client preferences, style settings, etc.
    configuration = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_activity_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships (we'll add these as we create other models)
    # knowledge_items = relationship("KnowledgeItem", back_populates="project", cascade="all, delete-orphan")
    # chat_instances = relationship("ChatInstance", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.project_id}, client={self.client_name}, status={self.status})>"
    
    def to_dict(self):
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