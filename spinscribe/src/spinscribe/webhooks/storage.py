# =============================================================================
# SPINSCRIBE WEBHOOK STORAGE
# In-memory workflow state management
# =============================================================================
"""
Storage system for managing workflow states and approval requests.

This module provides in-memory storage for workflow tracking. In production,
this should be replaced with Redis, PostgreSQL, or another persistent datastore.

The storage maintains:
- Workflow states and current status
- Approval requests and responses
- Audit trail of all decisions
- Cleanup of old workflows
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
import logging

from spinscribe.webhooks.models import (
    WorkflowStatus,
    CheckpointType,
    ApprovalRequest
)

logger = logging.getLogger(__name__)


# =============================================================================
# IN-MEMORY STORAGE
# =============================================================================

# Main workflow storage
# In production: Replace with Redis, PostgreSQL, or MongoDB
workflow_storage: Dict[str, Dict[str, Any]] = OrderedDict()

# Storage limits
MAX_WORKFLOWS = 1000  # Maximum workflows to keep in memory
MAX_AGE_HOURS = 48    # Maximum age before cleanup


# =============================================================================
# STORAGE OPERATIONS
# =============================================================================

def save_workflow_state(
    workflow_id: str,
    checkpoint_type: CheckpointType,
    content: str,
    metadata: Dict[str, Any],
    approval_request: ApprovalRequest
) -> None:
    """
    Save or update workflow state.
    
    Args:
        workflow_id: Unique workflow identifier
        checkpoint_type: Type of checkpoint
        content: Content or analysis awaiting approval
        metadata: Additional context
        approval_request: Generated approval request
    """
    now = datetime.utcnow().isoformat()
    
    # Check if workflow exists
    if workflow_id in workflow_storage:
        logger.info(f"Updating existing workflow: {workflow_id}")
        workflow_storage[workflow_id].update({
            "checkpoint_type": checkpoint_type,
            "content": content,
            "metadata": metadata,
            "approval_request": approval_request.dict(),
            "status": WorkflowStatus.AWAITING_APPROVAL,
            "updated_at": now
        })
        
        # Add to history
        workflow_storage[workflow_id]["history"].append({
            "checkpoint": checkpoint_type,
            "timestamp": now,
            "action": "checkpoint_reached"
        })
    else:
        logger.info(f"Creating new workflow: {workflow_id}")
        workflow_storage[workflow_id] = {
            "workflow_id": workflow_id,
            "checkpoint_type": checkpoint_type,
            "content": content,
            "metadata": metadata,
            "approval_request": approval_request.dict(),
            "approval_response": None,
            "status": WorkflowStatus.AWAITING_APPROVAL,
            "created_at": now,
            "updated_at": now,
            "history": [{
                "checkpoint": checkpoint_type,
                "timestamp": now,
                "action": "workflow_created"
            }]
        }
    
    # Enforce storage limits
    _enforce_storage_limits()
    
    logger.info(f"Workflow state saved: {workflow_id} (Total: {len(workflow_storage)})")


def get_workflow_state(workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve workflow state by ID.
    
    Args:
        workflow_id: Workflow identifier
    
    Returns:
        Workflow state dictionary or None if not found
    """
    return workflow_storage.get(workflow_id)


def update_workflow_status(workflow_id: str, status: WorkflowStatus) -> None:
    """
    Update the status of a workflow.
    
    Args:
        workflow_id: Workflow identifier
        status: New status
    """
    if workflow_id in workflow_storage:
        now = datetime.utcnow().isoformat()
        workflow_storage[workflow_id]["status"] = status
        workflow_storage[workflow_id]["updated_at"] = now
        
        # Add to history
        workflow_storage[workflow_id]["history"].append({
            "timestamp": now,
            "action": "status_updated",
            "new_status": status
        })
        
        logger.info(f"Workflow {workflow_id} status updated to: {status}")
    else:
        logger.warning(f"Attempted to update non-existent workflow: {workflow_id}")


def get_pending_approvals() -> Dict[str, Dict[str, Any]]:
    """
    Get all workflows awaiting human approval.
    
    Returns:
        Dictionary of workflows in AWAITING_APPROVAL status
    """
    pending = {
        wf_id: state
        for wf_id, state in workflow_storage.items()
        if state["status"] == WorkflowStatus.AWAITING_APPROVAL
    }
    
    logger.debug(f"Found {len(pending)} pending approvals")
    return pending


def get_workflows_by_status(status: WorkflowStatus) -> Dict[str, Dict[str, Any]]:
    """
    Get all workflows with a specific status.
    
    Args:
        status: Workflow status to filter by
    
    Returns:
        Dictionary of matching workflows
    """
    filtered = {
        wf_id: state
        for wf_id, state in workflow_storage.items()
        if state["status"] == status
    }
    
    return filtered


def delete_workflow(workflow_id: str) -> bool:
    """
    Delete a workflow from storage.
    
    Args:
        workflow_id: Workflow identifier
    
    Returns:
        True if deleted, False if not found
    """
    if workflow_id in workflow_storage:
        del workflow_storage[workflow_id]
        logger.info(f"Workflow deleted: {workflow_id}")
        return True
    else:
        logger.warning(f"Attempted to delete non-existent workflow: {workflow_id}")
        return False


# =============================================================================
# STORAGE MANAGEMENT
# =============================================================================

