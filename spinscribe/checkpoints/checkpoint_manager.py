# ─── NEW FILE: spinscribe/checkpoints/checkpoint_manager.py ────
"""
Core checkpoint management system for SpinScribe.
Handles creation, assignment, and resolution of human checkpoints.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class CheckpointType(Enum):
    """Types of human checkpoints in the workflow."""
    BRIEF_REVIEW = "brief_review"
    STYLE_GUIDE_APPROVAL = "style_guide_approval"
    OUTLINE_REVIEW = "outline_review"
    DRAFT_REVIEW = "draft_review"
    FINAL_APPROVAL = "final_approval"
    CUSTOM_REVIEW = "custom_review"

class CheckpointStatus(Enum):
    """Status of checkpoint processing."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class Priority(Enum):
    """Priority levels for checkpoints."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class CheckpointResponse:
    """Response from a human reviewer."""
    response_id: str
    checkpoint_id: str
    reviewer_id: str
    decision: str  # 'approve', 'reject', 'needs_revision'
    feedback: str
    suggestions: List[str] = field(default_factory=list)
    changes_requested: List[Dict[str, Any]] = field(default_factory=list)
    time_spent_minutes: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Checkpoint:
    """A human checkpoint in the workflow."""
    checkpoint_id: str
    project_id: str
    checkpoint_type: CheckpointType
    title: str
    description: str
    content_reference: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_by: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    status: CheckpointStatus = CheckpointStatus.PENDING
    workflow_stage: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    due_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    responses: List[CheckpointResponse] = field(default_factory=list)

class CheckpointManager:
    """
    Manages human checkpoints in the SpinScribe workflow.
    Handles creation, assignment, notifications, and resolution.
    """
    
    def __init__(self):
        self.checkpoints: Dict[str, Checkpoint] = {}
        self.checkpoint_callbacks: Dict[str, Callable] = {}
        self.notification_handlers: List[Callable] = []
        
    def create_checkpoint(
        self,
        project_id: str,
        checkpoint_type: CheckpointType,
        title: str,
        description: str,
        content_reference: Optional[str] = None,
        assigned_to: Optional[str] = None,
        assigned_by: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        workflow_stage: Optional[str] = None,
        context_data: Dict[str, Any] = None,
        due_hours: Optional[int] = None
    ) -> str:
        """
        Create a new human checkpoint.
        
        Args:
            project_id: Project identifier
            checkpoint_type: Type of checkpoint
            title: Checkpoint title
            description: Detailed description
            content_reference: Reference to content being reviewed
            assigned_to: User ID to assign checkpoint to
            assigned_by: User ID who created the checkpoint
            priority: Priority level
            workflow_stage: Current workflow stage
            context_data: Additional context information
            due_hours: Hours until due (optional)
            
        Returns:
            checkpoint_id: ID of created checkpoint
        """
        checkpoint_id = str(uuid.uuid4())
        
        due_date = None
        if due_hours:
            due_date = datetime.now() + timedelta(hours=due_hours)
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            project_id=project_id,
            checkpoint_type=checkpoint_type,
            title=title,
            description=description,
            content_reference=content_reference,
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            priority=priority,
            workflow_stage=workflow_stage,
            context_data=context_data or {},
            due_date=due_date
        )
        
        self.checkpoints[checkpoint_id] = checkpoint
        
        # Send notifications
        self._notify_checkpoint_created(checkpoint)
        
        logger.info(f"✋ Created checkpoint: {title} (ID: {checkpoint_id})")
        return checkpoint_id
    
    def assign_checkpoint(
        self,
        checkpoint_id: str,
        assigned_to: str,
        assigned_by: Optional[str] = None
    ) -> bool:
        """
        Assign a checkpoint to a user.
        
        Args:
            checkpoint_id: ID of checkpoint to assign
            assigned_to: User ID to assign to
            assigned_by: User ID making the assignment
            
        Returns:
            bool: True if assignment successful
        """
        if checkpoint_id not in self.checkpoints:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return False
        
        checkpoint = self.checkpoints[checkpoint_id]
        checkpoint.assigned_to = assigned_to
        checkpoint.assigned_by = assigned_by
        checkpoint.updated_at = datetime.now()
        
        if checkpoint.status == CheckpointStatus.PENDING:
            checkpoint.status = CheckpointStatus.IN_REVIEW
        
        self._notify_checkpoint_assigned(checkpoint)
        
        logger.info(f"📋 Assigned checkpoint {checkpoint_id} to {assigned_to}")
        return True
    
    def submit_response(
        self,
        checkpoint_id: str,
        reviewer_id: str,
        decision: str,
        feedback: str,
        suggestions: List[str] = None,
        changes_requested: List[Dict[str, Any]] = None,
        time_spent_minutes: Optional[int] = None
    ) -> bool:
        """
        Submit a response to a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint
            reviewer_id: ID of reviewer
            decision: 'approve', 'reject', or 'needs_revision'
            feedback: Reviewer feedback
            suggestions: List of suggestions
            changes_requested: Specific changes requested
            time_spent_minutes: Time spent on review
            
        Returns:
            bool: True if response submitted successfully
        """
        if checkpoint_id not in self.checkpoints:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return False
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        response = CheckpointResponse(
            response_id=str(uuid.uuid4()),
            checkpoint_id=checkpoint_id,
            reviewer_id=reviewer_id,
            decision=decision,
            feedback=feedback,
            suggestions=suggestions or [],
            changes_requested=changes_requested or [],
            time_spent_minutes=time_spent_minutes
        )
        
        checkpoint.responses.append(response)
        checkpoint.updated_at = datetime.now()
        
        # Update checkpoint status based on decision
        if decision == 'approve':
            checkpoint.status = CheckpointStatus.APPROVED
            checkpoint.resolved_at = datetime.now()
        elif decision == 'reject':
            checkpoint.status = CheckpointStatus.REJECTED
            checkpoint.resolved_at = datetime.now()
        elif decision == 'needs_revision':
            checkpoint.status = CheckpointStatus.NEEDS_REVISION
        
        # Notify about response
        self._notify_checkpoint_responded(checkpoint, response)
        
        # Execute callback if registered
        if checkpoint_id in self.checkpoint_callbacks:
            try:
                self.checkpoint_callbacks[checkpoint_id](checkpoint, response)
            except Exception as e:
                logger.error(f"Checkpoint callback failed: {e}")
        
        logger.info(f"✅ Response submitted for checkpoint {checkpoint_id}: {decision}")
        return True
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get checkpoint by ID."""
        return self.checkpoints.get(checkpoint_id)
    
    def get_checkpoints_by_project(self, project_id: str) -> List[Checkpoint]:
        """Get all checkpoints for a project."""
        return [cp for cp in self.checkpoints.values() if cp.project_id == project_id]
    
    def get_checkpoints_by_assignee(self, user_id: str) -> List[Checkpoint]:
        """Get all checkpoints assigned to a user."""
        return [cp for cp in self.checkpoints.values() if cp.assigned_to == user_id]
    
    def get_pending_checkpoints(self) -> List[Checkpoint]:
        """Get all pending checkpoints."""
        return [cp for cp in self.checkpoints.values() 
                if cp.status in [CheckpointStatus.PENDING, CheckpointStatus.IN_REVIEW]]
    
    def register_callback(self, checkpoint_id: str, callback: Callable) -> None:
        """Register a callback for when a checkpoint is resolved."""
        self.checkpoint_callbacks[checkpoint_id] = callback
    
    def add_notification_handler(self, handler: Callable) -> None:
        """Add a notification handler."""
        self.notification_handlers.append(handler)
    
    def _notify_checkpoint_created(self, checkpoint: Checkpoint) -> None:
        """Send notification when checkpoint is created."""
        for handler in self.notification_handlers:
            try:
                handler('checkpoint_created', checkpoint)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")
    
    def _notify_checkpoint_assigned(self, checkpoint: Checkpoint) -> None:
        """Send notification when checkpoint is assigned."""
        for handler in self.notification_handlers:
            try:
                handler('checkpoint_assigned', checkpoint)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")
    
    def _notify_checkpoint_responded(self, checkpoint: Checkpoint, response: CheckpointResponse) -> None:
        """Send notification when checkpoint receives response."""
        for handler in self.notification_handlers:
            try:
                handler('checkpoint_responded', checkpoint, response)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")