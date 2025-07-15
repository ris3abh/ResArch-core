# app/models/workflow.py
"""
Workflow models for task management and agent coordination.
"""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel

class WorkflowTask(BaseModel):
    """Workflow task model for CAMEL-AI agent tasks."""
    
    __tablename__ = "workflow_tasks"
    
    # Project Association
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    
    # Chat Association (optional - tasks can be created independently)
    chat_instance_id = Column(String, ForeignKey('chat_instances.id'), nullable=True)
    
    # Task Information
    task_name = Column(String(200), nullable=False)
    task_description = Column(Text, nullable=True)
    task_type = Column(String(100), nullable=True)  # 'style_analysis', 'content_planning', 'content_generation', 'qa'
    
    # Task Status
    status = Column(String(50), default='pending', nullable=False)  # 'pending', 'in_progress', 'completed', 'failed'
    
    # Agent Assignment
    assigned_agent = Column(String(100), nullable=True)  # Name/type of agent handling the task
    
    # Task Data (stored as JSON strings for simplicity)
    input_data = Column(Text, nullable=True)  # JSON string of input parameters
    output_data = Column(Text, nullable=True)  # JSON string of task results
    
    # Task Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    # project = relationship("Project", back_populates="workflow_tasks")
    # chat_instance = relationship("ChatInstance", back_populates="workflow_tasks")
    
    # Indexes
    __table_args__ = (
        Index('idx_task_project', 'project_id'),
        Index('idx_task_chat', 'chat_instance_id'),
        Index('idx_task_status', 'status'),
        Index('idx_task_type', 'task_type'),
        Index('idx_task_agent', 'assigned_agent'),
        Index('idx_task_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<WorkflowTask(id={self.id}, name={self.task_name}, status={self.status})>"
    
    @property
    def is_pending(self) -> bool:
        """Check if task is pending."""
        return self.status == 'pending'
    
    @property
    def is_in_progress(self) -> bool:
        """Check if task is in progress."""
        return self.status == 'in_progress'
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == 'completed'
    
    @property
    def is_failed(self) -> bool:
        """Check if task failed."""
        return self.status == 'failed'
    
    @property
    def duration_seconds(self) -> int:
        """Get task duration in seconds."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return 0
    
    @property
    def has_output(self) -> bool:
        """Check if task has output data."""
        return self.output_data is not None and self.output_data.strip() != ''
    
    @property
    def is_chat_task(self) -> bool:
        """Check if task is associated with a chat instance."""
        return self.chat_instance_id is not None
    
    def start_task(self, agent_name: str = None):
        """Mark task as started."""
        self.status = 'in_progress'
        self.started_at = datetime.utcnow()
        if agent_name:
            self.assigned_agent = agent_name
    
    def complete_task(self, output_data: str = None):
        """Mark task as completed."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if output_data:
            self.output_data = output_data
    
    def fail_task(self, error_message: str = None):
        """Mark task as failed."""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        if error_message:
            self.output_data = f'{{"error": "{error_message}"}}'
    
    def to_dict(self):
        """Convert workflow task to dictionary with computed properties."""
        data = super().to_dict()
        data.update({
            'is_pending': self.is_pending,
            'is_in_progress': self.is_in_progress,
            'is_completed': self.is_completed,
            'is_failed': self.is_failed,
            'duration_seconds': self.duration_seconds,
            'has_output': self.has_output,
            'is_chat_task': self.is_chat_task,
        })
        return data