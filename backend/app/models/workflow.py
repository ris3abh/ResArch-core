# backend/app/models/workflow.py
"""
Complete workflow models for SpinScribe CAMEL integration.
Updated to include chat_id field for agent communication.
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class WorkflowExecution(Base):
    """Model for tracking workflow executions - WITH chat_id field for agent communication."""
    __tablename__ = "workflow_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # NEW: Chat integration for agent communication and human checkpoints
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chat_instances.id"), nullable=True)
    
    # Workflow details
    workflow_id = Column(String, nullable=True, unique=True)  # ID from CAMEL workflow service
    title = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    initial_draft = Column(Text, nullable=True)
    use_project_documents = Column(Boolean, default=False)
    
    # Status tracking
    status = Column(String(50), default="pending")  # pending, starting, running, completed, failed, cancelled
    current_stage = Column(String(100), nullable=True)  # initialization, planning, creation, review, completed
    final_content = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    live_data = Column(JSON, nullable=True)  # Real-time data from workflow service
    
    # Performance metrics
    progress_percentage = Column(Integer, default=0)  # 0-100
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="workflow_executions")
    user = relationship("User")
    chat_instance = relationship("ChatInstance", foreign_keys=[chat_id])  # NEW: Link to chat
    checkpoints = relationship(
        "WorkflowCheckpoint", 
        back_populates="workflow", 
        cascade="all, delete-orphan"
    )

class WorkflowCheckpoint(Base):
    """Model for workflow checkpoints that require human approval."""
    __tablename__ = "workflow_checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False)
    
    # Checkpoint details
    checkpoint_type = Column(String(100), nullable=False)  # planning_approval, content_review, final_approval
    stage = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), default="pending")  # pending, approved, rejected, skipped
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    requires_approval = Column(Boolean, default=True)
    
    # Checkpoint content/data
    checkpoint_data = Column(JSON, nullable=True)
    content_preview = Column(Text, nullable=True)  # Preview of content for approval
    
    # Approval details
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approval_notes = Column(Text, nullable=True)
    feedback_data = Column(JSON, nullable=True)  # Structured feedback
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-approval timeout
    
    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="checkpoints")
    approver = relationship("User")