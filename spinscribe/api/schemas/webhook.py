# api/schemas/webhook.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from api.models.checkpoint import CheckpointType, CheckpointStatus

# HITL Webhook (received FROM CrewAI)
class HITLWebhookPayload(BaseModel):
    execution_id: str  # CrewAI execution ID
    task_id: str
    task_output: str
    agent_name: Optional[str] = None
    timestamp: Optional[datetime] = None

# Webhook Event (for streaming)
class WebhookEvent(BaseModel):
    id: str
    execution_id: str
    timestamp: datetime
    type: str  # llm_call_started, task_completed, etc.
    data: Dict[str, Any]

class WebhookEventsPayload(BaseModel):
    events: List[WebhookEvent]

# HITL Approval Actions (sent TO CrewAI)
class HITLApprovalRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject|revise)$")
    feedback: Optional[str] = Field(None, max_length=5000)

class HITLApprovalResponse(BaseModel):
    checkpoint_id: UUID
    execution_id: UUID
    status: CheckpointStatus
    decision: str
    message: str

# Checkpoint Response
class CheckpointResponse(BaseModel):
    checkpoint_id: UUID
    execution_id: UUID
    checkpoint_type: CheckpointType
    task_id: Optional[str]
    status: CheckpointStatus
    content: str
    reviewer_feedback: Optional[str]
    reviewed_by: Optional[UUID]
    created_at: datetime
    reviewed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class PendingCheckpointsResponse(BaseModel):
    checkpoints: List[CheckpointResponse]
    total: int