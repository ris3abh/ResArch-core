# backend/app/models/workflow.py
"""
Enhanced workflow models for SpinScribe multi-agent system integration.
These models track workflow execution, agent interactions, and knowledge onboarding.
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from app.models.base import BaseModel

class WorkflowExecution(BaseModel):
    """
    Model for tracking SpinScribe multi-agent workflow executions.
    Each workflow represents a complete content creation process.
    """
    
    __tablename__ = "workflow_executions"
    
    # Identity and Association
    workflow_id = Column(String(100), unique=True, nullable=False, index=True)  # Custom workflow ID
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)  # Who initiated
    
    # Workflow Configuration
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=False)  # article, landing_page, blog_post, etc.
    workflow_type = Column(String(50), default='enhanced', nullable=False)  # enhanced, basic, custom
    
    # Execution Status
    status = Column(String(50), default='pending', nullable=False)  # pending, running, completed, failed, cancelled
    current_stage = Column(String(100), nullable=True)  # workflow_building, task_creation, agent_processing, etc.
    progress_percentage = Column(Integer, default=0, nullable=False)
    
    # Configuration Settings
    timeout_seconds = Column(Integer, default=900, nullable=False)
    enable_human_interaction = Column(Boolean, default=True, nullable=False)
    enable_checkpoints = Column(Boolean, default=True, nullable=False)
    
    # Content Management
    first_draft = Column(Text, nullable=True)  # Optional existing content to enhance
    final_content = Column(Text, nullable=True)  # Generated result
    word_count = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)
    
    # Metadata and Results
    execution_metadata = Column(JSON, default=dict, nullable=True)  # Agent responses, intermediate results
    error_details = Column(JSON, nullable=True)  # Error information if failed
    agent_config = Column(JSON, default=dict, nullable=True)  # Agent configuration used
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    
    # Relationships
    # project = relationship("Project", back_populates="workflow_executions")
    # user = relationship("User", back_populates="workflow_executions")
    # agent_interactions = relationship("AgentInteraction", back_populates="workflow_execution", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_workflow_project_status', 'project_id', 'status'),
        Index('idx_workflow_user_created', 'user_id', 'created_at'),
        Index('idx_workflow_status_stage', 'status', 'current_stage'),
        Index('idx_workflow_type_status', 'workflow_type', 'status'),
    )
    
    def __repr__(self):
        return f"<WorkflowExecution(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"
    
    # Computed Properties
    @property
    def is_running(self) -> bool:
        """Check if workflow is currently running."""
        return self.status == 'running'
    
    @property
    def is_completed(self) -> bool:
        """Check if workflow completed successfully."""
        return self.status == 'completed'
    
    @property
    def is_failed(self) -> bool:
        """Check if workflow failed."""
        return self.status == 'failed'
    
    @property
    def is_cancelled(self) -> bool:
        """Check if workflow was cancelled."""
        return self.status == 'cancelled'
    
    @property
    def can_be_cancelled(self) -> bool:
        """Check if workflow can be cancelled."""
        return self.status in ['pending', 'running']
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get workflow duration in seconds."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None
    
    @property
    def agents_configured(self) -> List[str]:
        """Get list of configured agents."""
        if self.agent_config and 'agents' in self.agent_config:
            return self.agent_config['agents']
        return ['coordinator', 'style_analysis', 'content_planning', 'content_generation', 'qa']
    
    def update_progress(self, stage: str, percentage: int, metadata: Dict[str, Any] = None) -> None:
        """Update workflow progress."""
        self.current_stage = stage
        self.progress_percentage = min(100, max(0, percentage))
        
        if metadata:
            if self.execution_metadata is None:
                self.execution_metadata = {}
            self.execution_metadata.update(metadata)
    
    def mark_as_started(self) -> None:
        """Mark workflow as started."""
        self.status = 'running'
        self.started_at = datetime.utcnow()
        self.progress_percentage = 0
    
    def mark_as_completed(self, final_content: str, word_count: int = None, quality_score: float = None) -> None:
        """Mark workflow as completed."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100
        self.final_content = final_content
        self.word_count = word_count
        self.quality_score = quality_score
    
    def mark_as_failed(self, error_details: Dict[str, Any]) -> None:
        """Mark workflow as failed."""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_details = error_details
    
    def mark_as_cancelled(self, reason: str = None) -> None:
        """Mark workflow as cancelled."""
        self.status = 'cancelled'
        self.completed_at = datetime.utcnow()
        if reason:
            self.error_details = {'cancellation_reason': reason}
    
    def to_dict(self):
        """Convert to dictionary with computed properties."""
        data = super().to_dict()
        data.update({
            'is_running': self.is_running,
            'is_completed': self.is_completed,
            'is_failed': self.is_failed,
            'is_cancelled': self.is_cancelled,
            'can_be_cancelled': self.can_be_cancelled,
            'duration_seconds': self.duration_seconds,
            'agents_configured': self.agents_configured,
            'metadata': self.execution_metadata,  # Expose as 'metadata'
        })
        return data


