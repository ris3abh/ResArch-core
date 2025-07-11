# ─── COMPLETE FIXED FILE: spinscribe/checkpoints/checkpoint_manager.py ───

"""
Checkpoint Manager for human-in-the-loop workflow approval.
COMPLETE FIXED VERSION with proper implementation and fallbacks.
"""

import logging
import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

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
    resolved_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    feedback: Optional[str] = None
    decision_data: Optional[Dict[str, Any]] = None

class CheckpointManager:
    """
    Manages human checkpoints in the content creation workflow.
    """
    
    def __init__(self):
        self.checkpoints: Dict[str, CheckpointData] = {}
        self.notification_handlers: List[Callable] = []
        self.auto_approve_timeout = 300  # 5 minutes default
        
        logger.info("✅ Checkpoint Manager initialized")
    
    def create_checkpoint(self, project_id: str, checkpoint_type: CheckpointType,
                         title: str, description: str, content: str = "") -> str:
        """
        Create a new checkpoint for human review.
        
        Args:
            project_id: Project identifier
            checkpoint_type: Type of checkpoint
            title: Checkpoint title
            description: Checkpoint description
            content: Content to review
            
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
                created_at=datetime.now()
            )
            
            self.checkpoints[checkpoint_id] = checkpoint
            
            # Notify handlers
            self._notify_handlers({
                "type": "checkpoint_created",
                "checkpoint_id": checkpoint_id,
                "project_id": project_id,
                "checkpoint_type": checkpoint_type.value,
                "title": title,
                "description": description
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
            reviewer_id: ID of the reviewer
            decision: "approve" or "reject"
            feedback: Optional feedback text
            decision_data: Optional additional decision data
            
        Returns:
            Success status
        """
        try:
            checkpoint = self.checkpoints.get(checkpoint_id)
            if not checkpoint:
                logger.warning(f"⚠️ Checkpoint not found: {checkpoint_id}")
                return False
            
            if checkpoint.status != CheckpointStatus.PENDING:
                logger.warning(f"⚠️ Checkpoint already resolved: {checkpoint_id}")
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
                "status": checkpoint.status.value,
                "reviewer_id": reviewer_id,
                "feedback": feedback,
                "decision": decision
            })
            
            logger.info(f"✅ Checkpoint resolved: {checkpoint_id} ({decision})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to submit checkpoint response: {e}")
            return False
    
    def wait_for_checkpoint(self, checkpoint_id: str, timeout: int = None) -> CheckpointData:
        """
        Wait for a checkpoint to be resolved.
        
        Args:
            checkpoint_id: Checkpoint identifier
            timeout: Maximum wait time in seconds
            
        Returns:
            Resolved checkpoint data
        """
        try:
            timeout = timeout or self.auto_approve_timeout
            start_time = time.time()
            
            checkpoint = self.checkpoints.get(checkpoint_id)
            if not checkpoint:
                raise ValueError(f"Checkpoint not found: {checkpoint_id}")
            
            logger.info(f"⏳ Waiting for checkpoint resolution: {checkpoint_id}")
            
            # Poll for resolution
            while checkpoint.status == CheckpointStatus.PENDING:
                if time.time() - start_time > timeout:
                    # Timeout - auto-approve or mark as timeout
                    checkpoint.status = CheckpointStatus.TIMEOUT
                    checkpoint.resolved_at = datetime.now()
                    checkpoint.feedback = "Auto-approved due to timeout"
                    
                    self._notify_handlers({
                        "type": "checkpoint_timeout",
                        "checkpoint_id": checkpoint_id,
                        "project_id": checkpoint.project_id
                    })
                    
                    logger.warning(f"⏰ Checkpoint timed out: {checkpoint_id}")
                    break
                
                time.sleep(1)  # Poll every second
            
            return checkpoint
            
        except Exception as e:
            logger.error(f"❌ Error waiting for checkpoint: {e}")
            raise
    
    def get_project_checkpoints(self, project_id: str) -> List[CheckpointData]:
        """
        Get all checkpoints for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of checkpoints for the project
        """
        try:
            project_checkpoints = [
                cp for cp in self.checkpoints.values()
                if cp.project_id == project_id
            ]
            
            # Sort by creation time
            project_checkpoints.sort(key=lambda x: x.created_at)
            
            return project_checkpoints
            
        except Exception as e:
            logger.error(f"❌ Error retrieving project checkpoints: {e}")
            return []
    
    def get_pending_checkpoints(self, project_id: str = None) -> List[CheckpointData]:
        """
        Get all pending checkpoints, optionally filtered by project.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            List of pending checkpoints
        """
        try:
            pending = [
                cp for cp in self.checkpoints.values()
                if cp.status == CheckpointStatus.PENDING
            ]
            
            if project_id:
                pending = [cp for cp in pending if cp.project_id == project_id]
            
            # Sort by creation time
            pending.sort(key=lambda x: x.created_at)
            
            return pending
            
        except Exception as e:
            logger.error(f"❌ Error retrieving pending checkpoints: {e}")
            return []
    
    def cancel_checkpoint(self, checkpoint_id: str, reason: str = None) -> bool:
        """
        Cancel a pending checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            reason: Optional cancellation reason
            
        Returns:
            Success status
        """
        try:
            checkpoint = self.checkpoints.get(checkpoint_id)
            if not checkpoint:
                logger.warning(f"⚠️ Checkpoint not found: {checkpoint_id}")
                return False
            
            if checkpoint.status != CheckpointStatus.PENDING:
                logger.warning(f"⚠️ Checkpoint not pending: {checkpoint_id}")
                return False
            
            checkpoint.status = CheckpointStatus.CANCELLED
            checkpoint.resolved_at = datetime.now()
            checkpoint.feedback = reason or "Cancelled by system"
            
            self._notify_handlers({
                "type": "checkpoint_cancelled",
                "checkpoint_id": checkpoint_id,
                "project_id": checkpoint.project_id,
                "reason": reason
            })
            
            logger.info(f"✅ Checkpoint cancelled: {checkpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel checkpoint: {e}")
            return False
    
    def add_notification_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Add a notification handler for checkpoint events.
        
        Args:
            handler: Function to handle notifications
        """
        try:
            self.notification_handlers.append(handler)
            logger.info("✅ Notification handler added")
        except Exception as e:
            logger.error(f"❌ Failed to add notification handler: {e}")
    
    def _notify_handlers(self, notification: Dict[str, Any]):
        """
        Notify all registered handlers of an event.
        
        Args:
            notification: Notification data
        """
        try:
            for handler in self.notification_handlers:
                try:
                    handler(notification)
                except Exception as e:
                    logger.warning(f"⚠️ Notification handler failed: {e}")
        except Exception as e:
            logger.error(f"❌ Error notifying handlers: {e}")
    
    def get_checkpoint_stats(self, project_id: str = None) -> Dict[str, Any]:
        """
        Get checkpoint statistics.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            Checkpoint statistics
        """
        try:
            checkpoints = list(self.checkpoints.values())
            
            if project_id:
                checkpoints = [cp for cp in checkpoints if cp.project_id == project_id]
            
            stats = {
                "total": len(checkpoints),
                "pending": len([cp for cp in checkpoints if cp.status == CheckpointStatus.PENDING]),
                "approved": len([cp for cp in checkpoints if cp.status == CheckpointStatus.APPROVED]),
                "rejected": len([cp for cp in checkpoints if cp.status == CheckpointStatus.REJECTED]),
                "timeout": len([cp for cp in checkpoints if cp.status == CheckpointStatus.TIMEOUT]),
                "cancelled": len([cp for cp in checkpoints if cp.status == CheckpointStatus.CANCELLED])
            }
            
            # Calculate approval rate
            resolved = stats["approved"] + stats["rejected"]
            if resolved > 0:
                stats["approval_rate"] = stats["approved"] / resolved
            else:
                stats["approval_rate"] = 0.0
            
            # Calculate average resolution time
            resolved_checkpoints = [
                cp for cp in checkpoints
                if cp.status in [CheckpointStatus.APPROVED, CheckpointStatus.REJECTED]
                and cp.resolved_at
            ]
            
            if resolved_checkpoints:
                total_time = sum(
                    (cp.resolved_at - cp.created_at).total_seconds()
                    for cp in resolved_checkpoints
                )
                stats["avg_resolution_time"] = total_time / len(resolved_checkpoints)
            else:
                stats["avg_resolution_time"] = 0.0
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error calculating checkpoint stats: {e}")
            return {"error": str(e)}
    
    def export_checkpoint_data(self, project_id: str = None) -> List[Dict[str, Any]]:
        """
        Export checkpoint data for analysis.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            List of checkpoint data dictionaries
        """
        try:
            checkpoints = list(self.checkpoints.values())
            
            if project_id:
                checkpoints = [cp for cp in checkpoints if cp.project_id == project_id]
            
            export_data = []
            for cp in checkpoints:
                export_data.append({
                    "id": cp.id,
                    "project_id": cp.project_id,
                    "type": cp.checkpoint_type.value,
                    "title": cp.title,
                    "description": cp.description,
                    "status": cp.status.value,
                    "created_at": cp.created_at.isoformat(),
                    "resolved_at": cp.resolved_at.isoformat() if cp.resolved_at else None,
                    "reviewer_id": cp.reviewer_id,
                    "feedback": cp.feedback,
                    "content_length": len(cp.content) if cp.content else 0
                })
            
            return export_data
            
        except Exception as e:
            logger.error(f"❌ Error exporting checkpoint data: {e}")
            return []


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
            content="Sample content for review"
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