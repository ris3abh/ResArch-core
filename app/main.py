# app/main.py
"""
Main FastAPI application for SpinScribe
Integrates all core components and provides API endpoints.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import uvicorn
from datetime import datetime

# Core imports
from app.core.config import settings
from app.core.exceptions import SpinScribeError
from app.database.connection import init_db, get_db

# Service imports
from app.services.project_service import get_project_service, ProjectCreateData, ProjectUpdateData
from app.services.knowledge_service import get_knowledge_service, KnowledgeCreateData
from app.services.chat_service import get_chat_service, MessageData
from app.workflows.workflow_execution_engine import workflow_engine
from app.agents.coordination.agent_coordinator import agent_coordinator, AgentType, CoordinationMode

# Database models
from app.database.models.project import Project
from app.database.models.chat_instance import ChatInstance
from app.database.models.chat_message import ChatMessage
from app.database.models.knowledge_item import KnowledgeItem
from app.database.models.human_checkpoint import HumanCheckpoint

# Pydantic models for API
from pydantic import BaseModel
from typing import Union

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SpinScribe API",
    description="Multi-Agent Content Creation System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for requests/responses
class ProjectCreate(BaseModel):
    client_name: str
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None

class ProjectUpdate(BaseModel):
    client_name: Optional[str] = None
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class ChatCreate(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class MessageCreate(BaseModel):
    content: str
    sender_type: str = "human"
    sender_id: Optional[str] = None
    message_type: str = "text"

class WorkflowStart(BaseModel):
    workflow_type: str
    content_requirements: Dict[str, Any]
    custom_config: Optional[Dict[str, Any]] = None

class KnowledgeCreate(BaseModel):
    title: str
    item_type: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class CheckpointAction(BaseModel):
    action: str  # "approve" or "reject"
    feedback: Optional[str] = None

# Exception handler
@app.exception_handler(SpinScribeError)
async def spinscribe_exception_handler(request, exc: SpinScribeError):
    return JSONResponse(
        status_code=400,
        content=exc.to_dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error_type": "InternalServerError",
            "message": "An internal error occurred",
            "details": str(exc) if settings.debug else "Contact support"
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": "connected",
            "workflow_engine": "active",
            "agent_coordinator": "ready"
        }
    }

# Project endpoints
@app.post("/api/v1/projects", response_model=Dict[str, Any])
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db)
):
    """Create a new project"""
    project_service = get_project_service()
    
    create_data = ProjectCreateData(
        client_name=project_data.client_name,
        description=project_data.description,
        configuration=project_data.configuration
    )
    
    project = project_service.create(create_data, db)
    
    return {
        "project_id": project.project_id,
        "client_name": project.client_name,
        "description": project.description,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
        "configuration": project.configuration
    }

@app.get("/api/v1/projects", response_model=List[Dict[str, Any]])
async def get_projects(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all projects"""
    project_service = get_project_service()
    projects = project_service.get_all(db, limit=limit, offset=offset)
    
    return [
        {
            "project_id": project.project_id,
            "client_name": project.client_name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat() if project.updated_at else None
        }
        for project in projects
    ]

@app.get("/api/v1/projects/{project_id}", response_model=Dict[str, Any])
async def get_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific project"""
    project_service = get_project_service()
    project = project_service.get_by_id_or_raise(project_id, db)
    
    # Get additional project statistics
    chat_service = get_chat_service()
    knowledge_service = get_knowledge_service()
    
    chats = chat_service.get_chats_by_project(project_id, db)
    knowledge_items = knowledge_service.get_by_project_id(project_id, db)
    
    return {
        "project_id": project.project_id,
        "client_name": project.client_name,
        "description": project.description,
        "status": project.status,
        "configuration": project.configuration,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "statistics": {
            "chat_instances": len(chats),
            "knowledge_items": len(knowledge_items),
            "active_chats": len([c for c in chats if c.status == "active"])
        }
    }

@app.put("/api/v1/projects/{project_id}", response_model=Dict[str, Any])
async def update_project(
    project_id: str,
    update_data: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Update a project"""
    project_service = get_project_service()
    
    update_params = ProjectUpdateData(
        client_name=update_data.client_name,
        description=update_data.description,
        configuration=update_data.configuration,
        status=update_data.status
    )
    
    project = project_service.update(project_id, update_params, db)
    
    return {
        "project_id": project.project_id,
        "client_name": project.client_name,
        "description": project.description,
        "status": project.status,
        "configuration": project.configuration,
        "updated_at": project.updated_at.isoformat()
    }

