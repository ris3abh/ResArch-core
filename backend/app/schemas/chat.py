# backend/app/schemas/chat.py
"""
Updated chat schemas to support workflow integration and agent communication.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class ChatInstanceBase(BaseModel):
    name: str
    description: Optional[str] = None
    chat_type: str = "standard"  # standard, workflow, brainstorm

class ChatInstanceCreate(ChatInstanceBase):
    project_id: uuid.UUID

class ChatInstanceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ChatInstanceResponse(ChatInstanceBase):
    id: uuid.UUID
    project_id: uuid.UUID
    is_active: bool
    created_by: uuid.UUID
    agent_config: Dict[str, Any] = {}
    workflow_id: Optional[str] = None  # Legacy field
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0
    
    # NEW: Include linked workflow executions
    active_workflows: Optional[List[str]] = Field(default_factory=list, description="Active workflow IDs using this chat")
    
    class Config:
        from_attributes = True

class ChatMessageBase(BaseModel):
    message_content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field(default="text", description="text, checkpoint, file, action, agent_update")
    message_metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatMessageCreate(ChatMessageBase):
    parent_message_id: Optional[uuid.UUID] = None

class ChatMessageResponse(ChatMessageBase):
    id: uuid.UUID
    chat_instance_id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None
    sender_type: str  # user, agent, system
    agent_type: Optional[str] = None  # coordinator, style_analysis, content_planning, etc.
    parent_message_id: Optional[uuid.UUID] = None
    is_edited: bool = False
    created_at: datetime
    updated_at: datetime
    
    # NEW: Workflow context
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID from metadata")
    stage: Optional[str] = Field(None, description="Workflow stage from metadata")
    
    class Config:
        from_attributes = True

class AgentMessageCreate(BaseModel):
    """Schema for creating agent messages in workflow chats."""
    workflow_id: str
    agent_type: str = Field(..., description="coordinator, style_analysis, content_planning, quality_assurance")
    stage: str = Field(..., description="Current workflow stage")
    message_content: str = Field(..., min_length=1)
    message_type: str = Field(default="agent_update", description="agent_update, agent_thinking, checkpoint_required")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkflowChatUpdate(BaseModel):
    """Schema for workflow status updates sent to chat."""
    type: str  # workflow_started, agent_started, agent_completed, checkpoint_required, workflow_completed
    workflow_id: str
    agent_type: Optional[str] = None
    stage: Optional[str] = None
    message: str
    progress: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatListResponse(BaseModel):
    """Response schema for listing chats."""
    chats: List[ChatInstanceResponse]
    total: int
    limit: int
    offset: int

class ChatMessageUpdate(BaseModel):
    """Schema for updating chat messages."""
    message_content: Optional[str] = Field(None, min_length=1, max_length=10000)
    message_metadata: Optional[Dict[str, Any]] = None

class ChatMessagesResponse(BaseModel):
    """Response schema for chat messages with pagination."""
    messages: List[ChatMessageResponse]
    total: int
    limit: int
    offset: int
    chat_id: uuid.UUID
    
    # NEW: Workflow context
    active_workflows: List[str] = Field(default_factory=list, description="Active workflow IDs in this chat")