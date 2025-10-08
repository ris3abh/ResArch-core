# =============================================================================
# SPINSCRIBE WEBHOOK HANDLERS
# Business logic for processing HITL checkpoints with crew resume integration
# =============================================================================
"""
Handlers for each type of HITL checkpoint in the workflow.

Each handler processes the webhook payload, extracts relevant information,
creates an approval request for human review, and manages crew resumption
after human decision.

Crew Resume Flow:
1. Webhook receives checkpoint notification from crew
2. Handler creates approval request and stores in workflow storage
3. Human reviews in dashboard (auto-refreshing or websocket updates)
4. Crew execution is paused waiting for decision
5. Human reviews in dashboard and approves/rejects
6. Handler processes decision and signals crew to resume
7. Crew continues with feedback incorporated
"""

from typing import Dict, Any, Optional
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
        payload: Webhook payload from agent containing analysis results
    
    Returns:
        ApprovalRequest for human review
    """
    logger.info(f"🎨 Processing Brand Voice checkpoint for workflow: {payload.workflow_id}")
    
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
            "agent_name": payload.agent_name,
            "execution_id": payload.workflow_id
        },
        priority="high"  # Brand voice is critical to get right
    )
    
    logger.info(f"✅ Created approval request: {approval_request.approval_id}")
    logger.info(f"📊 Dashboard alert: Brand Voice Review needed for {client_name}")
    
    return approval_request


async def handle_style_compliance_checkpoint(payload: WebhookPayload) -> ApprovalRequest:
    """
    Handle Style Compliance Review checkpoint (Task 6).
    
    The style_compliance_agent has verified adherence to brand voice and
    style guidelines. This checkpoint ensures any deviations are caught
    before final QA.
    
    Args:
        payload: Webhook payload from agent containing compliance report
    
    Returns:
        ApprovalRequest for human review
    """
    logger.info(f"📝 Processing Style Compliance checkpoint for workflow: {payload.workflow_id}")
    
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
            "compliance_score": payload.metadata.get("compliance_score", "N/A"),
            "execution_id": payload.workflow_id
        },
        priority="normal"
    )
    
    logger.info(f"✅ Created approval request: {approval_request.approval_id}")
    logger.info(f"📊 Dashboard alert: Style Compliance Review needed for {client_name}")
    
    return approval_request


async def handle_final_qa_checkpoint(payload: WebhookPayload) -> ApprovalRequest:
    """
    Handle Final Quality Assurance checkpoint (Task 7).
    
    The quality_assurance_editor has completed comprehensive final review.
    This is the last checkpoint before content delivery to the client.
    
    Args:
        payload: Webhook payload from agent containing QA report
    
    Returns:
        ApprovalRequest for human review
    """
    logger.info(f"✨ Processing Final QA checkpoint for workflow: {payload.workflow_id}")
    
    # Extract relevant metadata
    client_name = payload.metadata.get("client_name", "Unknown Client")
    topic = payload.metadata.get("topic", "Unknown Topic")
    content_type = payload.metadata.get("content_type", "Unknown")
    
    # Create approval request
    approval_request = ApprovalRequest(
        approval_id=f"appr_{uuid.uuid4().hex[:12]}",
        workflow_id=payload.workflow_id,
        checkpoint_type=CheckpointType.FINAL_QA,
        title=f"Final QA Review: {client_name} - {topic}",
        description=(
            f"The Quality Assurance Editor has completed final review of the "
            f"{content_type} content for {client_name} on '{topic}'. This is the "
            f"final checkpoint before content delivery. Please review and approve "
            f"to proceed with delivery to the client."
        ),
        content=payload.content,
        questions=[
            "Is the content publication-ready?",
            "Are there any final corrections needed?",
            "Does the content meet all client requirements?",
            "Should we proceed with content delivery?"
        ],
        metadata={
            "client_name": client_name,
            "topic": topic,
            "content_type": content_type,
            "audience": payload.metadata.get("audience", "Unknown"),
            "agent_name": payload.agent_name,
            "quality_score": payload.metadata.get("quality_score", "N/A"),
            "execution_id": payload.workflow_id
        },
        priority="high"  # Final approval is critical
    )
    
    logger.info(f"✅ Created approval request: {approval_request.approval_id}")
    logger.info(f"📊 Dashboard alert: Final QA Approval needed for {client_name}")
    
    return approval_request


# =============================================================================
# APPROVAL DECISION PROCESSING
# =============================================================================

async def process_approval_decision(
    workflow_id: str,
    workflow_state: Dict[str, Any],
    response: ApprovalResponse
) -> Dict[str, Any]:
    """
    Process human approval decision and determine next action.
    
    This function handles the logic of what happens after a human
    makes an approval decision. It also attempts to communicate the
    decision back to the waiting crew execution.
    
    Args:
        workflow_id: Workflow identifier
        workflow_state: Current workflow state from storage
        response: Human approval response with decision and feedback
    
    Returns:
        Dictionary with next action information and crew resume status
    """
    checkpoint_type = workflow_state.get("checkpoint_type")
    decision = response.decision
    execution_id = workflow_state.get("execution_id", workflow_id)
    
    logger.info(f"⚙️  Processing {decision} decision for {checkpoint_type} checkpoint")
    logger.info(f"   Execution ID: {execution_id}")
    
    # Log reviewer information for audit trail
    if response.reviewer_name:
        logger.info(f"   Reviewed by: {response.reviewer_name}")
    if response.comments:
        logger.info(f"   Comments: {response.comments[:100]}...")
    
    # Determine next action based on checkpoint and decision
    if decision == ApprovalDecision.APPROVE:
        result = await _handle_approval(checkpoint_type, workflow_state, response)
    elif decision == ApprovalDecision.REJECT:
        result = await _handle_rejection(checkpoint_type, workflow_state, response)
    else:  # REVISE
        result = await _handle_revision(checkpoint_type, workflow_state, response)
    
    # Attempt to resume crew execution with decision
    resume_status = await _attempt_crew_resume(
        execution_id,
        decision,
        response.feedback,
        result
    )
    
    # Add resume status to result
    result['crew_resume_status'] = resume_status
    
    return result


async def _attempt_crew_resume(
    execution_id: str,
    decision: ApprovalDecision,
    feedback: str,
    action_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Attempt to resume crew execution after approval decision.
    
    This communicates the decision back to the paused crew so it can
    continue execution with the human feedback incorporated.
    
    Args:
        execution_id: Execution ID of the crew
        decision: Approval decision (approve/reject/revise)
        feedback: Human feedback text
        action_result: Result from decision handler
        
    Returns:
        Status of crew resume attempt
    """
    try:
        # Import crew module to access active executions
        from spinscribe.crew import get_active_crew_execution, resume_crew_execution
        
        # Check if crew execution is still active
        execution = get_active_crew_execution(execution_id)
        
        if not execution:
            logger.warning(f"⚠️  No active crew execution found for ID: {execution_id}")
            return {
                "success": False,
                "reason": "crew_execution_not_found",
                "message": "Crew execution not found or already completed"
            }
        
        # Prepare feedback for crew
        is_approve = (decision == ApprovalDecision.APPROVE)
        
        # Attempt to resume crew
        logger.info(f"📤 Attempting to resume crew execution: {execution_id}")
        logger.info(f"   Decision: {decision}")
        logger.info(f"   Feedback: {feedback[:100]}...")
        
        resume_result = resume_crew_execution(
            execution_id=execution_id,
            human_feedback=feedback,
            is_approve=is_approve
        )
        
        if resume_result:
            logger.info(f"✅ Crew execution resumed successfully")
            return {
                "success": True,
                "message": "Crew resumed and continuing execution",
                "execution_id": execution_id
            }
        else:
            logger.warning(f"⚠️  Crew resume returned None - may not support resume")
            return {
                "success": False,
                "reason": "crew_resume_not_supported",
                "message": "Crew does not support programmatic resume"
            }
        
    except ImportError as e:
        logger.error(f"❌ Could not import crew module: {e}")
        return {
            "success": False,
            "reason": "import_error",
            "message": f"Failed to import crew module: {str(e)}"
        }
    
    except Exception as e:
        logger.error(f"❌ Error resuming crew execution: {e}")
        return {
            "success": False,
            "reason": "resume_error",
            "message": f"Error during crew resume: {str(e)}"
        }


