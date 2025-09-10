# backend/app/models/chat_instance.py
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.core.database import Base

class ChatInstance(Base):
    __tablename__ = "chat_instances"
    __table_args__ = {'extend_existing': True}  # This fixes the duplicate table error
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)  # Remove ForeignKey for now
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    chat_type = Column(String, nullable=False, default="chat")  # 'chat', 'workflow', 'collaboration'
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)  # Remove ForeignKey for now
    agent_config = Column(JSON, nullable=True)
    workflow_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    
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