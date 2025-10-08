# =============================================================================
# SPINSCRIBE WEBHOOK HANDLERS
# Business logic for processing HITL checkpoints
# =============================================================================
"""
Handlers for each type of HITL checkpoint in the workflow.

Each handler processes the webhook payload, extracts relevant information,
and creates an approval request for human review.
"""

from typing import Dict, Any
import uuid
import logging

from spinscribe.webhooks.models import (
    WebhookPayload,
    ApprovalRequest,
    ApprovalResponse,
    CheckpointType,
    ApprovalDecision
)

logger = logging.getLogger(__name__)


# =============================================================================
# CHECKPOINT HANDLERS
# =============================================================================

async def handle_brand_voice_checkpoint(payload: WebhookPayload) -> ApprovalRequest:
    """
    Handle Brand Voice Analysis checkpoint (Task 2).
    
    The brand_voice_specialist agent has completed analysis of the client's
    brand voice and generated AI Language Code parameters. This requires
    human validation before content creation can proceed.
    
    Args:
        payload: Webhook payload from agent
    
    Returns:
        ApprovalRequest for human review
    """
    logger.info(f"Processing Brand Voice checkpoint for {payload.workflow_id}")
    
    # Extract relevant metadata
    client_name = payload.metadata.get("client_name", "Unknown Client")
    topic = payload.metadata.get("topic", "Unknown Topic")
    ai_language_code = payload.metadata.get("ai_language_code", "Not specified")
    
    # Create approval request
    approval_request = ApprovalRequest(
        approval_id=f"appr_{uuid.uuid4().hex[:12]}",
        workflow_id=payload.workflow_id,
        checkpoint_type=CheckpointType.BRAND_VOICE,
        title=f"Brand Voice Analysis: {client_name} - {topic}",
        description=(
            f"The Brand Voice Specialist has analyzed {client_name}'s brand voice "
            f"and generated AI Language Code parameters for creating content on '{topic}'. "
            f"Please review the analysis and approve the parameters before content creation begins."
        ),
        content=payload.content,
        questions=[
            f"Do the AI Language Code parameters accurately represent {client_name}'s brand voice?",
            "Are there any adjustments needed for this specific content type?",
            "Are the content creation guidelines clear and actionable?",
            "Should we proceed with these voice parameters?"
        ],
        metadata={
            "client_name": client_name,
            "topic": topic,
            "content_type": payload.metadata.get("content_type", "Unknown"),
            "audience": payload.metadata.get("audience", "Unknown"),
            "ai_language_code": ai_language_code,
            "agent_name": payload.agent_name
        },
        priority="high"  # Brand voice is critical to get right
    )
    
    logger.info(f"Created approval request: {approval_request.approval_id}")
    return approval_request


async def handle_style_compliance_checkpoint(payload: WebhookPayload) -> ApprovalRequest:
    """
    Handle Style Compliance Review checkpoint (Task 6).
    
    The style_compliance_agent has verified adherence to brand voice and
    style guidelines. This checkpoint ensures any deviations are caught
    before final QA.
    
    Args:
        payload: Webhook payload from agent
    
    Returns:
        ApprovalRequest for human review
    """
    logger.info(f"Processing Style Compliance checkpoint for {payload.workflow_id}")
    
    # Extract relevant metadata
    client_name = payload.metadata.get("client_name", "Unknown Client")
    topic = payload.metadata.get("topic", "Unknown Topic")
    content_type = payload.metadata.get("content_type", "Unknown")
    
    # Create approval request
    approval_request = ApprovalRequest(
        approval_id=f"appr_{uuid.uuid4().hex[:12]}",
        workflow_id=payload.workflow_id,
        checkpoint_type=CheckpointType.STYLE_COMPLIANCE,
        title=f"Style Compliance Review: {client_name} - {topic}",
        description=(
            f"The Style Compliance Agent has completed a comprehensive review of the "
            f"{content_type} content for {client_name} on '{topic}'. The review checks "
            f"brand voice consistency, style guideline adherence, and SEO optimization balance. "
            f"Please review the compliance report and approve before proceeding to final QA."
        ),
        content=payload.content,
        questions=[
            f"Does the content authentically represent {client_name}'s brand voice?",
            "Are the identified issues acceptable or do they require correction?",
            "Is the balance between SEO optimization and brand voice appropriate?",
            "Are there any additional concerns not captured in the review?"
        ],
        metadata={
            "client_name": client_name,
            "topic": topic,
            "content_type": content_type,
            "audience": payload.metadata.get("audience", "Unknown"),
            "agent_name": payload.agent_name,
            "compliance_score": payload.metadata.get("compliance_score", "N/A")
        },
        priority="normal"
    )
    
    logger.info(f"Created approval request: {approval_request.approval_id}")
    return approval_request


