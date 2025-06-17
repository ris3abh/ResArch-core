from fastapi import APIRouter
from . import projects, knowledge, chats, agents, workflows, content

router = APIRouter()

router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
router.include_router(chats.router, prefix="/chats", tags=["chats"])
router.include_router(agents.router, prefix="/agents", tags=["agents"])
router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
router.include_router(content.router, prefix="/content", tags=["content"])

