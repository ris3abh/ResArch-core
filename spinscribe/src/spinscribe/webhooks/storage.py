# =============================================================================
# SPINSCRIBE WORKFLOW STORAGE
# Persistent storage for HITL approval workflow state
# =============================================================================
"""
Storage module for managing workflow state, approval requests, and audit logs.

This module provides persistent storage for:
- Workflow execution state across HITL checkpoints
- Pending approval requests awaiting human review
- Approval decisions and feedback history
- Workflow metadata and execution timeline

Storage Strategy:
- In-memory dictionary for development/testing
- Can be replaced with Redis/PostgreSQL for production
- Thread-safe operations with proper locking
- Automatic cleanup of old workflows (>30 days)

Data Structure:
{
    "workflow_id": {
        "client_name": str,
        "topic": str,
        "content_type": str,
        "status": WorkflowStatus,
        "current_checkpoint": CheckpointType,
        "created_at": datetime,
        "updated_at": datetime,
        "task_outputs": {
            "task_name": "output_content"
        },
        "approval_history": [
            {
                "checkpoint": CheckpointType,
                "decision": ApprovalDecision,
                "feedback": str,
                "timestamp": datetime
            }
        ]
    }
}
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import json
import logging
from pathlib import Path

from spinscribe.webhooks.models import (
    WorkflowStatus,
    CheckpointType,
    ApprovalDecision,
    ApprovalRequest,
    PendingApprovalSummary,
    DashboardStats
)

logger = logging.getLogger(__name__)


# =============================================================================
# IN-MEMORY STORAGE (Thread-Safe)
# =============================================================================

class WorkflowStorage:
    """
    Thread-safe in-memory storage for workflow state.
    
    This implementation uses Python dictionaries with threading locks
    for concurrent access. For production, replace with Redis or PostgreSQL.
    """
    
    def __init__(self):
        """Initialize storage with thread locks."""
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._lock = threading.RLock()
        logger.info("📦 Workflow storage initialized (in-memory)")
    
    def create_workflow(
        self,
        workflow_id: str,
        client_name: str,
        topic: str,
        content_type: str,
        audience: str,
        ai_language_code: str
    ) -> Dict[str, Any]:
        """
        Create a new workflow entry.
        
        Args:
            workflow_id: Unique workflow identifier
            client_name: Client name
            topic: Content topic
            content_type: Type of content (blog, landing_page, local_article)
            audience: Target audience
            ai_language_code: AI Language Code for brand voice
        
        Returns:
            Created workflow dict
        """
        with self._lock:
            workflow = {
                "workflow_id": workflow_id,
                "client_name": client_name,
                "topic": topic,
                "content_type": content_type,
                "audience": audience,
                "ai_language_code": ai_language_code,
                "status": WorkflowStatus.ACTIVE.value,
                "current_checkpoint": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "task_outputs": {},
                "approval_history": [],
                "metadata": {}
            }
            
            self._workflows[workflow_id] = workflow
            logger.info(f"✨ Created workflow {workflow_id} for {client_name}")
            return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve workflow by ID.
        
        Args:
            workflow_id: Workflow identifier
        
        Returns:
            Workflow dict or None if not found
        """
        with self._lock:
            return self._workflows.get(workflow_id)
    
    def update_workflow(
        self,
        workflow_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update workflow fields.
        
        Args:
            workflow_id: Workflow identifier
            updates: Dictionary of fields to update
        
        Returns:
            Updated workflow or None if not found
        """
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                logger.warning(f"⚠️ Workflow {workflow_id} not found for update")
                return None
            
            workflow.update(updates)
            workflow["updated_at"] = datetime.utcnow().isoformat()
            
            logger.debug(f"📝 Updated workflow {workflow_id}: {list(updates.keys())}")
            return workflow
    
    def update_workflow_status(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        checkpoint: Optional[CheckpointType] = None
    ) -> bool:
        """
        Update workflow status and current checkpoint.
        
        Args:
            workflow_id: Workflow identifier
            status: New workflow status
            checkpoint: Current checkpoint (if applicable)
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return False
            
            workflow["status"] = status.value
            if checkpoint:
                workflow["current_checkpoint"] = checkpoint.value
            workflow["updated_at"] = datetime.utcnow().isoformat()
            
            logger.info(
                f"🔄 Workflow {workflow_id} status → {status.value}"
                f"{f' (checkpoint: {checkpoint.value})' if checkpoint else ''}"
            )
            return True
    
    def save_task_output(
        self,
        workflow_id: str,
        task_name: str,
        output: str
    ) -> bool:
        """
        Save output from a completed task.
        
        Args:
            workflow_id: Workflow identifier
            task_name: Name of completed task
            output: Task output content
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return False
            
            workflow["task_outputs"][task_name] = output
            workflow["updated_at"] = datetime.utcnow().isoformat()
            
            logger.debug(f"💾 Saved output for task '{task_name}' in workflow {workflow_id}")
            return True
    
    def add_approval_request(
        self,
        approval_request: ApprovalRequest
    ) -> None:
        """
        Store a pending approval request.
        
        Args:
            approval_request: ApprovalRequest model instance
        """
        with self._lock:
            self._approvals[approval_request.approval_id] = approval_request
            logger.info(
                f"📋 Added approval request {approval_request.approval_id} "
                f"for workflow {approval_request.workflow_id}"
            )
    
    def get_approval_request(
        self,
        approval_id: str
    ) -> Optional[ApprovalRequest]:
        """
        Retrieve an approval request by ID.
        
        Args:
            approval_id: Approval request identifier
        
        Returns:
            ApprovalRequest or None if not found
        """
        with self._lock:
            return self._approvals.get(approval_id)
    
    def remove_approval_request(self, approval_id: str) -> bool:
        """
        Remove an approval request after decision is made.
        
        Args:
            approval_id: Approval request identifier
        
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if approval_id in self._approvals:
                del self._approvals[approval_id]
                logger.debug(f"🗑️ Removed approval request {approval_id}")
                return True
            return False
    
    def add_approval_decision(
        self,
        workflow_id: str,
        checkpoint: CheckpointType,
        decision: ApprovalDecision,
        feedback: Optional[str] = None
    ) -> bool:
        """
        Record an approval decision in workflow history.
        
        Args:
            workflow_id: Workflow identifier
            checkpoint: Checkpoint where decision was made
            decision: Approval decision
            feedback: Optional human feedback
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return False
            
            approval_record = {
                "checkpoint": checkpoint.value,
                "decision": decision.value,
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            workflow["approval_history"].append(approval_record)
            workflow["updated_at"] = datetime.utcnow().isoformat()
            
            logger.info(
                f"✅ Recorded {decision.value} decision for workflow {workflow_id} "
                f"at {checkpoint.value} checkpoint"
            )
            return True
    
    def get_pending_approvals(self) -> List[PendingApprovalSummary]:
        """
        Get list of all pending approval requests.
        
        Returns:
            List of PendingApprovalSummary objects
        """
        with self._lock:
            summaries = []
            
            for approval_id, approval in self._approvals.items():
                workflow = self._workflows.get(approval.workflow_id)
                if not workflow:
                    continue
                
                summary = PendingApprovalSummary(
                    workflow_id=approval.workflow_id,
                    checkpoint=approval.checkpoint,
                    client_name=workflow["client_name"],
                    topic=workflow["topic"],
                    created_at=approval.created_at,
                    approval_id=approval_id
                )
                summaries.append(summary)
            
            # Sort by creation time (oldest first)
            summaries.sort(key=lambda x: x.created_at)
            
            return summaries
    
    def get_dashboard_stats(self) -> DashboardStats:
        """
        Get statistics for dashboard display.
        
        Returns:
            DashboardStats object with current metrics
        """
        with self._lock:
            total_workflows = len(self._workflows)
            pending_approvals = len(self._approvals)
            
            active_workflows = sum(
                1 for w in self._workflows.values()
                if w["status"] == WorkflowStatus.ACTIVE.value
            )
            
            # Count approvals/rejections today
            today = datetime.utcnow().date()
            approved_today = 0
            rejected_today = 0
            
            for workflow in self._workflows.values():
                for record in workflow["approval_history"]:
                    record_date = datetime.fromisoformat(record["timestamp"]).date()
                    if record_date == today:
                        if record["decision"] == ApprovalDecision.APPROVED.value:
                            approved_today += 1
                        elif record["decision"] == ApprovalDecision.REJECTED.value:
                            rejected_today += 1
            
            return DashboardStats(
                total_workflows=total_workflows,
                pending_approvals=pending_approvals,
                active_workflows=active_workflows,
                approved_today=approved_today,
                rejected_today=rejected_today
            )
    
    def cleanup_old_workflows(self, days: int = 30) -> int:
        """
        Remove workflows older than specified days.
        
        Args:
            days: Number of days to retain workflows
        
        Returns:
            Number of workflows removed
        """
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            to_remove = []
            for workflow_id, workflow in self._workflows.items():
                updated_at = datetime.fromisoformat(workflow["updated_at"])
                if updated_at < cutoff:
                    to_remove.append(workflow_id)
            
            for workflow_id in to_remove:
                del self._workflows[workflow_id]
            
            if to_remove:
                logger.info(f"🧹 Cleaned up {len(to_remove)} old workflows")
            
            return len(to_remove)
    
    def export_workflow(self, workflow_id: str) -> Optional[str]:
        """
        Export workflow as JSON string.
        
        Args:
            workflow_id: Workflow identifier
        
        Returns:
            JSON string or None if not found
        """
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return None
            
            return json.dumps(workflow, indent=2)
    
    def list_workflows(
        self,
        client_name: Optional[str] = None,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List workflows with optional filtering.
        
        Args:
            client_name: Filter by client name
            status: Filter by workflow status
            limit: Maximum number of results
        
        Returns:
            List of workflow dictionaries
        """
        with self._lock:
            workflows = list(self._workflows.values())
            
            # Apply filters
            if client_name:
                workflows = [
                    w for w in workflows
                    if w["client_name"] == client_name
                ]
            
            if status:
                workflows = [
                    w for w in workflows
                    if w["status"] == status.value
                ]
            
            # Sort by updated_at (most recent first)
            workflows.sort(
                key=lambda x: x["updated_at"],
                reverse=True
            )
            
            return workflows[:limit]


# =============================================================================
# GLOBAL STORAGE INSTANCE
# =============================================================================

# Singleton instance for application-wide use
workflow_storage = WorkflowStorage()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def save_workflow_state(
    workflow_id: str,
    task_name: str,
    output: str
) -> bool:
    """
    Convenience function to save task output.
    
    Args:
        workflow_id: Workflow identifier
        task_name: Task name
        output: Task output
    
    Returns:
        True if successful
    """
    return workflow_storage.save_task_output(workflow_id, task_name, output)


def get_workflow_state(workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get workflow.
    
    Args:
        workflow_id: Workflow identifier
    
    Returns:
        Workflow dict or None
    """
    return workflow_storage.get_workflow(workflow_id)


def update_workflow_status(
    workflow_id: str,
    status: WorkflowStatus,
    checkpoint: Optional[CheckpointType] = None
) -> bool:
    """
    Convenience function to update workflow status.
    
    Args:
        workflow_id: Workflow identifier
        status: New status
        checkpoint: Current checkpoint
    
    Returns:
        True if successful
    """
    return workflow_storage.update_workflow_status(workflow_id, status, checkpoint)


def get_pending_approvals() -> List[PendingApprovalSummary]:
    """
    Convenience function to get pending approvals.
    
    Returns:
        List of pending approval summaries
    """
    return workflow_storage.get_pending_approvals()


def cleanup_old_workflows(days: int = 30) -> int:
    """
    Convenience function to cleanup old workflows.
    
    Args:
        days: Retention period in days
    
    Returns:
        Number of workflows removed
    """
    return workflow_storage.cleanup_old_workflows(days)