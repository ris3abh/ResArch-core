# ─── NEW FILE: spinscribe/checkpoints/enhanced_agents.py ───────
"""
Enhanced agent classes that integrate with the checkpoint system.
Extends existing agents to pause workflow for human review.
"""

import logging
from typing import Dict, Any, Optional
import asyncio

from camel.agents import ChatAgent
from camel.messages import BaseMessage

from .checkpoint_manager import CheckpointType, Priority
from .workflow_integration import WorkflowCheckpointIntegration

logger = logging.getLogger(__name__)

class CheckpointEnabledAgent:
    """
    Mixin class that adds checkpoint functionality to agents.
    Allows agents to request human approval during their workflow.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkpoint_integration: Optional[WorkflowCheckpointIntegration] = None
        self.project_id: Optional[str] = None
    
    def set_checkpoint_integration(
        self, 
        integration: WorkflowCheckpointIntegration,
        project_id: str
    ) -> None:
        """Set checkpoint integration for this agent."""
        self.checkpoint_integration = integration
        self.project_id = project_id
    
    async def request_checkpoint(
        self,
        checkpoint_type: CheckpointType,
        title: str,
        description: str,
        content: str,
        assigned_to: Optional[str] = None,
        priority: Priority = Priority.MEDIUM
    ) -> Dict[str, Any]:
        """Request a human checkpoint."""
        if not self.checkpoint_integration:
            logger.warning("No checkpoint integration available - skipping checkpoint")
            return {'approved': True, 'skipped': True}
        
        return await self.checkpoint_integration.request_approval(
            project_id=self.project_id,
            checkpoint_type=checkpoint_type,
            title=title,
            description=description,
            content=content,
            assigned_to=assigned_to,
            priority=priority
        )

class EnhancedStyleAnalysisAgent(CheckpointEnabledAgent, ChatAgent):
    """Style Analysis Agent with checkpoint integration."""
    
    async def analyze_with_approval(self, content: str) -> Dict[str, Any]:
        """Analyze style and request human approval."""
        # Perform style analysis
        analysis_message = BaseMessage.make_assistant_message(
            role_name="Style Analyst",
            content=f"Analyze the brand voice and style patterns in this content: {content}"
        )
        
        response = self.step(analysis_message)
        analysis_result = response.msg.content
        
        # Request human approval for style analysis
        approval_result = await self.request_checkpoint(
            checkpoint_type=CheckpointType.STYLE_GUIDE_APPROVAL,
            title="Style Analysis Approval",
            description="Please review the brand voice analysis and confirm accuracy",
            content=f"Style Analysis Result:\n\n{analysis_result}\n\nOriginal Content:\n{content}",
            priority=Priority.HIGH
        )
        
        return {
            'analysis': analysis_result,
            'approval': approval_result
        }

class EnhancedContentPlanningAgent(CheckpointEnabledAgent, ChatAgent):
    """Content Planning Agent with checkpoint integration."""
    
    async def create_outline_with_approval(self, brief: str) -> Dict[str, Any]:
        """Create outline and request human approval."""
        # Create content outline
        outline_message = BaseMessage.make_assistant_message(
            role_name="Content Planner",
            content=f"Create a detailed content outline based on this brief: {brief}"
        )
        
        response = self.step(outline_message)
        outline_result = response.msg.content
        
        # Request human approval for outline
        approval_result = await self.request_checkpoint(
            checkpoint_type=CheckpointType.OUTLINE_REVIEW,
            title="Content Outline Review",
            description="Please review the content outline and provide feedback",
            content=f"Content Brief:\n{brief}\n\nProposed Outline:\n{outline_result}",
            priority=Priority.MEDIUM
        )
        
        return {
            'outline': outline_result,
            'approval': approval_result
        }

class EnhancedContentGenerationAgent(CheckpointEnabledAgent, ChatAgent):
    """Content Generation Agent with checkpoint integration."""
    
    async def generate_with_approval(self, outline: str, style_guide: str) -> Dict[str, Any]:
        """Generate content and request human approval."""
        # Generate content
        generation_message = BaseMessage.make_assistant_message(
            role_name="Content Generator",
            content=f"Generate content based on this outline: {outline}\n\nStyle Guide: {style_guide}"
        )
        
        response = self.step(generation_message)
        content_result = response.msg.content
        
        # Request human approval for draft
        approval_result = await self.request_checkpoint(
            checkpoint_type=CheckpointType.DRAFT_REVIEW,
            title="Content Draft Review",
            description="Please review the content draft and provide feedback",
            content=f"Generated Content:\n\n{content_result}\n\nOutline Used:\n{outline}",
            priority=Priority.HIGH
        )
        
        return {
            'content': content_result,
            'approval': approval_result
        }