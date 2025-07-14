# ─── FIXED FILE: spinscribe/checkpoints/checkpoint_manager.py ─────────

"""
Checkpoint Manager for human-in-the-loop workflow approval.
COMPLETE FIXED VERSION with Priority enum and proper implementation.
"""

import logging
import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CheckpointType(Enum):
    """Types of checkpoints in the workflow."""
    STYLE_GUIDE_APPROVAL = "style_guide_approval"
    CONTENT_OUTLINE_APPROVAL = "content_outline_approval"
    DRAFT_CONTENT_APPROVAL = "draft_content_approval"
    FINAL_CONTENT_APPROVAL = "final_content_approval"
    STRATEGY_APPROVAL = "strategy_approval"
    QUALITY_REVIEW = "quality_review"

class CheckpointStatus(Enum):
    """Status of a checkpoint."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class Priority(Enum):
    """Priority levels for checkpoints."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class CheckpointData:
    """Data structure for checkpoint information."""
    id: str
    project_id: str
    checkpoint_type: CheckpointType
    title: str
    description: str
    content: str
    status: CheckpointStatus
    created_at: datetime
    priority: Priority = Priority.MEDIUM
    assigned_to: Optional[str] = None
    due_hours: Optional[int] = None
    resolved_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    feedback: Optional[str] = None
    decision_data: Optional[Dict[str, Any]] = None

class CheckpointManager:
    """
    Manages human checkpoints in the content creation workflow.
    COMPLETE IMPLEMENTATION with Priority support.
    """
    
    def __init__(self):
        self.checkpoints: Dict[str, CheckpointData] = {}
        self.notification_handlers: List[Callable] = []
        self.auto_approve_timeout = 300  # 5 minutes default
        
        logger.info("✅ Checkpoint Manager initialized")
    
    def create_checkpoint(self, project_id: str, checkpoint_type: CheckpointType,
                         title: str, description: str, content: str = "",
                         priority: Priority = Priority.MEDIUM,
                         assigned_to: Optional[str] = None,
                         due_hours: Optional[int] = None) -> str:
        """
        Create a new checkpoint for human review.
        
        Args:
            project_id: Project identifier
            checkpoint_type: Type of checkpoint
            title: Checkpoint title
            description: Checkpoint description
            content: Content to review
            priority: Priority level
            assigned_to: User to assign to
            due_hours: Hours until due
            
        Returns:
            Checkpoint ID
        """
        try:
            checkpoint_id = str(uuid.uuid4())
            
            checkpoint = CheckpointData(
                id=checkpoint_id,
                project_id=project_id,
                checkpoint_type=checkpoint_type,
                title=title,
                description=description,
                content=content,
                status=CheckpointStatus.PENDING,
                created_at=datetime.now(),
                priority=priority,
                assigned_to=assigned_to,
                due_hours=due_hours
            )
            
            self.checkpoints[checkpoint_id] = checkpoint
            
            # Notify handlers
            self._notify_handlers({
                "type": "checkpoint_created",
                "checkpoint_id": checkpoint_id,
                "project_id": project_id,
                "checkpoint_type": checkpoint_type.value,
                "title": title,
                "description": description,
                "priority": priority.value,
                "assigned_to": assigned_to,
                "content": content
            })
            
            logger.info(f"✅ Checkpoint created: {checkpoint_id} ({checkpoint_type.value})")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create checkpoint: {e}")
            raise
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """
        Retrieve checkpoint data by ID.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Checkpoint data or None if not found
        """
        return self.checkpoints.get(checkpoint_id)
    
    def submit_response(self, checkpoint_id: str, reviewer_id: str,
                       decision: str, feedback: str = None,
                       decision_data: Dict[str, Any] = None) -> bool:
        """
        Submit a response to a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            reviewer_id: ID of reviewer
            decision: 'approve' or 'reject'
            feedback: Optional feedback text
            decision_data: Optional additional data
            
        Returns:
            True if response was submitted successfully
        """
        try:
            checkpoint = self.checkpoints.get(checkpoint_id)
            if not checkpoint:
                logger.warning(f"⚠️ Checkpoint not found: {checkpoint_id}")
                return False
            
            if checkpoint.status != CheckpointStatus.PENDING:
                logger.warning(f"⚠️ Checkpoint not pending: {checkpoint_id}")
                return False
            
            # Update checkpoint
            checkpoint.reviewer_id = reviewer_id
            checkpoint.feedback = feedback
            checkpoint.decision_data = decision_data or {}
            checkpoint.resolved_at = datetime.now()
            
            if decision.lower() == "approve":
                checkpoint.status = CheckpointStatus.APPROVED
            elif decision.lower() == "reject":
                checkpoint.status = CheckpointStatus.REJECTED
            else:
                logger.warning(f"⚠️ Invalid decision: {decision}")
                return False
            
            # Notify handlers
            self._notify_handlers({
                "type": "checkpoint_resolved",
                "checkpoint_id": checkpoint_id,
                "project_id": checkpoint.project_id,
                "decision": decision,
                "feedback": feedback,
                "reviewer_id": reviewer_id
            })
            
            logger.info(f"✅ Checkpoint {decision}: {checkpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to submit response: {e}")
            return False
    
    def add_notification_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Add a notification handler for checkpoint events.
        
        Args:
            handler: Function to call on checkpoint events
        """
        self.notification_handlers.append(handler)
        logger.info("✅ Notification handler added")
    
    def _notify_handlers(self, data: Dict[str, Any]):
        """
        Notify all registered handlers of an event.
        
        Args:
            data: Event data
        """
        for handler in self.notification_handlers:
            try:
                handler(data)
            except Exception as e:
                logger.warning(f"⚠️ Notification handler error: {e}")
    
    def get_pending_checkpoints(self, project_id: str = None) -> List[CheckpointData]:
        """
        Get list of pending checkpoints.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            List of pending checkpoints
        """
        pending = [
            cp for cp in self.checkpoints.values()
            if cp.status == CheckpointStatus.PENDING
        ]
        
        if project_id:
            pending = [cp for cp in pending if cp.project_id == project_id]
        
        return pending
    
    def get_checkpoint_stats(self, project_id: str = None) -> Dict[str, int]:
        """
        Get checkpoint statistics.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            Statistics dictionary
        """
        checkpoints = list(self.checkpoints.values())
        
        if project_id:
            checkpoints = [cp for cp in checkpoints if cp.project_id == project_id]
        
        stats = {
            "total": len(checkpoints),
            "pending": len([cp for cp in checkpoints if cp.status == CheckpointStatus.PENDING]),
            "approved": len([cp for cp in checkpoints if cp.status == CheckpointStatus.APPROVED]),
            "rejected": len([cp for cp in checkpoints if cp.status == CheckpointStatus.REJECTED]),
            "timeout": len([cp for cp in checkpoints if cp.status == CheckpointStatus.TIMEOUT])
        }
        
        return stats
    
    def cleanup_old_checkpoints(self, hours: int = 24) -> int:
        """
        Clean up old resolved checkpoints.
        
        Args:
            hours: Age threshold in hours
            
        Returns:
            Number of checkpoints cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            to_remove = []
            
            for checkpoint_id, checkpoint in self.checkpoints.items():
                if (checkpoint.status != CheckpointStatus.PENDING and
                    checkpoint.resolved_at and
                    checkpoint.resolved_at < cutoff_time):
                    to_remove.append(checkpoint_id)
            
            for checkpoint_id in to_remove:
                del self.checkpoints[checkpoint_id]
            
            logger.info(f"✅ Cleaned up {len(to_remove)} old checkpoints")
            return len(to_remove)
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup checkpoints: {e}")
            return 0

