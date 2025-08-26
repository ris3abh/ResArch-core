# backend/app/models/__init__.py
"""
Models package initialization.
Import all models here to ensure they're registered with SQLAlchemy.
"""
from .user import User
from .project import Project
from .document import Document
from .chat import ChatInstance, ChatMessage
from .workflow import WorkflowExecution, WorkflowCheckpoint

# Export all models for easy imports
__all__ = [
    "User", 
    "Project", 
    "Document", 
    "ChatInstance", 
    "ChatMessage",
    "WorkflowExecution",
    "WorkflowCheckpoint"
]