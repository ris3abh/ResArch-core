# app/database/models/chat_participant.py - UPDATED FOR SQLAlchemy 2.0
"""
Chat Participant model with proper SQLAlchemy 2.0 syntax using Mapped annotations.
Updated to follow modern best practices and fix relationship issues.
"""
from sqlalchemy import String, DateTime, JSON, Boolean, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from app.database.connection import Base

def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())

class ChatParticipant(Base):
    """
    Chat Participant model representing entities that can participate in chat instances.
    Includes both human users and AI agents with role-based permissions.
    """
    __tablename__ = "chat_participants"

    # Primary key
    participant_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Foreign key to chat instance
    chat_instance_id: Mapped[str] = mapped_column(String, ForeignKey("chat_instances.chat_instance_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Participant identification
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    agent_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    
    # Participant details
    participant_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Role and permissions
    role: Mapped[str] = mapped_column(String, nullable=False, default="participant")
    permissions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Agent-specific configuration
    agent_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    is_primary_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Participation status
    status: Mapped[str] = mapped_column(String, default="active")
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    can_send_messages: Mapped[bool] = mapped_column(Boolean, default=True)
    can_edit_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_participants: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Activity tracking
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    message_count: Mapped[str] = mapped_column(String, default="0")
    
    # Notification preferences (for humans)
    notification_preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    chat_instance: Mapped["ChatInstance"] = relationship("ChatInstance", back_populates="participants")
    
    # Unique constraint: one participant record per user/agent per chat
    __table_args__ = (
        UniqueConstraint('chat_instance_id', 'user_id', name='uq_chat_user'),
        UniqueConstraint('chat_instance_id', 'agent_type', name='uq_chat_agent'),
    )
    
    def __repr__(self):
        return f"<ChatParticipant(id={self.participant_id}, type={self.participant_type}, name={self.display_name})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert participant to dictionary for API responses"""
        return {
            "participant_id": self.participant_id,
            "chat_instance_id": self.chat_instance_id,
            "user_id": self.user_id,
            "agent_type": self.agent_type,
            "participant_type": self.participant_type,
            "display_name": self.display_name,
            "email": self.email,
            "role": self.role,
            "permissions": self.permissions,
            "is_primary_agent": self.is_primary_agent,
            "status": self.status,
            "is_online": self.is_online,
            "can_send_messages": self.can_send_messages,
            "can_edit_messages": self.can_edit_messages,
            "can_manage_participants": self.can_manage_participants,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "message_count": self.message_count,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }
    
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity_at = datetime.utcnow()
    
    @classmethod
    def create_human_participant(cls,
                               chat_instance_id: str,
                               user_id: str,
                               display_name: str,
                               email: str = None,
                               role: str = "participant"):
        """Create a human participant"""
        return cls(
            chat_instance_id=chat_instance_id,
            user_id=user_id,
            participant_type="human",
            display_name=display_name,
            email=email,
            role=role,
            permissions={
                "can_view_messages": True,
                "can_send_messages": True,
                "can_upload_files": True,
                "can_rate_messages": True
            },
            can_send_messages=True,
            can_edit_messages=(role in ["admin", "editor"]),
            can_manage_participants=(role in ["admin", "owner"])
        )
    
    @classmethod
    def create_agent_participant(cls,
                               chat_instance_id: str,
                               agent_type: str,
                               is_primary: bool = False,
                               agent_config: Dict[str, Any] = None):
        """Create an AI agent participant"""
        display_name = agent_type.replace("_", " ").title()
        
        return cls(
            chat_instance_id=chat_instance_id,
            agent_type=agent_type,
            participant_type="agent",
            display_name=display_name,
            role="agent",
            is_primary_agent=is_primary,
            agent_config=agent_config or {},
            permissions={
                "can_view_messages": True,
                "can_send_messages": True,
                "can_access_knowledge": True,
                "can_trigger_workflows": True
            },
            can_send_messages=True,
            status="active",
            is_online=True
        )
    
    def set_role(self, new_role: str):
        """Update participant role and associated permissions"""
        self.role = new_role
        
        if new_role == "owner":
            self.can_edit_messages = True
            self.can_manage_participants = True
            self.permissions.update({
                "can_delete_chat": True,
                "can_export_chat": True,
                "can_modify_settings": True
            })
        elif new_role == "admin":
            self.can_edit_messages = True
            self.can_manage_participants = True
            self.permissions.update({
                "can_export_chat": True,
                "can_modify_settings": True
            })
        elif new_role == "editor":
            self.can_edit_messages = True
            self.can_manage_participants = False
        elif new_role == "viewer":
            self.can_send_messages = False
            self.can_edit_messages = False
            self.can_manage_participants = False
        
        self.update_activity()
    
    def set_primary_agent(self, is_primary: bool = True):
        """Set this agent as primary or secondary"""
        if self.participant_type != "agent":
            raise ValueError("Only agents can be set as primary")
        
        self.is_primary_agent = is_primary
        self.update_activity()
    
    def set_online_status(self, is_online: bool):
        """Update online status (primarily for human participants)"""
        self.is_online = is_online
        if is_online:
            self.update_activity()
    
    def increment_message_count(self):
        """Increment message count and update last message time"""
        try:
            current_count = int(self.message_count)
            self.message_count = str(current_count + 1)
        except (ValueError, TypeError):
            self.message_count = "1"
        
        self.last_message_at = datetime.utcnow()
        self.update_activity()
    
    def update_notification_preferences(self, preferences: Dict[str, Any]):
        """Update notification preferences for human participants"""
        if self.participant_type != "human":
            return
        
        if not self.notification_preferences:
            self.notification_preferences = {}
        
        self.notification_preferences.update(preferences)
        self.update_activity()
    
    def update_agent_config(self, config: Dict[str, Any]):
        """Update agent configuration"""
        if self.participant_type != "agent":
            return
        
        if not self.agent_config:
            self.agent_config = {}
        
        self.agent_config.update(config)
        self.update_activity()
    
    def suspend_participant(self, reason: str = None):
        """Suspend participant from chat"""
        self.status = "suspended"
        self.can_send_messages = False
        self.is_online = False
        
        if reason:
            if not self.permissions:
                self.permissions = {}
            self.permissions["suspension_reason"] = reason
            self.permissions["suspended_at"] = datetime.utcnow().isoformat()
        
        self.update_activity()
    
    def reactivate_participant(self):
        """Reactivate suspended participant"""
        if self.status == "suspended":
            self.status = "active"
            self.can_send_messages = True
            
            if self.permissions and "suspension_reason" in self.permissions:
                del self.permissions["suspension_reason"]
                self.permissions["reactivated_at"] = datetime.utcnow().isoformat()
        
        self.update_activity()
    
    def remove_participant(self):
        """Remove participant from chat"""
        self.status = "removed"
        self.can_send_messages = False
        self.can_edit_messages = False
        self.can_manage_participants = False
        self.is_online = False
        self.removed_at = datetime.utcnow()
        
        self.update_activity()
    
    def has_permission(self, permission: str) -> bool:
        """Check if participant has specific permission"""
        if not self.permissions:
            return False
        
        return self.permissions.get(permission, False)
    
    def can_perform_action(self, action: str) -> bool:
        """Check if participant can perform a specific action"""
        if self.status != "active":
            return False
        
        action_mapping = {
            "send_message": self.can_send_messages,
            "edit_message": self.can_edit_messages,
            "manage_participants": self.can_manage_participants,
            "view_messages": True,
        }
        
        return action_mapping.get(action, False)
    
    def is_human(self) -> bool:
        """Check if participant is human"""
        return self.participant_type == "human"
    
    def is_agent(self) -> bool:
        """Check if participant is an AI agent"""
        return self.participant_type == "agent"
    
    def is_active(self) -> bool:
        """Check if participant is active"""
        return self.status == "active"
    
    def is_owner(self) -> bool:
        """Check if participant is the chat owner"""
        return self.role == "owner"
    
    def is_admin(self) -> bool:
        """Check if participant has admin privileges"""
        return self.role in ["owner", "admin"]
    
    def get_activity_summary(self) -> Dict[str, Any]:
        """Get participant activity summary"""
        return {
            "participant_id": self.participant_id,
            "display_name": self.display_name,
            "participant_type": self.participant_type,
            "message_count": self.message_count,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "is_online": self.is_online,
            "status": self.status
        }