# backend/app/models/chat_instance.py
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base

class ChatInstance(Base):
    __tablename__ = "chat_instances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    chat_type = Column(String, nullable=False, default="chat")  # 'chat', 'workflow', 'collaboration'
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_config = Column(JSON, nullable=True)
    workflow_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    
    # Relationships
    project = relationship("Project", back_populates="chat_instances")
    created_by_user = relationship("User", back_populates="chat_instances")
    workflow_executions = relationship("WorkflowExecution", back_populates="chat_instance")
    messages = relationship("ChatMessage", back_populates="chat_instance")
    
    @classmethod
    async def get_by_id(cls, db, chat_id: str):
        """Get chat instance by ID"""
        from sqlalchemy import select
        result = await db.execute(select(cls).where(cls.id == chat_id))
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_project(cls, db, project_id: str, user_id: str):
        """Get chat instances for a project"""
        from sqlalchemy import select
        result = await db.execute(
            select(cls).where(
                cls.project_id == project_id,
                cls.created_by == user_id,
                cls.is_active == True
            ).order_by(cls.created_at.desc())
        )
        return result.scalars().all()
    
    @classmethod
    async def create_workflow_chat(cls, db, project_id: str, user_id: str, title: str, workflow_id: str = None):
        """Create a new chat instance for workflow"""
        chat = cls(
            project_id=project_id,
            name=f"SpinScribe: {title}",
            description=f"Agent collaboration chat for workflow",
            chat_type="workflow",
            created_by=user_id,
            workflow_id=workflow_id,
            agent_config={
                "enable_agent_messages": True,
                "show_agent_thinking": True,
                "checkpoint_notifications": True,
                "workflow_transparency": True
            }
        )
        
        db.add(chat)
        await db.flush()  # Get the ID
        return chat