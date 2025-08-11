# backend/app/api/v1/endpoints/workflows.py
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.workflow import WorkflowExecution, WorkflowCheckpoint
from app.schemas.workflow import WorkflowCreateRequest, WorkflowResponse, CheckpointResponse, CheckpointApproval
from services.project.project_service import ProjectService
from services.workflow.camel_workflow_service import workflow_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/start", response_model=WorkflowResponse)
async def start_spinscribe_workflow(
    request: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start the complete Spinscribe multi-agent workflow."""
    try:
        project = await ProjectService.get_project_by_id(db, request.project_id, str(current_user.id))
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
        workflow_id = await workflow_service.start_workflow(
            db=db,
            project_id=request.project_id,
            user_id=str(current_user.id),
            chat_id=request.chat_id,
            title=request.title,
            content_type=request.content_type,
            initial_draft=request.initial_draft,
            use_project_documents=request.use_project_documents
        )
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="starting",
            message="🚀 SpinScribe multi-agent workflow started",
            project_id=request.project_id,
            title=request.title,
            content_type=request.content_type
        )
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start workflow: {str(e)}")

@router.get("/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get workflow status."""
    try:
        workflow = await db.get(WorkflowExecution, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        
        if str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
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
            live_data=live_status
        )
        
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve workflow status")

@router.post("/checkpoints/{checkpoint_id}/approve")
async def approve_checkpoint(
    checkpoint_id: str,
    approval: CheckpointApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a workflow checkpoint."""
    try:
        checkpoint = await db.get(WorkflowCheckpoint, checkpoint_id)
        if not checkpoint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found")
        
        workflow = await db.get(WorkflowExecution, checkpoint.workflow_id)
        if not workflow or str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        success = await workflow_service.approve_checkpoint(
            db=db,
            checkpoint_id=checkpoint_id,
            user_id=str(current_user.id),
            feedback=approval.feedback
        )
        
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to process checkpoint approval")
        
        return {"message": "Checkpoint approved - workflow continuing", "checkpoint_id": checkpoint_id}
        
    except Exception as e:
        logger.error(f"Failed to approve checkpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to approve checkpoint")

@router.get("/{workflow_id}/checkpoints", response_model=List[CheckpointResponse])
async def get_workflow_checkpoints(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all checkpoints for a workflow."""
    try:
        workflow = await db.get(WorkflowExecution, workflow_id)
        if not workflow or str(workflow.user_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        
        from sqlalchemy import select
        result = await db.execute(
            select(WorkflowCheckpoint).where(WorkflowCheckpoint.workflow_id == workflow_id).order_by(WorkflowCheckpoint.created_at)
        )
        checkpoints = result.scalars().all()
        
        return [
            CheckpointResponse(
                id=str(cp.id),
                workflow_id=cp.workflow_id,
                checkpoint_type=cp.checkpoint_type,
                stage=cp.stage,
                title=cp.title,
                description=cp.description,
                status=cp.status,
                priority=cp.priority,
                requires_approval=cp.requires_approval,
                checkpoint_data=cp.checkpoint_data,
                created_at=cp.created_at
            )
            for cp in checkpoints
        ]
        
    except Exception as e:
        logger.error(f"Failed to get checkpoints: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve checkpoints")