# =============================================================================
# DECISION HANDLERS
# =============================================================================

async def _handle_approval(
    checkpoint_type: CheckpointType,
    workflow_state: Dict[str, Any],
    response: ApprovalResponse
) -> Dict[str, Any]:
    """
    Handle APPROVE decision.
    
    Determines which task the crew should proceed to next based on
    the checkpoint that was approved.
    
    Args:
        checkpoint_type: Type of checkpoint that was approved
        workflow_state: Current workflow state
        response: Human approval response
        
    Returns:
        Dict with next action information
    """
    next_actions = {
        CheckpointType.BRAND_VOICE: {
            "next_action": "proceed_to_content_strategy",
            "message": "Brand voice approved. Content Strategy task will begin.",
            "next_task": "content_strategy_task",
            "status": "approved"
        },
        CheckpointType.STYLE_COMPLIANCE: {
            "next_action": "proceed_to_final_qa",
            "message": "Style compliance approved. Final QA task will begin.",
            "next_task": "final_quality_assurance_task",
            "status": "approved"
        },
        CheckpointType.FINAL_QA: {
            "next_action": "deliver_content",
            "message": "Final QA approved. Content is ready for delivery.",
            "next_task": "content_delivery",
            "status": "completed"
        }
    }
    
    result = next_actions.get(checkpoint_type, {
        "next_action": "unknown",
        "message": "Approval recorded but next action unclear.",
        "status": "approved"
    })
    
    logger.info(f"✅ Approved: {result['message']}")
    
    # Add feedback to result
    result['feedback'] = response.feedback
    result['decision'] = "approve"
    
    return result


