# backend/app/api/v1/endpoints/workflows.py
"""
UPDATED workflow endpoints with complete Spinscribe integration.
Replace the existing workflows.py with this version.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.workflow import WorkflowExecution, WorkflowCheckpoint
from app.models.document import Document
from app.schemas.workflow import (
    WorkflowCreateRequest, 
    WorkflowResponse, 
    CheckpointResponse, 
    CheckpointApproval,
    WorkflowListResponse
)
from services.project.project_service import ProjectService
from services.workflow.camel_workflow_service import workflow_service, health_check
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Connect the workflow service to websocket manager
workflow_service.set_websocket_manager(websocket_manager)

@router.post("/start", response_model=WorkflowResponse)
async def start_spinscribe_workflow(
    request: WorkflowCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start the complete Spinscribe multi-agent workflow with real CAMEL integration.
    
    This endpoint now properly calls the Spinscribe library!
    """
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
        
        # Get project documents for RAG if requested
        project_documents = []
        if request.use_project_documents:
            documents = await ProjectService.get_project_documents(db, request.project_id, str(current_user.id))
            project_documents = [doc.file_path for doc in documents]
            logger.info(f"📄 Found {len(project_documents)} project documents for RAG")
        
        # Create workflow execution record
        workflow_execution = WorkflowExecution(
            id=uuid.uuid4(),
            project_id=uuid.UUID(request.project_id),
            chat_id=uuid.UUID(request.chat_id) if request.chat_id else None,
            user_id=current_user.id,
            title=request.title,
            content_type=request.content_type,
            initial_draft=request.initial_draft,
            use_project_documents=request.use_project_documents,
            status="starting",
            current_stage="initialization"
        )
        
        db.add(workflow_execution)
        await db.commit()
        await db.refresh(workflow_execution)
        
        logger.info(f"💾 Created workflow execution record: {workflow_execution.id}")
        
        # Start the actual Spinscribe workflow via the service
        workflow_response = await workflow_service.start_workflow(
            request=request,
            project_documents=project_documents,
            user_id=str(current_user.id)
        )
        
        # Update database record with workflow service response
        workflow_execution.workflow_id = workflow_response.workflow_id
        workflow_execution.status = workflow_response.status
        workflow_execution.current_stage = workflow_response.current_stage
        workflow_execution.final_content = workflow_response.final_content
        workflow_execution.live_data = workflow_response.live_data
        
        if workflow_response.status == "completed":
            workflow_execution.completed_at = workflow_response.completed_at
        
        await db.commit()
        
        # Add background task for cleanup
        background_tasks.add_task(
            cleanup_old_workflows,
            db_session=db
        )
        
        logger.info(f"✅ Workflow started successfully: {workflow_response.workflow_id}")
        return workflow_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Failed to start workflow: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Update workflow record if it exists
        if 'workflow_execution' in locals():
            try:
                workflow_execution.status = "failed"
                workflow_execution.error_message = str(e)
                await db.commit()
            except Exception:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )

@router.get("/status/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_status(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current status of a workflow."""
    
    try:
        # Get status from workflow service (real-time)
        service_status = await workflow_service.get_workflow_status(workflow_id)
        
        if not service_status:
            # Fallback to database record
            from sqlalchemy import select
            result = await db.execute(
                select(WorkflowExecution)
                .where(
                    WorkflowExecution.workflow_id == workflow_id,
                    WorkflowExecution.user_id == current_user.id
                )
            )
            workflow_execution = result.scalar_one_or_none()
            
            if not workflow_execution:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found"
                )
            
            return WorkflowResponse(
                workflow_id=workflow_execution.workflow_id or workflow_id,
                status=workflow_execution.status,
                current_stage=workflow_execution.current_stage,
                project_id=str(workflow_execution.project_id),
                title=workflow_execution.title,
                content_type=workflow_execution.content_type,
                final_content=workflow_execution.final_content,
                created_at=workflow_execution.created_at,
                completed_at=workflow_execution.completed_at,
                live_data=workflow_execution.live_data
            )
        
        # Return live status from service
        return WorkflowResponse(
            workflow_id=workflow_id,
            status=service_status["status"],
            project_id=service_status["project_id"],
            title=service_status["title"],
            content_type=service_status["content_type"],
            created_at=service_status["created_at"],
            completed_at=service_status.get("completed_at"),
            message="Live status from workflow service"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(e)}"
        )

