# backend/app/api/v1/endpoints/workflows.py
"""
FIXED workflow endpoints - corrected start_workflow call
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
from datetime import datetime, timezone
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.workflow import WorkflowExecution, WorkflowCheckpoint
from app.models.chat import ChatInstance
from app.models.document import Document
from app.schemas.workflow import (
    WorkflowCreateRequest, 
    WorkflowResponse, 
    CheckpointResponse, 
    CheckpointApproval,
    WorkflowListResponse,
    AgentCommunication,
    WorkflowChatMessage
)
from services.project.project_service import ProjectService
from services.workflow.camel_workflow_service import workflow_service, health_check
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Connect the workflow service to websocket manager
workflow_service.set_websocket_manager(websocket_manager)

async def cleanup_old_workflows(db_session: AsyncSession):
    """Background task to clean up old workflows."""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import select, delete
        
        # Delete workflows older than 30 days that are completed or failed
        cutoff_date = datetime.now() - timedelta(days=30)
        
        old_workflows = await db_session.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.created_at < cutoff_date,
                WorkflowExecution.status.in_(["completed", "failed", "cancelled"])
            )
        )
        
        count = 0
        for workflow in old_workflows.scalars():
            await db_session.delete(workflow)
            count += 1
        
        await db_session.commit()
        
        if count > 0:
            logger.info(f"🧹 Cleaned up {count} old workflow executions")
            
    except Exception as e:
        logger.warning(f"⚠️ Failed to cleanup old workflows: {e}")

@router.post("/start", response_model=WorkflowResponse)
async def start_spinscribe_workflow(
    request: WorkflowCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start the complete Spinscribe multi-agent workflow with real CAMEL integration.
    """
    try:
        # Validate project access
        project = await ProjectService.get_project_by_id(db, request.project_id, str(current_user.id))
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
        # Validate chat exists if provided, or create one if not
        chat_instance = None
        if request.chat_id:
            from sqlalchemy import select
            result = await db.execute(
                select(ChatInstance).where(
                    ChatInstance.id == uuid.UUID(request.chat_id),
                    ChatInstance.project_id == uuid.UUID(request.project_id)
                )
            )
            chat_instance = result.scalar_one_or_none()
            
            if not chat_instance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Invalid chat ID or chat doesn't belong to this project"
                )
        else:
            # Create a new workflow chat if none provided
            chat_instance = ChatInstance(
                project_id=uuid.UUID(request.project_id),
                name=f"SpinScribe: {request.title}",
                description=f"Agent collaboration chat for {request.content_type}",
                chat_type="workflow",
                created_by=current_user.id,
                agent_config={
                    "enable_agent_messages": True,
                    "show_agent_thinking": True,
                    "checkpoint_notifications": True,
                    "workflow_transparency": True
                }
            )
            db.add(chat_instance)
            await db.flush()  # Get the ID without committing
            
            # Update request with new chat_id
            request.chat_id = str(chat_instance.id)
        
        logger.info(f"🚀 Starting Spinscribe workflow for user {current_user.email}")
        logger.info(f"   Project: {request.project_id}")
        logger.info(f"   Chat: {request.chat_id}")
        logger.info(f"   Title: {request.title}")
        logger.info(f"   Content Type: {request.content_type}")
        
        # Get project documents for RAG if requested
        project_documents = []
        if request.use_project_documents:
            from sqlalchemy import select
            result = await db.execute(
                select(Document).where(Document.project_id == uuid.UUID(request.project_id))
            )
            documents = result.scalars().all()
            project_documents = [doc.file_path for doc in documents]
            logger.info(f"📄 Found {len(project_documents)} project documents for RAG")
        
        # Create workflow execution record
        workflow_execution = WorkflowExecution(
            workflow_id=str(uuid.uuid4()),
            project_id=uuid.UUID(request.project_id),
            user_id=current_user.id,
            chat_instance_id=uuid.UUID(request.chat_id),
            chat_id=uuid.UUID(request.chat_id),
            title=request.title,
            content_type=request.content_type,
            status="starting",
            current_stage="initialization",
            progress_percentage=0.0,
            
            # Required fields with defaults
            timeout_seconds=600,
            enable_human_interaction=True,
            enable_checkpoints=True,
            
            # Timestamp fields
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            
            # JSON fields
            agent_config={
                "use_project_documents": request.use_project_documents,
                "enable_agent_messages": True,
                "show_agent_thinking": True,
                "checkpoint_notifications": True,
                "workflow_transparency": True
            },
            execution_log={
                "started_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "stage": "initialization",
                "status": "starting"
            },
            
            # Optional fields
            first_draft=request.initial_draft
        )
        
        db.add(workflow_execution)
        await db.commit()
        await db.refresh(workflow_execution)
        
        logger.info(f"💾 Created workflow execution record: {workflow_execution.id}")
        logger.info(f"🔗 Linked to chat: {chat_instance.id}")
        
        # Send initial message to chat
        await websocket_manager.send_to_chat(str(chat_instance.id), {
            "type": "workflow_started",
            "data": {
                "workflow_id": str(workflow_execution.id),
                "title": request.title,
                "content_type": request.content_type,
                "message": f"🚀 Starting SpinScribe workflow: {request.title}"
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        })
        
        # ===== FIXED: START THE WORKFLOW PROPERLY =====
        # Start the workflow in background task with correct parameters
        background_tasks.add_task(
            workflow_service.start_workflow,
            db,  # Pass the database session
            workflow_execution,  # Pass the workflow execution object
            project_documents  # Pass the project documents list
        )
        # ===== END FIX =====
        
        # Add cleanup task
        background_tasks.add_task(
            cleanup_old_workflows,
            db_session=db
        )
        
        # Return response
        return WorkflowResponse(
            workflow_id=str(workflow_execution.workflow_id),
            status=workflow_execution.status,
            current_stage=workflow_execution.current_stage,
            progress=float(workflow_execution.progress_percentage) if workflow_execution.progress_percentage else 0.0,
            project_id=str(workflow_execution.project_id),
            chat_id=str(chat_instance.id),
            title=workflow_execution.title,
            content_type=workflow_execution.content_type,
            final_content=workflow_execution.final_content,
            created_at=workflow_execution.created_at,
            completed_at=workflow_execution.completed_at,
            live_data=workflow_execution.agent_config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Failed to start workflow: {str(e)}", exc_info=True)
        
        # Update workflow record if it exists
        if 'workflow_execution' in locals():
            try:
                workflow_execution.status = "failed"
                workflow_execution.error_details = {"message": str(e), "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}
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
    """Get the current status of a workflow with chat information."""
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
        try:
            live_status = await workflow_service.get_workflow_status(workflow_id)
        except:
            live_status = None
        
        return WorkflowResponse(
            workflow_id=workflow_execution.workflow_id or str(workflow_execution.id),
            status=workflow_execution.status,
            current_stage=workflow_execution.current_stage,
            progress=float(workflow_execution.progress_percentage) if workflow_execution.progress_percentage else None,
            project_id=str(workflow_execution.project_id),
            chat_id=str(workflow_execution.chat_id) if workflow_execution.chat_id else None,
            title=workflow_execution.title,
            content_type=workflow_execution.content_type,
            final_content=workflow_execution.final_content,
            created_at=workflow_execution.created_at,
            completed_at=workflow_execution.completed_at,
            live_data=workflow_execution.agent_config or (live_status.get("live_data") if live_status else None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Failed to get workflow status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow status"
        )

@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a running workflow and notify the chat."""
    try:
        # Get workflow
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
        
        # Update status
        workflow_execution.status = "cancelled"
        workflow_execution.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        
        # Notify chat if linked
        if workflow_execution.chat_id:
            await websocket_manager.send_to_chat(str(workflow_execution.chat_id), {
                "type": "workflow_cancelled",
                "data": {
                    "workflow_id": workflow_id,
                    "message": "🛑 Workflow was cancelled by user"
                },
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        
        # Cancel in workflow service
        try:
            await workflow_service.cancel_workflow(workflow_id)
        except Exception as e:
            logger.warning(f"⚠️ Failed to cancel workflow service: {e}")
        
        return {
            "message": "Workflow cancelled successfully",
            "workflow_id": workflow_id,
            "status": "cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Failed to cancel workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel workflow"
        )

@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Number of workflows to return"),
    offset: int = Query(0, ge=0, description="Number of workflows to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List workflows with optional filtering, including chat information."""
    try:
        from sqlalchemy import select, and_, desc
        
        # Build query
        query = select(WorkflowExecution).where(WorkflowExecution.user_id == current_user.id)
        
        if project_id:
            query = query.where(WorkflowExecution.project_id == uuid.UUID(project_id))
        
        if status_filter:
            query = query.where(WorkflowExecution.status == status_filter)
        
        # Add ordering and pagination
        query = query.order_by(desc(WorkflowExecution.created_at)).offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        workflows = result.scalars().all()
        
        # Convert to response format
        workflow_responses = []
        for wf in workflows:
            workflow_responses.append(WorkflowResponse(
                workflow_id=wf.workflow_id or str(wf.id),
                status=wf.status,
                current_stage=wf.current_stage,
                progress=float(wf.progress_percentage) if wf.progress_percentage else None,
                project_id=str(wf.project_id),
                chat_id=str(wf.chat_id) if wf.chat_id else None,
                title=wf.title,
                content_type=wf.content_type,
                final_content=wf.final_content,
                created_at=wf.created_at,
                completed_at=wf.completed_at,
                live_data=wf.agent_config
            ))
        
        # Get total count for pagination
        count_query = select(WorkflowExecution).where(WorkflowExecution.user_id == current_user.id)
        if project_id:
            count_query = count_query.where(WorkflowExecution.project_id == uuid.UUID(project_id))
        if status_filter:
            count_query = count_query.where(WorkflowExecution.status == status_filter)
        
        total_result = await db.execute(count_query)
        total = len(total_result.scalars().all())
        
        return WorkflowListResponse(
            workflows=workflow_responses,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"💥 Failed to list workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workflows"
        )

@router.get("/{workflow_id}/content")
async def get_workflow_content(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the final content of a completed workflow."""
    try:
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
        
        return {
            "workflow_id": workflow_id,
            "title": workflow_execution.title,
            "content_type": workflow_execution.content_type,
            "content": workflow_execution.final_content or "",
            "status": workflow_execution.status,
            "chat_id": str(workflow_execution.chat_id) if workflow_execution.chat_id else None,
            "created_at": workflow_execution.created_at.isoformat(),
            "completed_at": workflow_execution.completed_at.isoformat() if workflow_execution.completed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Failed to get workflow content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow content"
        )

@router.get("/{workflow_id}/checkpoints", response_model=List[CheckpointResponse])
async def get_workflow_checkpoints(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all checkpoints for a workflow."""
    try:
        from sqlalchemy import select
        
        # Get workflow first to verify ownership
        workflow_result = await db.execute(
            select(WorkflowExecution)
            .where(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.user_id == current_user.id
            )
        )
        workflow_execution = workflow_result.scalar_one_or_none()
        
        if not workflow_execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Get checkpoints
        checkpoint_result = await db.execute(
            select(WorkflowCheckpoint)
            .where(WorkflowCheckpoint.workflow_id == workflow_execution.id)
            .order_by(WorkflowCheckpoint.created_at)
        )
        checkpoints = checkpoint_result.scalars().all()
        
        return [
            CheckpointResponse(
                id=str(checkpoint.id),
                workflow_id=workflow_id,
                checkpoint_type=checkpoint.checkpoint_type,
                stage=checkpoint.stage,
                title=checkpoint.title,
                description=checkpoint.description or "",
                status=checkpoint.status,
                priority=checkpoint.priority,
                requires_approval=checkpoint.requires_approval,
                checkpoint_data=checkpoint.checkpoint_data or {},
                content_preview=checkpoint.content_preview,
                created_at=checkpoint.created_at,
                approved_by=str(checkpoint.approved_by) if checkpoint.approved_by else None,
                approval_notes=checkpoint.approval_notes
            )
            for checkpoint in checkpoints
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Failed to get workflow checkpoints: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow checkpoints"
        )

@router.post("/checkpoints/{checkpoint_id}/approve")
async def approve_checkpoint(
    checkpoint_id: str,
    approval: CheckpointApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a workflow checkpoint and notify agents via chat."""
    try:
        from sqlalchemy import select
        
        # Get checkpoint
        result = await db.execute(
            select(WorkflowCheckpoint).where(WorkflowCheckpoint.id == uuid.UUID(checkpoint_id))
        )
        checkpoint = result.scalar_one_or_none()
        
        if not checkpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checkpoint not found"
            )
        
        # Verify ownership through workflow
        workflow_result = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == checkpoint.workflow_id,
                WorkflowExecution.user_id == current_user.id
            )
        )
        workflow = workflow_result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to approve this checkpoint"
            )
        
        # Update checkpoint
        checkpoint.status = "approved"
        checkpoint.approved_by = current_user.id
        checkpoint.approval_notes = approval.feedback
        checkpoint.responded_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        await db.commit()
        
        # Notify chat if workflow has chat_id
        if workflow.chat_id:
            await websocket_manager.send_to_chat(str(workflow.chat_id), {
                "type": "checkpoint_approved",
                "data": {
                    "checkpoint_id": checkpoint_id,
                    "workflow_id": workflow.workflow_id,
                    "stage": checkpoint.stage,
                    "feedback": approval.feedback,
                    "message": f"✅ {checkpoint.title} approved by {current_user.first_name}"
                },
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        
        # Continue workflow execution
        try:
            await workflow_service.continue_workflow_after_approval(
                workflow.workflow_id, 
                checkpoint_id, 
                approval.feedback
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to continue workflow: {e}")
        
        return {
            "message": "Checkpoint approved successfully",
            "checkpoint_id": checkpoint_id,
            "workflow_id": workflow.workflow_id,
            "status": "approved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Failed to approve checkpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve checkpoint"
        )

@router.post("/checkpoints/{checkpoint_id}/reject")
async def reject_checkpoint(
    checkpoint_id: str,
    rejection: CheckpointApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a workflow checkpoint and notify agents via chat."""
    try:
        from sqlalchemy import select
        
        # Get checkpoint
        result = await db.execute(
            select(WorkflowCheckpoint).where(WorkflowCheckpoint.id == uuid.UUID(checkpoint_id))
        )
        checkpoint = result.scalar_one_or_none()
        
        if not checkpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checkpoint not found"
            )
        
        # Verify ownership
        workflow_result = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == checkpoint.workflow_id,
                WorkflowExecution.user_id == current_user.id
            )
        )
        workflow = workflow_result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reject this checkpoint"
            )
        
        # Update checkpoint
        checkpoint.status = "rejected"
        checkpoint.approved_by = current_user.id
        checkpoint.approval_notes = rejection.feedback
        checkpoint.responded_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        await db.commit()
        
        # Notify chat
        if workflow.chat_id:
            await websocket_manager.send_to_chat(str(workflow.chat_id), {
                "type": "checkpoint_rejected",
                "data": {
                    "checkpoint_id": checkpoint_id,
                    "workflow_id": workflow.workflow_id,
                    "stage": checkpoint.stage,
                    "feedback": rejection.feedback,
                    "message": f"❌ {checkpoint.title} rejected - needs revision"
                },
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        
        # Send rejection feedback to agents
        try:
            await workflow_service.handle_checkpoint_rejection(
                workflow.workflow_id, 
                checkpoint_id, 
                rejection.feedback
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to handle rejection in workflow: {e}")
        
        return {
            "message": "Checkpoint rejected",
            "checkpoint_id": checkpoint_id,
            "workflow_id": workflow.workflow_id,
            "status": "rejected"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Failed to reject checkpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject checkpoint"
        )

# Health check endpoint
@router.get("/health")
async def workflow_health():
    """Check workflow service health."""
    try:
        status = health_check()
        return {
            "status": "healthy" if status.get("available") else "unhealthy",
            "spinscribe_available": status.get("available", False),
            "enhanced_mode": status.get("enhanced", False),
            "camel_version": status.get("version", "unknown"),
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }