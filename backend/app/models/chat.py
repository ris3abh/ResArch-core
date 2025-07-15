# app/models/chat.py
"""
Chat models for real-time communication and agent interaction.
"""
from sqlalchemy import Column, String, Text, ForeignKey, Boolean, JSON, Index
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class ChatInstance(BaseModel):
    """Chat instance model for project conversations."""
    
    __tablename__ = "chat_instances"
    
    # Project Association
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    
    # Chat Information
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Chat Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Creator
    created_by = Column(String, ForeignKey('users.id'), nullable=False)
    
    # Agent Configuration
    agent_config = Column(JSON, default=dict, nullable=True)  # Configuration for CAMEL-AI agents
    
    # Relationships
    # project = relationship("Project", back_populates="chat_instances")
    # creator = relationship("User", back_populates="created_chats")
    # messages = relationship("ChatMessage", back_populates="chat_instance", cascade="all, delete-orphan")
    # workflow_tasks = relationship("WorkflowTask", back_populates="chat_instance")
    
    # Indexes
    __table_args__ = (
        Index('idx_chat_project', 'project_id'),
        Index('idx_chat_creator', 'created_by'),
        Index('idx_chat_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<ChatInstance(id={self.id}, name={self.name}, project_id={self.project_id})>"
    
    @property
    def agent_types(self) -> list:
        """Get list of configured agent types."""
        if self.agent_config and 'agents' in self.agent_config:
            return self.agent_config['agents']
        return []
    
    @property
    def workflow_type(self) -> str:
        """Get workflow type from agent config."""
        if self.agent_config and 'workflow_type' in self.agent_config:
            return self.agent_config['workflow_type']
        return 'default'


class ChatMessage(BaseModel):
    """Chat message model for conversation history."""
    
    __tablename__ = "chat_messages"
    
    # Chat Association
    chat_instance_id = Column(String, ForeignKey('chat_instances.id', ondelete='CASCADE'), nullable=False)
    
    # Message Content
    message_content = Column(Text, nullable=False)
    message_type = Column(String(50), default='text', nullable=False)  # 'text', 'system', 'file', 'task_result'
    
    # Sender Information
    sender_type = Column(String(20), nullable=False)  # 'user', 'agent'
    sender_id = Column(String, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)  # NULL for agents
    agent_name = Column(String(100), nullable=True)  # Name of the agent (if sender_type='agent')
    
    # Message Threading
    parent_message_id = Column(String, ForeignKey('chat_messages.id'), nullable=True)
    
    # Message Metadata (renamed to avoid SQLAlchemy reserved word)
    message_metadata = Column(JSON, default=dict, nullable=True)
    
    # Relationships
    # chat_instance = relationship("ChatInstance", back_populates="messages")
    # sender = relationship("User", back_populates="chat_messages")
    # parent_message = relationship("ChatMessage", remote_side=[BaseModel.id])
    # child_messages = relationship("ChatMessage", back_populates="parent_message")
    
    # Indexes
    __table_args__ = (
        Index('idx_message_chat', 'chat_instance_id'),
        Index('idx_message_sender', 'sender_id'),
        Index('idx_message_type', 'message_type'),
        Index('idx_message_created', 'created_at'),
        Index('idx_message_thread', 'parent_message_id'),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, sender_type={self.sender_type}, message_type={self.message_type})>"
    
    @property
    def is_from_user(self) -> bool:
        """Check if message is from a user."""
        return self.sender_type == 'user'
    
    @property
    def is_from_agent(self) -> bool:
        """Check if message is from an agent."""
        return self.sender_type == 'agent'
    
    @property
    def is_system_message(self) -> bool:
        """Check if message is a system message."""
        return self.message_type == 'system'
    
    @property
    def is_task_result(self) -> bool:
        """Check if message contains task results."""
        return self.message_type == 'task_result'
    
    @property
    def is_threaded(self) -> bool:
        """Check if message is part of a thread."""
        return self.parent_message_id is not None
    
    @property
    def content_preview(self) -> str:
        """Get a preview of the message content."""
        if len(self.message_content) <= 100:
            return self.message_content
        return self.message_content[:97] + "..."
    
    def to_dict(self):
        """Convert message to dictionary with computed properties."""
        data = super().to_dict()
        data.update({
            'is_from_user': self.is_from_user,
            'is_from_agent': self.is_from_agent,
            'is_system_message': self.is_system_message,
            'is_task_result': self.is_task_result,
            'is_threaded': self.is_threaded,
            'content_preview': self.content_preview,
            'metadata': self.message_metadata,  # Expose as 'metadata' in API
        })
        return data