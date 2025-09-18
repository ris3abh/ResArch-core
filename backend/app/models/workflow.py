# backend/app/models/workflow.py
"""
WorkflowExecution model that matches your actual database schema.
This preserves your existing SpinScribe functionality.
COMPLETE CORRECTED VERSION - matches your actual database structure.
"""
import uuid
from enum import Enum
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from app.core.database import Base

# Enum for workflow status values
class WorkflowStatus(str, Enum):
    """Valid workflow status values."""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"  # Alias for running

# Enum for checkpoint status values
class CheckpointStatus(str, Enum):
    """Valid checkpoint status values."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"
    WAITING = "waiting"
    RESPONDED = "responded"

# Enum for checkpoint priority values
class CheckpointPriority(str, Enum):
    """Valid checkpoint priority values."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class WorkflowExecution(Base):
    """Model for tracking workflow executions - MATCHES YOUR ACTUAL DATABASE SCHEMA."""
    __tablename__ = "workflow_executions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core workflow identification
    workflow_id = Column(String, nullable=False, unique=True, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Chat integration - using your existing column names
    chat_instance_id = Column(UUID(as_uuid=True), ForeignKey("chat_instances.id"), nullable=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chat_instances.id"), nullable=True)  # Added by migration
    
    # Content details
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=False)
    
    # Status and progress
    status = Column(String(50), nullable=False, default=WorkflowStatus.PENDING)
    current_stage = Column(String(100), nullable=True)
    progress_percentage = Column(Float, nullable=False, default=0.0)  # Note: your DB uses double precision
    
    # Timing
    started_at = Column(DateTime, nullable=True)  # Note: your DB uses timestamp without time zone
    completed_at = Column(DateTime, nullable=True)
    
    # SpinScribe-specific configuration
    timeout_seconds = Column(Integer, nullable=False, default=600)
    enable_human_interaction = Column(Boolean, nullable=False, default=True)
    enable_checkpoints = Column(Boolean, nullable=False, default=True)
    
    # Content management
    first_draft = Column(Text, nullable=True)  # Your DB uses first_draft, not initial_draft
    final_content = Column(Text, nullable=True)
    
    # System data
    agent_config = Column(JSON, nullable=False, default={})  # Your DB uses agent_config, not live_data
    execution_log = Column(JSON, nullable=False, default={})
    error_details = Column(JSON, nullable=True)  # Your DB uses error_details, not error_message
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="workflow_executions")
    user = relationship("User")
    # Use chat_instance_id as primary chat relationship
    chat_instance = relationship("ChatInstance", foreign_keys=[chat_instance_id])
    
    @validates('status')
    def validate_status(self, key, value):
        """Validate status field to ensure it contains expected values."""
        valid_statuses = [s.value for s in WorkflowStatus]
        if value not in valid_statuses:
            # Allow legacy values but log warning
            print(f"⚠️ Warning: Workflow status '{value}' not in expected values: {valid_statuses}")
        return value

    @classmethod
    async def get_by_id(cls, db, workflow_id: str):
        """Get workflow by ID"""
        from sqlalchemy import select
        result = await db.execute(select(cls).where(cls.id == workflow_id))
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_workflow_id(cls, db, workflow_id: str):
        """Get workflow by workflow_id field (not primary key id)"""
        from sqlalchemy import select
        result = await db.execute(select(cls).where(cls.workflow_id == workflow_id))
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_filters(cls, db, filters: dict, limit: int = 20, offset: int = 0):
        """Get workflows by filters"""
        from sqlalchemy import select
        query = select(cls)
        
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.where(getattr(cls, key) == value)
        
        query = query.order_by(cls.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        return result.scalars().all()
    
    @classmethod
    async def count_by_filters(cls, db, filters: dict):
        """Count workflows by filters"""
        from sqlalchemy import select, func
        query = select(func.count(cls.id))
        
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.where(getattr(cls, key) == value)
        
        result = await db.execute(query)
        return result.scalar()
    
    # Property to maintain compatibility with new code expecting initial_draft
    @property
    def initial_draft(self):
        return self.first_draft
    
    @initial_draft.setter
    def initial_draft(self, value):
        self.first_draft = value
    
    # Property to maintain compatibility with new code expecting error_message
    @property
    def error_message(self):
        return self.error_details.get('message') if self.error_details else None
    
    @error_message.setter
    def error_message(self, value):
        if not self.error_details:
            self.error_details = {}
        self.error_details['message'] = value
    
    # Property to maintain compatibility with new code expecting live_data
    @property
    def live_data(self):
        return self.agent_config
    
    @live_data.setter
    def live_data(self, value):
        self.agent_config = value or {}
    
    # Property for use_project_documents (store in agent_config)
    @property
    def use_project_documents(self):
        return self.agent_config.get('use_project_documents', False) if self.agent_config else False
    
    @use_project_documents.setter
    def use_project_documents(self, value):
        if not self.agent_config:
            self.agent_config = {}
        self.agent_config['use_project_documents'] = value

class WorkflowCheckpoint(Base):
    """Model for workflow checkpoints - CORRECTED TO MATCH YOUR ACTUAL DATABASE."""
    __tablename__ = "workflow_checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String, ForeignKey("workflow_executions.workflow_id", ondelete="CASCADE"), nullable=False)
    
    # Checkpoint details - MATCH YOUR ACTUAL DATABASE
    checkpoint_type = Column(String(50), nullable=False)
    stage = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default=CheckpointStatus.PENDING)
    priority = Column(String(20), nullable=False, default=CheckpointPriority.MEDIUM)
    requires_approval = Column(Boolean, nullable=False, default=True)
    
    # Data storage - YOUR DATABASE USES checkpoint_data, NOT content_preview
    checkpoint_data = Column(JSON, nullable=False, default={})
    
    # Approval details
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Timestamps - MATCH YOUR DATABASE (no server_default)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    workflow = relationship("WorkflowExecution", backref="checkpoints")
    approver = relationship("User")
    
    @validates('status')
    def validate_status(self, key, value):
        """Validate status field to ensure it contains expected values."""
        valid_statuses = [s.value for s in CheckpointStatus]
        if value not in valid_statuses:
            print(f"⚠️ Warning: Checkpoint status '{value}' not in expected values: {valid_statuses}")
        return value
    
    @validates('priority')
    def validate_priority(self, key, value):
        """Validate priority field to ensure it contains expected values."""
        valid_priorities = [p.value for p in CheckpointPriority]
        if value not in valid_priorities:
            print(f"⚠️ Warning: Checkpoint priority '{value}' not in expected values: {valid_priorities}")
        return value
    
    # Property for content_preview compatibility
    @property
    def content_preview(self):
        """Extract content preview from checkpoint_data for backward compatibility."""
        if self.checkpoint_data:
            return self.checkpoint_data.get('content_preview', '')
        return ''
    
    @content_preview.setter
    def content_preview(self, value):
        """Store content preview in checkpoint_data."""
        if not self.checkpoint_data:
            self.checkpoint_data = {}
        self.checkpoint_data['content_preview'] = value
    
    # Property for feedback_data compatibility 
    @property
    def feedback_data(self):
        """Extract feedback data from checkpoint_data."""
        if self.checkpoint_data:
            return self.checkpoint_data.get('feedback_data', {})
        return {}
    
    @feedback_data.setter
    def feedback_data(self, value):
        """Store feedback data in checkpoint_data."""
        if not self.checkpoint_data:
            self.checkpoint_data = {}
        self.checkpoint_data['feedback_data'] = value
    
    # Enhanced responded_at property with better handling
    @property
    def responded_at(self):
        """Extract responded_at from checkpoint_data."""
        if self.checkpoint_data:
            responded_str = self.checkpoint_data.get('responded_at')
            if responded_str:
                from datetime import datetime
                try:
                    # Handle various datetime formats
                    if isinstance(responded_str, str):
                        return datetime.fromisoformat(responded_str.replace('Z', '+00:00'))
                    elif hasattr(responded_str, 'isoformat'):
                        return responded_str
                except (ValueError, AttributeError):
                    print(f"⚠️ Invalid responded_at format: {responded_str}")
        return None
    
    @responded_at.setter
    def responded_at(self, value):
        """Store responded_at in checkpoint_data."""
        if not self.checkpoint_data:
            self.checkpoint_data = {}
        if value:
            if hasattr(value, 'isoformat'):
                self.checkpoint_data['responded_at'] = value.isoformat()
            else:
                self.checkpoint_data['responded_at'] = str(value)
    
    @property
    def expires_at(self):
        """Extract expires_at from checkpoint_data."""
        if self.checkpoint_data:
            expires_str = self.checkpoint_data.get('expires_at')
            if expires_str:
                from datetime import datetime
                try:
                    if isinstance(expires_str, str):
                        return datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                    elif hasattr(expires_str, 'isoformat'):
                        return expires_str
                except (ValueError, AttributeError):
                    print(f"⚠️ Invalid expires_at format: {expires_str}")
        return None
    
    @expires_at.setter
    def expires_at(self, value):
        """Store expires_at in checkpoint_data."""
        if not self.checkpoint_data:
            self.checkpoint_data = {}
        if value:
            if hasattr(value, 'isoformat'):
                self.checkpoint_data['expires_at'] = value.isoformat()
            else:
                self.checkpoint_data['expires_at'] = str(value)
    
    # Additional helper methods
    def mark_as_responded(self, user_id: str, decision: str, notes: str = None):
        """Mark checkpoint as responded with decision."""
        from datetime import datetime
        self.approved_by = user_id
        self.approval_notes = notes
        self.responded_at = datetime.utcnow()
        
        if decision.lower() == 'approve':
            self.status = CheckpointStatus.APPROVED
        elif decision.lower() == 'reject':
            self.status = CheckpointStatus.REJECTED
        else:
            self.status = CheckpointStatus.RESPONDED
    
    def is_expired(self):
        """Check if checkpoint has expired."""
        if self.expires_at:
            from datetime import datetime
            return datetime.utcnow() > self.expires_at
        return False
    
    def get_time_remaining(self):
        """Get time remaining before expiration."""
        if self.expires_at:
            from datetime import datetime
            delta = self.expires_at - datetime.utcnow()
            if delta.total_seconds() > 0:
                return int(delta.total_seconds())
        return 0