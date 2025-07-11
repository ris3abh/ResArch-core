# ─── COMPLETE FIXED FILE: spinscribe/checkpoints/mock_reviewer.py ───

"""
Mock Reviewer for automated checkpoint responses during testing.
COMPLETE FIXED VERSION with configurable behavior and realistic delays.
"""

import logging
import time
import random
from typing import Dict, Any, Optional
from threading import Timer

try:
    from spinscribe.checkpoints.checkpoint_manager import CheckpointType, CheckpointManager
except ImportError:
    # Fallback definitions if not available
    from enum import Enum
    
    class CheckpointType(Enum):
        STYLE_GUIDE_APPROVAL = "style_guide_approval"
        CONTENT_OUTLINE_APPROVAL = "content_outline_approval"
        DRAFT_CONTENT_APPROVAL = "draft_content_approval"
        FINAL_CONTENT_APPROVAL = "final_content_approval"
        STRATEGY_APPROVAL = "strategy_approval"
        QUALITY_REVIEW = "quality_review"
    
    class CheckpointManager:
        def submit_response(self, *args, **kwargs):
            return True

logger = logging.getLogger(__name__)

class MockReviewer:
    """
    Mock reviewer that automatically responds to checkpoints for testing.
    """
    
    def __init__(self, 
                 approval_rate: float = 0.85,
                 response_delay_range: tuple = (5, 30),
                 reviewer_id: str = "mock-reviewer"):
        """
        Initialize mock reviewer.
        
        Args:
            approval_rate: Probability of approving checkpoints (0.0-1.0)
            response_delay_range: Min/max seconds to wait before responding
            reviewer_id: ID to use when submitting responses
        """
        self.approval_rate = approval_rate
        self.response_delay_range = response_delay_range
        self.reviewer_id = reviewer_id
        self.active_timers = {}
        self.response_count = 0
        self.checkpoint_manager = None
        
        logger.info(f"✅ Mock Reviewer initialized (approval rate: {approval_rate:.1%})")
    
    def set_checkpoint_manager(self, checkpoint_manager: CheckpointManager):
        """
        Set the checkpoint manager reference.
        
        Args:
            checkpoint_manager: CheckpointManager instance
        """
        self.checkpoint_manager = checkpoint_manager
        logger.info("✅ Checkpoint manager reference set")
    
    def handle_notification(self, notification: Dict[str, Any]):
        """
        Handle checkpoint notifications and schedule responses.
        
        Args:
            notification: Notification data from checkpoint manager
        """
        try:
            if notification.get("type") == "checkpoint_created":
                checkpoint_id = notification.get("checkpoint_id")
                checkpoint_type = notification.get("checkpoint_type")
                
                if checkpoint_id:
                    self._schedule_response(checkpoint_id, checkpoint_type)
                    
        except Exception as e:
            logger.error(f"❌ Error handling notification: {e}")
    
    def _schedule_response(self, checkpoint_id: str, checkpoint_type: str):
        """
        Schedule an automatic response to a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            checkpoint_type: Type of checkpoint
        """
        try:
            # Calculate response delay
            min_delay, max_delay = self.response_delay_range
            delay = random.uniform(min_delay, max_delay)
            
            # Determine approval decision
            will_approve = random.random() < self.approval_rate
            
            logger.info(f"⏰ Scheduling mock response for {checkpoint_id} in {delay:.1f}s (will {'approve' if will_approve else 'reject'})")
            
            # Schedule the response
            timer = Timer(delay, self._submit_response, args=(checkpoint_id, checkpoint_type, will_approve))
            timer.start()
            
            self.active_timers[checkpoint_id] = timer
            
        except Exception as e:
            logger.error(f"❌ Error scheduling response: {e}")
    
    def _submit_response(self, checkpoint_id: str, checkpoint_type: str, approve: bool):
        """
        Submit the mock response to a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            checkpoint_type: Type of checkpoint
            approve: Whether to approve or reject
        """
        try:
            decision = "approve" if approve else "reject"
            feedback = self._generate_feedback(checkpoint_type, approve)
            
            if self.checkpoint_manager:
                success = self.checkpoint_manager.submit_response(
                    checkpoint_id=checkpoint_id,
                    reviewer_id=self.reviewer_id,
                    decision=decision,
                    feedback=feedback,
                    decision_data={"mock_review": True, "response_time": time.time()}
                )
                
                if success:
                    self.response_count += 1
                    logger.info(f"✅ Mock response submitted: {checkpoint_id} ({decision})")
                else:
                    logger.warning(f"⚠️ Failed to submit mock response: {checkpoint_id}")
            else:
                logger.warning("⚠️ No checkpoint manager available for response")
            
            # Clean up timer reference
            self.active_timers.pop(checkpoint_id, None)
            
        except Exception as e:
            logger.error(f"❌ Error submitting mock response: {e}")
    
    def _generate_feedback(self, checkpoint_type: str, approve: bool) -> str:
        """
        Generate realistic feedback for different checkpoint types.
        
        Args:
            checkpoint_type: Type of checkpoint
            approve: Whether this is an approval or rejection
            
        Returns:
            Generated feedback text
        """
        try:
            if approve:
                feedback_options = {
                    "style_guide_approval": [
                        "Style guide looks comprehensive and aligns well with brand voice.",
                        "Good balance of professional and approachable tone. Approved.",
                        "Style guidelines are clear and actionable. Ready to proceed.",
                        "Brand voice analysis captures the essence well. Approved."
                    ],
                    "content_outline_approval": [
                        "Content outline has good structure and flow. Approved.",
                        "Outline covers all key points effectively. Ready for content creation.",
                        "Good logical progression and compelling sections. Approved.",
                        "Outline aligns with content objectives. Proceed with generation."
                    ],
                    "draft_content_approval": [
                        "Draft content is engaging and on-brand. Approved.",
                        "Good use of brand voice and clear messaging. Ready for final review.",
                        "Content flows well and addresses key points effectively. Approved.",
                        "Strong draft with good professional tone. Approved for finalization."
                    ],
                    "final_content_approval": [
                        "Final content meets all requirements. Approved for publication.",
                        "Excellent quality and brand alignment. Ready to publish.",
                        "Content is polished and professional. Final approval granted.",
                        "Outstanding work. Approved for immediate use."
                    ],
                    "strategy_approval": [
                        "Content strategy is well thought out. Approved.",
                        "Strategic approach aligns with objectives. Proceed with implementation.",
                        "Good strategic framework and clear execution plan. Approved.",
                        "Strategy covers all key aspects effectively. Approved."
                    ],
                    "quality_review": [
                        "Quality standards met across all criteria. Approved.",
                        "Content passes all quality checks. Ready for delivery.",
                        "High quality work with attention to detail. Approved.",
                        "Excellent quality and professionalism. Approved."
                    ]
                }
            else:
                feedback_options = {
                    "style_guide_approval": [
                        "Style guide needs more specific brand voice examples.",
                        "Tone guidelines could be clearer. Please revise and resubmit.",
                        "Brand voice section needs strengthening before approval.",
                        "Style guide lacks sufficient detail for consistent application."
                    ],
                    "content_outline_approval": [
                        "Outline structure needs improvement. Some sections unclear.",
                        "Missing key points in the content flow. Please revise.",
                        "Outline doesn't fully address the content objectives.",
                        "Need stronger call-to-action integration in the outline."
                    ],
                    "draft_content_approval": [
                        "Draft needs more professional tone in several sections.",
                        "Content doesn't fully align with brand voice. Revisions needed.",
                        "Some sections lack clarity and need strengthening.",
                        "Draft requires more compelling messaging throughout."
                    ],
                    "final_content_approval": [
                        "Final content still has areas that need refinement.",
                        "Quality standards not fully met. Additional polish needed.",
                        "Content needs final review and minor adjustments.",
                        "Almost ready but requires one more revision cycle."
                    ],
                    "strategy_approval": [
                        "Strategy needs more detailed implementation plan.",
                        "Strategic approach could be more comprehensive.",
                        "Strategy lacks sufficient market consideration.",
                        "Need clearer success metrics in the strategic plan."
                    ],
                    "quality_review": [
                        "Quality review identified areas for improvement.",
                        "Content doesn't meet minimum quality thresholds.",
                        "Additional quality improvements needed before approval.",
                        "Quality standards require attention in several areas."
                    ]
                }
            
            # Get feedback options for the checkpoint type
            options = feedback_options.get(checkpoint_type, 
                                         feedback_options.get("quality_review", 
                                                            ["Standard review feedback."]))
            
            # Select random feedback
            return random.choice(options)
            
        except Exception as e:
            logger.warning(f"⚠️ Error generating feedback: {e}")
            return f"{'Approved' if approve else 'Rejected'} by mock reviewer."
    
    def cancel_pending_responses(self, checkpoint_id: str = None):
        """
        Cancel pending mock responses.
        
        Args:
            checkpoint_id: Specific checkpoint to cancel, or None for all
        """
        try:
            if checkpoint_id:
                timer = self.active_timers.pop(checkpoint_id, None)
                if timer:
                    timer.cancel()
                    logger.info(f"✅ Cancelled mock response for {checkpoint_id}")
            else:
                # Cancel all pending responses
                for checkpoint_id, timer in self.active_timers.items():
                    timer.cancel()
                cancelled_count = len(self.active_timers)
                self.active_timers.clear()
                logger.info(f"✅ Cancelled {cancelled_count} pending mock responses")
                
        except Exception as e:
            logger.error(f"❌ Error cancelling responses: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get mock reviewer statistics.
        
        Returns:
            Statistics about mock reviewer activity
        """
        try:
            return {
                "reviewer_id": self.reviewer_id,
                "approval_rate": self.approval_rate,
                "response_delay_range": self.response_delay_range,
                "total_responses": self.response_count,
                "pending_responses": len(self.active_timers),
                "active": bool(self.checkpoint_manager)
            }
        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            return {"error": str(e)}
    
    def update_settings(self, approval_rate: float = None, 
                       response_delay_range: tuple = None):
        """
        Update mock reviewer settings.
        
        Args:
            approval_rate: New approval rate (0.0-1.0)
            response_delay_range: New delay range (min, max) in seconds
        """
        try:
            if approval_rate is not None:
                if 0.0 <= approval_rate <= 1.0:
                    self.approval_rate = approval_rate
                    logger.info(f"✅ Updated approval rate to {approval_rate:.1%}")
                else:
                    logger.warning("⚠️ Invalid approval rate. Must be between 0.0 and 1.0")
            
            if response_delay_range is not None:
                if len(response_delay_range) == 2 and response_delay_range[0] < response_delay_range[1]:
                    self.response_delay_range = response_delay_range
                    logger.info(f"✅ Updated response delay range to {response_delay_range}")
                else:
                    logger.warning("⚠️ Invalid delay range. Must be (min, max) with min < max")
                    
        except Exception as e:
            logger.error(f"❌ Error updating settings: {e}")
    
    def simulate_human_reviewer(self, 
                               approval_rate: float = 0.90,
                               response_delay_range: tuple = (10, 60)):
        """
        Configure mock reviewer to simulate human reviewer behavior.
        
        Args:
            approval_rate: Human-like approval rate
            response_delay_range: Human-like response time range
        """
        self.update_settings(approval_rate, response_delay_range)
        logger.info("✅ Configured for human-like reviewer behavior")
    
    def simulate_strict_reviewer(self,
                                approval_rate: float = 0.60,
                                response_delay_range: tuple = (30, 120)):
        """
        Configure mock reviewer to simulate strict reviewer behavior.
        
        Args:
            approval_rate: Strict approval rate
            response_delay_range: Longer response time range
        """
        self.update_settings(approval_rate, response_delay_range)
        logger.info("✅ Configured for strict reviewer behavior")
    
    def simulate_fast_reviewer(self,
                              approval_rate: float = 0.95,
                              response_delay_range: tuple = (2, 10)):
        """
        Configure mock reviewer to simulate fast reviewer behavior.
        
        Args:
            approval_rate: High approval rate
            response_delay_range: Fast response time range
        """
        self.update_settings(approval_rate, response_delay_range)
        logger.info("✅ Configured for fast reviewer behavior")


def test_mock_reviewer():
    """Test the mock reviewer functionality."""
    try:
        print("🧪 Testing Mock Reviewer")
        
        # Create mock reviewer
        reviewer = MockReviewer(
            approval_rate=0.8,
            response_delay_range=(1, 3),  # Fast for testing
            reviewer_id="test-mock-reviewer"
        )
        print("✅ Mock Reviewer created")
        
        # Test notification handling
        test_notification = {
            "type": "checkpoint_created",
            "checkpoint_id": "test-checkpoint-123",
            "checkpoint_type": "style_guide_approval",
            "project_id": "test-project",
            "title": "Test Checkpoint"
        }
        
        reviewer.handle_notification(test_notification)
        print("✅ Notification handled")
        
        # Test feedback generation
        feedback = reviewer._generate_feedback("style_guide_approval", True)
        print(f"✅ Feedback generated: {feedback[:50]}...")
        
        # Test stats
        stats = reviewer.get_stats()
        print(f"✅ Stats: {stats['approval_rate']:.1%} approval rate")
        
        # Test configuration updates
        reviewer.simulate_human_reviewer()
        print("✅ Human reviewer simulation configured")
        
        return {
            "success": True,
            "reviewer_created": True,
            "notification_handled": True,
            "stats": stats
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Run test
    test_result = test_mock_reviewer()
    print("\n" + "="*60)
    print("Mock Reviewer Test Complete")
    print("="*60)
    print(f"Success: {test_result.get('success', False)}")
    if test_result.get('success'):
        print("✅ Mock Reviewer operational")
        print(f"📊 Approval Rate: {test_result['stats']['approval_rate']:.1%}")
    else:
        print(f"❌ Error: {test_result.get('error', 'Unknown')}")