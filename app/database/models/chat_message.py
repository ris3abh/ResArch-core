# app/database/models/chat_message.py - UPDATED FOR SQLAlchemy 2.0
"""
Chat Message model with proper SQLAlchemy 2.0 syntax using Mapped annotations.
Updated to follow modern best practices and fix relationship issues.
"""
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey, Boolean, Integer, func, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.database.connection import Base

def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())

class ChatMessage(Base):
    """
    Chat Message model representing individual messages within a chat instance.
    Supports both human and AI agent messages with rich metadata.
    """
    __tablename__ = "chat_messages"

    # Primary key
    message_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Foreign keys
    chat_instance_id: Mapped[str] = mapped_column(String, ForeignKey("chat_instances.chat_instance_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Message metadata
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    message_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    
    # Participant information
    participant_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    participant_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    participant_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Agent-specific fields
    agent_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    agent_role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Message content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String, default="text")
    
    # Rich content support (renamed to avoid SQLAlchemy conflict)
    attachments: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True, default=list)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # AI processing information
    model_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Message state
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    edit_count: Mapped[int] = mapped_column(Integer, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Workflow integration
    task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stage: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Human feedback
    human_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    human_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Threading and references
    reply_to_message_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("chat_messages.message_id"), nullable=True)
    thread_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Processing status
    processing_status: Mapped[str] = mapped_column(String, default="sent")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    chat_instance: Mapped["ChatInstance"] = relationship("ChatInstance", back_populates="messages")
    reply_to: Mapped[Optional["ChatMessage"]] = relationship("ChatMessage", remote_side=[message_id], back_populates="replies")
    replies: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="reply_to")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.message_id}, type={self.message_type}, participant={self.participant_name})>"
    
    def to_dict(self, include_content: bool = True) -> Dict[str, Any]:
        """Convert message to dictionary for API responses"""
        result = {
            "message_id": self.message_id,
            "chat_instance_id": self.chat_instance_id,
            "sequence_number": self.sequence_number,
            "message_type": self.message_type,
            "participant_type": self.participant_type,
            "participant_id": self.participant_id,
            "participant_name": self.participant_name,
            "agent_type": self.agent_type,
            "agent_role": self.agent_role,
            "content_type": self.content_type,
            "attachments": self.attachments,
            "meta_data": self.meta_data,
            "is_edited": self.is_edited,
            "edit_count": self.edit_count,
            "is_deleted": self.is_deleted,
            "task_id": self.task_id,
            "stage": self.stage,
            "human_rating": self.human_rating,
            "flagged_for_review": self.flagged_for_review,
            "reply_to_message_id": self.reply_to_message_id,
            "thread_id": self.thread_id,
            "processing_status": self.processing_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }
        
        if include_content and not self.is_deleted:
            result["content"] = self.content
        
        return result
    
    def to_camel_message(self):
        """Convert to CAMEL BaseMessage format for agent processing"""
        from camel.messages import BaseMessage
        from camel.types import RoleType
        
        # Determine role type for CAMEL
        if self.participant_type == "human":
            role_type = RoleType.USER
        else:
            role_type = RoleType.ASSISTANT
        
        return BaseMessage(
            role_name=self.participant_name or self.agent_type or "unknown",
            role_type=role_type,
            meta_dict=self.meta_data or {},
            content=self.content
        )
    
    @classmethod
    def create_user_message(cls,
                          chat_instance_id: str,
                          content: str,
                          participant_id: str,
                          participant_name: str,
                          sequence_number: int,
                          attachments: List[Dict] = None,
                          metadata: Dict[str, Any] = None):
        """Create a user message"""
        return cls(
            chat_instance_id=chat_instance_id,
            content=content,
            sequence_number=sequence_number,
            message_type="user",
            participant_type="human",
            participant_id=participant_id,
            participant_name=participant_name,
            attachments=attachments or [],
            meta_data=metadata or {},
            sent_at=datetime.utcnow()
        )
    
    @classmethod
    def create_agent_message(cls,
                           chat_instance_id: str,
                           content: str,
                           agent_type: str,
                           sequence_number: int,
                           agent_role: str = None,
                           model_used: str = None,
                           tokens_used: int = None,
                           processing_time: float = None,
                           task_id: str = None,
                           stage: str = None,
                           metadata: Dict[str, Any] = None):
        """Create an agent message"""
        return cls(
            chat_instance_id=chat_instance_id,
            content=content,
            sequence_number=sequence_number,
            message_type="agent",
            participant_type="agent",
            participant_id=agent_type,
            participant_name=agent_type.replace("_", " ").title(),
            agent_type=agent_type,
            agent_role=agent_role,
            model_used=model_used,
            tokens_used=tokens_used,
            processing_time=processing_time,
            task_id=task_id,
            stage=stage,
            meta_data=metadata or {},
            sent_at=datetime.utcnow()
        )
    
    @classmethod
    def create_system_message(cls,
                            chat_instance_id: str,
                            content: str,
                            sequence_number: int,
                            metadata: Dict[str, Any] = None):
        """Create a system message"""
        return cls(
            chat_instance_id=chat_instance_id,
            content=content,
            sequence_number=sequence_number,
            message_type="system",
            participant_type="system",
            participant_name="System",
            meta_data=metadata or {},
            sent_at=datetime.utcnow()
        )
    
    def mark_as_sent(self):
        """Mark message as sent"""
        self.processing_status = "sent"
        self.sent_at = datetime.utcnow()
    
    def mark_as_processed(self):
        """Mark message as processed"""
        self.processing_status = "processed"
    
    def mark_as_failed(self, error_message: str):
        """Mark message processing as failed"""
        self.processing_status = "failed"
        self.error_message = error_message