# backend/app/api/v1/endpoints/workflows.py (FIXED VERSION)
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.workflow import WorkflowExecution, WorkflowCheckpoint
from app.schemas.workflow import (
    WorkflowCreateRequest, 
    WorkflowResponse, 
    CheckpointResponse, 
    CheckpointApproval
)
from services.project.project_service import ProjectService
from services.workflow.camel_workflow_service import workflow_service
from app.core.websocket_manager import websocket_manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Connect the workflow service to websocket manager
workflow_service.set_websocket_manager(websocket_manager)

@router.post("/start", response_model=WorkflowResponse)
async def start_spinscribe_workflow(
    request: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start the complete Spinscribe multi-agent workflow with real CAMEL integration."""
    try:
        # Validate project access
        project = await ProjectService.get_project_by_id(db, request.project_id, str(current_user.id))
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
        # Validate chat exists if provided
        if request.chat_id:
            from app.models.chat import ChatInstance
            chat = await db.get(ChatInstance, request.chat_id)
            if not chat or str(chat.project_id) != request.project_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chat ID")
        
        logger.info(f"🚀 Starting Spinscribe workflow for user {current_user.email}")
        logger.info(f"   Project: {request.project_id}")
        logger.info(f"   Title: {request.title}")
        logger.info(f"   Content Type: {request.content_type}")
        logger.info(f"   Has Initial Draft: {bool(request.initial_draft)}")
        logger.info(f"   Use Project Documents: {request.use_project_documents}")
        
        # Generate unique workflow ID first
        unique_workflow_id = str(uuid.uuid4())
        
        # Create chat_id if not provided - generate a proper UUID instead of string concatenation
        if request.chat_id:
            final_chat_id = request.chat_id
        else:
            # Generate a proper UUID for chat_id instead of concatenating strings
            final_chat_id = str(uuid.uuid4())
        
        # Start the actual Spinscribe workflow with the pre-generated ID
        workflow_id = await workflow_service.start_workflow(
            db=db,
            project_id=request.project_id,
            user_id=str(current_user.id),
            chat_id=final_chat_id,
            title=request.title,
            content_type=request.content_type,
            initial_draft=request.initial_draft,
            use_project_documents=request.use_project_documents,
            workflow_id=unique_workflow_id  # Pass the pre-generated ID
        )
        
        logger.info(f"✅ Workflow started successfully: {workflow_id}")
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="starting",
            message="🚀 SpinScribe multi-agent workflow started successfully",
            project_id=request.project_id,
            title=request.title,
            content_type=request.content_type,
            current_stage="initialization",
            progress=0.0
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to start workflow: {str(e)}"
        )

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_status(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed workflow status including live agent updates."""
    try:
        # Get workflow from database
        workflow = await db.get(WorkflowExecution, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        
        # Check user access
        if str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        # Get live status from workflow service
        live_status = workflow_service.get_workflow_status(workflow_id)
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status=workflow.status,
            current_stage=workflow.current_stage,
            progress=workflow.progress_percentage,
            message=f"Workflow is {workflow.status}",
            project_id=str(workflow.project_id),
            title=workflow.title,
            content_type=workflow.content_type,
            final_content=workflow.final_content,
            created_at=workflow.created_at,
            completed_at=workflow.completed_at,
            live_data=live_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get workflow status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to retrieve workflow status"
        )

# Rest of the endpoints remain the same...
@router.post("/checkpoints/{checkpoint_id}/approve")
async def approve_checkpoint(
    checkpoint_id: str,
    approval: CheckpointApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a workflow checkpoint and continue the agent workflow."""
    try:
        checkpoint = await db.get(WorkflowCheckpoint, checkpoint_id)
        if not checkpoint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found")
        
        workflow = await db.get(WorkflowExecution, checkpoint.workflow_id)
        if not workflow or str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        logger.info(f"✅ Approving checkpoint {checkpoint_id} for workflow {checkpoint.workflow_id}")
        logger.info(f"   User feedback: {approval.feedback}")
        
        # Update checkpoint status
        checkpoint.status = "approved"
        checkpoint.approved_by = str(current_user.id)
        checkpoint.approval_notes = approval.feedback
        await db.commit()
        
        # Send approval through workflow service
        await workflow_service.handle_checkpoint_approval(
            checkpoint.workflow_id, 
            checkpoint_id, 
            approval.feedback
        )
        
        return {
            "message": "Checkpoint approved - workflow will continue",
            "checkpoint_id": checkpoint_id,
            "workflow_id": checkpoint.workflow_id,
            "status": "approved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to approve checkpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to approve checkpoint"
        )