async def handle_final_qa_checkpoint(payload: WebhookPayload) -> ApprovalRequest:
    """
    Handle Final Quality Assurance checkpoint (Task 7).
    
    The quality_assurance_editor has completed comprehensive final review.
    This is the last checkpoint before content delivery to the client.
    
    Args:
        payload: Webhook payload from agent
    
    Returns:
        ApprovalRequest for human review
    """
    logger.info(f"Processing Final QA checkpoint for {payload.workflow_id}")
    
    # Extract relevant metadata
    client_name = payload.metadata.get("client_name", "Unknown Client")
    topic = payload.metadata.get("topic", "Unknown Topic")
    content_type = payload.metadata.get("content_type", "Unknown")
    quality_score = payload.metadata.get("quality_score", "N/A")
    
    # Create approval request
    approval_request = ApprovalRequest(
        approval_id=f"appr_{uuid.uuid4().hex[:12]}",
        workflow_id=payload.workflow_id,
        checkpoint_type=CheckpointType.FINAL_QA,
        title=f"Final QA Approval: {client_name} - {topic}",
        description=(
            f"The Quality Assurance Editor has completed the final comprehensive review "
            f"of the {content_type} content for {client_name} on '{topic}'. "
            f"This is the FINAL checkpoint before content delivery. "
            f"Please review the QA report and approve for publication or client delivery."
        ),
        content=payload.content,
        questions=[
            "Is this content ready to represent {client_name} publicly?",
            "Does it meet all quality standards for publication?",
            "Are any final adjustments needed?",
            "Is this content likely to achieve business objectives?"
        ],
        metadata={
            "client_name": client_name,
            "topic": topic,
            "content_type": content_type,
            "audience": payload.metadata.get("audience", "Unknown"),
            "agent_name": payload.agent_name,
            "quality_score": quality_score,
            "word_count": payload.metadata.get("word_count", "N/A")
        },
        priority="urgent"  # Final approval is time-sensitive
    )
    
    logger.info(f"Created approval request: {approval_request.approval_id}")
    return approval_request


# =============================================================================
# APPROVAL DECISION PROCESSOR
# =============================================================================

async def process_approval_decision(
    workflow_id: str,
    workflow_state: Dict[str, Any],
    response: ApprovalResponse
) -> Dict[str, Any]:
    """
    Process human approval decision and determine next action.
    
    This function handles the logic of what happens after a human
    makes an approval decision.
    
    Args:
        workflow_id: Workflow identifier
        workflow_state: Current workflow state
        response: Human approval response
    
    Returns:
        Dictionary with next action information
    """
    checkpoint_type = workflow_state["checkpoint_type"]
    decision = response.decision
    
    logger.info(f"Processing {decision} decision for {checkpoint_type} checkpoint")
    
    # Log reviewer information for audit trail
    if response.reviewer_name:
        logger.info(f"Reviewed by: {response.reviewer_name}")
    if response.comments:
        logger.info(f"Comments: {response.comments[:100]}...")
    
    # Determine next action based on checkpoint and decision
    if decision == ApprovalDecision.APPROVE:
        return await _handle_approval(checkpoint_type, workflow_state, response)
    elif decision == ApprovalDecision.REJECT:
        return await _handle_rejection(checkpoint_type, workflow_state, response)
    else:  # REVISE
        return await _handle_revision(checkpoint_type, workflow_state, response)


