# backend/app/models/project.py
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Project(BaseModel):
    """Project model for organizing content creation work."""
    __tablename__ = "projects"
    
    name = Column(String(200), nullable=False)
    description = Column(Text)
    client_name = Column(String(200))
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    chats = relationship("ChatInstance", back_populates="project", cascade="all, delete-orphan")
    
    # FIX: Add the missing workflow_executions relationship
    workflow_executions = relationship(
        "WorkflowExecution", 
        back_populates="project", 
        cascade="all, delete-orphan"
    )