class AgentInteraction(BaseModel):
    """
    Model for tracking individual agent interactions within a workflow.
    Each interaction represents communication between agents or with humans.
    """
    
    __tablename__ = "agent_interactions"
    
    # Identity and Association
    workflow_execution_id = Column(String, ForeignKey('workflow_executions.id', ondelete='CASCADE'), nullable=False)
    agent_type = Column(String(100), nullable=False)  # coordinator, style_analysis, content_planning, etc.
    interaction_sequence = Column(Integer, nullable=False)  # Order within workflow
    
    # Interaction Content
    input_message = Column(Text, nullable=True)  # Input to agent
    output_message = Column(Text, nullable=True)  # Agent response
    agent_response_data = Column(JSON, nullable=True)  # Structured agent response
    
    # Interaction Status
    interaction_status = Column(String(50), default='pending', nullable=False)  # pending, processing, completed, failed
    processing_time_ms = Column(Integer, nullable=True)  # Processing duration
    
    # Human Interaction
    requires_human_input = Column(Boolean, default=False, nullable=False)
    human_question = Column(Text, nullable=True)  # Question posed to human
    human_response = Column(Text, nullable=True)  # Human's response
    human_responded_at = Column(DateTime, nullable=True)
    human_timeout = Column(DateTime, nullable=True)  # When human response times out
    
    # Metadata
    token_usage = Column(JSON, nullable=True)  # Token consumption data
    interaction_metadata = Column(JSON, default=dict, nullable=True)
    
    # Relationships
    # workflow_execution = relationship("WorkflowExecution", back_populates="agent_interactions")
    
    # Indexes
    __table_args__ = (
        Index('idx_interaction_workflow_sequence', 'workflow_execution_id', 'interaction_sequence'),
        Index('idx_interaction_agent_status', 'agent_type', 'interaction_status'),
        Index('idx_interaction_human_required', 'requires_human_input', 'human_responded_at'),
    )
    
    def __repr__(self):
        return f"<AgentInteraction(id={self.id}, agent_type={self.agent_type}, status={self.interaction_status})>"
    
    # Computed Properties
    @property
    def is_completed(self) -> bool:
        """Check if interaction is completed."""
        return self.interaction_status == 'completed'
    
    @property
    def is_pending_human_response(self) -> bool:
        """Check if waiting for human response."""
        return self.requires_human_input and self.human_response is None
    
    @property
    def is_human_response_overdue(self) -> bool:
        """Check if human response is overdue."""
        if not self.requires_human_input or self.human_timeout is None:
            return False
        return datetime.utcnow() > self.human_timeout
    
    @property
    def processing_duration_display(self) -> str:
        """Get formatted processing duration."""
        if self.processing_time_ms is None:
            return "N/A"
        if self.processing_time_ms < 1000:
            return f"{self.processing_time_ms}ms"
        return f"{self.processing_time_ms / 1000:.1f}s"
    
    def set_human_question(self, question: str, timeout_minutes: int = 30) -> None:
        """Set human interaction question with timeout."""
        self.requires_human_input = True
        self.human_question = question
        self.human_timeout = datetime.utcnow() + timedelta(minutes=timeout_minutes)
    
    def set_human_response(self, response: str) -> None:
        """Set human response."""
        self.human_response = response
        self.human_responded_at = datetime.utcnow()
    
    def mark_as_completed(self, output_message: str, processing_time_ms: int = None, 
                         response_data: Dict[str, Any] = None) -> None:
        """Mark interaction as completed."""
        self.interaction_status = 'completed'
        self.output_message = output_message
        self.processing_time_ms = processing_time_ms
        if response_data:
            self.agent_response_data = response_data
    
    def mark_as_failed(self, error_message: str) -> None:
        """Mark interaction as failed."""
        self.interaction_status = 'failed'
        self.output_message = error_message
    
    def to_dict(self):
        """Convert to dictionary with computed properties."""
        data = super().to_dict()
        data.update({
            'is_completed': self.is_completed,
            'is_pending_human_response': self.is_pending_human_response,
            'is_human_response_overdue': self.is_human_response_overdue,
            'processing_duration_display': self.processing_duration_display,
            'metadata': self.interaction_metadata,  # Expose as 'metadata'
        })
        return data


