# ─── UPDATE FILE: spinscribe/workforce/enhanced_builder.py ──────
"""
Enhanced workforce builder that integrates RAG and checkpoints.
Replaces the existing builder.py with enhanced functionality.
"""

from camel.societies.workforce import Workforce

from spinscribe.agents.enhanced_style_analysis import EnhancedStyleAnalysisAgent
from spinscribe.agents.enhanced_content_planning import EnhancedContentPlanningAgent
from spinscribe.agents.enhanced_content_generation import EnhancedContentGenerationAgent
from spinscribe.agents.qa import create_qa_agent  # Keep existing QA agent
from spinscribe.agents.coordinator import create_coordinator_agent  # Keep existing coordinator
from spinscribe.agents.task_planner import create_task_planner_agent  # Keep existing task planner

from spinscribe.checkpoints.checkpoint_manager import CheckpointManager
from spinscribe.checkpoints.workflow_integration import WorkflowCheckpointIntegration
from spinscribe.checkpoints.mock_reviewer import MockReviewer

from config.settings import ENABLE_HUMAN_CHECKPOINTS, ENABLE_MOCK_REVIEWER

import logging

logger = logging.getLogger(__name__)

def build_enhanced_content_workflow(project_id: str = "default") -> Workforce:
    """
    Build enhanced workforce with RAG and checkpoint integration.
    
    Args:
        project_id: Project identifier for knowledge isolation
        
    Returns:
        Enhanced Workforce with integrated systems
    """
    logger.info(f"🏗️ Building enhanced workflow for project: {project_id}")
    
    # Initialize checkpoint system
    checkpoint_manager = None
    checkpoint_integration = None
    
    if ENABLE_HUMAN_CHECKPOINTS:
        checkpoint_manager = CheckpointManager()
        checkpoint_integration = WorkflowCheckpointIntegration(checkpoint_manager)
        
        # Enable mock reviewer if configured
        if ENABLE_MOCK_REVIEWER:
            mock_reviewer = MockReviewer(checkpoint_manager)
            logger.info("🤖 Mock reviewer enabled for automatic checkpoint responses")
        
        logger.info("✋ Human checkpoint system enabled")
    else:
        logger.info("⚠️ Human checkpoint system disabled")
    
    # Create enhanced agents with project context
    enhanced_style_agent = EnhancedStyleAnalysisAgent(project_id=project_id)
    enhanced_planning_agent = EnhancedContentPlanningAgent(project_id=project_id)
    enhanced_generation_agent = EnhancedContentGenerationAgent(project_id=project_id)
    
    # Set checkpoint integration for enhanced agents
    if checkpoint_integration:
        enhanced_style_agent.set_checkpoint_integration(checkpoint_integration, project_id)
        enhanced_planning_agent.set_checkpoint_integration(checkpoint_integration, project_id)
        enhanced_generation_agent.set_checkpoint_integration(checkpoint_integration, project_id)
    
    # Create standard agents (coordinator, task planner, QA)
    coordinator = create_coordinator_agent()
    task_planner = create_task_planner_agent()
    qa_agent = create_qa_agent()
    
    # Create enhanced workforce
    workforce = Workforce(
        description="Enhanced SpinScribe Multi-Agent Content Creation System - "
                   "Integrates RAG knowledge retrieval and human checkpoint workflow "
                   "for superior brand-consistent content creation.",
        coordinator_agent=coordinator,
        task_agent=task_planner
    )
    
    # Add enhanced agents to workforce
    workforce.add_single_agent_worker(
        description=(
            "Enhanced Style Analysis Agent: Analyzes client brand voice using RAG knowledge base, "
            "performs comprehensive stylometry analysis, generates language codes, and requests "
            "human approval for style guidelines. Accesses previous analyses and brand documents."
        ),
        worker=enhanced_style_agent
    ).add_single_agent_worker(
        description=(
            "Enhanced Content Planning Agent: Creates strategic content outlines using client "
            "knowledge base, references marketing strategies and brand guidelines, ensures "
            "audience alignment, and requests human review for strategic content decisions."
        ),
        worker=enhanced_planning_agent
    ).add_single_agent_worker(
        description=(
            "Enhanced Content Generation Agent: Generates brand-consistent content using approved "
            "outlines, applies style patterns from knowledge base, references factual information, "
            "and requests human quality review for content drafts."
        ),
        worker=enhanced_generation_agent
    ).add_single_agent_worker(
        description=(
            "Quality Assurance Agent: Reviews and refines content for quality, accuracy, and "
            "brand alignment. Validates compliance with style guidelines and provides "
            "final quality checks before delivery."
        ),
        worker=qa_agent
    )
    
    logger.info("✅ Enhanced workforce built successfully")
    
    # Store references for external access
    workforce._checkpoint_manager = checkpoint_manager
    workforce._checkpoint_integration = checkpoint_integration
    workforce._project_id = project_id
    
    return workforce