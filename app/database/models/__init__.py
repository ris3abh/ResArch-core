# app/database/models/__init__.py - UPDATED FILE
"""
Database models module with proper SQLAlchemy 2.0 syntax and relationships.
This file needs updating to use modern SQLAlchemy 2.0 syntax with Mapped annotations.
"""

# Import Base first
from app.database.connection import Base

# Import all models
from .project import Project
from .knowledge_item import KnowledgeItem
from .chat_instance import ChatInstance
from .chat_message import ChatMessage
from .chat_participant import ChatParticipant
from .human_checkpoint import HumanCheckpoint

# Export all models for easy importing
__all__ = [
    "Base",
    "Project",
    "KnowledgeItem",
    "ChatInstance", 
    "ChatMessage",
    "ChatParticipant",
    "HumanCheckpoint",
]