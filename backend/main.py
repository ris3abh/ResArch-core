# File: backend/main.py
"""
Complete FastAPI Backend for Spinscribe Web Application
Integrates with existing CAMEL infrastructure using Service Wrapper Pattern
"""

import os
import sys
import logging
import asyncio
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import (
    FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, 
    UploadFile, File, Form, BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

# Database imports
from backend.database.database import get_db, engine, Base
from backend.database.models import (
    User, Project, Document, ChatInstance, ChatMessage, 
    WorkflowExecution, WorkflowCheckpoint, ContentDraft, KnowledgeItem
)

# Try to import Spinscribe modules
SPINSCRIBE_AVAILABLE = False
try:
    from spinscribe.enhanced_process import run_enhanced_content_task
    from spinscribe.workforce.enhanced_builder import create_enhanced_workforce
    from spinscribe.knowledge.document_processor import DocumentProcessor
    from spinscribe.knowledge.knowledge_manager import KnowledgeManager
    SPINSCRIBE_AVAILABLE = True
    print("✅ Spinscribe modules imported successfully")
except ImportError as e:
    print(f"⚠️ Could not import Spinscribe modules: {e}")
    print("Running in API-only mode without Spinscribe functionality")

# WebSocket manager
from backend.services.websocket_manager import WebSocketManager

# Configuration
from backend.config.settings import settings

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
websocket_manager = WebSocketManager()
document_processor = None
knowledge_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global document_processor, knowledge_manager
    
    try:
        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
        
        # Initialize Spinscribe services if available
        if SPINSCRIBE_AVAILABLE:
            try:
                document_processor = DocumentProcessor()
                knowledge_manager = KnowledgeManager()
                logger.info("✅ Spinscribe services initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Spinscribe services: {e}")
        
        # Create upload directory
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory ready: {upload_dir}")
        
        logger.info("🚀 Backend services started successfully")
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise
    finally:
        logger.info("🔄 Shutting down backend services")

# Create FastAPI app
app = FastAPI(
    title="Spinscribe API",
    description="Multi-Agent Content Creation Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
if Path("uploads").exists():
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Pydantic models
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    client_name: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    client_name: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatCreate(BaseModel):
    name: str
    description: Optional[str] = None
    chat_type: str = "standard"

class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"

class WorkflowCreate(BaseModel):
    title: str
    content_type: str
    project_id: str
    enable_checkpoints: bool = True
    enable_human_interaction: bool = True
    timeout_seconds: int = 600

class WorkflowResponse(BaseModel):
    id: str
    workflow_id: str
    title: str
    status: str
    progress_percentage: float
    current_stage: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Authentication (simplified for development)
async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Get current authenticated user - simplified version for development."""
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create a default user for development
        user = User(
            id=str(uuid.uuid4()),
            email="dev@spinutech.com",
            first_name="Development",
            last_name="User"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Created default development user")
    
    return user

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "spinscribe_available": SPINSCRIBE_AVAILABLE,
        "version": "1.0.0"
    }

# System status
@app.get("/api/v1/system/status")
async def system_status():
    """Get system status and statistics."""
    return {
        "status": "operational",
        "spinscribe_available": SPINSCRIBE_AVAILABLE,
        "websocket_connections": websocket_manager.get_stats(),
        "timestamp": datetime.now().isoformat()
    }

# Project Management
@app.get("/api/v1/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user projects."""
    result = await db.execute(
        select(Project).where(Project.created_by == current_user.id)
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return projects

@app.post("/api/v1/projects", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new project."""
    project = Project(
        id=str(uuid.uuid4()),
        name=project_data.name,
        description=project_data.description,
        client_name=project_data.client_name,
        created_by=current_user.id
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    logger.info(f"Created project: {project.name} (ID: {project.id})")
    return project

@app.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project details."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project

@app.put("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.name = project_data.name
    project.description = project_data.description
    project.client_name = project_data.client_name
    project.updated_at = datetime.now()
    
    await db.commit()
    await db.refresh(project)
    
    return project

# Document Management
@app.post("/api/v1/projects/{project_id}/documents")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    document_type: str = Form("general"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload document to project."""
    # Verify project exists and user has access
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    # Save file
    upload_dir = Path(settings.UPLOAD_DIR) / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix if file.filename else ""
    file_path = upload_dir / f"{file_id}{file_extension}"
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create document record
    document = Document(
        id=file_id,
        project_id=project_id,
        filename=f"{file_id}{file_extension}",
        original_filename=file.filename or "unknown",
        file_size=len(content),
        file_type=file.content_type or "application/octet-stream",
        file_path=str(file_path),
        document_type=document_type,
        uploaded_by=current_user.id,
        processing_status="pending"
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    # Process document with Spinscribe in background
    if SPINSCRIBE_AVAILABLE and document_processor:
        background_tasks.add_task(process_document_background, document.id, file_path, project_id, db)
    
    logger.info(f"Uploaded document: {file.filename} to project {project_id}")
    
    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "status": document.processing_status,
        "file_size": document.file_size,
        "document_type": document.document_type
    }

async def process_document_background(document_id: str, file_path: Path, project_id: str, db: AsyncSession):
    """Background task to process document with Spinscribe."""
    try:
        # Get fresh database session for background task
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Document).where(Document.id == document_id))
            document = result.scalar_one_or_none()
            
            if not document:
                return
            
            document.processing_status = "processing"
            await session.commit()
            
            # Process with Spinscribe
            if document_processor:
                await document_processor.process_document_async(file_path, project_id, document_id)
                document.processing_status = "completed"
                document.processed_at = datetime.now()
            else:
                document.processing_status = "failed"
            
            await session.commit()
            
    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {e}")
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Document).where(Document.id == document_id))
            document = result.scalar_one_or_none()
            if document:
                document.processing_status = "failed"
                await session.commit()

