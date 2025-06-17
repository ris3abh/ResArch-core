# app/database/models/__init__.py
"""
Database models for SpinScribe

This module imports all database models to ensure they are registered
with SQLAlchemy's declarative base.
"""

# Import Base first
from app.database.connection import Base

# Import all models
from .project import Project

# We'll add these imports as we create more models:
# from .knowledge_item import KnowledgeItem
# from .chat_instance import ChatInstance
# from .chat_message import ChatMessage
# from .chat_participant import ChatParticipant
# from .human_checkpoint import HumanCheckpoint

# Export all models for easy importing
__all__ = [
    "Base",
    "Project",
    # "KnowledgeItem",
    # "ChatInstance", 
    # "ChatMessage",
    # "ChatParticipant",
    # "HumanCheckpoint",
]