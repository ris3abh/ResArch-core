# ─── FILE: spinscribe/workforce/enhanced_builder.py ────────────
"""
Enhanced workforce builder with logging integration.
UPDATE: Modify existing builder.py or create new enhanced_builder.py
"""

import logging
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
from spinscribe.utils.enhanced_logging import workflow_tracker

from config.settings import ENABLE_HUMAN_CHECKPOINTS, ENABLE_MOCK_REVIEWER

def build_enhanced_content_workflow(project_id: str = "default") -> Workforce:
    """
    Build enhanced workforce with RAG and checkpoint integration plus logging.
    
    Args:
        project_id: Project identifier for knowledge isolation
        
    Returns:
        Enhanced Workforce with integrated systems and logging
    """
    
    logger = logging.getLogger('spinscribe.workforce_builder')
    logger.info(f"🏗️ Building enhanced workflow for project: {project_id}")
    
    # Initialize checkpoint system
    checkpoint_manager = None
    checkpoint_integration = None
    
    if ENABLE_HUMAN_CHECKPOINTS:
        logger.info("✋ Initializing human checkpoint system")
        checkpoint_manager = CheckpointManager()
        checkpoint_integration = WorkflowCheckpointIntegration(checkpoint_manager)
        
        # Enable mock reviewer if configured
        if ENABLE_MOCK_REVIEWER:
            mock_reviewer = MockReviewer(checkpoint_manager)
            # Configure for faster testing
            mock_reviewer.auto_approve_rate = 0.8  # 80% approval rate
            mock_reviewer.response_delay_seconds = (0.5, 2.0)  # 0.5-2 second delay
            logger.info("🤖 Mock reviewer enabled for automatic checkpoint responses")
        else:
            logger.info("👥 Real human reviewers expected for checkpoints")
        
        logger.info("✅ Human checkpoint system initialized")
    else:
        logger.warning("⚠️ Human checkpoint system disabled in configuration")
    
    # Create enhanced agents with project context
    logger.info("🤖 Creating enhanced agents...")
    
    enhanced_style_agent = EnhancedStyleAnalysisAgent(project_id=project_id)
    logger.info("✅ Enhanced Style Analysis Agent created")
    
    enhanced_planning_agent = EnhancedContentPlanningAgent(project_id=project_id)
    logger.info("✅ Enhanced Content Planning Agent created")
    
    enhanced_generation_agent = EnhancedContentGenerationAgent(project_id=project_id)
    logger.info("✅ Enhanced Content Generation Agent created")
    
    # Set checkpoint integration for enhanced agents
    if checkpoint_integration:
        logger.info("🔗 Connecting agents to checkpoint system...")
        
        enhanced_style_agent.set_checkpoint_integration(checkpoint_integration, project_id)
        enhanced_planning_agent.set_checkpoint_integration(checkpoint_integration, project_id)
        enhanced_generation_agent.set_checkpoint_integration(checkpoint_integration, project_id)
        
        logger.info("✅ All enhanced agents connected to checkpoint system")
    else:
        logger.warning("⚠️ No checkpoint integration - agents will skip human approval")
    
    # Create standard agents (coordinator, task planner, QA)
    logger.info("🤖 Creating standard workflow agents...")
    
    coordinator = create_coordinator_agent()
    task_planner = create_task_planner_agent()
    qa_agent = create_qa_agent()
    
    logger.info("✅ Standard agents created")
    
    # Create enhanced workforce
    logger.info("🏗️ Assembling workforce...")
    
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
    
    logger.info("✅ Enhanced workforce assembled successfully")
    
    # Store references for external access
    workforce._checkpoint_manager = checkpoint_manager
    workforce._checkpoint_integration = checkpoint_integration
    workforce._project_id = project_id
    
    logger.info(f"📊 Workforce summary:")
    logger.info(f"   - Project ID: {project_id}")
    logger.info(f"   - Checkpoints enabled: {ENABLE_HUMAN_CHECKPOINTS}")
    logger.info(f"   - Mock reviewer: {ENABLE_MOCK_REVIEWER}")
    logger.info(f"   - Agents: 6 (3 enhanced + 3 standard)")
    
    return workforce
