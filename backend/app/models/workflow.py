# backend/app/models/workflow.py
from sqlalchemy import Column, String, DateTime, Float, Boolean, Text, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String, unique=True, nullable=False, index=True)
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    chat_instance_id = Column(UUID(as_uuid=True), ForeignKey("chat_instances.id"), nullable=True)
    
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=False)
    
    status = Column(String(50), default="pending", nullable=False)
    current_stage = Column(String(100), nullable=True)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    timeout_seconds = Column(Integer, default=1800, nullable=False)
    
    enable_human_interaction = Column(Boolean, default=True, nullable=False)
    enable_checkpoints = Column(Boolean, default=True, nullable=False)
    
    first_draft = Column(Text, nullable=True)
    final_content = Column(Text, nullable=True)
    
    agent_config = Column(JSON, default=dict, nullable=False)
    execution_log = Column(JSON, default=list, nullable=False)
    error_details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    checkpoints = relationship("WorkflowCheckpoint", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowCheckpoint(Base):
    __tablename__ = "workflow_checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String, ForeignKey("workflow_executions.workflow_id", ondelete="CASCADE"), nullable=False)
    
    checkpoint_type = Column(String(50), nullable=False)
    stage = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    status = Column(String(50), default="pending", nullable=False)
    priority = Column(String(20), default="medium", nullable=False)
    requires_approval = Column(Boolean, default=True, nullable=False)
    
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    checkpoint_data = Column(JSON, default=dict, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    workflow = relationship("WorkflowExecution", back_populates="checkpoints")