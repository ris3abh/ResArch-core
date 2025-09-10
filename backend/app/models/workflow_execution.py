# backend/app/models/workflow_execution.py
from sqlalchemy import Column, String, DateTime, Float, Boolean, Text, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String, nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    chat_instance_id = Column(UUID(as_uuid=True), ForeignKey("chat_instances.id"), nullable=True)
    chat_id = Column(UUID(as_uuid=True), nullable=True)
    
    title = Column(String, nullable=False)
    content_type = Column(String, nullable=False, default="article")
    status = Column(String, nullable=False, default="starting")
    current_stage = Column(String, nullable=True)
    progress_percentage = Column(Float, default=0.0)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    timeout_seconds = Column(Integer, default=600)
    
    enable_human_interaction = Column(Boolean, default=True)
    enable_checkpoints = Column(Boolean, default=True)
    
    first_draft = Column(Text, nullable=True)
    final_content = Column(Text, nullable=True)
    agent_config = Column(JSON, nullable=True)
    execution_log = Column(JSON, nullable=True)
    error_details = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    
    # Relationships
    project = relationship("Project", back_populates="workflow_executions")
    user = relationship("User", back_populates="workflow_executions")
    chat_instance = relationship("ChatInstance", back_populates="workflow_executions")
    
    @classmethod
    async def get_by_id(cls, db, workflow_id: str):
        """Get workflow by ID"""
        from sqlalchemy import select
        result = await db.execute(select(cls).where(cls.id == workflow_id))
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_filters(cls, db, filters: dict, limit: int = 20, offset: int = 0):
        """Get workflows by filters"""
        from sqlalchemy import select
        query = select(cls)
        
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.where(getattr(cls, key) == value)
        
        query = query.order_by(cls.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        return result.scalars().all()
    
    @classmethod
    async def count_by_filters(cls, db, filters: dict):
        """Count workflows by filters"""
        from sqlalchemy import select, func
        query = select(func.count(cls.id))
        
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.where(getattr(cls, key) == value)
        
        result = await db.execute(query)
        return result.scalar()