async def _handle_rejection(
    checkpoint_type: CheckpointType,
    workflow_state: Dict[str, Any],
    response: ApprovalResponse
) -> Dict[str, Any]:
    """
    Handle REJECT decision.
    
    Determines which task the crew should restart from based on
    the checkpoint that was rejected.
    
    Args:
        checkpoint_type: Type of checkpoint that was rejected
        workflow_state: Current workflow state
        response: Human approval response
        
    Returns:
        Dict with restart action information
    """
    restart_tasks = {
        CheckpointType.BRAND_VOICE: {
            "next_action": "restart_from_brand_voice",
            "message": "Rejected. Will restart from Brand Voice Analysis task.",
            "restart_task": "brand_voice_analysis_task",
            "issues": response.specific_changes or [],
            "status": "rejected"
        },
        CheckpointType.STYLE_COMPLIANCE: {
            "next_action": "restart_from_content_generation",
            "message": "Rejected. Will restart from Content Generation task.",
            "restart_task": "content_generation_task",
            "issues": response.specific_changes or [],
            "status": "rejected"
        },
        CheckpointType.FINAL_QA: {
            "next_action": "restart_from_seo_optimization",
            "message": "Rejected. Will restart from SEO Optimization task.",
            "restart_task": "seo_optimization_task",
            "issues": response.specific_changes or [],
            "status": "rejected"
        }
    }
    
    result = restart_tasks.get(checkpoint_type, {
        "next_action": "unknown",
        "message": "Rejection recorded but restart point unclear.",
        "status": "rejected"
    })
    
    logger.info(f"❌ Rejected: {result['message']}")
    if response.specific_changes:
        logger.info(f"   Issues to address: {len(response.specific_changes)} items")
    
    # Add feedback to result
    result['feedback'] = response.feedback
    result['decision'] = "reject"
    result['required_changes'] = response.specific_changes
    
    return result


