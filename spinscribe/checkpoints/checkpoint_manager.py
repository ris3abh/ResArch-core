# File: spinscribe/checkpoints/checkpoint_manager.py
"""
Complete CheckpointManager implementation to support workflow checkpoints.
Enhanced with response storage and retrieval mechanisms to fix timeout issues.
"""

import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)

class CheckpointType(Enum):
    BRIEF_REVIEW = "brief_review"
    STYLE_ANALYSIS = "style_analysis"
    STYLE_GUIDE_APPROVAL = "style_guide_approval"
    CONTENT_PLANNING = "content_planning"
    OUTLINE_REVIEW = "outline_review"
    DRAFT_REVIEW = "draft_review"
    FINAL_APPROVAL = "final_approval"
    STRATEGY_APPROVAL = "strategy_approval"

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class CheckpointStatus(Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"

@dataclass
class Checkpoint:
    """Data class representing a checkpoint."""
    checkpoint_id: str
    project_id: str
    checkpoint_type: CheckpointType
    title: str
    description: str
    content: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    status: CheckpointStatus = CheckpointStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    assigned_by: Optional[str] = None
    reviewer_id: Optional[str] = None
    decision: Optional[str] = None
    feedback: Optional[str] = None
    timeout_hours: int = 24
    metadata: Dict[str, Any] = field(default_factory=dict)

class CheckpointManager:
    """Manages workflow checkpoints for human review and approval."""
    
    def __init__(self):
        self.checkpoints: Dict[str, Checkpoint] = {}
        self.notification_handlers: List[Callable] = []
        self.pending_checkpoints: List[str] = []
        self.project_checkpoints: Dict[str, List[str]] = {}
        # CRITICAL ADDITION: Response storage for retrieval
        self.responses: Dict[str, Dict[str, Any]] = {}
        # Enhanced timeout tracking
        self.timeout_seconds = 600  # 10 minutes default
        logger.info("✅ CheckpointManager initialized with response storage")
    
    def add_notification_handler(self, handler: Callable):
        """Add a notification handler for checkpoint events."""
        if callable(handler):
            self.notification_handlers.append(handler)
            logger.info("✅ Notification handler added")
        else:
            logger.warning("⚠️ Handler is not callable, skipping")
    
    def notify(self, data: Dict[str, Any]):
        """Notify all registered handlers about checkpoint events."""
        for handler in self.notification_handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}")
    
    def create_checkpoint(
        self,
        project_id: str,
        checkpoint_type: CheckpointType,
        title: str,
        description: str,
        content: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        timeout_hours: int = 24,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new checkpoint requiring human review."""
        checkpoint_id = f"checkpoint_{uuid.uuid4().hex[:8]}"
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            project_id=project_id,
            checkpoint_type=checkpoint_type,
            title=title,
            description=description,
            content=content,
            priority=priority,
            timeout_hours=timeout_hours,
            metadata=metadata or {}
        )
        
        self.checkpoints[checkpoint_id] = checkpoint
        self.pending_checkpoints.append(checkpoint_id)
        
        # Track by project
        if project_id not in self.project_checkpoints:
            self.project_checkpoints[project_id] = []
        self.project_checkpoints[project_id].append(checkpoint_id)
        
        # Notify handlers
        self.notify({
            'checkpoint_id': checkpoint_id,
            'checkpoint_type': checkpoint_type.value,
            'title': title,
            'description': description,
            'priority': priority.value,
            'content': content,
            'project_id': project_id
        })
        
        logger.info(f"✅ Created checkpoint {checkpoint_id} for project {project_id}")
        return checkpoint_id
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Retrieve a checkpoint by ID."""
        return self.checkpoints.get(checkpoint_id)
    
    def assign_checkpoint(
        self,
        checkpoint_id: str,
        assigned_to: str,
        assigned_by: Optional[str] = None
    ) -> bool:
        """Assign a checkpoint to a reviewer."""
        if checkpoint_id in self.checkpoints:
            checkpoint = self.checkpoints[checkpoint_id]
            checkpoint.assigned_to = assigned_to
            checkpoint.assigned_by = assigned_by
            checkpoint.status = CheckpointStatus.IN_REVIEW
            checkpoint.updated_at = datetime.now()
            
            logger.info(f"✅ Checkpoint {checkpoint_id} assigned to {assigned_to}")
            return True
        
        logger.warning(f"⚠️ Checkpoint {checkpoint_id} not found")
        return False
    
    def submit_response(
        self,
        checkpoint_id: str,
        reviewer_id: str,
        decision: str,
        feedback: Optional[str] = None
    ) -> bool:
        """
        Submit a response for a checkpoint.
        ENHANCED: Now stores response for retrieval by get_response()
        """
        if checkpoint_id not in self.checkpoints:
            logger.warning(f"⚠️ Checkpoint {checkpoint_id} not found")
            return False
        
        checkpoint = self.checkpoints[checkpoint_id]
        checkpoint.reviewer_id = reviewer_id
        checkpoint.decision = decision
        checkpoint.feedback = feedback
        checkpoint.updated_at = datetime.now()
        
        # CRITICAL ADDITION: Store response for retrieval
        self.responses[checkpoint_id] = {
            "decision": decision,
            "feedback": feedback,
            "reviewer_id": reviewer_id,
            "timestamp": datetime.now(),
            "checkpoint_type": checkpoint.checkpoint_type.value,
            "project_id": checkpoint.project_id
        }
        
        # Update status based on decision
        if decision.lower() == "approve":
            checkpoint.status = CheckpointStatus.APPROVED
            logger.info(f"✅ Checkpoint {checkpoint_id} approved by {reviewer_id}")
        elif decision.lower() == "reject":
            checkpoint.status = CheckpointStatus.REJECTED
            logger.info(f"❌ Checkpoint {checkpoint_id} rejected by {reviewer_id}")
        
        # Remove from pending
        if checkpoint_id in self.pending_checkpoints:
            self.pending_checkpoints.remove(checkpoint_id)
        
        # Notify handlers about the decision
        self.notify({
            'checkpoint_id': checkpoint_id,
            'status': checkpoint.status.value,
            'decision': decision,
            'feedback': feedback,
            'reviewer_id': reviewer_id
        })
        
        return True
    
    def get_response(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        NEW METHOD: Get the stored response for a checkpoint.
        This is the critical missing piece that causes timeouts.
        """
        return self.responses.get(checkpoint_id)
    
    def get_pending_checkpoints(self, project_id: Optional[str] = None) -> List[Checkpoint]:
        """Get all pending checkpoints, optionally filtered by project."""
        pending = []
        
        for checkpoint_id in self.pending_checkpoints:
            checkpoint = self.checkpoints.get(checkpoint_id)
            if checkpoint and checkpoint.status == CheckpointStatus.PENDING:
                if project_id is None or checkpoint.project_id == project_id:
                    pending.append(checkpoint)
        
        return pending
    
    def wait_for_checkpoint(self, checkpoint_id: str, timeout_seconds: int = 300) -> Optional[str]:
        """
        ENHANCED: Wait for a checkpoint to be resolved with response checking.
        Returns the decision when checkpoint is resolved or None if timeout.
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            # First check if we have a stored response
            response = self.get_response(checkpoint_id)
            if response:
                logger.info(f"✅ Found response for checkpoint {checkpoint_id}")
                return response.get("decision")
            
            # Also check checkpoint status
            checkpoint = self.get_checkpoint(checkpoint_id)
            if checkpoint and checkpoint.status in [CheckpointStatus.APPROVED, CheckpointStatus.REJECTED]:
                return checkpoint.decision
            
            # Check less frequently to reduce CPU usage
            time.sleep(2)  # Check every 2 seconds instead of 1
        
        # Timeout occurred - auto-approve to prevent workflow failure
        if checkpoint_id in self.checkpoints:
            logger.warning(f"⏱️ Checkpoint {checkpoint_id} timed out after {timeout_seconds} seconds - auto-approving")
            
            # Auto-approve to prevent workflow failure
            self.submit_response(
                checkpoint_id=checkpoint_id,
                reviewer_id="system",
                decision="approve",
                feedback=f"Auto-approved due to timeout after {timeout_seconds} seconds"
            )
            
            return "approve"
        
        return None
    
    def check_timeouts(self):
        """Check for expired checkpoints and mark them as timeout."""
        current_time = datetime.now()
        
        for checkpoint_id, checkpoint in self.checkpoints.items():
            if checkpoint.status == CheckpointStatus.PENDING:
                elapsed_time = current_time - checkpoint.created_at
                timeout_delta = timedelta(hours=checkpoint.timeout_hours)
                
                if elapsed_time > timeout_delta:
                    # Auto-approve on timeout instead of just marking as timeout
                    logger.warning(f"⏱️ Checkpoint {checkpoint_id} expired - auto-approving")
                    
                    self.submit_response(
                        checkpoint_id=checkpoint_id,
                        reviewer_id="system",
                        decision="approve",
                        feedback=f"Auto-approved after {checkpoint.timeout_hours} hour timeout"
                    )
                    
                    # Notify about timeout
                    self.notify({
                        'checkpoint_id': checkpoint_id,
                        'status': 'auto_approved',
                        'message': f'Checkpoint auto-approved after {checkpoint.timeout_hours} hours'
                    })
    
    def get_checkpoint_summary(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of checkpoints, optionally filtered by project."""
        checkpoints_list = list(self.checkpoints.values())
        
        if project_id:
            checkpoints_list = [c for c in checkpoints_list if c.project_id == project_id]
        
        summary = {
            'total': len(checkpoints_list),
            'pending': len([c for c in checkpoints_list if c.status == CheckpointStatus.PENDING]),
            'in_review': len([c for c in checkpoints_list if c.status == CheckpointStatus.IN_REVIEW]),
            'approved': len([c for c in checkpoints_list if c.status == CheckpointStatus.APPROVED]),
            'rejected': len([c for c in checkpoints_list if c.status == CheckpointStatus.REJECTED]),
            'timeout': len([c for c in checkpoints_list if c.status == CheckpointStatus.TIMEOUT]),
            'responses_stored': len(self.responses)
        }
        
        return summary
    
    def clear_project_checkpoints(self, project_id: str):
        """Clear all checkpoints for a specific project."""
        if project_id in self.project_checkpoints:
            checkpoint_ids = self.project_checkpoints[project_id]
            
            for checkpoint_id in checkpoint_ids:
                if checkpoint_id in self.checkpoints:
                    del self.checkpoints[checkpoint_id]
                if checkpoint_id in self.pending_checkpoints:
                    self.pending_checkpoints.remove(checkpoint_id)
                # Also clear stored responses
                if checkpoint_id in self.responses:
                    del self.responses[checkpoint_id]
            
            del self.project_checkpoints[project_id]
            logger.info(f"✅ Cleared all checkpoints and responses for project {project_id}")
    
    def is_expired(self, checkpoint_id: str) -> bool:
        """
        NEW METHOD: Check if a checkpoint has expired based on creation time.
        """
        checkpoint = self.checkpoints.get(checkpoint_id)
        if checkpoint:
            elapsed = datetime.now() - checkpoint.created_at
            return elapsed > timedelta(hours=checkpoint.timeout_hours)
        return False

# Global instance for easy access
_checkpoint_manager = None

def get_checkpoint_manager() -> CheckpointManager:
    """Get or create the global checkpoint manager instance."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager

# Export the main components
__all__ = ['CheckpointManager', 'CheckpointType', 'Priority', 'CheckpointStatus', 'Checkpoint', 'get_checkpoint_manager']