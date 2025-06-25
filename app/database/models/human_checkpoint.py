# app/database/models/human_checkpoint.py - UPDATED FOR SQLAlchemy 2.0
"""
Human Checkpoint model with proper SQLAlchemy 2.0 syntax using Mapped annotations.
Updated to follow modern best practices and fix relationship issues.
"""
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from app.database.connection import Base

def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())

class CheckpointType(Enum):
    """Types of human checkpoints in the workflow"""
    CONTENT_APPROVAL = "content_approval"
    STYLE_REVIEW = "style_review"
    QUALITY_ASSURANCE = "quality_assurance"
    CLIENT_REVIEW = "client_review"
    FINAL_APPROVAL = "final_approval"
    REVISION_REQUEST = "revision_request"
    BRAND_COMPLIANCE = "brand_compliance"
    SEO_REVIEW = "seo_review"

class CheckpointStatus(Enum):
    """Status of checkpoint processing"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"

class HumanCheckpoint(Base):
    """
    Human Checkpoint model for managing quality control and approval processes
    in the AI content creation workflow.
    """
    __tablename__ = "human_checkpoints"

    # Primary key
    checkpoint_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Foreign keys
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    chat_instance_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("chat_instances.chat_instance_id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Checkpoint classification
    checkpoint_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String, default="normal", index=True)
    
    # Content being reviewed
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_to_review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Review context and instructions
    review_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_criteria: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    context_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Assignment and ownership
    assigned_to_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    assigned_to_role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_by_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Status and processing
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_escalate_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Review results
    reviewer_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    reviewer_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    review_decision: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    review_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Revision tracking
    revision_requests: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True, default=list)
    revision_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requires_agent_action: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Escalation handling
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    escalated_to_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Workflow integration
    blocks_next_stage: Mapped[bool] = mapped_column(Boolean, default=True)
    completion_triggers: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="human_checkpoints")
    chat_instance: Mapped[Optional["ChatInstance"]] = relationship("ChatInstance")
    
    def __repr__(self):
        return f"<HumanCheckpoint(id={self.checkpoint_id}, type={self.checkpoint_type}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for API responses"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "project_id": self.project_id,
            "chat_instance_id": self.chat_instance_id,
            "checkpoint_type": self.checkpoint_type,
            "stage": self.stage,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "content_type": self.content_type,
            "review_instructions": self.review_instructions,
            "review_criteria": self.review_criteria,
            "assigned_to_user_id": self.assigned_to_user_id,
            "assigned_to_role": self.assigned_to_role,
            "created_by_agent": self.created_by_agent,
            "status": self.status,
            "is_blocking": self.is_blocking,
            "reviewer_user_id": self.reviewer_user_id,
            "reviewer_name": self.reviewer_name,
            "review_decision": self.review_decision,
            "review_feedback": self.review_feedback,
            "review_score": self.review_score,
            "revision_requests": self.revision_requests,
            "requires_agent_action": self.requires_agent_action,
            "escalation_level": self.escalation_level,
            "blocks_next_stage": self.blocks_next_stage,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
        }
    
    @classmethod
    def create_content_approval(cls,
                              project_id: str,
                              chat_instance_id: str,
                              content: str,
                              content_type: str,
                              assigned_to_user_id: str = None,
                              created_by_agent: str = None):
        """Create a content approval checkpoint"""
        return cls(
            project_id=project_id,
            chat_instance_id=chat_instance_id,
            checkpoint_type=CheckpointType.CONTENT_APPROVAL.value,
            stage="content_review",
            title=f"{content_type.title()} Content Approval",
            description=f"Review and approve {content_type} content before publication",
            content_to_review=content,
            content_type=content_type,
            assigned_to_user_id=assigned_to_user_id,
            created_by_agent=created_by_agent,
            review_instructions="Please review the content for accuracy, brand alignment, and quality.",
            review_criteria=[
                "Content accuracy",
                "Brand voice consistency",
                "Grammar and style",
                "Target audience appropriateness",
                "Call-to-action effectiveness"
            ]
        )
    
    @classmethod
    def create_style_review(cls,
                          project_id: str,
                          chat_instance_id: str,
                          content: str,
                          content_type: str,
                          style_guidelines: Dict[str, Any] = None,
                          created_by_agent: str = None):
        """Create a style review checkpoint"""
        return cls(
            project_id=project_id,
            chat_instance_id=chat_instance_id,
            checkpoint_type=CheckpointType.STYLE_REVIEW.value,
            stage="style_validation",
            title=f"{content_type.title()} Style Review",
            description=f"Validate {content_type} content against brand style guidelines",
            content_to_review=content,
            content_type=content_type,
            created_by_agent=created_by_agent,
            context_data={"style_guidelines": style_guidelines} if style_guidelines else {},
            review_instructions="Ensure content adheres to brand style guidelines and voice.",
            review_criteria=[
                "Brand voice consistency",
                "Tone appropriateness",
                "Style guide compliance",
                "Terminology accuracy",
                "Format adherence"
            ]
        )
    
    @classmethod
    def create_client_review(cls,
                           project_id: str,
                           chat_instance_id: str,
                           content: str,
                           content_type: str,
                           client_user_id: str,
                           created_by_agent: str = None):
        """Create a client review checkpoint"""
        return cls(
            project_id=project_id,
            chat_instance_id=chat_instance_id,
            checkpoint_type=CheckpointType.CLIENT_REVIEW.value,
            stage="client_approval",
            title=f"Client Review - {content_type.title()}",
            description=f"Client review and approval for {content_type} content",
            content_to_review=content,
            content_type=content_type,
            assigned_to_user_id=client_user_id,
            created_by_agent=created_by_agent,
            priority="high",
            review_instructions="Please review the content and provide feedback or approval.",
            review_criteria=[
                "Meets business objectives",
                "Accurate representation",
                "Appropriate messaging",
                "Ready for publication"
            ]
        )
    
    def assign_to_user(self, user_id: str, role: str = None):
        """Assign checkpoint to specific user"""
        self.assigned_to_user_id = user_id
        if role:
            self.assigned_to_role = role
        self.assigned_at = datetime.utcnow()
        self.status = CheckpointStatus.PENDING.value
    
    def start_review(self, reviewer_user_id: str, reviewer_name: str):
        """Mark checkpoint as being reviewed"""
        self.status = CheckpointStatus.IN_REVIEW.value
        self.reviewer_user_id = reviewer_user_id
        self.reviewer_name = reviewer_name
        self.started_review_at = datetime.utcnow()
    
    def approve(self, reviewer_user_id: str, feedback: str = None, score: int = None):
        """Approve the checkpoint"""
        self.status = CheckpointStatus.APPROVED.value
        self.review_decision = "approve"
        self.reviewer_user_id = reviewer_user_id
        self.review_feedback = feedback
        if score:
            self.review_score = max(1, min(5, score))
        self.completed_at = datetime.utcnow()
        self.requires_agent_action = False
    
    def reject(self, reviewer_user_id: str, feedback: str, revision_requests: List[str] = None):
        """Reject the checkpoint with feedback"""
        self.status = CheckpointStatus.REJECTED.value
        self.review_decision = "reject"
        self.reviewer_user_id = reviewer_user_id
        self.review_feedback = feedback
        if revision_requests:
            self.revision_requests = revision_requests
        self.completed_at = datetime.utcnow()
        self.requires_agent_action = True
    
    def request_revision(self, reviewer_user_id: str, feedback: str, revision_requests: List[str]):
        """Request revisions with specific guidance"""
        self.status = CheckpointStatus.NEEDS_REVISION.value
        self.review_decision = "revise"
        self.reviewer_user_id = reviewer_user_id
        self.review_feedback = feedback
        self.revision_requests = revision_requests
        self.requires_agent_action = True
        self.completed_at = datetime.utcnow()
    
    def escalate(self, escalated_to_user_id: str, reason: str):
        """Escalate checkpoint to higher authority"""
        self.status = CheckpointStatus.ESCALATED.value
        self.escalation_level += 1
        self.escalated_to_user_id = escalated_to_user_id
        self.escalation_reason = reason
        self.escalated_at = datetime.utcnow()
        self.assigned_to_user_id = escalated_to_user_id
    
    def cancel(self, reason: str = None):
        """Cancel the checkpoint"""
        self.status = CheckpointStatus.CANCELLED.value
        self.completed_at = datetime.utcnow()
        if reason:
            if not self.context_data:
                self.context_data = {}
            self.context_data["cancellation_reason"] = reason
    
    def add_revision_request(self, request: str):
        """Add a revision request"""
        if not self.revision_requests:
            self.revision_requests = []
        self.revision_requests.append({
            "request": request,
            "added_at": datetime.utcnow().isoformat()
        })
    
    def set_due_date(self, due_date: datetime):
        """Set due date for the checkpoint"""
        self.due_date = due_date
    
    def is_overdue(self) -> bool:
        """Check if checkpoint is overdue"""
        if not self.due_date:
            return False
        return datetime.utcnow() > self.due_date and self.status in [
            CheckpointStatus.PENDING.value,
            CheckpointStatus.IN_REVIEW.value
        ]
    
    def should_auto_escalate(self) -> bool:
        """Check if checkpoint should be auto-escalated"""
        if not self.auto_escalate_hours or not self.created_at:
            return False
        
        if self.status not in [CheckpointStatus.PENDING.value, CheckpointStatus.IN_REVIEW.value]:
            return False
        
        hours_since_creation = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        return hours_since_creation >= self.auto_escalate_hours
    
    def is_pending(self) -> bool:
        """Check if checkpoint is pending"""
        return self.status == CheckpointStatus.PENDING.value
    
    def is_completed(self) -> bool:
        """Check if checkpoint is completed"""
        return self.status in [
            CheckpointStatus.APPROVED.value,
            CheckpointStatus.REJECTED.value,
            CheckpointStatus.NEEDS_REVISION.value,
            CheckpointStatus.CANCELLED.value
        ]
    
    def is_blocking_workflow(self) -> bool:
        """Check if this checkpoint is blocking workflow progression"""
        return self.is_blocking and not self.is_completed()
    
    def get_review_summary(self) -> Dict[str, Any]:
        """Get summary of review results"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "status": self.status,
            "review_decision": self.review_decision,
            "reviewer_name": self.reviewer_name,
            "review_score": self.review_score,
            "feedback": self.review_feedback,
            "revision_requests": self.revision_requests,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }