# backend/app/api/v1/endpoints/workflows.py
"""
Complete workflow endpoints with integrated checkpoint response handling
Fixes the timeout issue by providing proper response mechanisms
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query, Body, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import uuid
import logging
import json
import asyncio
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

# CRITICAL IMPORT: Checkpoint manager for response handling
from spinscribe.checkpoints.checkpoint_manager import (
    get_checkpoint_manager,
    CheckpointType,
    Priority as CheckpointPriority
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Connect the workflow service to websocket manager
workflow_service.set_websocket_manager(websocket_manager)

# Initialize checkpoint manager
checkpoint_manager = get_checkpoint_manager()

async def cleanup_old_workflows(db_session: AsyncSession):
    """Background task to clean up old workflows."""
    try:
        from datetime import timedelta
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
        
        # Validate or create chat instance
        chat_instance = None
        if request.chat_id:
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
            await db.flush()
            request.chat_id = str(chat_instance.id)
        
        logger.info(f"🚀 Starting Spinscribe workflow for user {current_user.email}")
        logger.info(f"   Project: {request.project_id}")
        logger.info(f"   Chat: {request.chat_id}")
        logger.info(f"   Title: {request.title}")
        logger.info(f"   Content Type: {request.content_type}")
        
        # Get project documents for RAG if requested
        project_documents = []
        if request.use_project_documents:
            result = await db.execute(
                select(Document).where(Document.project_id == uuid.UUID(request.project_id))
            )
            documents = result.scalars().all()
            project_documents = [doc.file_path for doc in documents]
            logger.info(f"📄 Found {len(project_documents)} project documents for RAG")
        
        # Generate consistent workflow_id
        generated_workflow_id = str(uuid.uuid4())
        
        # Create workflow execution record
        workflow_execution = WorkflowExecution(
            workflow_id=generated_workflow_id,
            project_id=uuid.UUID(request.project_id),
            user_id=current_user.id,
            chat_instance_id=uuid.UUID(request.chat_id),
            chat_id=uuid.UUID(request.chat_id),
            title=request.title,
            content_type=request.content_type,
            status="starting",
            current_stage="initialization",
            progress_percentage=0.0,
            timeout_seconds=600,
            enable_human_interaction=True,
            enable_checkpoints=True,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
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
            first_draft=request.initial_draft
        )
        
        db.add(workflow_execution)
        await db.commit()
        await db.refresh(workflow_execution)
        
        logger.info(f"💾 Created workflow execution record: {workflow_execution.id}")
        logger.info(f"🔑 Workflow ID: {generated_workflow_id}")
        logger.info(f"🔗 Linked to chat: {chat_instance.id}")
        
        # Notify WebSocket
        await websocket_manager.broadcast_to_workflow(generated_workflow_id, {
            "type": "workflow_initializing",
            "workflow_id": generated_workflow_id,
            "title": request.title,
            "status": "starting",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Send initial message to chat
        await websocket_manager.send_to_chat(str(chat_instance.id), {
            "type": "workflow_started",
            "data": {
                "workflow_id": generated_workflow_id,
                "title": request.title,
                "content_type": request.content_type,
                "message": f"🚀 Starting SpinScribe workflow: {request.title}"
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        })
        
        # Start workflow in background
        background_tasks.add_task(
            workflow_service.start_workflow,
            db,
            workflow_execution,
            project_documents
        )
        
        background_tasks.add_task(cleanup_old_workflows, db_session=db)
        
        return WorkflowResponse(
            workflow_id=generated_workflow_id,
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
        
        # Get any checkpoints from database
        checkpoint_result = await db.execute(
            select(WorkflowCheckpoint)
            .where(WorkflowCheckpoint.workflow_id == workflow_execution.workflow_id)
        )
        checkpoints = checkpoint_result.scalars().all()
        
        # Also check checkpoint manager for pending checkpoints
        pending_checkpoints = checkpoint_manager.get_pending_checkpoints(str(workflow_execution.project_id))
        
        # Get live status if available
        try:
            live_status = await workflow_service.get_workflow_status(workflow_id)
        except:
            live_status = None
        
        return WorkflowResponse(
            workflow_id=workflow_execution.workflow_id,
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
            live_data={
                **(workflow_execution.agent_config or {}),
                "pending_checkpoints": len(pending_checkpoints),
                "db_checkpoints": len(checkpoints),
                **(live_status.get("live_data", {}) if live_status else {})
            }
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
        
        # Clear any pending checkpoints
        checkpoint_manager.clear_project_checkpoints(str(workflow_execution.project_id))
        
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
        query = select(WorkflowExecution).where(WorkflowExecution.user_id == current_user.id)
        
        if project_id:
            query = query.where(WorkflowExecution.project_id == uuid.UUID(project_id))
        
        if status_filter:
            query = query.where(WorkflowExecution.status == status_filter)
        
        query = query.order_by(desc(WorkflowExecution.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        workflows = result.scalars().all()
        
        workflow_responses = []
        for wf in workflows:
            # Check for pending checkpoints
            pending = checkpoint_manager.get_pending_checkpoints(str(wf.project_id))
            workflow_responses.append(WorkflowResponse(
                workflow_id=wf.workflow_id,
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
                live_data={
                    **(wf.agent_config or {}),
                    "pending_checkpoints": len(pending)
                }
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
            "workflow_id": workflow_execution.workflow_id,
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
        
        # Get checkpoints from database
        checkpoint_result = await db.execute(
            select(WorkflowCheckpoint)
            .where(WorkflowCheckpoint.workflow_id == workflow_execution.workflow_id)
            .order_by(WorkflowCheckpoint.created_at)
        )
        checkpoints = checkpoint_result.scalars().all()
        
        return [
            CheckpointResponse(
                id=str(checkpoint.id),
                workflow_id=workflow_execution.workflow_id,
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

# CRITICAL ADDITION: Checkpoint response endpoint
@router.post("/checkpoint/{checkpoint_id}/respond")
async def respond_to_checkpoint(
    checkpoint_id: str,
    decision: str = Body(..., regex="^(approve|reject)$"),
    feedback: Optional[str] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a response for a workflow checkpoint.
    CRITICAL: This endpoint fixes the timeout issue by providing a way to respond to checkpoints.
    """
    cm = checkpoint_manager
    
    # Submit the response using the enhanced checkpoint manager
    success = cm.submit_response(
        checkpoint_id=checkpoint_id,
        reviewer_id=current_user.email,
        decision=decision,
        feedback=feedback
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Checkpoint {checkpoint_id} not found")
    
    # Get checkpoint details for notification
    checkpoint = cm.get_checkpoint(checkpoint_id)
    
    if checkpoint:
        # Broadcast the response via WebSocket for real-time updates
        await websocket_manager.broadcast_to_workflow(
            checkpoint.metadata.get("workflow_id", ""),
            {
                "type": "checkpoint_response",
                "checkpoint_id": checkpoint_id,
                "decision": decision,
                "feedback": feedback,
                "reviewer": current_user.email,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Also send to chat if linked
        if checkpoint.metadata.get("chat_id"):
            await websocket_manager.send_to_chat(
                checkpoint.metadata.get("chat_id"),
                {
                    "type": "checkpoint_responded",
                    "data": {
                        "checkpoint_id": checkpoint_id,
                        "decision": decision,
                        "feedback": feedback,
                        "message": f"{'✅' if decision == 'approve' else '❌'} Checkpoint {decision}d by {current_user.first_name}"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    logger.info(f"✅ Checkpoint {checkpoint_id} {decision}d by {current_user.email}")
    
    return {
        "status": "success",
        "message": f"Checkpoint {decision}d successfully",
        "checkpoint_id": checkpoint_id,
        "decision": decision,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# CRITICAL ADDITION: Get pending checkpoints for SpinScribe system
@router.get("/checkpoints/pending")
async def get_pending_checkpoints(
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all pending checkpoints for review"""
    cm = checkpoint_manager
    checkpoints = cm.get_pending_checkpoints(project_id)
    
    return {
        "total": len(checkpoints),
        "checkpoints": [
            {
                "id": cp.checkpoint_id,
                "project_id": cp.project_id,
                "title": cp.title,
                "description": cp.description,
                "type": cp.checkpoint_type.value,
                "priority": cp.priority.value,
                "status": cp.status.value,
                "created_at": cp.created_at.isoformat(),
                "content_preview": cp.content[:200] + "..." if cp.content and len(cp.content) > 200 else cp.content
            }
            for cp in checkpoints
        ]
    }

# CRITICAL ADDITION: Get checkpoint details
@router.get("/checkpoint/{checkpoint_id}")
async def get_checkpoint_details(
    checkpoint_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific checkpoint"""
    cm = checkpoint_manager
    checkpoint = cm.get_checkpoint(checkpoint_id)
    
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    
    # Check for stored response
    response = cm.get_response(checkpoint_id)
    
    return {
        "id": checkpoint.checkpoint_id,
        "project_id": checkpoint.project_id,
        "title": checkpoint.title,
        "description": checkpoint.description,
        "content": checkpoint.content,
        "type": checkpoint.checkpoint_type.value,
        "priority": checkpoint.priority.value,
        "status": checkpoint.status.value,
        "created_at": checkpoint.created_at.isoformat(),
        "decision": checkpoint.decision or (response.get("decision") if response else None),
        "feedback": checkpoint.feedback or (response.get("feedback") if response else None),
        "reviewer_id": checkpoint.reviewer_id or (response.get("reviewer_id") if response else None),
        "updated_at": checkpoint.updated_at.isoformat()
    }

@router.post("/checkpoints/{checkpoint_id}/approve")
async def approve_checkpoint(
    checkpoint_id: str,
    approval: CheckpointApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a workflow checkpoint and notify agents via chat."""
    try:
        # Get checkpoint from database
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
        
        # Update checkpoint in database
        checkpoint.status = "approved"
        checkpoint.approved_by = current_user.id
        checkpoint.approval_notes = approval.feedback
        checkpoint.responded_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        await db.commit()
        
        # Also update in checkpoint manager if exists
        checkpoint_manager.submit_response(
            checkpoint_id=checkpoint_id,
            reviewer_id=current_user.email,
            decision="approve",
            feedback=approval.feedback
        )
        
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
        
        # Also update in checkpoint manager
        checkpoint_manager.submit_response(
            checkpoint_id=checkpoint_id,
            reviewer_id=current_user.email,
            decision="reject",
            feedback=rejection.feedback
        )
        
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
    

@router.get("/workflows/{workflow_id}/pending-checkpoint")
async def get_pending_checkpoint(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get any pending checkpoint for a workflow"""
    from spinscribe.checkpoints.checkpoint_manager import get_checkpoint_manager
    checkpoint_manager = get_checkpoint_manager()
    
    # Get all pending checkpoints for this workflow
    pending = checkpoint_manager.get_pending_checkpoints()
    for checkpoint in pending:
        if checkpoint.metadata.get('workflow_id') == workflow_id:
            return {
                "checkpoint_id": checkpoint.checkpoint_id,
                "title": checkpoint.title,
                "description": checkpoint.description,
                "content_preview": checkpoint.content[:500] if checkpoint.content else None
            }
    
    return {"checkpoint_id": None}

# WebSocket endpoint for real-time updates
@router.websocket("/ws/workflow/{workflow_id}")
async def workflow_websocket(
    websocket: WebSocket,
    workflow_id: str
):
    """WebSocket endpoint for real-time workflow and checkpoint updates"""
    await websocket_manager.connect(websocket, workflow_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "checkpoint_query":
                # Allow querying checkpoint status via WebSocket
                checkpoint_id = message.get("checkpoint_id")
                if checkpoint_id:
                    checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
                    response = checkpoint_manager.get_response(checkpoint_id)
                    await websocket.send_json({
                        "type": "checkpoint_status",
                        "checkpoint_id": checkpoint_id,
                        "status": checkpoint.status.value if checkpoint else "not_found",
                        "has_response": response is not None
                    })
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, workflow_id)
        logger.info(f"WebSocket disconnected for workflow {workflow_id}")

# Health check endpoint
@router.get("/health")
async def workflow_health():
    """Check workflow service health."""
    try:
        status = health_check()
        checkpoint_summary = checkpoint_manager.get_checkpoint_summary()
        
        return {
            "status": "healthy" if status.get("available") else "unhealthy",
            "spinscribe_available": status.get("available", False),
            "enhanced_mode": status.get("enhanced", False),
            "camel_version": status.get("version", "unknown"),
            "checkpoint_system": {
                "operational": True,
                "total_checkpoints": checkpoint_summary.get("total", 0),
                "pending": checkpoint_summary.get("pending", 0),
                "responses_stored": checkpoint_summary.get("responses_stored", 0)
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }