# backend/app/api/v1/api.py
from fastapi import APIRouter
from .endpoints import health, auth, projects, documents, chats, workflows, websocket

api_router = APIRouter()

# Include working endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])

# WebSocket endpoints
api_router.include_router(websocket.router, prefix="/ws", tags=["websockets"])
