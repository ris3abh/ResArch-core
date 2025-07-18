# backend/main.py
"""
FastAPI Backend for Spinscribe Web Application
Integrates with existing CAMEL infrastructure using Service Wrapper Pattern
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# Database and infrastructure
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.database import get_db
from backend.database.models import WorkflowExecution, ChatInstance, User, Project

# Service imports - using existing Spinscribe modules
from backend.services.camel_workflow_service import (
    CAMELWorkflowService, 
    CheckpointManager,
    WorkflowCreateRequest,
    WorkflowEventBridge,
    create_workflow_service,
    create_checkpoint_manager
)

# WebSocket management
from backend.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

# Global service instances
workflow_service: CAMELWorkflowService = None
checkpoint_manager: CheckpointManager = None
websocket_manager: WebSocketManager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global workflow_service, checkpoint_manager, websocket_manager
    
    logger.info("🚀 Starting Spinscribe Backend")
    
    # Initialize services
    workflow_service = create_workflow_service()
    checkpoint_manager = create_checkpoint_manager(workflow_service)
    websocket_manager = WebSocketManager()
    
    logger.info("✅ Services initialized")
    yield
    
    logger.info("🛑 Shutting down Spinscribe Backend")

app = FastAPI(
    title="Spinscribe API",
    description="Multi-Agent Content Creation System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class WorkflowCreateRequestModel(BaseModel):
    project_id: str
    title: str
    content_type: str
    task_description: str
    workflow_type: str = "enhanced"
    enable_checkpoints: bool = True
    client_documents_path: Optional[str] = None
    first_draft: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CheckpointApprovalModel(BaseModel):
    decision: str  # 'approved' or 'rejected'
    feedback: Optional[str] = None
    user_id: str

class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    progress: float
    current_stage: str
    started_at: str
    title: str
    content_type: str
    checkpoints_enabled: bool
    recent_events: List[Dict[str, Any]]

# Authentication dependency (simplified for demo)
async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Get current authenticated user. Simplified for demo."""
    # In production, implement proper JWT authentication
    # For now, return a mock user
    return User(id="demo_user", email="demo@spinscribe.com", first_name="Demo", last_name="User")

# ================================
# WORKFLOW MANAGEMENT ENDPOINTS
# ================================