def _enforce_storage_limits() -> None:
    """
    Enforce maximum storage limits by removing oldest workflows.
    
    This prevents unbounded memory growth. In production, use a
    database with proper archiving instead.
    """
    if len(workflow_storage) > MAX_WORKFLOWS:
        # Remove oldest workflows (OrderedDict maintains insertion order)
        remove_count = len(workflow_storage) - MAX_WORKFLOWS
        oldest_ids = list(workflow_storage.keys())[:remove_count]
        
        for workflow_id in oldest_ids:
            logger.info(f"Removing workflow due to storage limit: {workflow_id}")
            del workflow_storage[workflow_id]
        
        logger.warning(f"Storage limit enforced: removed {remove_count} oldest workflows")


def cleanup_old_workflows(hours: int = MAX_AGE_HOURS) -> int:
    """
    Clean up workflows older than specified hours.
    
    This is typically called as a background task to prevent
    memory accumulation.
    
    Args:
        hours: Maximum age in hours before cleanup
    
    Returns:
        Number of workflows cleaned up
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    cutoff_iso = cutoff_time.isoformat()
    
    workflows_to_remove = []
    
    for workflow_id, state in workflow_storage.items():
        created_at = datetime.fromisoformat(state["created_at"].replace('Z', '+00:00').replace('+00:00', ''))
        
        if created_at < cutoff_time:
            workflows_to_remove.append(workflow_id)
    
    # Remove old workflows
    for workflow_id in workflows_to_remove:
        logger.info(f"Cleaning up old workflow: {workflow_id}")
        del workflow_storage[workflow_id]
    
    if workflows_to_remove:
        logger.info(f"Cleanup complete: removed {len(workflows_to_remove)} workflows older than {hours} hours")
    
    return len(workflows_to_remove)


def get_storage_stats() -> Dict[str, Any]:
    """
    Get statistics about current storage state.
    
    Returns:
        Dictionary with storage statistics
    """
    status_counts = {}
    for state in workflow_storage.values():
        status = state["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    checkpoint_counts = {}
    for state in workflow_storage.values():
        checkpoint = state["checkpoint_type"]
        checkpoint_counts[checkpoint] = checkpoint_counts.get(checkpoint, 0) + 1
    
    # Calculate age distribution
    now = datetime.utcnow()
    age_distribution = {
        "under_1h": 0,
        "1h_to_6h": 0,
        "6h_to_24h": 0,
        "over_24h": 0
    }
    
    for state in workflow_storage.values():
        created_at = datetime.fromisoformat(state["created_at"].replace('Z', '+00:00').replace('+00:00', ''))
        age_hours = (now - created_at).total_seconds() / 3600
        
        if age_hours < 1:
            age_distribution["under_1h"] += 1
        elif age_hours < 6:
            age_distribution["1h_to_6h"] += 1
        elif age_hours < 24:
            age_distribution["6h_to_24h"] += 1
        else:
            age_distribution["over_24h"] += 1
    
    return {
        "total_workflows": len(workflow_storage),
        "by_status": status_counts,
        "by_checkpoint": checkpoint_counts,
        "age_distribution": age_distribution,
        "storage_limit": MAX_WORKFLOWS,
        "max_age_hours": MAX_AGE_HOURS
    }


# =============================================================================
# AUDIT TRAIL
# =============================================================================

def add_audit_entry(
    workflow_id: str,
    action: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add an audit trail entry to a workflow.
    
    Args:
        workflow_id: Workflow identifier
        action: Description of action taken
        details: Additional details about the action
    """
    if workflow_id in workflow_storage:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action
        }
        
        if details:
            entry.update(details)
        
        workflow_storage[workflow_id]["history"].append(entry)
        logger.debug(f"Audit entry added to {workflow_id}: {action}")
    else:
        logger.warning(f"Attempted to add audit entry to non-existent workflow: {workflow_id}")


def get_audit_trail(workflow_id: str) -> List[Dict[str, Any]]:
    """
    Get complete audit trail for a workflow.
    
    Args:
        workflow_id: Workflow identifier
    
    Returns:
        List of audit entries
    """
    if workflow_id in workflow_storage:
        return workflow_storage[workflow_id].get("history", [])
    else:
        return []


# =============================================================================
# SEARCH AND FILTERING
# =============================================================================

def search_workflows(
    client_name: Optional[str] = None,
    topic: Optional[str] = None,
    checkpoint_type: Optional[CheckpointType] = None,
    status: Optional[WorkflowStatus] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Search workflows by various criteria.
    
    Args:
        client_name: Filter by client name
        topic: Filter by topic
        checkpoint_type: Filter by checkpoint type
        status: Filter by workflow status
    
    Returns:
        Dictionary of matching workflows
    """
    results = {}
    
    for workflow_id, state in workflow_storage.items():
        # Apply filters
        if client_name and state["metadata"].get("client_name") != client_name:
            continue
        if topic and state["metadata"].get("topic") != topic:
            continue
        if checkpoint_type and state["checkpoint_type"] != checkpoint_type:
            continue
        if status and state["status"] != status:
            continue
        
        results[workflow_id] = state
    
    logger.debug(f"Search found {len(results)} matching workflows")
    return results


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_storage():
    """Initialize storage system (called on server startup)."""
    logger.info("Initializing workflow storage...")
    logger.info(f"Storage limits: {MAX_WORKFLOWS} workflows, {MAX_AGE_HOURS} hours max age")
    logger.info("Storage system ready")


def clear_all_storage():
    """
    Clear all storage (use with caution!).
    
    This is primarily for testing or maintenance.
    """
    workflow_storage.clear()
    logger.warning("All workflow storage cleared!")


# Initialize on import
initialize_storage()