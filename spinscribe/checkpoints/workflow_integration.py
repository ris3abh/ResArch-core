# File: spinscribe/checkpoints/workflow_integration.py
"""
Complete WorkflowCheckpointIntegration implementation for integrating checkpoints into workflows.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from spinscribe.checkpoints.checkpoint_manager import (
    CheckpointManager, 
    CheckpointType, 
    Priority
)

logger = logging.getLogger(__name__)

class WorkflowCheckpointIntegration:
    """Integrates checkpoint functionality into the workflow execution."""
    
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        project_id: str,
        enable_async: bool = True
    ):
        self.checkpoint_manager = checkpoint_manager
        self.project_id = project_id
        self.enable_async = enable_async
        self.active_checkpoints = {}
        logger.info(f"✅ WorkflowCheckpointIntegration initialized for project {project_id}")
    
    async def request_approval(
        self,
        checkpoint_type: CheckpointType,
        title: str,
        content: str,
        description: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        timeout_seconds: int = 300,
        timeout_hours: Optional[int] = None,  # Add this for compatibility
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Request approval for a checkpoint and wait for response.
        
        Returns:
            Dict containing decision and feedback
        """
        logger.info(f"📋 Requesting approval for: {title}")
        
        # Handle both timeout_hours and timeout_seconds
        if timeout_hours is not None:
            actual_timeout_seconds = timeout_hours * 3600
        else:
            actual_timeout_seconds = timeout_seconds
        
        # Create the checkpoint
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            project_id=self.project_id,
            checkpoint_type=checkpoint_type,
            title=title,
            description=description or f"Approval required for {title}",
            content=content,
            priority=priority,
            timeout_hours=actual_timeout_seconds // 3600 if actual_timeout_seconds >= 3600 else 1,
            metadata=metadata or {}
        )
        
        self.active_checkpoints[checkpoint_id] = {
            'type': checkpoint_type,
            'title': title,
            'created_at': datetime.now()
        }
        
        logger.info(f"⏳ Waiting for approval on checkpoint {checkpoint_id}...")
        
        # Wait for checkpoint resolution
        if self.enable_async:
            decision = await self._wait_for_approval_async(checkpoint_id, timeout_seconds)
        else:
            decision = self.checkpoint_manager.wait_for_checkpoint(checkpoint_id, timeout_seconds)
        
        # Get the full checkpoint for feedback
        checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
        
        result = {
            'checkpoint_id': checkpoint_id,
            'approved': decision and decision.lower() == 'approve',
            'decision': decision or 'timeout',
            'feedback': checkpoint.feedback if checkpoint else None,
            'reviewer_id': checkpoint.reviewer_id if checkpoint else None
        }
        
        # Clean up
        if checkpoint_id in self.active_checkpoints:
            del self.active_checkpoints[checkpoint_id]
        
        if result['approved']:
            logger.info(f"✅ Checkpoint {checkpoint_id} approved")
        elif decision == 'reject':
            logger.info(f"❌ Checkpoint {checkpoint_id} rejected")
        else:
            logger.warning(f"⏱️ Checkpoint {checkpoint_id} timed out")
        
        return result
    
    async def _wait_for_approval_async(
        self,
        checkpoint_id: str,
        timeout_seconds: int
    ) -> Optional[str]:
        """Async wait for checkpoint approval."""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
            
            if checkpoint and checkpoint.decision:
                return checkpoint.decision
            
            await asyncio.sleep(1)  # Check every second
        
        return None
    
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
        ))
    
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
        ))
    
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
        ))
    
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
        ))
    
    def get_active_checkpoints(self) -> Dict[str, Any]:
        """Get all active checkpoints for this integration."""
        return self.active_checkpoints.copy()
    
    def clear_checkpoints(self):
        """Clear all checkpoints for this project."""
        self.checkpoint_manager.clear_project_checkpoints(self.project_id)
        self.active_checkpoints.clear()
        logger.info(f"✅ Cleared all checkpoints for project {self.project_id}")

# Export the integration class
__all__ = ['WorkflowCheckpointIntegration']