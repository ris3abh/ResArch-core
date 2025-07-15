# backend/app/schemas/workflow.py
"""
Pydantic schemas for workflow API endpoints.
These schemas define the structure of requests and responses for the SpinScribe workflow system.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum

# Enums for consistent values
class ContentType(str, Enum):
    """Supported content types for workflows."""
    ARTICLE = "article"
    LANDING_PAGE = "landing_page"
    BLOG_POST = "blog_post"
    SOCIAL_POST = "social_post"
    EMAIL = "email"

class WorkflowType(str, Enum):
    """Supported workflow types."""
    ENHANCED = "enhanced"
    BASIC = "basic"
    CUSTOM = "custom"

class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentType(str, Enum):
    """Agent types in the workflow."""
    COORDINATOR = "coordinator"
    STYLE_ANALYSIS = "style_analysis"
    CONTENT_PLANNING = "content_planning"
    CONTENT_GENERATION = "content_generation"
    QA = "qa"

class InteractionStatus(str, Enum):
    """Agent interaction status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Request Schemas
class WorkflowCreateRequest(BaseModel):
    """Schema for creating a new workflow."""
    
    title: str = Field(..., min_length=1, max_length=500, description="Title of the content to create")
    content_type: ContentType = Field(..., description="Type of content to generate")
    project_id: str = Field(..., min_length=1, description="Project ID for workflow execution")
    
    # Optional configuration
    first_draft: Optional[str] = Field(None, description="Existing content to enhance")
    timeout_seconds: int = Field(900, ge=60, le=3600, description="Workflow timeout in seconds")
    enable_human_interaction: bool = Field(True, description="Enable human-in-the-loop interactions")
    enable_checkpoints: bool = Field(True, description="Enable human approval checkpoints")
    workflow_type: WorkflowType = Field(WorkflowType.ENHANCED, description="Type of workflow to execute")
    
    # Advanced configuration
    workflow_config: Optional[Dict[str, Any]] = Field(
        None, 
        description="Advanced workflow configuration"
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate title is not empty after stripping."""
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @field_validator('first_draft')
    @classmethod
    def validate_first_draft(cls, v):
        """Validate first draft if provided."""
        if v is not None and not v.strip():
            raise ValueError('First draft cannot be empty if provided')
        return v.strip() if v else None

class CheckpointResponseRequest(BaseModel):
    """Schema for responding to workflow checkpoints."""
    
    checkpoint_id: str = Field(..., description="Checkpoint ID to respond to")
    response: str = Field(..., description="Response to the checkpoint (approved/rejected)")
    feedback: Optional[str] = Field(None, description="Additional feedback")
    modifications: Optional[Dict[str, Any]] = Field(None, description="Requested modifications")
    
    @field_validator('response')
    @classmethod
    def validate_response(cls, v):
        """Validate checkpoint response."""
        valid_responses = ['approved', 'rejected', 'approve', 'reject', 'yes', 'no']
        if v.lower() not in valid_responses:
            raise ValueError(f'Response must be one of: {", ".join(valid_responses)}')
        return v.lower()

class HumanInteractionRequest(BaseModel):
    """Schema for human interaction responses."""
    
    interaction_id: str = Field(..., description="Interaction ID to respond to")
    response: str = Field(..., min_length=1, description="Human response to the agent question")
    continue_workflow: bool = Field(True, description="Whether to continue the workflow")
    
    @field_validator('response')
    @classmethod
    def validate_response(cls, v):
        """Validate human response is not empty."""
        if not v.strip():
            raise ValueError('Response cannot be empty')
        return v.strip()

class KnowledgeOnboardingRequest(BaseModel):
    """Schema for knowledge onboarding requests."""
    
    project_id: str = Field(..., description="Project ID for onboarding")
    document_ids: List[str] = Field(..., min_items=1, description="List of document IDs to process")
    document_types: Optional[Dict[str, str]] = Field(None, description="Document type mapping")
    processing_priority: str = Field("normal", description="Processing priority")
    
    @field_validator('processing_priority')
    @classmethod
    def validate_priority(cls, v):
        """Validate processing priority."""
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if v.lower() not in valid_priorities:
            raise ValueError(f'Priority must be one of: {", ".join(valid_priorities)}')
        return v.lower()

class KnowledgeSearchRequest(BaseModel):
    """Schema for knowledge search requests."""
    
    project_id: str = Field(..., description="Project ID to search within")
    query: str = Field(..., min_length=1, description="Search query")
    knowledge_types: Optional[List[str]] = Field(None, description="Filter by knowledge types")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Validate search query is not empty."""
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()

# Response Schemas
class WorkflowExecutionResponse(BaseModel):
    """Schema for workflow execution responses."""
    
    # Basic Information
    id: str
    workflow_id: str
    project_id: str
    user_id: str
    
    # Workflow Details
    title: str
    content_type: ContentType
    workflow_type: WorkflowType
    status: WorkflowStatus
    current_stage: Optional[str] = None
    progress_percentage: int
    
    # Configuration
    timeout_seconds: int
    enable_human_interaction: bool
    enable_checkpoints: bool
    
    # Content
    first_draft: Optional[str] = None
    final_content: Optional[str] = None
    word_count: Optional[int] = None
    quality_score: Optional[float] = None
    
    # Timing
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Computed Properties
    is_running: bool
    is_completed: bool
    is_failed: bool
    is_cancelled: bool
    can_be_cancelled: bool
    duration_seconds: Optional[int] = None
    agents_configured: List[str]
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    
    model_config = {"from_attributes": True}

class WorkflowStatusResponse(BaseModel):
    """Schema for workflow status responses."""
    
    workflow_id: str
    status: WorkflowStatus
    current_stage: Optional[str] = None
    progress_percentage: int
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    agents_active: List[str] = []
    next_checkpoint: Optional[Dict[str, Any]] = None
    
    model_config = {"from_attributes": True}

class AgentInteractionResponse(BaseModel):
    """Schema for agent interaction responses."""
    
    # Basic Information
    id: str
    workflow_execution_id: str
    agent_type: AgentType
    interaction_sequence: int
    
    # Interaction Content
    input_message: Optional[str] = None
    output_message: Optional[str] = None
    agent_response_data: Optional[Dict[str, Any]] = None
    
    # Status
    interaction_status: InteractionStatus
    processing_time_ms: Optional[int] = None
    
    # Human Interaction
    requires_human_input: bool
    human_question: Optional[str] = None
    human_response: Optional[str] = None
    human_responded_at: Optional[datetime] = None
    human_timeout: Optional[datetime] = None
    
    # Computed Properties
    is_completed: bool
    is_pending_human_response: bool
    is_human_response_overdue: bool
    processing_duration_display: str
    
    # Metadata
    token_usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class KnowledgeOnboardingResponse(BaseModel):
    """Schema for knowledge onboarding responses."""
    
    # Basic Information
    id: str
    project_id: str
    onboarding_id: str
    
    # Status
    status: str
    processing_stage: Optional[str] = None
    
    # Progress
    total_documents: int
    processed_documents: int
    failed_documents: int
    progress_percentage: int
    success_rate: float
    
    # Results
    documents_processed: Optional[Dict[str, int]] = None
    knowledge_extracted: Optional[Dict[str, int]] = None
    processing_summary: Optional[str] = None
    
    # Recommendations
    recommendations: Optional[List[str]] = None
    next_steps: Optional[List[str]] = None
    
    # Timing
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    
    # Computed Properties
    is_completed: bool
    is_processing: bool
    is_failed: bool
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    
    model_config = {"from_attributes": True}

class WorkflowListResponse(BaseModel):
    """Schema for workflow list responses."""
    
    workflows: List[WorkflowExecutionResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_previous: bool

class AgentStatusResponse(BaseModel):
    """Schema for agent status responses."""
    
    agents: List[Dict[str, Any]]
    workflow_id: str
    active_agents: int
    completed_agents: int
    failed_agents: int

class PendingInteractionResponse(BaseModel):
    """Schema for pending interaction responses."""
    
    pending_interactions: List[Dict[str, Any]]
    total_pending: int
    overdue_interactions: int

class KnowledgeSearchResponse(BaseModel):
    """Schema for knowledge search responses."""
    
    results: List[Dict[str, Any]]
    total_results: int
    query: str
    processing_time_ms: int

class WorkflowCreateResponse(BaseModel):
    """Schema for workflow creation responses."""
    
    workflow_id: str
    status: str
    message: str
    estimated_completion: Optional[datetime] = None

class CheckpointResponse(BaseModel):
    """Schema for checkpoint responses."""
    
    checkpoint_id: str
    status: str
    message: str
    workflow_continues: bool

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

# Utility schemas for complex nested data
class WorkflowConfigSchema(BaseModel):
    """Schema for workflow configuration."""
    
    agents: List[AgentType] = [
        AgentType.COORDINATOR,
        AgentType.STYLE_ANALYSIS,
        AgentType.CONTENT_PLANNING,
        AgentType.CONTENT_GENERATION,
        AgentType.QA
    ]
    rag_enabled: bool = True
    quality_threshold: float = Field(0.8, ge=0.0, le=1.0)
    max_iterations: int = Field(3, ge=1, le=10)
    checkpoint_stages: List[str] = ["strategy_approval", "content_review", "final_approval"]

class TokenUsageSchema(BaseModel):
    """Schema for token usage information."""
    
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: Optional[float] = None

class AgentMetadataSchema(BaseModel):
    """Schema for agent metadata."""
    
    agent_version: str
    model_used: str
    temperature: float
    max_tokens: int
    token_usage: Optional[TokenUsageSchema] = None
    processing_time_ms: int
    confidence_score: Optional[float] = None