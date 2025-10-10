# api/schemas/execution.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from api.models.execution import ExecutionStatus

# Request schemas
class StartCrewRequest(BaseModel):
    project_id: UUID
    workflow_mode: str = Field(..., pattern="^(creation|revision)$")
    initial_draft: Optional[str] = Field(None, description="For revision workflow")

# Response schemas
class ExecutionResponse(BaseModel):
    execution_id: UUID
    project_id: UUID
    workflow_mode: str
    status: ExecutionStatus
    crewai_execution_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    metrics: Dict[str, Any]
    
    class Config:
        from_attributes = True

class ExecutionStatusResponse(BaseModel):
    execution_id: UUID
    status: ExecutionStatus
    crewai_status: Optional[str]
    current_task: Optional[str]
    progress_percentage: Optional[int]
    pending_checkpoint: Optional[UUID]
    started_at: datetime
    duration_seconds: Optional[int]