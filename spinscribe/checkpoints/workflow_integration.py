# File: spinscribe/checkpoints/workflow_integration.py
"""
Complete WorkflowCheckpointIntegration implementation for integrating checkpoints into workflows.
Fixes the timeout issue by implementing proper async waiting with polling and auto-approval fallback.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from spinscribe.checkpoints.checkpoint_manager import (
    get_checkpoint_manager,
    CheckpointManager, 
    CheckpointType, 
    Priority
)

logger = logging.getLogger(__name__)

class WorkflowCheckpointIntegration:
    """Integrates checkpoint functionality into the SpinScribe workflow execution."""
    
    def __init__(
        self,
        project_id: str,
        workflow_id: str = None,
        enable_checkpoints: bool = True,
        enable_async: bool = True,
        checkpoint_manager: CheckpointManager = None
    ):
        """
        Initialize workflow checkpoint integration.
        
        Args:
            project_id: The project ID
            workflow_id: The workflow ID (optional for backwards compatibility)
            enable_checkpoints: Whether to enable checkpoints
            enable_async: Whether to use async operations
            checkpoint_manager: Optional checkpoint manager instance
        """
        self.checkpoint_manager = checkpoint_manager or get_checkpoint_manager()
        self.project_id = project_id
        self.workflow_id = workflow_id or f"workflow_{id(self)}"
        self.enable_checkpoints = enable_checkpoints
        self.enable_async = enable_async
        self.active_checkpoints = {}
        self.created_checkpoints = []
        logger.info(f"✅ WorkflowCheckpointIntegration initialized for project {project_id}, workflow {self.workflow_id}")
    
    async def request_approval(
        self,
        checkpoint_type: CheckpointType,
        title: str,
        content: str,
        description: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        timeout_seconds: int = 300,
        timeout_hours: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Request approval for a checkpoint and wait for response.
        
        Returns:
            Dict containing decision and feedback
        """
        if not self.enable_checkpoints:
            logger.info("⏭️ Checkpoints disabled, auto-approving")
            return {
                "checkpoint_id": None,
                "approved": True,
                "decision": "approve",
                "feedback": "Auto-approved (checkpoints disabled)",
                "auto_approved": True
            }
        
        logger.info(f"📋 Requesting approval for: {title}")
        
        # Handle both timeout_hours and timeout_seconds for compatibility
        if timeout_hours is not None:
            actual_timeout_seconds = timeout_hours * 3600
        else:
            actual_timeout_seconds = timeout_seconds
        
        # Create the checkpoint with workflow_id in metadata
        enhanced_metadata = {
            **(metadata or {}),
            "workflow_id": self.workflow_id,
            "requested_at": datetime.now().isoformat()
        }
        
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            project_id=self.project_id,
            checkpoint_type=checkpoint_type,
            title=title,
            description=description or f"Approval required for {title}",
            content=content,
            priority=priority,
            timeout_hours=actual_timeout_seconds // 3600 if actual_timeout_seconds >= 3600 else 1,
            metadata=enhanced_metadata
        )
        
        self.active_checkpoints[checkpoint_id] = {
            'type': checkpoint_type,
            'title': title,
            'created_at': datetime.now()
        }
        self.created_checkpoints.append(checkpoint_id)
        
        # Display checkpoint information with curl command for testing
        logger.info(f"""
🔴 CHECKPOINT {len(self.created_checkpoints)}: {title.upper()}
================================================================================
Type: {checkpoint_type.value}
Title: {title}
ID: {checkpoint_id}
Description: {description or 'Approval required'}
Priority: {priority.value}
Workflow: {self.workflow_id}

Content Preview:
--------------------------------------------------
{content[:500]}{"..." if len(content) > 500 else ""}
--------------------------------------------------

💡 TO APPROVE THIS CHECKPOINT:
   curl -X POST "http://localhost:8000/api/v1/workflows/checkpoint/{checkpoint_id}/respond" \\
        -H "Content-Type: application/json" \\
        -H "Authorization: Bearer YOUR_TOKEN" \\
        -d '{{"decision": "approve", "feedback": "Looks good"}}'
        
   OR TO REJECT:
   curl -X POST "http://localhost:8000/api/v1/workflows/checkpoint/{checkpoint_id}/respond" \\
        -H "Content-Type: application/json" \\
        -H "Authorization: Bearer YOUR_TOKEN" \\
        -d '{{"decision": "reject", "feedback": "Needs revision"}}'
================================================================================
⏳ Workflow paused - waiting for your response (timeout: {actual_timeout_seconds}s)...
        """)
        
        # Wait for checkpoint resolution
        if self.enable_async:
            decision = await self._wait_for_approval_async(checkpoint_id, actual_timeout_seconds)
        else:
            decision = self.checkpoint_manager.wait_for_checkpoint(checkpoint_id, actual_timeout_seconds)
        
        # Get the full response with feedback
        response = self.checkpoint_manager.get_response(checkpoint_id)
        checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
        
        result = {
            'checkpoint_id': checkpoint_id,
            'approved': decision and decision.lower() == 'approve',
            'decision': decision or 'timeout',
            'feedback': response.get('feedback') if response else (checkpoint.feedback if checkpoint else None),
            'reviewer_id': response.get('reviewer_id') if response else (checkpoint.reviewer_id if checkpoint else None),
            'auto_approved': response.get('reviewer_id') == 'system' if response else False
        }
        
        # Clean up
        if checkpoint_id in self.active_checkpoints:
            del self.active_checkpoints[checkpoint_id]
        
        if result['approved']:
            logger.info(f"✅ Checkpoint {checkpoint_id} approved" + 
                       (" (auto)" if result['auto_approved'] else ""))
        elif decision == 'reject':
            logger.info(f"❌ Checkpoint {checkpoint_id} rejected: {result['feedback']}")
            raise ValueError(f"Checkpoint rejected: {result.get('feedback', 'No feedback provided')}")
        else:
            logger.warning(f"⏱️ Checkpoint {checkpoint_id} timed out - auto-approved to continue")
        
        return result
    
    async def _wait_for_approval_async(
        self,
        checkpoint_id: str,
        timeout_seconds: int
    ) -> Optional[str]:
        """
        Async wait for checkpoint approval with improved polling and auto-approval.
        """
        start_time = time.time()
        poll_interval = 2  # Check every 2 seconds instead of 1 for efficiency
        reminder_sent = False
        halfway_reminder_sent = False
        
        while time.time() - start_time < timeout_seconds:
            # First check for stored response (critical for fixing timeout issue)
            response = self.checkpoint_manager.get_response(checkpoint_id)
            if response:
                logger.info(f"✅ Found response for checkpoint {checkpoint_id}")
                return response.get("decision")
            
            # Also check checkpoint status
            checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
            if checkpoint and checkpoint.decision:
                return checkpoint.decision
            
            # Send reminders at intervals
            elapsed = time.time() - start_time
            
            if not halfway_reminder_sent and elapsed > timeout_seconds / 2:
                logger.warning(f"⏰ Checkpoint {checkpoint_id} waiting for {elapsed:.0f}s - timeout in {timeout_seconds - elapsed:.0f}s")
                halfway_reminder_sent = True
            
            if not reminder_sent and elapsed > timeout_seconds * 0.75:
                logger.warning(f"⚠️ Checkpoint {checkpoint_id} will auto-approve in {timeout_seconds - elapsed:.0f}s")
                reminder_sent = True
            
            await asyncio.sleep(poll_interval)
        
        # Timeout reached - auto-approve to prevent workflow failure
        logger.warning(f"⚠️ Checkpoint {checkpoint_id} timed out after {timeout_seconds}s - auto-approving to continue")
        
        # Auto-approve using the enhanced checkpoint manager
        self.checkpoint_manager.submit_response(
            checkpoint_id=checkpoint_id,
            reviewer_id="system",
            decision="approve",
            feedback=f"Auto-approved due to timeout after {timeout_seconds} seconds"
        )
        
        return "approve"
    
    # Convenience methods for creating specific checkpoint types
    async def create_and_wait_for_checkpoint(
        self,
        checkpoint_type: CheckpointType,
        title: str,
        description: str,
        content: str,
        priority: Priority = Priority.MEDIUM,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Create a checkpoint and wait for approval.
        Wrapper method for backwards compatibility.
        """
        return await self.request_approval(
            checkpoint_type=checkpoint_type,
            title=title,
            content=content,
            description=description,
            priority=priority,
            timeout_seconds=timeout
        )
    
    def create_style_checkpoint(
        self,
        style_analysis: str,
        language_codes: str
    ) -> Dict[str, Any]:
        """Create a checkpoint for style analysis approval."""
        return asyncio.run(self.request_approval(
            checkpoint_type=CheckpointType.STYLE_ANALYSIS,
            title="Style Analysis Review",
            content=f"Style Analysis:\n{style_analysis}\n\nLanguage Codes:\n{language_codes}",
            description="Review and approve the style analysis and language codes",
            priority=Priority.HIGH
        )) if self.enable_async else self.request_approval(
            checkpoint_type=CheckpointType.STYLE_ANALYSIS,
            title="Style Analysis Review",
            content=f"Style Analysis:\n{style_analysis}\n\nLanguage Codes:\n{language_codes}",
            description="Review and approve the style analysis and language codes",
            priority=Priority.HIGH
        )
    
    def create_outline_checkpoint(
        self,
        outline: str,
        strategy: str
    ) -> Dict[str, Any]:
        """Create a checkpoint for content outline approval."""
        return asyncio.run(self.request_approval(
            checkpoint_type=CheckpointType.OUTLINE_REVIEW,
            title="Content Outline Review",
            content=f"Content Strategy:\n{strategy}\n\nOutline:\n{outline}",
            description="Review and approve the content outline",
            priority=Priority.MEDIUM
        )) if self.enable_async else self.request_approval(
            checkpoint_type=CheckpointType.OUTLINE_REVIEW,
            title="Content Outline Review",
            content=f"Content Strategy:\n{strategy}\n\nOutline:\n{outline}",
            description="Review and approve the content outline",
            priority=Priority.MEDIUM
        )
    
    def create_draft_checkpoint(
        self,
        draft_content: str
    ) -> Dict[str, Any]:
        """Create a checkpoint for draft content approval."""
        return asyncio.run(self.request_approval(
            checkpoint_type=CheckpointType.DRAFT_REVIEW,
            title="Draft Content Review",
            content=draft_content,
            description="Review and approve the draft content",
            priority=Priority.MEDIUM
        )) if self.enable_async else self.request_approval(
            checkpoint_type=CheckpointType.DRAFT_REVIEW,
            title="Draft Content Review",
            content=draft_content,
            description="Review and approve the draft content",
            priority=Priority.MEDIUM
        )
    
    def create_final_checkpoint(
        self,
        final_content: str
    ) -> Dict[str, Any]:
        """Create a checkpoint for final content approval."""
        return asyncio.run(self.request_approval(
            checkpoint_type=CheckpointType.FINAL_APPROVAL,
            title="Final Content Approval",
            content=final_content,
            description="Final review and approval before publication",
            priority=Priority.HIGH
        )) if self.enable_async else self.request_approval(
            checkpoint_type=CheckpointType.FINAL_APPROVAL,
            title="Final Content Approval",
            content=final_content,
            description="Final review and approval before publication",
            priority=Priority.HIGH
        )
    
    def create_strategy_checkpoint(
        self,
        strategy: str,
        content_type: str
    ) -> Dict[str, Any]:
        """Create a checkpoint for strategy approval (addresses the log error)."""
        return asyncio.run(self.request_approval(
            checkpoint_type=CheckpointType.STRATEGY_APPROVAL,
            title="Strategy Approval",
            content=f"Content Type: {content_type}\n\nProposed Strategy:\n{strategy}",
            description="Review and approve the content strategy before proceeding",
            priority=Priority.HIGH,
            timeout_seconds=600  # Longer timeout for strategy decisions
        )) if self.enable_async else self.request_approval(
            checkpoint_type=CheckpointType.STRATEGY_APPROVAL,
            title="Strategy Approval",
            content=f"Content Type: {content_type}\n\nProposed Strategy:\n{strategy}",
            description="Review and approve the content strategy before proceeding",
            priority=Priority.HIGH,
            timeout_seconds=600
        )
    
    def get_active_checkpoints(self) -> Dict[str, Any]:
        """Get all active checkpoints for this integration."""
        return self.active_checkpoints.copy()
    
    def get_checkpoint_summary(self) -> Dict:
        """Get summary of all checkpoints in this workflow."""
        summary = {
            "total_checkpoints": len(self.created_checkpoints),
            "active_checkpoints": len(self.active_checkpoints),
            "checkpoints": []
        }
        
        for checkpoint_id in self.created_checkpoints:
            checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
            if checkpoint:
                response = self.checkpoint_manager.get_response(checkpoint_id)
                summary["checkpoints"].append({
                    "id": checkpoint.checkpoint_id,
                    "type": checkpoint.checkpoint_type.value,
                    "title": checkpoint.title,
                    "status": checkpoint.status.value,
                    "decision": checkpoint.decision or (response.get("decision") if response else None),
                    "has_response": response is not None,
                    "created_at": checkpoint.created_at.isoformat(),
                    "updated_at": checkpoint.updated_at.isoformat()
                })
        
        return summary
    
    def clear_checkpoints(self):
        """Clear all checkpoints for this project."""
        self.checkpoint_manager.clear_project_checkpoints(self.project_id)
        self.active_checkpoints.clear()
        self.created_checkpoints.clear()
        logger.info(f"✅ Cleared all checkpoints for project {self.project_id}")

# Export the integration class
__all__ = ['WorkflowCheckpointIntegration']