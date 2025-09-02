# backend/app/api/v1/endpoints/chats.py
"""
Updated chat endpoints with workflow integration and agent communication support.
"""
from typing import List, Optional
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.project import Project
from app.schemas.chat import (
    ChatInstanceResponse, 
    ChatInstanceCreate, 
    ChatInstanceUpdate,
    ChatMessageResponse, 
    ChatMessageCreate, 
    ChatMessageUpdate,
    ChatMessagesResponse,
    AgentMessageCreate,
    WorkflowChatUpdate
)
from app.models.user import User
from app.dependencies.auth import get_current_user
from services.chat.chat_service import ChatService
from services.chat.message_service import MessageService
from app.core.websocket_manager import websocket_manager

router = APIRouter()

# ========================================
# CHAT INSTANCE ENDPOINTS
# ========================================

@router.post("/", response_model=ChatInstanceResponse)
async def create_chat_instance(
    chat_data: ChatInstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat instance for a project."""
    try:
        chat_instance = await ChatService.create_chat_instance(db, chat_data, current_user.id)
        
        return ChatInstanceResponse(
            id=chat_instance.id,
            name=chat_instance.name,
            description=chat_instance.description,
            chat_type=chat_instance.chat_type,
            project_id=chat_instance.project_id,
            is_active=chat_instance.is_active,
            created_by=chat_instance.created_by,
            agent_config=chat_instance.agent_config,
            workflow_id=chat_instance.workflow_id,
            created_at=chat_instance.created_at,
            updated_at=chat_instance.updated_at,
            message_count=0,
            active_workflows=[]  # Will be populated with actual data in production
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/project/{project_id}", response_model=List[ChatInstanceResponse])
async def get_chat_instances_by_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all chat instances for a project."""
    chats = await ChatService.get_chat_instances_by_project(db, str(project_id), str(current_user.id))
    
    # Get active workflows for each chat
    chat_responses = []
    for chat in chats:
        # Get active workflows for this chat
        from sqlalchemy import select
        from app.models.workflow import WorkflowExecution
        
        workflow_result = await db.execute(
            select(WorkflowExecution.workflow_id)
            .where(
                WorkflowExecution.chat_id == chat.id,
                WorkflowExecution.status.in_(["starting", "running", "pending"])
            )
        )
        active_workflows = [wf for wf in workflow_result.scalars().all() if wf]
        
        chat_responses.append(ChatInstanceResponse(
            id=chat.id,
            name=chat.name,
            description=chat.description,
            chat_type=chat.chat_type,
            project_id=chat.project_id,
            is_active=chat.is_active,
            created_by=chat.created_by,
            agent_config=chat.agent_config,
            workflow_id=chat.workflow_id,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            message_count=0,  # TODO: Add actual message count query
            active_workflows=active_workflows
        ))
    
    return chat_responses

@router.get("/{chat_id}", response_model=ChatInstanceResponse)
async def get_chat_instance(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chat instance with workflow context."""
    chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, current_user.id)
    
    if not chat_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    # Get active workflows
    from sqlalchemy import select
    from app.models.workflow import WorkflowExecution
    
    workflow_result = await db.execute(
        select(WorkflowExecution.workflow_id)
        .where(
            WorkflowExecution.chat_id == chat_instance.id,
            WorkflowExecution.status.in_(["starting", "running", "pending"])
        )
    )
    active_workflows = [wf for wf in workflow_result.scalars().all() if wf]
    
    return ChatInstanceResponse(
        id=chat_instance.id,
        name=chat_instance.name,
        description=chat_instance.description,
        chat_type=chat_instance.chat_type,
        project_id=chat_instance.project_id,
        is_active=chat_instance.is_active,
        created_by=chat_instance.created_by,
        agent_config=chat_instance.agent_config,
        workflow_id=chat_instance.workflow_id,
        created_at=chat_instance.created_at,
        updated_at=chat_instance.updated_at,
        message_count=0,  # TODO: Add actual message count
        active_workflows=active_workflows
    )

@router.put("/{chat_id}", response_model=ChatInstanceResponse)
async def update_chat_instance(
    chat_id: uuid.UUID,
    chat_update: ChatInstanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a chat instance."""
    updated_chat = await ChatService.update_chat_instance(db, chat_id, chat_update, current_user.id)
    
    if not updated_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    return ChatInstanceResponse(
        id=updated_chat.id,
        name=updated_chat.name,
        description=updated_chat.description,
        chat_type=updated_chat.chat_type,
        project_id=updated_chat.project_id,
        is_active=updated_chat.is_active,
        created_by=updated_chat.created_by,
        agent_config=updated_chat.agent_config,
        workflow_id=updated_chat.workflow_id,
        created_at=updated_chat.created_at,
        updated_at=updated_chat.updated_at,
        message_count=0,
        active_workflows=[]
    )

@router.delete("/{chat_id}")
async def delete_chat_instance(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat instance."""
    success = await ChatService.delete_chat_instance(db, chat_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    return {"message": "Chat instance deleted successfully"}

# ========================================
# CHAT MESSAGE ENDPOINTS WITH WORKFLOW INTEGRATION
# ========================================

@router.get("/{chat_id}/messages", response_model=ChatMessagesResponse)
async def get_chat_messages(
    chat_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    include_workflow_context: bool = Query(True, description="Include workflow metadata"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat messages with workflow context and agent communication."""
    
    # Verify chat access
    chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, current_user.id)
    if not chat_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    # Get messages
    messages = await MessageService.get_messages_by_chat(db, chat_id, limit, offset)
    
    # Get active workflows for this chat
    active_workflows = []
    if include_workflow_context:
        from sqlalchemy import select
        from app.models.workflow import WorkflowExecution
        
        workflow_result = await db.execute(
            select(WorkflowExecution.workflow_id)
            .where(
                WorkflowExecution.chat_id == chat_id,
                WorkflowExecution.status.in_(["starting", "running", "pending"])
            )
        )
        active_workflows = [wf for wf in workflow_result.scalars().all() if wf]
    
    # Convert messages to response format with workflow context
    message_responses = []
    for msg in messages:
        # Extract workflow info from metadata
        workflow_id = msg.message_metadata.get("workflow_id") if msg.message_metadata else None
        stage = msg.message_metadata.get("stage") if msg.message_metadata else None
        
        message_responses.append(ChatMessageResponse(
            id=msg.id,
            chat_instance_id=msg.chat_instance_id,
            sender_id=msg.sender_id,
            sender_type=msg.sender_type,
            agent_type=msg.agent_type,
            message_content=msg.message_content,
            message_type=msg.message_type,
            message_metadata=msg.message_metadata or {},
            parent_message_id=msg.parent_message_id,
            is_edited=msg.is_edited,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            workflow_id=workflow_id,
            stage=stage
        ))
    
    # Get total count for pagination
    total_count = await MessageService.get_message_count(db, chat_id)
    
    return ChatMessagesResponse(
        messages=message_responses,
        total=total_count,
        limit=limit,
        offset=offset,
        chat_id=chat_id,
        active_workflows=active_workflows
    )

@router.post("/{chat_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    chat_id: uuid.UUID,
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message in a chat."""
    
    # Verify chat access
    chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, current_user.id)
    if not chat_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    # Create message
    message = await MessageService.create_message(
        db=db,
        message_data=message_data,
        sender_id=current_user.id,
        sender_type="user"
    )
    
    # Broadcast via WebSocket
    await websocket_manager.send_to_chat(str(chat_id), {
        "type": "new_message",
        "data": {
            "id": str(message.id),
            "sender_type": "user",
            "sender_id": str(current_user.id),
            "message_content": message.message_content,
            "message_type": message.message_type,
            "metadata": message.message_metadata,
            "created_at": message.created_at.isoformat()
        },
        "timestamp": message.created_at.isoformat()
    })
    
    return ChatMessageResponse(
        id=message.id,
        chat_instance_id=message.chat_instance_id,
        sender_id=message.sender_id,
        sender_type=message.sender_type,
        agent_type=message.agent_type,
        message_content=message.message_content,
        message_type=message.message_type,
        message_metadata=message.message_metadata or {},
        parent_message_id=message.parent_message_id,
        is_edited=message.is_edited,
        created_at=message.created_at,
        updated_at=message.updated_at,
        workflow_id=message.message_metadata.get("workflow_id") if message.message_metadata else None,
        stage=message.message_metadata.get("stage") if message.message_metadata else None
    )

@router.put("/{chat_id}/messages/{message_id}", response_model=ChatMessageResponse)
async def update_chat_message(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    message_update: ChatMessageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a chat message (user messages only)."""
    
    # Verify chat access
    chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, current_user.id)
    if not chat_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    # Update message
    updated_message = await MessageService.update_message(
        db=db,
        message_id=message_id,
        message_update=message_update,
        user_id=current_user.id
    )
    
    if not updated_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or not authorized to edit"
        )
    
    # Broadcast update via WebSocket
    await websocket_manager.send_to_chat(str(chat_id), {
        "type": "message_updated",
        "data": {
            "id": str(updated_message.id),
            "message_content": updated_message.message_content,
            "is_edited": True,
            "updated_at": updated_message.updated_at.isoformat()
        },
        "timestamp": updated_message.updated_at.isoformat()
    })
    
    return ChatMessageResponse(
        id=updated_message.id,
        chat_instance_id=updated_message.chat_instance_id,
        sender_id=updated_message.sender_id,
        sender_type=updated_message.sender_type,
        agent_type=updated_message.agent_type,
        message_content=updated_message.message_content,
        message_type=updated_message.message_type,
        message_metadata=updated_message.message_metadata or {},
        parent_message_id=updated_message.parent_message_id,
        is_edited=updated_message.is_edited,
        created_at=updated_message.created_at,
        updated_at=updated_message.updated_at,
        workflow_id=updated_message.message_metadata.get("workflow_id") if updated_message.message_metadata else None,
        stage=updated_message.message_metadata.get("stage") if updated_message.message_metadata else None
    )

@router.delete("/{chat_id}/messages/{message_id}")
async def delete_chat_message(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat message (user messages only)."""
    
    # Verify chat access
    chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, current_user.id)
    if not chat_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    success = await MessageService.delete_message(db, message_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or not authorized to delete"
        )
    
    # Broadcast deletion via WebSocket
    await websocket_manager.send_to_chat(str(chat_id), {
        "type": "message_deleted",
        "data": {
            "message_id": str(message_id),
            "deleted_by": str(current_user.id)
        },
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"message": "Message deleted successfully"}

# ========================================
# AGENT COMMUNICATION ENDPOINTS
# ========================================

@router.post("/{chat_id}/agent-message", response_model=ChatMessageResponse)
async def send_agent_message(
    chat_id: uuid.UUID,
    agent_data: AgentMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # For authentication, but agent messages don't have human senders
):
    """Send an agent message to a chat (used by workflow service)."""
    
    # Verify chat exists and user has access
    chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, current_user.id)
    if not chat_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    # Create agent message
    message = await MessageService.create_agent_message(
        db=db,
        chat_id=chat_id,
        agent_type=agent_data.agent_type,
        message_content=agent_data.message_content,
        message_type=agent_data.message_type,
        metadata={
            "workflow_id": agent_data.workflow_id,
            "stage": agent_data.stage,
            **agent_data.metadata
        }
    )
    
    # Broadcast via WebSocket
    await websocket_manager.send_to_chat(str(chat_id), {
        "type": "agent_message",
        "data": {
            "id": str(message.id),
            "sender_type": "agent",
            "agent_type": message.agent_type,
            "message_content": message.message_content,
            "workflow_id": agent_data.workflow_id,
            "stage": agent_data.stage,
            "metadata": message.message_metadata
        },
        "timestamp": message.created_at.isoformat()
    })
    
    return ChatMessageResponse(
        id=message.id,
        chat_instance_id=message.chat_instance_id,
        sender_id=message.sender_id,
        sender_type=message.sender_type,
        agent_type=message.agent_type,
        message_content=message.message_content,
        message_type=message.message_type,
        message_metadata=message.message_metadata or {},
        parent_message_id=message.parent_message_id,
        is_edited=message.is_edited,
        created_at=message.created_at,
        updated_at=message.updated_at,
        workflow_id=agent_data.workflow_id,
        stage=agent_data.stage
    )

# ========================================
# WORKFLOW INTEGRATION ENDPOINTS
# ========================================

@router.post("/{chat_id}/workflow-update")
async def send_workflow_update(
    chat_id: uuid.UUID,
    update: WorkflowChatUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a workflow status update to chat (used by workflow service)."""
    
    # Verify chat access
    chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, current_user.id)
    if not chat_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    # Create system message for the update
    message = await MessageService.create_agent_message(
        db=db,
        chat_id=chat_id,
        agent_type="system",
        message_content=update.message,
        message_type="system",
        metadata={
            "workflow_id": update.workflow_id,
            "update_type": update.type,
            "stage": update.stage,
            "progress": update.progress,
            **update.metadata
        }
    )
    
    # Broadcast via WebSocket
    await websocket_manager.send_to_chat(str(chat_id), {
        "type": "workflow_update",
        "data": {
            "workflow_id": update.workflow_id,
            "update_type": update.type,
            "message": update.message,
            "stage": update.stage,
            "progress": update.progress,
            "agent_type": update.agent_type,
            "metadata": update.metadata
        },
        "timestamp": message.created_at.isoformat()
    })
    
    return {"message": "Workflow update sent successfully"}

# NEW SpinScribe Integration Endpoint (Enhanced)
@router.post("/{chat_id}/start-workflow")
async def start_spinscribe_workflow(
    chat_id: uuid.UUID,
    task_description: str = Query(..., description="What content to create"),
    content_type: str = Query("article", description="Type of content"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a SpinScribe workflow for content creation linked to this chat."""
    
    # Verify user has access to chat
    chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, current_user.id)
    
    if not chat_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
    # Send system message that workflow is starting
    await MessageService.create_agent_message(
        db=db,
        chat_id=chat_id,
        agent_type="coordinator",
        message_content=f"🚀 Starting SpinScribe workflow to create: {task_description}",
        message_type="system",
        metadata={
            "workflow_status": "starting",
            "task_description": task_description,
            "content_type": content_type
        }
    )
    
    # Start the actual workflow via the workflow service
    from app.schemas.workflow import WorkflowCreateRequest
    workflow_request = WorkflowCreateRequest(
        project_id=str(chat_instance.project_id),
        chat_id=str(chat_id),  # Link the workflow to this chat
        title=task_description,
        content_type=content_type,
        use_project_documents=True
    )
    
    # Import and call the workflow service
    from services.workflow.camel_workflow_service import workflow_service
    
    try:
        # This will now work because chat_id is properly supported!
        workflow_response = await workflow_service.start_workflow(
            request=workflow_request,
            project_documents=[],  # Will be populated by the service
            user_id=str(current_user.id)
        )
        
        return {
            "message": "SpinScribe workflow started successfully",
            "chat_id": str(chat_id),
            "workflow_id": workflow_response.workflow_id,
            "task_description": task_description,
            "status": "workflow_started"
        }
        
    except Exception as e:
        # Send error message to chat
        await MessageService.create_agent_message(
            db=db,
            chat_id=chat_id,
            agent_type="system",
            message_content=f"❌ Failed to start workflow: {str(e)}",
            message_type="error",
            metadata={
                "workflow_status": "failed",
                "error": str(e)
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )