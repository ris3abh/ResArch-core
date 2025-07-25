# ─── NEW FILE: spinscribe/checkpoints/mock_reviewer.py ─────────
"""
Mock reviewer system for testing and development.
Simulates human reviewers for automated testing.
"""

import logging
import asyncio
import random
from typing import Dict, Any, List

from .checkpoint_manager import CheckpointManager, CheckpointType, CheckpointStatus

logger = logging.getLogger(__name__)

class MockReviewer:
    """
    Mock reviewer that automatically responds to checkpoints.
    Useful for testing and development without human interaction.
    """
    
    def __init__(self, checkpoint_manager: CheckpointManager, reviewer_id: str = "mock_reviewer"):
        self.checkpoint_manager = checkpoint_manager
        self.reviewer_id = reviewer_id
        self.auto_approve_rate = 0.7  # 70% auto-approve rate
        self.response_delay_seconds = (1, 5)  # Random delay range
        
        # Register as notification handler
        self.checkpoint_manager.add_notification_handler(self._handle_checkpoint_notification)
    
    def _handle_checkpoint_notification(self, event_type: str, checkpoint, *args) -> None:
        """Handle checkpoint notifications."""
        if event_type == 'checkpoint_created':
            # Automatically respond to new checkpoints
            asyncio.create_task(self._auto_respond(checkpoint))
    
    async def _auto_respond(self, checkpoint) -> None:
        """Automatically respond to a checkpoint after a delay."""
        # Random delay to simulate thinking time
        delay = random.uniform(*self.response_delay_seconds)
        await asyncio.sleep(delay)
        
        # Generate response based on checkpoint type
        response = self._generate_response(checkpoint)
        
        # Submit response
        success = self.checkpoint_manager.submit_response(
            checkpoint_id=checkpoint.checkpoint_id,
            reviewer_id=self.reviewer_id,
            decision=response['decision'],
            feedback=response['feedback'],
            suggestions=response.get('suggestions', []),
            changes_requested=response.get('changes_requested', []),
            time_spent_minutes=random.randint(5, 30)
        )
        
        if success:
            logger.info(f"🤖 Mock reviewer responded to {checkpoint.title}: {response['decision']}")
    
    def _generate_response(self, checkpoint) -> Dict[str, Any]:
        """Generate a mock response based on checkpoint type."""
        # Decide whether to approve
        should_approve = random.random() < self.auto_approve_rate
        
        if should_approve:
            return {
                'decision': 'approve',
                'feedback': self._get_approval_feedback(checkpoint.checkpoint_type),
                'suggestions': []
            }
        else:
            # Decide between revision or rejection
            needs_revision = random.random() < 0.8  # 80% revision, 20% rejection
            
            if needs_revision:
                return {
                    'decision': 'needs_revision',
                    'feedback': self._get_revision_feedback(checkpoint.checkpoint_type),
                    'changes_requested': self._get_revision_changes(checkpoint.checkpoint_type)
                }
            else:
                return {
                    'decision': 'reject',
                    'feedback': self._get_rejection_feedback(checkpoint.checkpoint_type)
                }
    
    def _get_approval_feedback(self, checkpoint_type: CheckpointType) -> str:
        """Get approval feedback based on checkpoint type."""
        feedback_templates = {
            CheckpointType.STYLE_GUIDE_APPROVAL: [
                "Style analysis looks accurate and comprehensive.",
                "Brand voice patterns are well identified.",
                "Good analysis of tone and linguistic markers."
            ],
            CheckpointType.OUTLINE_REVIEW: [
                "Content outline is well-structured and logical.",
                "Good flow and organization of topics.",
                "Outline aligns well with project requirements."
            ],
            CheckpointType.DRAFT_REVIEW: [
                "Content draft is well-written and engaging.",
                "Good adherence to brand voice and style.",
                "Content flows well and meets objectives."
            ]
        }
        
        templates = feedback_templates.get(checkpoint_type, ["Looks good!"])
        return random.choice(templates)
    
    def _get_revision_feedback(self, checkpoint_type: CheckpointType) -> str:
        """Get revision feedback based on checkpoint type."""
        feedback_templates = {
            CheckpointType.STYLE_GUIDE_APPROVAL: [
                "Style analysis needs more detail on vocabulary patterns.",
                "Please include more specific tone characteristics.",
                "Need better examples of linguistic markers."
            ],
            CheckpointType.OUTLINE_REVIEW: [
                "Outline structure could be improved.",
                "Some sections need more detail.",
                "Flow between sections needs work."
            ],
            CheckpointType.DRAFT_REVIEW: [
                "Content needs better brand voice alignment.",
                "Some sections need more engaging writing.",
                "Facts need verification and sources."
            ]
        }
        
        templates = feedback_templates.get(checkpoint_type, ["Needs improvement."])
        return random.choice(templates)
    
    def _get_revision_changes(self, checkpoint_type: CheckpointType) -> List[Dict[str, Any]]:
        """Get specific change requests for revisions."""
        change_templates = {
            CheckpointType.STYLE_GUIDE_APPROVAL: [
                {"section": "vocabulary", "change": "Add more specific word choice examples"},
                {"section": "tone", "change": "Include emotional tone indicators"}
            ],
            CheckpointType.OUTLINE_REVIEW: [
                {"section": "introduction", "change": "Expand the opening section"},
                {"section": "conclusion", "change": "Add stronger call-to-action"}
            ],
            CheckpointType.DRAFT_REVIEW: [
                {"section": "paragraph_2", "change": "Improve transitions between ideas"},
                {"section": "overall", "change": "Strengthen brand voice consistency"}
            ]
        }
        
        changes = change_templates.get(checkpoint_type, [])
        return random.sample(changes, min(2, len(changes))) if changes else []
    
    def _get_rejection_feedback(self, checkpoint_type: CheckpointType) -> str:
        """Get rejection feedback based on checkpoint type."""
        return "This doesn't meet our quality standards. Please start over with a different approach."