def test_checkpoint_manager():
    """Test the checkpoint manager functionality."""
    try:
        print("🧪 Testing Checkpoint Manager")
        
        manager = CheckpointManager()
        print("✅ Checkpoint Manager created")
        
        # Test checkpoint creation
        checkpoint_id = manager.create_checkpoint(
            project_id="test-project",
            checkpoint_type=CheckpointType.STYLE_GUIDE_APPROVAL,
            title="Test Checkpoint",
            description="Testing checkpoint functionality",
            content="Sample content for review",
            priority=Priority.HIGH
        )
        print(f"✅ Checkpoint created: {checkpoint_id}")
        
        # Test checkpoint retrieval
        checkpoint = manager.get_checkpoint(checkpoint_id)
        print(f"✅ Checkpoint retrieved: {checkpoint.status.value}")
        
        # Test response submission
        success = manager.submit_response(
            checkpoint_id=checkpoint_id,
            reviewer_id="test-reviewer",
            decision="approve",
            feedback="Looks good!"
        )
        print(f"✅ Response submitted: {success}")
        
        # Test statistics
        stats = manager.get_checkpoint_stats("test-project")
        print(f"✅ Statistics: {stats['total']} total, {stats['approved']} approved")
        
        return {
            "success": True,
            "checkpoint_created": True,
            "response_submitted": success,
            "stats": stats
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Run test
    test_result = test_checkpoint_manager()
    print("\n" + "="*60)
    print("Checkpoint Manager Test Complete")
    print("="*60)
    print(f"Success: {test_result.get('success', False)}")
    if test_result.get('success'):
        print("✅ Checkpoint Manager operational")
        print(f"📊 Checkpoints: {test_result['stats']['total']}")
    else:
        print(f"❌ Error: {test_result.get('error', 'Unknown')}")