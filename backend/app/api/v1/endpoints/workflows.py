# backend/app/api/v1/endpoints/workflows.py (Enhanced Version)
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

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
        
        # Start the actual Spinscribe workflow
        workflow_id = await workflow_service.start_workflow(
            db=db,
            project_id=request.project_id,
            user_id=str(current_user.id),
            chat_id=request.chat_id or f"wf_chat_{workflow_id}",
            title=request.title,
            content_type=request.content_type,
            initial_draft=request.initial_draft,
            use_project_documents=request.use_project_documents
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

@router.post("/checkpoints/{checkpoint_id}/approve")
async def approve_checkpoint(
    checkpoint_id: str,
    approval: CheckpointApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a workflow checkpoint and continue the agent workflow."""
    try:
        # Validate checkpoint exists and user has access
        checkpoint = await db.get(WorkflowCheckpoint, checkpoint_id)
        if not checkpoint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found")
        
        # Get associated workflow to check user access
        workflow = await db.get(WorkflowExecution, checkpoint.workflow_id)
        if not workflow or str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        logger.info(f"📋 Approving checkpoint {checkpoint_id} for workflow {checkpoint.workflow_id}")
        logger.info(f"   User feedback: {approval.feedback[:100]}..." if len(approval.feedback) > 100 else approval.feedback)
        
        # Process approval through workflow service
        success = await workflow_service.approve_checkpoint(
            db=db,
            checkpoint_id=checkpoint_id,
            user_id=str(current_user.id),
            feedback=approval.feedback
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Failed to process checkpoint approval"
            )
        
        logger.info(f"✅ Checkpoint {checkpoint_id} approved - workflow continuing")
        
        return {
            "message": "Checkpoint approved - SpinScribe agents continuing workflow",
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

@router.post("/checkpoints/{checkpoint_id}/reject")
async def reject_checkpoint(
    checkpoint_id: str,
    rejection: CheckpointApproval,  # Same schema but for rejection
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a workflow checkpoint and request changes from agents."""
    try:
        checkpoint = await db.get(WorkflowCheckpoint, checkpoint_id)
        if not checkpoint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found")
        
        workflow = await db.get(WorkflowExecution, checkpoint.workflow_id)
        if not workflow or str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        logger.info(f"❌ Rejecting checkpoint {checkpoint_id} for workflow {checkpoint.workflow_id}")
        logger.info(f"   User feedback: {rejection.feedback}")
        
        # Update checkpoint status
        checkpoint.status = "rejected"
        checkpoint.approved_by = str(current_user.id)
        checkpoint.approval_notes = rejection.feedback
        await db.commit()
        
        # Send rejection message through workflow service
        await workflow_service.handle_checkpoint_rejection(
            checkpoint.workflow_id, 
            checkpoint_id, 
            rejection.feedback
        )
        
        return {
            "message": "Checkpoint rejected - agents will revise their work",
            "checkpoint_id": checkpoint_id,
            "workflow_id": checkpoint.workflow_id,
            "status": "rejected"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to reject checkpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to reject checkpoint"
        )

@router.get("/{workflow_id}/checkpoints", response_model=List[CheckpointResponse])
async def get_workflow_checkpoints(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all checkpoints for a workflow."""
    try:
        # Verify workflow access
        workflow = await db.get(WorkflowExecution, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        
        if str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        # Get checkpoints from database
        from sqlalchemy import select
        result = await db.execute(
            select(WorkflowCheckpoint).where(WorkflowCheckpoint.workflow_id == workflow_id)
        )
        checkpoints = result.scalars().all()
        
        return [
            CheckpointResponse(
                id=cp.id,
                workflow_id=cp.workflow_id,
                checkpoint_type=cp.checkpoint_type,
                stage=cp.stage,
                title=cp.title,
                description=cp.description,
                status=cp.status,
                checkpoint_data=cp.checkpoint_data,
                approved_by=cp.approved_by,
                approval_notes=cp.approval_notes,
                created_at=cp.created_at
            )
            for cp in checkpoints
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get checkpoints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to retrieve checkpoints"
        )

@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a running workflow."""
    try:
        workflow = await db.get(WorkflowExecution, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        
        if str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        if workflow.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Cannot cancel workflow with status: {workflow.status}"
            )
        
        logger.info(f"🛑 Cancelling workflow {workflow_id}")
        
        # Cancel through workflow service
        success = await workflow_service.cancel_workflow(workflow_id)
        
        if success:
            # Update database
            workflow.status = "cancelled"
            await db.commit()
            
            return {
                "message": "Workflow cancelled successfully",
                "workflow_id": workflow_id,
                "status": "cancelled"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Failed to cancel workflow"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cancel workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to cancel workflow"
        )

@router.get("/{workflow_id}/content")
async def get_workflow_content(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the final content produced by the workflow."""
    try:
        workflow = await db.get(WorkflowExecution, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        
        if str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        if not workflow.final_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="No content available - workflow may still be running"
            )
        
        return {
            "workflow_id": workflow_id,
            "title": workflow.title,
            "content_type": workflow.content_type,
            "content": workflow.final_content,
            "status": workflow.status,
            "created_at": workflow.created_at,
            "completed_at": workflow.completed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get workflow content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to retrieve workflow content"
        )

@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List workflows for the current user with optional filtering."""
    try:
        from sqlalchemy import select
        
        query = select(WorkflowExecution).where(WorkflowExecution.user_id == str(current_user.id))
        
        if project_id:
            query = query.where(WorkflowExecution.project_id == project_id)
        
        if status:
            query = query.where(WorkflowExecution.status == status)
        
        query = query.order_by(WorkflowExecution.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        workflows = result.scalars().all()
        
        return [
            WorkflowResponse(
                workflow_id=wf.workflow_id,
                status=wf.status,
                current_stage=wf.current_stage,
                progress=wf.progress_percentage,
                message=f"Workflow {wf.status}",
                project_id=str(wf.project_id),
                title=wf.title,
                content_type=wf.content_type,
                created_at=wf.created_at,
                completed_at=wf.completed_at
            )
            for wf in workflows
        ]
        
    except Exception as e:
        logger.error(f"❌ Failed to list workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to retrieve workflows"
        )