async def _handle_revision(
    checkpoint_type: CheckpointType,
    workflow_state: Dict[str, Any],
    response: ApprovalResponse
) -> Dict[str, Any]:
    """
    Handle REVISE decision.
    
    Similar to rejection but indicates minor changes needed rather
    than complete restart.
    
    Args:
        checkpoint_type: Type of checkpoint requesting revision
        workflow_state: Current workflow state
        response: Human approval response
        
    Returns:
        Dict with revision action information
    """
    revision_actions = {
        CheckpointType.BRAND_VOICE: {
            "next_action": "revise_brand_voice",
            "message": "Revision requested. Brand Voice Specialist will refine analysis.",
            "revision_task": "brand_voice_analysis_task",
            "changes_requested": response.specific_changes or [],
            "status": "revision_requested"
        },
        CheckpointType.STYLE_COMPLIANCE: {
            "next_action": "revise_style_compliance",
            "message": "Revision requested. Style Compliance Agent will address issues.",
            "revision_task": "style_compliance_review_task",
            "changes_requested": response.specific_changes or [],
            "status": "revision_requested"
        },
        CheckpointType.FINAL_QA: {
            "next_action": "revise_qa",
            "message": "Revision requested. QA Editor will address issues.",
            "revision_task": "final_quality_assurance_task",
            "changes_requested": response.specific_changes or [],
            "status": "revision_requested"
        }
    }
    
    result = revision_actions.get(checkpoint_type, {
        "next_action": "unknown",
        "message": "Revision requested but unclear how to proceed.",
        "status": "revision_requested"
    })
    
    logger.info(f"🔄 Revision requested: {result['message']}")
    if response.specific_changes:
        logger.info(f"   Specific changes: {len(response.specific_changes)} items")
    
    # Add feedback to result
    result['feedback'] = response.feedback
    result['decision'] = "revise"
    result['requested_changes'] = response.specific_changes
    
    return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_key_info_from_content(content: str, checkpoint_type: CheckpointType) -> Dict[str, Any]:
    """
    Extract key information from content for quick display.
    
    This helps create summaries for dashboards and notifications.
    
    Args:
        content: Content text to analyze
        checkpoint_type: Type of checkpoint
        
    Returns:
        Dict with extracted key information
    """
    # Basic extraction (can be enhanced with more sophisticated parsing)
    lines = content.split('\n')
    first_heading = next((line for line in lines if line.startswith('#')), "No heading found")
    
    info = {
        "first_heading": first_heading.strip('#').strip(),
        "line_count": len(lines),
        "char_count": len(content),
        "word_count": len(content.split())
    }
    
    # Checkpoint-specific extraction
    if checkpoint_type == CheckpointType.BRAND_VOICE:
        # Try to find AI Language Code
        for line in lines:
            if "AI Language Code" in line or "/TN/" in line:
                info["ai_code_found"] = True
                # Extract the code
                parts = line.split("/TN/")
                if len(parts) > 1:
                    info["ai_language_code"] = "/TN/" + parts[1].split()[0]
                break
    
    elif checkpoint_type == CheckpointType.STYLE_COMPLIANCE:
        # Try to find compliance score
        for line in lines:
            if "compliance score" in line.lower() or "score:" in line.lower():
                info["score_found"] = True
                break
    
    return info


def get_crew_communication_status() -> Dict[str, Any]:
    """
    Get status of crew communication system.
    
    This helps diagnose issues with crew resume functionality.
    
    Returns:
        Dict with communication system status
    """
    try:
        from spinscribe.crew import list_active_executions
        
        active_executions = list_active_executions()
        
        return {
            "status": "operational",
            "active_executions": len(active_executions),
            "execution_ids": active_executions,
            "can_resume": True
        }
        
    except ImportError:
        return {
            "status": "error",
            "error": "Cannot import crew module",
            "can_resume": False
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "can_resume": False
        }