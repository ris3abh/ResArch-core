from fastapi import APIRouter

from nexustalk.api.v1 import auth, clients, conversations, agents

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(clients.router, prefix="/clients", tags=["Client Management"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agent Management"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])

