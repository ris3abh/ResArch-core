from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.chat import ChatInstanceResponse, ChatInstanceCreate
from app.models.user import User
from app.dependencies.auth import get_current_user
from services.chat.chat_service import ChatService

router = APIRouter()

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
            message_count=0
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
    chats = await ChatService.get_chat_instances_by_project(db, project_id, current_user.id)
    
    return [
        ChatInstanceResponse(
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
            message_count=0
        )
        for chat in chats
    ]
# backend/app/api/v1/endpoints/chats.py (UPDATE - add message endpoints)
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.chat import (
    ChatInstanceResponse, ChatInstanceCreate, ChatInstanceUpdate,
    ChatMessageResponse, ChatMessageCreate, ChatMessageUpdate
)
from app.models.user import User
from app.dependencies.auth import get_current_user
from services.chat.chat_service import ChatService
from services.chat.message_service import MessageService

router = APIRouter()

# Chat Instance Endpoints (EXISTING - keep these)
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
            message_count=0
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
    chats = await ChatService.get_chat_instances_by_project(db, project_id, current_user.id)
    
    return [ChatInstanceResponse(**chat) for chat in chats]

# NEW Message Endpoints
@router.post("/{chat_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    chat_id: uuid.UUID,
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to a chat instance."""
    
    # Ensure chat_id matches the message data
    message_data.chat_instance_id = chat_id
    
    try:
        message = await MessageService.create_message(
            db, message_data, current_user.id, sender_type="user"
        )
        
        return ChatMessageResponse(
            id=message.id,
            chat_instance_id=message.chat_instance_id,
            sender_id=message.sender_id,
            sender_type=message.sender_type,
            agent_type=message.agent_type,
            message_content=message.message_content,
            message_type=message.message_type,
            message_metadata=message.message_metadata,
            parent_message_id=message.parent_message_id,
            is_edited=message.is_edited,
            created_at=message.created_at,
            updated_at=message.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{chat_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    chat_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages for a chat instance."""
    messages = await MessageService.get_messages_by_chat(
        db, chat_id, current_user.id, limit, offset
    )
    
    return [
        ChatMessageResponse(
            id=message.id,
            chat_instance_id=message.chat_instance_id,
            sender_id=message.sender_id,
            sender_type=message.sender_type,
            agent_type=message.agent_type,
            message_content=message.message_content,
            message_type=message.message_type,
            message_metadata=message.message_metadata,
            parent_message_id=message.parent_message_id,
            is_edited=message.is_edited,
            created_at=message.created_at,
            updated_at=message.updated_at
        )
        for message in messages
    ]

@router.get("/{chat_id}", response_model=ChatInstanceResponse)
async def get_chat_instance(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chat instance."""
    chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, current_user.id)
    
    if not chat_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat instance not found"
        )
    
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
        updated_at=chat_instance.updated_at
    )

# NEW SpinScribe Integration Endpoint
@router.post("/{chat_id}/start-workflow")
async def start_spinscribe_workflow(
    chat_id: uuid.UUID,
    task_description: str = Query(..., description="What content to create"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a SpinScribe workflow for content creation."""
    
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
            "task_description": task_description
        }
    )
    
    # TODO: Integrate with your actual SpinScribe workflow here
    # For now, simulate agent responses
    await MessageService.create_agent_message(
        db=db,
        chat_id=chat_id,
        agent_type="style_analysis",
        message_content="🔍 Analyzing your brand voice and style preferences...",
        message_type="text",
        metadata={
            "workflow_stage": "style_analysis",
            "agent_status": "working"
        }
    )
    
    return {
        "message": "SpinScribe workflow started successfully",
        "chat_id": str(chat_id),
        "task_description": task_description,
        "status": "workflow_started"
    }