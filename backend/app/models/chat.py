# backend/app/models/chat.py (FIXED VERSION)
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class ChatInstance(BaseModel):
    """Chat instance model for project-based conversations."""
    __tablename__ = "chat_instances"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    chat_type = Column(String(50), default="standard")  # 'standard', 'workflow', 'brainstorm'
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_config = Column(JSONB, default={})
    workflow_id = Column(String(100))  # Link to CAMEL workflow execution
    
    # Relationships
    project = relationship("Project", back_populates="chats")
    creator = relationship("User")
    messages = relationship("ChatMessage", back_populates="chat_instance", cascade="all, delete-orphan")

class ChatMessage(BaseModel):
    """Chat message model for storing conversation history."""
    __tablename__ = "chat_messages"
    
    chat_instance_id = Column(UUID(as_uuid=True), ForeignKey("chat_instances.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    sender_type = Column(String(50), nullable=False)  # 'user', 'agent', 'system'
    agent_type = Column(String(100))  # 'coordinator', 'style_analysis', 'content_planning', etc.
    message_content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # 'text', 'checkpoint', 'file', 'action'
    message_metadata = Column(JSONB, default={})  # CHANGED: metadata -> message_metadata
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id"))
    is_edited = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    chat_instance = relationship("ChatInstance", back_populates="messages")
    sender = relationship("User")
    parent_message = relationship("ChatMessage", remote_side="ChatMessage.id")
    replies = relationship("ChatMessage", remote_side="ChatMessage.parent_message_id")