async def _handle_approval(
    checkpoint_type: CheckpointType,
    workflow_state: Dict[str, Any],
    response: ApprovalResponse
) -> Dict[str, Any]:
    """Handle APPROVE decision."""
    
    next_actions = {
        CheckpointType.BRAND_VOICE: {
            "next_action": "proceed_to_content_strategy",
            "message": "Brand voice approved. Content Strategy task will begin.",
            "next_task": "content_strategy_task"
        },
        CheckpointType.STYLE_COMPLIANCE: {
            "next_action": "proceed_to_final_qa",
            "message": "Style compliance approved. Final QA task will begin.",
            "next_task": "final_quality_assurance_task"
        },
        CheckpointType.FINAL_QA: {
            "next_action": "deliver_content",
            "message": "Final QA approved. Content is ready for delivery.",
            "next_task": "content_delivery"
        }
    }
    
    result = next_actions.get(checkpoint_type, {
        "next_action": "unknown",
        "message": "Approval recorded but next action unclear."
    })
    
    logger.info(f"✅ Approved: {result['message']}")
    return result


async def _handle_rejection(
    checkpoint_type: CheckpointType,
    workflow_state: Dict[str, Any],
    response: ApprovalResponse
) -> Dict[str, Any]:
    """Handle REJECT decision."""
    
    restart_tasks = {
        CheckpointType.BRAND_VOICE: {
            "next_action": "restart_from_brand_voice",
            "message": "Rejected. Will restart from Brand Voice Analysis task.",
            "restart_task": "brand_voice_analysis_task",
            "issues": response.specific_changes or []
        },
        CheckpointType.STYLE_COMPLIANCE: {
            "next_action": "restart_from_content_generation",
            "message": "Rejected. Will restart from Content Generation task.",
            "restart_task": "content_generation_task",
            "issues": response.specific_changes or []
        },
        CheckpointType.FINAL_QA: {
            "next_action": "restart_from_seo_optimization",
            "message": "Rejected. Will restart from SEO Optimization task.",
            "restart_task": "seo_optimization_task",
            "issues": response.specific_changes or []
        }
    }
    
    result = restart_tasks.get(checkpoint_type, {
        "next_action": "unknown",
        "message": "Rejection recorded but restart point unclear."
    })
    
    logger.warning(f"❌ Rejected: {result['message']}")
    if response.priority_issues:
        logger.warning(f"Priority issues: {', '.join(response.priority_issues)}")
    
    return result


async def _handle_revision(
    checkpoint_type: CheckpointType,
    workflow_state: Dict[str, Any],
    response: ApprovalResponse
) -> Dict[str, Any]:
    """Handle REVISE decision."""
    
    revision_actions = {
        CheckpointType.BRAND_VOICE: {
            "next_action": "revise_brand_voice",
            "message": "Revision requested. Brand Voice Specialist will make adjustments.",
            "revision_task": "brand_voice_analysis_task",
            "changes_requested": response.specific_changes or []
        },
        CheckpointType.STYLE_COMPLIANCE: {
            "next_action": "revise_style",
            "message": "Revision requested. Style Compliance Agent will address issues.",
            "revision_task": "style_compliance_review_task",
            "changes_requested": response.specific_changes or []
        },
        CheckpointType.FINAL_QA: {
            "next_action": "revise_qa",
            "message": "Revision requested. QA Editor will address issues.",
            "revision_task": "final_quality_assurance_task",
            "changes_requested": response.specific_changes or []
        }
    }
    
    result = revision_actions.get(checkpoint_type, {
        "next_action": "unknown",
        "message": "Revision requested but unclear how to proceed."
    })
    
    logger.info(f"🔄 Revision requested: {result['message']}")
    if response.specific_changes:
        logger.info(f"Specific changes: {len(response.specific_changes)} items")
    
    return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_key_info_from_content(content: str, checkpoint_type: CheckpointType) -> Dict[str, Any]:
    """
    Extract key information from content for quick display.
    
    This helps create summaries for dashboards and notifications.
    """
    # Basic extraction (can be enhanced with more sophisticated parsing)
    lines = content.split('\n')
    first_heading = next((line for line in lines if line.startswith('#')), "No heading found")
    
    info = {
        "first_heading": first_heading.strip('#').strip(),
        "line_count": len(lines),
        "char_count": len(content)
    }
    
    # Checkpoint-specific extraction
    if checkpoint_type == CheckpointType.BRAND_VOICE:
        # Try to find AI Language Code
        for line in lines:
            if "AI Language Code" in line or "/TN/" in line:
                info["ai_code_found"] = True
                break
    
    return info