@router.post("/cancel/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a running workflow."""
    
    try:
        # Cancel via workflow service
        cancelled = await workflow_service.cancel_workflow(workflow_id)
        
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found or cannot be cancelled"
            )
        
        # Update database record
        from sqlalchemy import select, update
        await db.execute(
            update(WorkflowExecution)
            .where(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.user_id == current_user.id
            )
            .values(
                status="cancelled",
                current_stage="cancelled"
            )
        )
        await db.commit()
        
        return {"message": "Workflow cancelled successfully", "workflow_id": workflow_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel workflow: {str(e)}"
        )

@router.get("/list", response_model=WorkflowListResponse)
async def list_workflows(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's workflows with optional filtering."""
    
    try:
        from sqlalchemy import select, func, desc
        
        # Build query
        query = select(WorkflowExecution).where(WorkflowExecution.user_id == current_user.id)
        
        if project_id:
            query = query.where(WorkflowExecution.project_id == uuid.UUID(project_id))
        
        if status:
            query = query.where(WorkflowExecution.status == status)
        
        # Get total count
        count_query = select(func.count(WorkflowExecution.id)).where(WorkflowExecution.user_id == current_user.id)
        if project_id:
            count_query = count_query.where(WorkflowExecution.project_id == uuid.UUID(project_id))
        if status:
            count_query = count_query.where(WorkflowExecution.status == status)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(desc(WorkflowExecution.created_at))
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        # Execute query
        result = await db.execute(query)
        workflows = result.scalars().all()
        
        # Convert to response format
        workflow_responses = []
        for workflow in workflows:
            workflow_responses.append(WorkflowResponse(
                workflow_id=workflow.workflow_id or str(workflow.id),
                status=workflow.status,
                current_stage=workflow.current_stage,
                project_id=str(workflow.project_id),
                title=workflow.title,
                content_type=workflow.content_type,
                final_content=workflow.final_content,
                created_at=workflow.created_at,
                completed_at=workflow.completed_at,
                live_data=workflow.live_data
            ))
        
        return WorkflowListResponse(
            workflows=workflow_responses,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )

@router.get("/health")
async def check_workflow_service_health():
    """Check if the workflow service and Spinscribe integration is working."""
    
    try:
        health_status = await health_check()
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "spinscribe_status": "unknown"
        }

# Background task for cleanup
async def cleanup_old_workflows(db_session: AsyncSession):
    """Clean up old workflow records."""
    
    try:
        # Clean up workflow service
        workflow_service.cleanup_completed_workflows(max_age_hours=24)
        
        # Clean up database records older than 7 days
        from datetime import datetime, timedelta
        from sqlalchemy import delete
        
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        await db_session.execute(
            delete(WorkflowExecution)
            .where(
                WorkflowExecution.created_at < cutoff_date,
                WorkflowExecution.status.in_(["completed", "failed", "cancelled"])
            )
        )
        await db_session.commit()
        
        logger.info("🧹 Completed workflow cleanup")
        
    except Exception as e:
        logger.error(f"Failed to cleanup workflows: {str(e)}")

# Additional endpoint for getting workflow logs/details
@router.get("/details/{workflow_id}")
async def get_workflow_details(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a workflow including stages and checkpoints."""
    
    try:
        # Get workflow execution record
        from sqlalchemy import select
        result = await db.execute(
            select(WorkflowExecution)
            .where(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.user_id == current_user.id
            )
        )
        workflow_execution = result.scalar_one_or_none()
        
        if not workflow_execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Get any checkpoints
        checkpoint_result = await db.execute(
            select(WorkflowCheckpoint)
            .where(WorkflowCheckpoint.workflow_id == workflow_execution.id)
        )
        checkpoints = checkpoint_result.scalars().all()
        
        # Get live status if available
        live_status = await workflow_service.get_workflow_status(workflow_id)
        
        return {
            "workflow": {
                "id": workflow_execution.workflow_id or str(workflow_execution.id),
                "title": workflow_execution.title,
                "content_type": workflow_execution.content_type,
                "status": workflow_execution.status,
                "current_stage": workflow_execution.current_stage,
                "created_at": workflow_execution.created_at,
                "completed_at": workflow_execution.completed_at,
                "final_content": workflow_execution.final_content,
                "live_data": workflow_execution.live_data,
                "error_message": workflow_execution.error_message
            },
            "checkpoints": [
                {
                    "id": str(checkpoint.id),
                    "checkpoint_type": checkpoint.checkpoint_type,
                    "stage": checkpoint.stage,
                    "title": checkpoint.title,
                    "description": checkpoint.description,
                    "status": checkpoint.status,
                    "created_at": checkpoint.created_at,
                    "approved_by": checkpoint.approved_by,
                    "approval_notes": checkpoint.approval_notes
                }
                for checkpoint in checkpoints
            ],
            "live_status": live_status,
            "websocket_subscribers": websocket_manager.get_workflow_subscribers(workflow_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow details: {str(e)}"
        )