@app.post("/api/v1/workflows", response_model=Dict[str, str])
async def create_workflow(
    request: WorkflowCreateRequestModel,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create and start a new workflow.
    Uses existing CAMEL infrastructure with zero changes to agent communication.
    """
    try:
        # Convert to internal request model
        workflow_request = WorkflowCreateRequest(
            project_id=request.project_id,
            title=request.title,
            content_type=request.content_type,
            task_description=request.task_description,
            workflow_type=request.workflow_type,
            enable_checkpoints=request.enable_checkpoints,
            client_documents_path=request.client_documents_path,
            first_draft=request.first_draft,
            metadata=request.metadata
        )
        
        # Start workflow using existing CAMEL system
        workflow_id = await workflow_service.start_workflow(workflow_request)
        
        # Store workflow in database
        db_workflow = WorkflowExecution(
            workflow_id=workflow_id,
            project_id=request.project_id,
            user_id=current_user.id,
            title=request.title,
            content_type=request.content_type,
            workflow_type=request.workflow_type,
            status="running",
            current_stage="initialization",
            enable_checkpoints=request.enable_checkpoints,
            started_at=datetime.utcnow()
        )
        
        db.add(db_workflow)
        await db.commit()
        
        # Setup WebSocket monitoring
        bridge = WorkflowEventBridge(websocket_manager)
        await bridge.monitor_camel_workflow(workflow_id, workflow_service)
        
        return {"workflow_id": workflow_id, "status": "started"}
        
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workflows/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get workflow status and progress."""
    try:
        status = await workflow_service.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
            
        return WorkflowStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/workflows/{workflow_id}/pause")
async def pause_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Pause a running workflow."""
    try:
        success = await workflow_service.pause_workflow(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found or cannot be paused")
            
        return {"status": "paused"}
        
    except Exception as e:
        logger.error(f"Failed to pause workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a running workflow."""
    try:
        success = await workflow_service.cancel_workflow(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found")
            
        return {"status": "cancelled"}
        
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workflows/{workflow_id}/logs")
async def get_workflow_logs(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed workflow execution logs."""
    try:
        logs = await workflow_service.get_workflow_logs(workflow_id)
        return {"logs": logs}
        
    except Exception as e:
        logger.error(f"Failed to get workflow logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workflows")
async def list_workflows(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List workflows, optionally filtered by project."""
    try:
        workflows = await workflow_service.list_workflows(project_id)
        return {"workflows": workflows}
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# CHECKPOINT MANAGEMENT ENDPOINTS
# ================================

@app.get("/api/v1/workflows/{workflow_id}/checkpoints")
async def list_workflow_checkpoints(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """List checkpoints for a specific workflow."""
    try:
        checkpoints = await checkpoint_manager.list_pending_checkpoints(workflow_id)
        return {"checkpoints": checkpoints}
        
    except Exception as e:
        logger.error(f"Failed to list checkpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/checkpoints/{checkpoint_id}")
async def get_checkpoint_details(
    checkpoint_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed checkpoint information."""
    try:
        checkpoint = await checkpoint_manager.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
            
        return checkpoint
        
    except Exception as e:
        logger.error(f"Failed to get checkpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/checkpoints/{checkpoint_id}/approve")
async def approve_checkpoint(
    checkpoint_id: str,
    approval: CheckpointApprovalModel,
    current_user: User = Depends(get_current_user)
):
    """
    Approve or reject a checkpoint.
    Feeds back into CAMEL's HumanLayer system.
    """
    try:
        success = await checkpoint_manager.approve_checkpoint(
            checkpoint_id=checkpoint_id,
            user_id=current_user.id,
            decision=approval.decision,
            feedback=approval.feedback
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
            
        return {"status": "approved" if approval.decision.lower() == "approved" else "rejected"}
        
    except Exception as e:
        logger.error(f"Failed to approve checkpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# PROJECT MANAGEMENT ENDPOINTS
# ================================

@app.get("/api/v1/projects")
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user projects."""
    try:
        # Query projects from database
        # Implementation depends on your specific database setup
        return {"projects": []}  # Placeholder
        
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/projects")
async def create_project(
    project_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    try:
        # Create project in database
        # Implementation depends on your specific database setup
        return {"project_id": "new_project_id"}  # Placeholder
        
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# WEBSOCKET ENDPOINTS
# ================================

@app.websocket("/api/v1/workflows/{workflow_id}/live")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """
    WebSocket endpoint for real-time workflow updates.
    Provides live progress and event updates.
    """
    await websocket.accept()
    
    try:
        # Add client to WebSocket manager
        await websocket_manager.add_client(workflow_id, websocket)
        
        # Send initial status
        status = await workflow_service.get_workflow_status(workflow_id)
        if status:
            await websocket.send_json({
                "type": "initial_status",
                "data": status
            })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                # Handle client messages if needed
                logger.info(f"Received WebSocket message: {data}")
                
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Remove client from manager
        await websocket_manager.remove_client(workflow_id, websocket)

# ================================
# HEALTH CHECK ENDPOINTS
# ================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "workflow_service": "active" if workflow_service else "inactive",
            "checkpoint_manager": "active" if checkpoint_manager else "inactive",
            "websocket_manager": "active" if websocket_manager else "inactive"
        }
    }

@app.get("/api/v1/system/status")
async def system_status():
    """Get system status and metrics."""
    try:
        active_workflows = len(workflow_service.active_workflows) if workflow_service else 0
        pending_checkpoints = len(checkpoint_manager.pending_checkpoints) if checkpoint_manager else 0
        
        return {
            "active_workflows": active_workflows,
            "pending_checkpoints": pending_checkpoints,
            "websocket_connections": websocket_manager.get_connection_count() if websocket_manager else 0,
            "uptime": "N/A"  # Implement uptime tracking
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )