# backend/app/api/v1/workflows.py
"""
FastAPI endpoints for workflow management.
Provides REST API access to the SpinScribe workflow system.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.workflow_service import WorkflowService
from app.schemas.workflow import (
    WorkflowCreateRequest, WorkflowExecutionResponse, WorkflowStatusResponse,
    AgentInteractionResponse, CheckpointResponseRequest, HumanInteractionRequest,
    WorkflowListResponse, WorkflowCreateResponse, CheckpointResponse,
    PendingInteractionResponse, ErrorResponse
)
from app.api.deps import get_current_active_user

router = APIRouter()

def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    """
    Dependency to get workflow service instance.
    In production, this would pass the session factory for background tasks.
    """
    # TODO: In production, pass the actual session factory
    return WorkflowService(db, session_factory=None)

@router.post("/create", response_model=WorkflowCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Create a new workflow execution.
    
    Creates a new workflow and optionally starts it immediately.
    The workflow will be executed asynchronously in the background.
    """
    try:
        # Create the workflow
        workflow = await service.create_workflow(request, current_user.id)
        
        # Start the workflow execution
        started = await service.start_workflow(workflow.workflow_id)
        
        if not started:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start workflow execution"
            )
        
        return WorkflowCreateResponse(
            workflow_id=workflow.workflow_id,
            status="started",
            message="Workflow created and started successfully",
            estimated_completion=workflow.estimated_completion
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )

@router.get("/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Get current workflow status.
    
    Returns real-time information about workflow progress, current stage,
    and estimated completion time.
    """
    status_info = await service.get_workflow_status(workflow_id)
    
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # TODO: Add access control check - ensure user has access to this workflow
    
    return status_info

@router.get("/{workflow_id}", response_model=WorkflowExecutionResponse)
async def get_workflow_details(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Get detailed workflow information.
    
    Returns complete workflow execution details including configuration,
    content, and execution metadata.
    """
    workflow = await service.get_workflow_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # TODO: Add access control check - ensure user has access to this workflow
    
    return WorkflowExecutionResponse.model_validate(workflow.to_dict())

@router.post("/{workflow_id}/cancel", response_model=CheckpointResponse)
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Cancel a running workflow.
    
    Cancels workflow execution and marks it as cancelled.
    Only works for workflows that are currently running or pending.
    """
    cancelled = await service.cancel_workflow(workflow_id, "User requested cancellation")
    
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow cannot be cancelled (not found or not in cancellable state)"
        )
    
    return CheckpointResponse(
        checkpoint_id=workflow_id,
        status="cancelled",
        message="Workflow cancelled successfully",
        workflow_continues=False
    )

@router.get("/{workflow_id}/interactions", response_model=List[AgentInteractionResponse])
async def get_workflow_interactions(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Get all interactions for a workflow.
    
    Returns all agent interactions including human-in-the-loop communications
    and their current status.
    """
    interactions = await service.get_workflow_interactions(workflow_id)
    return interactions

@router.get("/{workflow_id}/pending-interactions", response_model=PendingInteractionResponse)
async def get_pending_interactions(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Get pending human interactions for a workflow.
    
    Returns interactions that are waiting for human response,
    including questions from agents and timeout information.
    """
    pending = await service.get_pending_human_interactions(workflow_id)
    
    overdue_count = sum(1 for interaction in pending if interaction.is_human_response_overdue)
    
    return PendingInteractionResponse(
        pending_interactions=[interaction.model_dump() for interaction in pending],
        total_pending=len(pending),
        overdue_interactions=overdue_count
    )

@router.post("/{workflow_id}/human-response", response_model=CheckpointResponse)
async def respond_to_human_interaction(
    workflow_id: str,
    request: HumanInteractionRequest,
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Respond to a human interaction request.
    
    Provides human response to an agent question, allowing the workflow
    to continue execution.
    """
    success = await service.respond_to_human_interaction(
        request.interaction_id,
        request.response
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to record human response (interaction not found or already responded)"
        )
    
    return CheckpointResponse(
        checkpoint_id=request.interaction_id,
        status="responded",
        message="Human response recorded successfully",
        workflow_continues=request.continue_workflow
    )

@router.post("/{workflow_id}/checkpoint-response", response_model=CheckpointResponse)
async def respond_to_checkpoint(
    workflow_id: str,
    request: CheckpointResponseRequest,
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Respond to a workflow checkpoint.
    
    Provides approval or rejection for workflow checkpoints,
    allowing the workflow to proceed or requiring modifications.
    """
    # TODO: Implement checkpoint response handling
    # This would integrate with the actual checkpoint system
    
    return CheckpointResponse(
        checkpoint_id=request.checkpoint_id,
        status="approved" if request.response in ["approved", "approve", "yes"] else "rejected",
        message=f"Checkpoint {request.response}: {request.feedback or 'No feedback provided'}",
        workflow_continues=request.response in ["approved", "approve", "yes"]
    )

@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    List workflows for the current user.
    
    Returns paginated list of workflows, optionally filtered by project.
    Includes workflow status, progress, and basic metadata.
    """
    offset = (page - 1) * limit
    
    workflows = await service.get_workflows_for_user(
        current_user.id,
        project_id=project_id,
        limit=limit + 1,  # Get one extra to check if there are more
        offset=offset
    )
    
    # Check if there are more items
    has_next = len(workflows) > limit
    if has_next:
        workflows = workflows[:-1]  # Remove the extra item
    
    has_previous = page > 1
    
    return WorkflowListResponse(
        workflows=workflows,
        total=len(workflows),  # TODO: Get actual total count
        page=page,
        limit=limit,
        has_next=has_next,
        has_previous=has_previous
    )

@router.get("/project/{project_id}/workflows", response_model=WorkflowListResponse)
async def list_project_workflows(
    project_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    List workflows for a specific project.
    
    Returns paginated list of workflows for the given project.
    User must have access to the project.
    """
    offset = (page - 1) * limit
    
    # TODO: Add project access control check
    
    workflows = await service.get_workflows_for_user(
        current_user.id,
        project_id=project_id,
        limit=limit + 1,
        offset=offset
    )
    
    has_next = len(workflows) > limit
    if has_next:
        workflows = workflows[:-1]
    
    has_previous = page > 1
    
    return WorkflowListResponse(
        workflows=workflows,
        total=len(workflows),
        page=page,
        limit=limit,
        has_next=has_next,
        has_previous=has_previous
    )