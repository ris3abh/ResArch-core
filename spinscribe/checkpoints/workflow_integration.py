# ─── NEW FILE: spinscribe/checkpoints/workflow_integration.py ──
"""
Integration layer for checkpoints with the agent workflow.
Provides utilities for pausing workflow and waiting for human input.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from .checkpoint_manager import CheckpointManager, CheckpointType, Priority, CheckpointStatus

logger = logging.getLogger(__name__)

class WorkflowCheckpointIntegration:
    """
    Integrates checkpoints with the agent workflow system.
    Provides methods to pause workflow and wait for human approval.
    """
    
    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self.workflow_pauses: Dict[str, asyncio.Event] = {}
    
    async def request_approval(
        self,
        project_id: str,
        checkpoint_type: CheckpointType,
        title: str,
        description: str,
        content: str,
        assigned_to: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        timeout_hours: Optional[int] = 24
    ) -> Dict[str, Any]:
        """
        Request human approval and pause workflow until response.
        
        Args:
            project_id: Project identifier
            checkpoint_type: Type of checkpoint
            title: Checkpoint title
            description: Description of what needs review
            content: Content to be reviewed
            assigned_to: User to assign checkpoint to
            priority: Priority level
            timeout_hours: Hours to wait before timeout
            
        Returns:
            Dict containing approval result and feedback
        """
        logger.info(f"🛑 Requesting human approval: {title}")
        
        # Create checkpoint
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            project_id=project_id,
            checkpoint_type=checkpoint_type,
            title=title,
            description=description,
            content_reference=content,
            assigned_to=assigned_to,
            priority=priority,
            due_hours=timeout_hours
        )
        
        # Create event to pause workflow
        approval_event = asyncio.Event()
        self.workflow_pauses[checkpoint_id] = approval_event
        
        # Register callback for when checkpoint is resolved
        result_container = {}
        
        def on_checkpoint_resolved(checkpoint, response):
            result_container['checkpoint'] = checkpoint
            result_container['response'] = response
            approval_event.set()
        
        self.checkpoint_manager.register_callback(checkpoint_id, on_checkpoint_resolved)
        
        # Wait for approval or timeout
        try:
            if timeout_hours:
                await asyncio.wait_for(approval_event.wait(), timeout=timeout_hours * 3600)
            else:
                await approval_event.wait()
            
            # Process result
            checkpoint = result_container.get('checkpoint')
            response = result_container.get('response')
            
            if checkpoint.status == CheckpointStatus.APPROVED:
                logger.info(f"✅ Checkpoint approved: {title}")
                return {
                    'approved': True,
                    'feedback': response.feedback if response else '',
                    'suggestions': response.suggestions if response else [],
                    'checkpoint_id': checkpoint_id
                }
            elif checkpoint.status == CheckpointStatus.NEEDS_REVISION:
                logger.info(f"🔄 Revision requested: {title}")
                return {
                    'approved': False,
                    'needs_revision': True,
                    'feedback': response.feedback if response else '',
                    'changes_requested': response.changes_requested if response else [],
                    'checkpoint_id': checkpoint_id
                }
            else:
                logger.info(f"❌ Checkpoint rejected: {title}")
                return {
                    'approved': False,
                    'rejected': True,
                    'feedback': response.feedback if response else '',
                    'checkpoint_id': checkpoint_id
                }
                
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Checkpoint timeout: {title}")
            return {
                'approved': False,
                'timeout': True,
                'checkpoint_id': checkpoint_id
            }
        finally:
            # Cleanup
            if checkpoint_id in self.workflow_pauses:
                del self.workflow_pauses[checkpoint_id]
    
    def resume_workflow(self, checkpoint_id: str) -> bool:
        """Resume workflow after checkpoint resolution."""
        if checkpoint_id in self.workflow_pauses:
            self.workflow_pauses[checkpoint_id].set()
            return True
        return False