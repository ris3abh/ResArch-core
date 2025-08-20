# backend/app/models/workflow.py
"""
FIXED: WorkflowExecution model with proper imports.
Add the missing Base import at the top of your workflow.py file.
"""

# ADD THESE IMPORTS at the top of your file:
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base  # This was missing!
import uuid

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Workflow details
    workflow_id = Column(String, nullable=True)  # ID from the workflow service
    title = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    initial_draft = Column(Text, nullable=True)
    use_project_documents = Column(Boolean, default=False)
    
    # Status tracking
    status = Column(String, default="pending")
    current_stage = Column(String, nullable=True)
    final_content = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    live_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="workflow_executions")
    user = relationship("User")

class WorkflowCheckpoint(Base):
    __tablename__ = "workflow_checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False)
    
    # Checkpoint details
    checkpoint_type = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, approved, rejected
    priority = Column(String, default="medium")
    requires_approval = Column(Boolean, default=True)
    
    # Checkpoint data
    checkpoint_data = Column(JSON, nullable=True)
    
    # Approval details
    approved_by = Column(String, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workflow = relationship("WorkflowExecution")
    workflow_executions = relationship("WorkflowExecution", back_populates="project")
    
    # Make sure you also have the documents relationship:
    documents = relationship("Document", back_populates="project")