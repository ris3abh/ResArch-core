from fastapi import APIRouter
from .endpoints import health, auth, projects, documents, chats

api_router = APIRouter()

# Include working endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])

# TODO: Add these later
# api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
# api_router.include_router(checkpoints.router, prefix="/checkpoints", tags=["checkpoints"])