@app.get("/api/v1/projects/{project_id}/documents")
async def list_documents(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List project documents."""
    # Verify project access
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get documents
    result = await db.execute(
        select(Document).where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()
    
    return [
        {
            "id": doc.id,
            "filename": doc.original_filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "document_type": doc.document_type,
            "processing_status": doc.processing_status,
            "created_at": doc.created_at,
            "processed_at": doc.processed_at
        }
        for doc in documents
    ]

# Chat Management
@app.post("/api/v1/projects/{project_id}/chats")
async def create_chat(
    project_id: str,
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new chat instance."""
    # Verify project access
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    chat = ChatInstance(
        id=str(uuid.uuid4()),
        project_id=project_id,
        name=chat_data.name,
        description=chat_data.description,
        chat_type=chat_data.chat_type,
        created_by=current_user.id
    )
    
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    
    logger.info(f"Created chat: {chat.name} in project {project_id}")
    
    return {
        "id": chat.id,
        "name": chat.name,
        "description": chat.description,
        "chat_type": chat.chat_type,
        "is_active": chat.is_active,
        "created_at": chat.created_at
    }

@app.get("/api/v1/projects/{project_id}/chats")
async def list_chats(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List project chats."""
    result = await db.execute(
        select(ChatInstance).where(
            ChatInstance.project_id == project_id,
            ChatInstance.created_by == current_user.id
        ).order_by(ChatInstance.created_at.desc())
    )
    chats = result.scalars().all()
    
    return [
        {
            "id": chat.id,
            "name": chat.name,
            "description": chat.description,
            "chat_type": chat.chat_type,
            "is_active": chat.is_active,
            "created_at": chat.created_at,
            "last_activity": chat.last_activity
        }
        for chat in chats
    ]

@app.post("/api/v1/chats/{chat_id}/messages")
async def send_message(
    chat_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send message to chat."""
    # Verify chat access
    result = await db.execute(
        select(ChatInstance).where(ChatInstance.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    message = ChatMessage(
        id=str(uuid.uuid4()),
        chat_instance_id=chat_id,
        sender_id=current_user.id,
        sender_type="user",
        message_content=message_data.content,
        message_type=message_data.message_type
    )
    
    db.add(message)
    
    # Update chat last activity
    chat.last_activity = datetime.now()
    
    await db.commit()
    await db.refresh(message)
    
    # Broadcast to WebSocket clients
    await websocket_manager.broadcast_to_chat(chat_id, {
        "type": "new_message",
        "message": {
            "id": message.id,
            "content": message.message_content,
            "sender_type": message.sender_type,
            "sender_id": message.sender_id,
            "created_at": message.created_at.isoformat()
        }
    })
    
    return {
        "message_id": message.id,
        "status": "sent",
        "created_at": message.created_at
    }

@app.get("/api/v1/chats/{chat_id}/messages")
async def get_messages(
    chat_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat messages."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_instance_id == chat_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()
    
    return [
        {
            "id": msg.id,
            "content": msg.message_content,
            "sender_type": msg.sender_type,
            "sender_id": msg.sender_id,
            "agent_type": msg.agent_type,
            "message_type": msg.message_type,
            "created_at": msg.created_at,
            "metadata": msg.metadata
        }
        for msg in reversed(messages)
    ]

# Workflow Management
@app.post("/api/v1/workflows", response_model=WorkflowResponse)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create and start new workflow."""
    if not SPINSCRIBE_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Spinscribe services not available"
        )
    
    # Verify project access
    result = await db.execute(
        select(Project).where(
            Project.id == workflow_data.project_id,
            Project.created_by == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workflow_id = f"workflow_{int(datetime.now().timestamp())}_{workflow_data.project_id}"
    
    workflow = WorkflowExecution(
        id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        project_id=workflow_data.project_id,
        user_id=current_user.id,
        title=workflow_data.title,
        content_type=workflow_data.content_type,
        workflow_type="enhanced",
        status="pending",
        current_stage="initialization",
        timeout_seconds=workflow_data.timeout_seconds,
        enable_human_interaction=workflow_data.enable_human_interaction,
        enable_checkpoints=workflow_data.enable_checkpoints
    )
    
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    
    # Start workflow in background
    background_tasks.add_task(
        run_workflow_background, workflow_id, workflow_data, current_user.id
    )
    
    logger.info(f"Created workflow: {workflow.title} (ID: {workflow_id})")
    
    return WorkflowResponse(
        id=workflow.id,
        workflow_id=workflow.workflow_id,
        title=workflow.title,
        status=workflow.status,
        progress_percentage=workflow.progress_percentage,
        current_stage=workflow.current_stage,
        created_at=workflow.created_at
    )

async def run_workflow_background(workflow_id: str, workflow_data: WorkflowCreate, user_id: str):
    """Run Spinscribe workflow in background."""
    async with AsyncSession(engine) as db:
        try:
            # Update status to running
            result = await db.execute(
                select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
            )
            workflow = result.scalar_one_or_none()
            if not workflow:
                return
            
            workflow.status = "running"
            workflow.started_at = datetime.now()
            workflow.current_stage = "starting"
            await db.commit()
            
            # Notify via WebSocket
            await websocket_manager.notify_workflow_progress(
                workflow_id, 10.0, "starting", {"message": "Workflow started"}
            )
            
            # Run the enhanced content task
            result = await run_enhanced_content_task(
                title=workflow_data.title,
                content_type=workflow_data.content_type,
                project_id=workflow_data.project_id,
                timeout_seconds=workflow_data.timeout_seconds,
                enable_human_interaction=workflow_data.enable_human_interaction,
                enable_checkpoints=workflow_data.enable_checkpoints
            )
            
            # Update workflow with results
            workflow.status = result.get('status', 'completed')
            workflow.final_content = result.get('final_content')
            workflow.progress_percentage = 100.0
            workflow.completed_at = datetime.now()
            workflow.current_stage = "completed"
            
            if 'error' in result:
                workflow.error_details = {"error": result['error']}
                workflow.status = "failed"
            
            await db.commit()
            
            # Notify completion
            if workflow.status == "completed":
                await websocket_manager.notify_workflow_complete(workflow_id, result)
            else:
                await websocket_manager.notify_workflow_error(
                    workflow_id, result.get('error', 'Unknown error')
                )
            
            logger.info(f"Workflow {workflow_id} completed with status: {workflow.status}")
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            
            # Update workflow status
            result = await db.execute(
                select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
            )
            workflow = result.scalar_one_or_none()
            if workflow:
                workflow.status = "failed"
                workflow.error_details = {"error": str(e)}
                workflow.current_stage = "failed"
                await db.commit()
                
                await websocket_manager.notify_workflow_error(workflow_id, str(e))

@app.get("/api/v1/workflows/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get workflow status."""
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.user_id == current_user.id
        )
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "workflow_id": workflow.workflow_id,
        "title": workflow.title,
        "status": workflow.status,
        "progress_percentage": workflow.progress_percentage,
        "current_stage": workflow.current_stage,
        "started_at": workflow.started_at,
        "completed_at": workflow.completed_at,
        "final_content": workflow.final_content,
        "error_details": workflow.error_details,
        "enable_checkpoints": workflow.enable_checkpoints,
        "enable_human_interaction": workflow.enable_human_interaction
    }

@app.get("/api/v1/workflows")
async def list_workflows(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user workflows."""
    query = select(WorkflowExecution).where(WorkflowExecution.user_id == current_user.id)
    
    if project_id:
        query = query.where(WorkflowExecution.project_id == project_id)
    
    result = await db.execute(query.order_by(WorkflowExecution.created_at.desc()))
    workflows = result.scalars().all()
    
    return [
        {
            "workflow_id": wf.workflow_id,
            "title": wf.title,
            "content_type": wf.content_type,
            "status": wf.status,
            "progress_percentage": wf.progress_percentage,
            "current_stage": wf.current_stage,
            "created_at": wf.created_at,
            "started_at": wf.started_at,
            "completed_at": wf.completed_at
        }
        for wf in workflows
    ]

@app.post("/api/v1/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel running workflow."""
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.user_id == current_user.id
        )
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Workflow cannot be cancelled")
    
    workflow.status = "cancelled"
    workflow.completed_at = datetime.now()
    workflow.current_stage = "cancelled"
    
    await db.commit()
    
    await websocket_manager.broadcast_to_workflow(workflow_id, {
        "type": "workflow_cancelled",
        "message": "Workflow has been cancelled"
    })
    
    return {"message": "Workflow cancelled", "status": "cancelled"}

# Content Drafts
@app.get("/api/v1/projects/{project_id}/drafts")
async def list_content_drafts(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List content drafts for project."""
    result = await db.execute(
        select(ContentDraft).where(
            ContentDraft.project_id == project_id,
            ContentDraft.created_by == current_user.id
        ).order_by(ContentDraft.created_at.desc())
    )
    drafts = result.scalars().all()
    
    return [
        {
            "id": draft.id,
            "title": draft.title,
            "content_type": draft.content_type,
            "status": draft.status,
            "draft_version": draft.draft_version,
            "word_count": draft.word_count,
            "created_at": draft.created_at,
            "updated_at": draft.updated_at
        }
        for draft in drafts
    ]

@app.get("/api/v1/drafts/{draft_id}")
async def get_content_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get content draft details."""
    result = await db.execute(
        select(ContentDraft).where(
            ContentDraft.id == draft_id,
            ContentDraft.created_by == current_user.id
        )
    )
    draft = result.scalar_one_or_none()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    return {
        "id": draft.id,
        "title": draft.title,
        "content_type": draft.content_type,
        "draft_content": draft.draft_content,
        "status": draft.status,
        "draft_version": draft.draft_version,
        "metadata": draft.metadata,
        "word_count": draft.word_count,
        "character_count": draft.character_count,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at
    }

# WebSocket endpoints
@app.websocket("/api/v1/ws/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: str):
    """WebSocket endpoint for real-time chat updates."""
    await websocket_manager.connect(websocket, chat_id, "chat")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                await websocket_manager.handle_message(websocket, message_data)
            except json.JSONDecodeError:
                await websocket_manager.connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

@app.websocket("/api/v1/ws/workflow/{workflow_id}")
async def websocket_workflow(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for workflow progress updates."""
    await websocket_manager.connect(websocket, workflow_id, "workflow")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                await websocket_manager.handle_message(websocket, message_data)
            except json.JSONDecodeError:
                await websocket_manager.connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

# Statistics and Analytics
@app.get("/api/v1/analytics/overview")
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics overview for user."""
    # Get counts
    projects_count = await db.scalar(
        select(func.count(Project.id)).where(Project.created_by == current_user.id)
    )
    
    workflows_count = await db.scalar(
        select(func.count(WorkflowExecution.id)).where(WorkflowExecution.user_id == current_user.id)
    )
    
    documents_count = await db.scalar(
        select(func.count(Document.id))
        .join(Project, Document.project_id == Project.id)
        .where(Project.created_by == current_user.id)
    )
    
    chats_count = await db.scalar(
        select(func.count(ChatInstance.id))
        .join(Project, ChatInstance.project_id == Project.id)
        .where(Project.created_by == current_user.id)
    )
    
    # Get recent workflows
    recent_workflows = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.user_id == current_user.id)
        .order_by(WorkflowExecution.created_at.desc())
        .limit(5)
    )
    
    return {
        "totals": {
            "projects": projects_count or 0,
            "workflows": workflows_count or 0,
            "documents": documents_count or 0,
            "chats": chats_count or 0
        },
        "recent_workflows": [
            {
                "workflow_id": wf.workflow_id,
                "title": wf.title,
                "status": wf.status,
                "created_at": wf.created_at
            }
            for wf in recent_workflows.scalars()
        ],
        "system_status": {
            "spinscribe_available": SPINSCRIBE_AVAILABLE,
            "websocket_connections": websocket_manager.get_stats()
        }
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Not found", "detail": "The requested resource was not found"}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "detail": "An unexpected error occurred"}

# Development endpoints (remove in production)
if settings.DEBUG:
    @app.get("/api/v1/dev/reset-db")
    async def reset_database():
        """Reset database for development."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        return {"message": "Database reset successfully"}
    
    @app.get("/api/v1/dev/sample-data")
    async def create_sample_data(db: AsyncSession = Depends(get_db)):
        """Create sample data for development."""
        # Create sample user
        user = User(
            id="sample-user",
            email="sample@spinutech.com",
            first_name="Sample",
            last_name="User"
        )
        db.add(user)
        
        # Create sample project
        project = Project(
            id="sample-project",
            name="Sample Project",
            description="A sample project for testing",
            client_name="Sample Client",
            created_by="sample-user"
        )
        db.add(project)
        
        await db.commit()
        return {"message": "Sample data created successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )