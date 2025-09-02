# backend/app/schemas/workflow.py
"""
Updated workflow schemas to properly handle chat_id integration.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class WorkflowCreateRequest(BaseModel):
    """Request schema for starting a workflow with chat integration."""
    project_id: str = Field(..., description="Project ID")
    chat_id: Optional[str] = Field(None, description="Chat instance ID for agent communication and checkpoints")
    title: str = Field(..., min_length=1, max_length=500, description="Content title")
    content_type: str = Field(..., description="Type of content (article, blog_post, etc.)")
    initial_draft: Optional[str] = Field(None, description="Optional initial draft")
    use_project_documents: bool = Field(True, description="Use project documents for RAG")

class WorkflowConfig(BaseModel):
    """Configuration for starting a workflow - used by frontend."""
    title: str = Field(..., min_length=1, max_length=500)
    content_type: str = Field(..., description="Type of content to create")
    has_initial_draft: bool = Field(False, description="Whether user provided initial draft")
    initial_draft: Optional[str] = Field(None, description="Initial draft content")
    use_project_documents: bool = Field(True, description="Use project documents for context")
    enable_checkpoints: bool = Field(True, description="Enable human approval checkpoints")

class WorkflowResponse(BaseModel):
    """Response schema for workflow operations."""
    workflow_id: str
    status: str
    current_stage: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0.0, le=100.0)
    message: Optional[str] = None
    project_id: str
    chat_id: Optional[str] = None  # NEW: Include chat_id in responses
    title: str
    content_type: str
    final_content: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    live_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class CheckpointResponse(BaseModel):
    """Response schema for workflow checkpoints."""
    id: str
    workflow_id: str
    checkpoint_type: str
    stage: str
    title: str
    description: str
    status: str
    priority: Optional[str] = "medium"
    requires_approval: bool = True
    checkpoint_data: Dict[str, Any]
    content_preview: Optional[str] = None
    created_at: datetime
    approved_by: Optional[str] = None
    approval_notes: Optional[str] = None
    
    class Config:
        from_attributes = True

class CheckpointApproval(BaseModel):
    """Schema for checkpoint approval/rejection."""
    feedback: Optional[str] = Field(None, max_length=2000, description="Optional feedback")

class WorkflowStatusUpdate(BaseModel):
    """Schema for WebSocket status updates."""
    workflow_id: str
    chat_id: Optional[str] = None  # NEW: Include chat for targeted updates
    status: str
    current_stage: str
    progress: float
    message: Optional[str] = None
    agent_type: Optional[str] = None
    timestamp: datetime

class WorkflowListResponse(BaseModel):
    """Schema for listing workflows."""
    workflows: List[WorkflowResponse]
    total: int
    limit: int
    offset: int

class AgentCommunication(BaseModel):
    """Schema for agent communication messages in chat."""
    workflow_id: str
    agent_type: str  # coordinator, style_analysis, content_planning, quality_assurance
    stage: str
    message_type: str = Field(..., description="agent_started, agent_thinking, agent_completed, checkpoint_required")
    content: str
    metadata: Dict[str, Any] = {}
    timestamp: datetime

class WorkflowChatMessage(BaseModel):
    """Schema for workflow-related chat messages."""
    chat_id: str
    workflow_id: str
    sender_type: str = "agent"  # agent, system, user
    agent_type: Optional[str] = None
    message_content: str
    message_type: str = "agent_update"  # text, agent_update, checkpoint, system
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True