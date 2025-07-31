# backend/app/schemas/chat.py (UPDATED to match the model fix)
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid

class ChatInstanceBase(BaseModel):
    name: str
    description: Optional[str] = None
    chat_type: str = "standard"

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
    workflow_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class ChatMessageBase(BaseModel):
    message_content: str
    message_type: str = "text"
    message_metadata: Optional[Dict[str, Any]] = {}  # CHANGED: metadata -> message_metadata

class ChatMessageCreate(ChatMessageBase):
    chat_instance_id: uuid.UUID
    parent_message_id: Optional[uuid.UUID] = None

class ChatMessageUpdate(BaseModel):
    message_content: Optional[str] = None
    message_metadata: Optional[Dict[str, Any]] = None  # CHANGED: metadata -> message_metadata

class ChatMessageResponse(ChatMessageBase):
    id: uuid.UUID
    chat_instance_id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None
    sender_type: str
    agent_type: Optional[str] = None
    parent_message_id: Optional[uuid.UUID] = None
    is_edited: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True