# app/database/models/chat_instance.py - CORRECT FILE (NO DUPLICATE CLASSES)
"""
Chat Instance model with proper SQLAlchemy 2.0 syntax using Mapped annotations.
Updated to follow modern best practices and fix relationship issues.
"""
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from app.database.connection import Base

if TYPE_CHECKING:
    from .project import Project
    from .chat_message import ChatMessage
    from .chat_participant import ChatParticipant

def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())

class ChatInstance(Base):
    """
    Chat Instance model representing a conversation session for content creation.
    Each instance is tied to a project and has a specific purpose/goal.
    """
    __tablename__ = "chat_instances"

    # Primary key
    chat_instance_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Foreign key to project
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Chat metadata
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chat_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    
    # Content creation specific
    content_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    target_audience: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content_goal: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Chat configuration
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Workflow state
    current_stage: Mapped[str] = mapped_column(String, default="initiated")
    workflow_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Agent management
    active_agents: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    primary_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Status and metrics
    status: Mapped[str] = mapped_column(String, default="active", index=True)
    priority: Mapped[str] = mapped_column(String, default="normal")
    
    # Human interaction
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    human_checkpoint_stage: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_human_interaction: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Usage statistics
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    agent_interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="chat_instances")
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="chat_instance", cascade="all, delete-orphan")
    participants: Mapped[List["ChatParticipant"]] = relationship("ChatParticipant", back_populates="chat_instance", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatInstance(id={self.chat_instance_id}, title={self.title}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chat instance to dictionary for API responses"""
        return {
            "chat_instance_id": self.chat_instance_id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "chat_type": self.chat_type,
            "content_type": self.content_type,
            "target_audience": self.target_audience,
            "content_goal": self.content_goal,
            "current_stage": self.current_stage,
            "status": self.status,
            "priority": self.priority,
            "active_agents": self.active_agents,
            "primary_agent": self.primary_agent,
            "requires_human_review": self.requires_human_review,
            "message_count": self.message_count,
            "agent_interaction_count": self.agent_interaction_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity_at = datetime.utcnow()
    
    @classmethod
    def create_content_chat(cls,
                          project_id: str,
                          title: str,
                          content_type: str,
                          target_audience: str = None,
                          content_goal: str = None,
                          description: str = None):
        """Create a new content creation chat instance"""
        return cls(
            project_id=project_id,
            title=title,
            description=description or f"Content creation chat for {content_type}",
            chat_type="content_creation",
            content_type=content_type,
            target_audience=target_audience,
            content_goal=content_goal,
            current_stage="initiated",
            active_agents=["coordinator"],
            primary_agent="coordinator"
        )
    
    @classmethod
    def create_style_analysis_chat(cls,
                                 project_id: str,
                                 title: str,
                                 description: str = None):
        """Create a chat for style analysis"""
        return cls(
            project_id=project_id,
            title=title,
            description=description or "Style analysis and brand voice extraction",
            chat_type="style_analysis",
            current_stage="initiated",
            active_agents=["style_analyzer"],
            primary_agent="style_analyzer"
        )
    
    def add_agent(self, agent_type: str):
        """Add an agent to the active agents list"""
        if not self.active_agents:
            self.active_agents = []
        
        if agent_type not in self.active_agents:
            self.active_agents.append(agent_type)
            self.update_activity()
    
    def remove_agent(self, agent_type: str):
        """Remove an agent from the active agents list"""
        if self.active_agents and agent_type in self.active_agents:
            self.active_agents.remove(agent_type)
            self.update_activity()
    
    def set_primary_agent(self, agent_type: str):
        """Set the primary agent for this chat"""
        self.primary_agent = agent_type
        self.add_agent(agent_type)
    
    def advance_stage(self, new_stage: str):
        """Advance the chat to a new workflow stage"""
        self.current_stage = new_stage
        self.update_activity()
        
        if not self.workflow_state:
            self.workflow_state = {}
        
        self.workflow_state[f"{new_stage}_started_at"] = datetime.utcnow().isoformat()
    
    def set_human_checkpoint(self, stage: str):
        """Set a human checkpoint requirement"""
        self.requires_human_review = True
        self.human_checkpoint_stage = stage
        self.update_activity()
    
    def clear_human_checkpoint(self):
        """Clear human checkpoint requirement"""
        self.requires_human_review = False
        self.human_checkpoint_stage = None
        self.last_human_interaction = datetime.utcnow()
        self.update_activity()
    
    def complete_chat(self):
        """Mark the chat as completed"""
        self.status = "completed"
        self.current_stage = "completed"
        self.completed_at = datetime.utcnow()
        self.active_agents = []
        self.update_activity()
    
    def archive_chat(self):
        """Archive the chat"""
        self.status = "archived"
        self.active_agents = []
        self.update_activity()
    
    def increment_message_count(self):
        """Increment the message counter"""
        self.message_count += 1
        self.update_activity()
    
    def increment_agent_interaction(self):
        """Increment the agent interaction counter"""
        self.agent_interaction_count += 1
        self.update_activity()
    
    def add_token_usage(self, tokens: int):
        """Add to the total token usage"""
        self.total_tokens_used += tokens
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the chat context for agents"""
        return {
            "chat_id": self.chat_instance_id,
            "title": self.title,
            "chat_type": self.chat_type,
            "content_type": self.content_type,
            "target_audience": self.target_audience,
            "content_goal": self.content_goal,
            "current_stage": self.current_stage,
            "active_agents": self.active_agents,
            "requires_human_review": self.requires_human_review,
            "context": self.context or {}
        }
    
    def update_context(self, new_context: Dict[str, Any]):
        """Update the shared context"""
        if not self.context:
            self.context = {}
        
        self.context.update(new_context)
        self.update_activity()
    
    def is_active(self) -> bool:
        """Check if chat is active"""
        return self.status == "active"
    
    def is_completed(self) -> bool:
        """Check if chat is completed"""
        return self.status == "completed"
    
    def needs_human_review(self) -> bool:
        """Check if chat needs human review"""
        return self.requires_human_review