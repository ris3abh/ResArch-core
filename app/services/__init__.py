# app/services/__init__.py - Service Registration
"""
Service module initialization - Register all services
This ensures all services are registered when the module is imported
"""

from app.services.base_service import ServiceRegistry

# Import and register all services
from app.services.project_service import ProjectService
from app.services.knowledge_service import KnowledgeService  
from app.services.chat_service import ChatService

# Register services with the registry
ServiceRegistry.register(ProjectService)
ServiceRegistry.register(KnowledgeService)
ServiceRegistry.register(ChatService)

# Import the get_service functions for easy access
from app.services.project_service import get_project_service
from app.services.knowledge_service import get_knowledge_service
from app.services.chat_service import get_chat_service

__all__ = [
    'get_project_service',
    'get_knowledge_service', 
    'get_chat_service',
    'ServiceRegistry'
]