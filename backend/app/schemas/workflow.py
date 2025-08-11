# backend/app/schemas/workflow.py
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class WorkflowCreateRequest(BaseModel):
    project_id: str = Field(..., description="Project ID")
    chat_id: str = Field(..., description="Chat instance ID for updates")
    title: str = Field(..., min_length=1, max_length=500, description="Content title")
    content_type: str = Field(..., description="Type of content (article, blog_post, etc.)")
    initial_draft: Optional[str] = Field(None, description="Optional initial draft")
    use_project_documents: bool = Field(True, description="Use project documents for RAG")

class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    current_stage: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0.0, le=100.0)
    message: Optional[str] = None
    project_id: str
    title: str
    content_type: str
    final_content: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    live_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class CheckpointResponse(BaseModel):
    id: str
    workflow_id: str
    checkpoint_type: str
    stage: str
    title: str
    description: str
    status: str
    priority: str
    requires_approval: bool
    checkpoint_data: Dict[str, Any]
    created_at: datetime
    approved_by: Optional[str] = None
    approval_notes: Optional[str] = None
    
    class Config:
        from_attributes = True

class CheckpointApproval(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    feedback: Optional[str] = Field(None, max_length=2000, description="Optional feedback")