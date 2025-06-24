# app/agents/memory/__init__.py
"""
Memory module for SpinScribe agents
Integrates CAMEL memory system with project-specific context
"""

from .agent_memory import AgentMemoryManager, ProjectMemory
from .conversation_memory import ConversationMemory
from .knowledge_memory import KnowledgeMemory

__all__ = [
    'AgentMemoryManager',
    'ProjectMemory', 
    'ConversationMemory',
    'KnowledgeMemory'
]