# Chat endpoints
@app.post("/api/v1/chats", response_model=Dict[str, Any])
async def create_chat(
    chat_data: ChatCreate,
    db: Session = Depends(get_db)
):
    """Create a new chat instance"""
    chat_service = get_chat_service()
    
    chat = await chat_service.create_chat_instance(
        project_id=chat_data.project_id,
        name=chat_data.name,
        description=chat_data.description,
        settings=chat_data.settings,
        db=db
    )
    
    return {
        "chat_id": chat.chat_id,
        "project_id": chat.project_id,
        "name": chat.name,
        "description": chat.description,
        "status": chat.status,
        "created_at": chat.created_at.isoformat()
    }

@app.get("/api/v1/chats/{chat_id}", response_model=Dict[str, Any])
async def get_chat(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Get chat instance details"""
    chat_service = get_chat_service()
    return await chat_service.get_chat_status(chat_id, db)

@app.get("/api/v1/projects/{project_id}/chats", response_model=List[Dict[str, Any]])
async def get_project_chats(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Get all chats for a project"""
    chat_service = get_chat_service()
    chats = chat_service.get_chats_by_project(project_id, db)
    
    return [
        {
            "chat_id": chat.chat_id,
            "name": chat.name,
            "description": chat.description,
            "status": chat.status,
            "created_at": chat.created_at.isoformat(),
            "updated_at": chat.updated_at.isoformat() if chat.updated_at else None
        }
        for chat in chats
    ]

@app.post("/api/v1/chats/{chat_id}/messages", response_model=Dict[str, Any])
async def send_message(
    chat_id: str,
    message_data: MessageCreate,
    db: Session = Depends(get_db)
):
    """Send a message to a chat"""
    chat_service = get_chat_service()
    
    message_obj = MessageData(
        content=message_data.content,
        sender_type=message_data.sender_type,
        sender_id=message_data.sender_id,
        message_type=message_data.message_type
    )
    
    message = await chat_service.send_message(chat_id, message_obj, db=db)
    
    return {
        "message_id": message.message_id,
        "chat_id": message.chat_id,
        "sender_type": message.sender_type,
        "content": message.content,
        "created_at": message.created_at.isoformat()
    }

@app.get("/api/v1/chats/{chat_id}/messages", response_model=List[Dict[str, Any]])
async def get_chat_messages(
    chat_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get messages for a chat"""
    chat_service = get_chat_service()
    messages = await chat_service.get_chat_messages(chat_id, limit, offset, db=db)
    
    return [
        {
            "message_id": msg.message_id,
            "sender_id": msg.sender_id,
            "sender_type": msg.sender_type,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "attachments": msg.attachments,
            "references": msg.references
        }
        for msg in messages
    ]

# Workflow endpoints
@app.post("/api/v1/chats/{chat_id}/workflows", response_model=Dict[str, Any])
async def start_workflow(
    chat_id: str,
    workflow_data: WorkflowStart,
    db: Session = Depends(get_db)
):
    """Start a content creation workflow"""
    chat_service = get_chat_service()
    
    workflow_id = await chat_service.start_content_workflow(
        chat_id=chat_id,
        workflow_type=workflow_data.workflow_type,
        content_requirements=workflow_data.content_requirements,
        db=db
    )
    
    return {
        "workflow_id": workflow_id,
        "chat_id": chat_id,
        "workflow_type": workflow_data.workflow_type,
        "status": "started",
        "started_at": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/workflows/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow_status(workflow_id: str):
    """Get workflow status"""
    return workflow_engine.get_workflow_status(workflow_id)

@app.get("/api/v1/workflows/types", response_model=List[Dict[str, Any]])
async def get_workflow_types():
    """Get available workflow types"""
    return workflow_engine.get_available_workflows()

@app.post("/api/v1/workflows/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow"""
    success = await workflow_engine.cancel_workflow(workflow_id)
    return {"workflow_id": workflow_id, "cancelled": success}

# Knowledge management endpoints
@app.post("/api/v1/projects/{project_id}/knowledge", response_model=Dict[str, Any])
async def create_knowledge_item(
    project_id: str,
    knowledge_data: KnowledgeCreate,
    db: Session = Depends(get_db)
):
    """Create a new knowledge item"""
    knowledge_service = get_knowledge_service()
    
    create_data = KnowledgeCreateData(
        project_id=project_id,
        title=knowledge_data.title,
        item_type=knowledge_data.item_type,
        content=knowledge_data.content,
        metadata=knowledge_data.metadata
    )
    
    knowledge_item = knowledge_service.create(create_data, db)
    
    return {
        "item_id": knowledge_item.item_id,
        "project_id": knowledge_item.project_id,
        "title": knowledge_item.title,
        "item_type": knowledge_item.item_type,
        "created_at": knowledge_item.created_at.isoformat()
    }

@app.get("/api/v1/projects/{project_id}/knowledge", response_model=List[Dict[str, Any]])
async def get_project_knowledge(
    project_id: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get knowledge items for a project"""
    knowledge_service = get_knowledge_service()
    items = knowledge_service.get_by_project_id(project_id, db, limit=limit, offset=offset)
    
    return [
        {
            "item_id": item.item_id,
            "title": item.title,
            "item_type": item.item_type,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "content_preview": str(item.content)[:200] + "..." if len(str(item.content)) > 200 else str(item.content)
        }
        for item in items
    ]

@app.get("/api/v1/knowledge/{item_id}", response_model=Dict[str, Any])
async def get_knowledge_item(
    item_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific knowledge item"""
    knowledge_service = get_knowledge_service()
    item = knowledge_service.get_by_id_or_raise(item_id, db)
    
    return {
        "item_id": item.item_id,
        "project_id": item.project_id,
        "title": item.title,
        "item_type": item.item_type,
        "content": item.content,
        "metadata": item.metadata,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat() if item.updated_at else None
    }

# Human checkpoint endpoints
@app.get("/api/v1/chats/{chat_id}/checkpoints", response_model=List[Dict[str, Any]])
async def get_chat_checkpoints(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Get active checkpoints for a chat"""
    chat_service = get_chat_service()
    checkpoints = await chat_service.get_active_checkpoints(chat_id, db)
    
    return [
        {
            "checkpoint_id": cp.checkpoint_id,
            "checkpoint_type": cp.checkpoint_type,
            "content_reference": cp.content_reference,
            "status": cp.status,
            "created_at": cp.created_at.isoformat(),
            "feedback": cp.feedback
        }
        for cp in checkpoints
    ]

@app.post("/api/v1/checkpoints/{checkpoint_id}/action")
async def handle_checkpoint(
    checkpoint_id: str,
    action_data: CheckpointAction,
    db: Session = Depends(get_db)
):
    """Approve or reject a human checkpoint"""
    chat_service = get_chat_service()
    
    if action_data.action == "approve":
        success = await chat_service.approve_checkpoint(
            checkpoint_id, action_data.feedback, db
        )
    elif action_data.action == "reject":
        success = await chat_service.reject_checkpoint(
            checkpoint_id, action_data.feedback or "No reason provided", db
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid action. Must be 'approve' or 'reject'"
        )
    
    return {
        "checkpoint_id": checkpoint_id,
        "action": action_data.action,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }

# Agent coordination endpoints
@app.post("/api/v1/projects/{project_id}/coordination", response_model=Dict[str, Any])
async def create_coordination_session(
    project_id: str,
    chat_id: str,
    agent_types: List[str] = None,
    coordination_mode: str = "sequential"
):
    """Create a multi-agent coordination session"""
    
    # Convert string agent types to enum
    if agent_types:
        converted_types = []
        for agent_type in agent_types:
            try:
                converted_types.append(AgentType(agent_type))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid agent type: {agent_type}"
                )
    else:
        # Default agent set
        converted_types = [
            AgentType.COORDINATOR,
            AgentType.STYLE_ANALYZER,
            AgentType.CONTENT_PLANNER,
            AgentType.CONTENT_GENERATOR,
            AgentType.EDITOR_QA
        ]
    
    # Convert coordination mode
    try:
        mode = CoordinationMode(coordination_mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid coordination mode: {coordination_mode}"
        )
    
    session_id = await agent_coordinator.create_collaboration_session(
        project_id=project_id,
        chat_id=chat_id,
        agent_types=converted_types,
        coordination_mode=mode
    )
    
    return {
        "session_id": session_id,
        "project_id": project_id,
        "chat_id": chat_id,
        "agent_types": agent_types,
        "coordination_mode": coordination_mode,
        "created_at": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/coordination/{session_id}", response_model=Dict[str, Any])
async def get_coordination_status(session_id: str):
    """Get coordination session status"""
    return agent_coordinator.get_session_status(session_id)

@app.post("/api/v1/coordination/{session_id}/content", response_model=Dict[str, Any])
async def coordinate_content_creation(
    session_id: str,
    content_brief: Dict[str, Any],
    workflow_type: str = "blog_post"
):
    """Coordinate content creation through multi-agent session"""
    result = await agent_coordinator.coordinate_content_creation(
        session_id=session_id,
        content_brief=content_brief,
        workflow_type=workflow_type
    )
    
    return result

@app.get("/api/v1/agents/types", response_model=List[Dict[str, Any]])
async def get_agent_types():
    """Get available agent types"""
    return agent_coordinator.get_available_agent_types()

# System status endpoints
@app.get("/api/v1/system/status", response_model=Dict[str, Any])
async def get_system_status():
    """Get comprehensive system status"""
    return {
        "system": "SpinScribe",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "connected",
            "workflow_engine": {
                "status": "active",
                "active_workflows": len(workflow_engine.active_workflows)
            },
            "agent_coordinator": {
                "status": "ready",
                "active_sessions": len(agent_coordinator.active_sessions)
            },
            "available_workflows": len(workflow_engine.workflow_definitions),
            "available_agents": len(AgentType)
        },
        "configuration": {
            "debug_mode": settings.debug,
            "environment": settings.environment
        }
    }

# Test endpoints for development
@app.post("/api/v1/test/complete-workflow")
async def test_complete_workflow(
    project_name: str = "Test Project",
    content_type: str = "blog_post",
    db: Session = Depends(get_db)
):
    """Test complete workflow from project creation to content delivery"""
    
    try:
        # 1. Create test project
        project_service = get_project_service()
        project_data = ProjectCreateData(
            client_name=project_name,
            description="Test project for complete workflow",
            configuration={
                "brand_voice": "professional and informative",
                "target_audience": "general",
                "content_types": ["blog", "documentation"]
            }
        )
        project = project_service.create(project_data, db)
        
        # 2. Create chat instance
        chat_service = get_chat_service()
        chat = await chat_service.create_chat_instance(
            project_id=project.project_id,
            name="Test Workflow Chat",
            description="Testing complete workflow",
            db=db
        )
        
        # 3. Add sample knowledge
        knowledge_service = get_knowledge_service()
        knowledge_data = KnowledgeCreateData(
            project_id=project.project_id,
            title="Sample Content",
            item_type="content_sample",
            content={
                "text": "This is a sample piece of content that demonstrates our professional and informative brand voice. We focus on clarity and providing value to our readers."
            }
        )
        knowledge_service.create(knowledge_data, db)
        
        # 4. Start workflow
        content_requirements = {
            "content_type": content_type,
            "topic": "The Future of AI in Content Creation",
            "target_audience": "business professionals",
            "word_count": 800,
            "tone": "professional",
            "key_points": [
                "Current state of AI in content creation",
                "Benefits and challenges",
                "Future predictions"
            ]
        }
        
        workflow_id = await chat_service.start_content_workflow(
            chat_id=chat.chat_id,
            workflow_type=content_type,
            content_requirements=content_requirements,
            db=db
        )
        
        return {
            "test_status": "success",
            "project_id": project.project_id,
            "chat_id": chat.chat_id,
            "workflow_id": workflow_id,
            "message": "Complete workflow test initiated successfully",
            "next_steps": [
                f"Monitor workflow at /api/v1/workflows/{workflow_id}",
                f"Check chat messages at /api/v1/chats/{chat.chat_id}/messages",
                f"Review checkpoints at /api/v1/chats/{chat.chat_id}/checkpoints"
            ]
        }
        
    except Exception as e:
        logger.error(f"Test workflow failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Test workflow failed: {str(e)}"
        )

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting SpinScribe application...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Additional startup tasks
    logger.info("SpinScribe application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down SpinScribe application...")
    
    # Cancel any active workflows
    for workflow_id in list(workflow_engine.active_workflows.keys()):
        await workflow_engine.cancel_workflow(workflow_id)
    
    # End coordination sessions
    for session_id in list(agent_coordinator.active_sessions.keys()):
        await agent_coordinator.end_session(session_id)
    
    logger.info("SpinScribe application shutdown complete")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )