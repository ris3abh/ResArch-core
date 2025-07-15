# app/api/v1/router.py
"""
Main API router that combines all endpoint modules.
"""
from fastapi import APIRouter

from app.api.v1 import auth, projects

# Create main API router
api_router = APIRouter()

# Include authentication routes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# Include project management routes
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"],
)

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns the API status and basic system information.
    """
    return {
        "status": "healthy",
        "service": "SpinScribe API",
        "version": "1.0.0"
    }

# API info endpoint
@api_router.get("/info")
async def api_info():
    """
    API information endpoint.
    
    Returns information about available endpoints and features.
    """
    return {
        "name": "SpinScribe API",
        "version": "1.0.0",
        "description": "Multi-Agent Content Creation System for Spinutech",
        "features": [
            "User authentication with JWT tokens",
            "Project management (personal and shared)",
            "Real-time chat with AI agents",
            "Document upload and management",
            "Content draft creation and versioning",
            "Knowledge base for RAG",
            "Workflow task management"
        ],
        "endpoints": {
            "authentication": "/auth",
            "projects": "/projects",
            "documents": "/documents",  # TODO: Implement
            "chat": "/chat",            # TODO: Implement
            "content": "/content",      # TODO: Implement
            "workflow": "/workflow"     # TODO: Implement
        }
    }