class KnowledgeOnboarding(BaseModel):
    """
    Model for tracking knowledge base onboarding processes.
    Each onboarding represents processing client documents for RAG.
    """
    
    __tablename__ = "knowledge_onboardings"
    
    # Identity and Association
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    onboarding_id = Column(String(100), unique=True, nullable=False, index=True)  # Custom onboarding ID
    
    # Processing Status
    status = Column(String(50), default='pending', nullable=False)  # pending, processing, completed, failed
    processing_stage = Column(String(100), nullable=True)  # document_upload, extraction, vectorization, etc.
    
    # Documents Processing
    total_documents = Column(Integer, default=0, nullable=False)
    processed_documents = Column(Integer, default=0, nullable=False)
    failed_documents = Column(Integer, default=0, nullable=False)
    
    # Processing Results
    documents_processed = Column(JSON, default=dict, nullable=True)  # Count by document type
    knowledge_extracted = Column(JSON, default=dict, nullable=True)  # Insights and patterns found
    processing_summary = Column(Text, nullable=True)  # Human-readable summary
    
    # Recommendations and Next Steps
    recommendations = Column(JSON, default=list, nullable=True)  # List of recommendations
    next_steps = Column(JSON, default=list, nullable=True)  # Suggested actions
    
    # Metadata
    processing_metadata = Column(JSON, default=dict, nullable=True)  # Processing details
    error_details = Column(JSON, nullable=True)  # Error information if failed
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    
    # Relationships
    # project = relationship("Project", back_populates="knowledge_onboardings")
    
    # Indexes
    __table_args__ = (
        Index('idx_onboarding_project_status', 'project_id', 'status'),
        Index('idx_onboarding_id_project', 'onboarding_id', 'project_id'),
    )
    
    def __repr__(self):
        return f"<KnowledgeOnboarding(id={self.id}, project_id={self.project_id}, status={self.status})>"
    
    # Computed Properties
    @property
    def is_completed(self) -> bool:
        """Check if onboarding is completed."""
        return self.status == 'completed'
    
    @property
    def is_processing(self) -> bool:
        """Check if onboarding is in progress."""
        return self.status == 'processing'
    
    @property
    def is_failed(self) -> bool:
        """Check if onboarding failed."""
        return self.status == 'failed'
    
    @property
    def progress_percentage(self) -> int:
        """Calculate processing progress percentage."""
        if self.total_documents == 0:
            return 0
        return int((self.processed_documents / self.total_documents) * 100)
    
    @property
    def success_rate(self) -> float:
        """Calculate document processing success rate."""
        if self.total_documents == 0:
            return 0.0
        return (self.processed_documents / self.total_documents) * 100
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get onboarding duration in seconds."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None
    
    def update_progress(self, processed_count: int, stage: str = None) -> None:
        """Update processing progress."""
        self.processed_documents = processed_count
        if stage:
            self.processing_stage = stage
    
    def add_document_count(self, document_type: str, count: int) -> None:
        """Add document count by type."""
        if self.documents_processed is None:
            self.documents_processed = {}
        self.documents_processed[document_type] = self.documents_processed.get(document_type, 0) + count
    
    def add_knowledge_insight(self, insight_type: str, count: int) -> None:
        """Add knowledge insight count."""
        if self.knowledge_extracted is None:
            self.knowledge_extracted = {}
        self.knowledge_extracted[insight_type] = self.knowledge_extracted.get(insight_type, 0) + count
    
    def add_recommendation(self, recommendation: str) -> None:
        """Add a recommendation."""
        if self.recommendations is None:
            self.recommendations = []
        if recommendation not in self.recommendations:
            self.recommendations.append(recommendation)
    
    def add_next_step(self, step: str) -> None:
        """Add a next step."""
        if self.next_steps is None:
            self.next_steps = []
        if step not in self.next_steps:
            self.next_steps.append(step)
    
    def mark_as_started(self, total_documents: int) -> None:
        """Mark onboarding as started."""
        self.status = 'processing'
        self.started_at = datetime.utcnow()
        self.total_documents = total_documents
        self.processed_documents = 0
        self.failed_documents = 0
    
    def mark_as_completed(self, summary: str = None) -> None:
        """Mark onboarding as completed."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if summary:
            self.processing_summary = summary
    
    def mark_as_failed(self, error_details: Dict[str, Any]) -> None:
        """Mark onboarding as failed."""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_details = error_details
    
    def to_dict(self):
        """Convert to dictionary with computed properties."""
        data = super().to_dict()
        data.update({
            'is_completed': self.is_completed,
            'is_processing': self.is_processing,
            'is_failed': self.is_failed,
            'progress_percentage': self.progress_percentage,
            'success_rate': self.success_rate,
            'duration_seconds': self.duration_seconds,
            'metadata': self.processing_metadata,  # Expose as 'metadata'
        })
        return data