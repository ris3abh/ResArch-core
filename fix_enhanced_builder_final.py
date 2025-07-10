#!/usr/bin/env python3
"""
Fix enhanced builder to use standard agents when checkpoints disabled.
"""

enhanced_builder_content = '''# File: spinscribe/workforce/enhanced_builder.py (FIXED)
"""
Enhanced workforce builder with conditional agent selection.
Uses standard agents when checkpoints are disabled.
"""

import logging
from camel.societies.workforce import Workforce

# Standard agents (always work)
from spinscribe.agents.style_analysis import create_style_analysis_agent
from spinscribe.agents.content_planning import create_content_planning_agent
from spinscribe.agents.content_generation import create_content_generation_agent
from spinscribe.agents.qa import create_qa_agent
from spinscribe.agents.coordinator import create_coordinator_agent
from spinscribe.agents.task_planner import create_task_planner_agent

# Enhanced agents (only when checkpoints enabled)
try:
    from spinscribe.agents.enhanced_style_analysis import EnhancedStyleAnalysisAgent
    from spinscribe.agents.enhanced_content_planning import EnhancedContentPlanningAgent
    from spinscribe.agents.enhanced_content_generation import EnhancedContentGenerationAgent
    ENHANCED_AGENTS_AVAILABLE = True
except ImportError:
    ENHANCED_AGENTS_AVAILABLE = False

from spinscribe.checkpoints.checkpoint_manager import CheckpointManager
from spinscribe.checkpoints.workflow_integration import WorkflowCheckpointIntegration
from spinscribe.checkpoints.mock_reviewer import MockReviewer

from config.settings import ENABLE_HUMAN_CHECKPOINTS, ENABLE_MOCK_REVIEWER

def build_enhanced_content_workflow(project_id: str = "default") -> Workforce:
    """
    Build workforce with conditional agent selection.
    Uses standard agents when checkpoints disabled for guaranteed reliability.
    """
    
    logger = logging.getLogger('spinscribe.workforce_builder')
    logger.info(f"🏗️ Building workflow for project: {project_id}")
    
    # Determine which agents to use
    use_enhanced_agents = ENABLE_HUMAN_CHECKPOINTS and ENHANCED_AGENTS_AVAILABLE
    
    if use_enhanced_agents:
        logger.info("🚀 Using enhanced agents with checkpoint integration")
        
        # Initialize checkpoint system
        checkpoint_manager = CheckpointManager()
        checkpoint_integration = WorkflowCheckpointIntegration(checkpoint_manager)
        
        if ENABLE_MOCK_REVIEWER:
            mock_reviewer = MockReviewer(checkpoint_manager)
            mock_reviewer.auto_approve_rate = 0.8
            mock_reviewer.response_delay_seconds = (0.5, 2.0)
            logger.info("🤖 Mock reviewer enabled")
        
        # Create enhanced agents
        style_agent = EnhancedStyleAnalysisAgent(project_id=project_id)
        planning_agent = EnhancedContentPlanningAgent(project_id=project_id)
        generation_agent = EnhancedContentGenerationAgent(project_id=project_id)
        
        # Set checkpoint integration
        style_agent.set_checkpoint_integration(checkpoint_integration, project_id)
        planning_agent.set_checkpoint_integration(checkpoint_integration, project_id)
        generation_agent.set_checkpoint_integration(checkpoint_integration, project_id)
        
        agent_type = "enhanced"
        
    else:
        logger.info("🔧 Using standard agents for reliable performance")
        
        # Use proven standard agents
        style_agent = create_style_analysis_agent()
        planning_agent = create_content_planning_agent()
        generation_agent = create_content_generation_agent()
        
        checkpoint_manager = None
        checkpoint_integration = None
        agent_type = "standard"
    
    # Create standard workflow components (always synchronous)
    coordinator = create_coordinator_agent()
    task_planner = create_task_planner_agent()
    qa_agent = create_qa_agent()
    
    logger.info(f"✅ All agents created successfully (mode: {agent_type})")
    
    # Create workforce
    logger.info("🏗️ Assembling workforce...")
    
    workforce_description = (
        f"SpinScribe Multi-Agent Content Creation System ({agent_type} mode) - "
        f"Project: {project_id}"
    )
    
    workforce = Workforce(
        description=workforce_description,
        coordinator_agent=coordinator,
        task_agent=task_planner
    )
    
    # Add agents to workforce
    workforce.add_single_agent_worker(
        description=f"Style Analysis Agent ({agent_type}): Analyzes brand voice and style patterns",
        worker=style_agent
    ).add_single_agent_worker(
        description=f"Content Planning Agent ({agent_type}): Creates structured content outlines",
        worker=planning_agent
    ).add_single_agent_worker(
        description=f"Content Generation Agent ({agent_type}): Generates brand-consistent content",
        worker=generation_agent
    ).add_single_agent_worker(
        description="Quality Assurance Agent: Reviews and refines content quality",
        worker=qa_agent
    )
    
    # Store references
    workforce._checkpoint_manager = checkpoint_manager
    workforce._checkpoint_integration = checkpoint_integration
    workforce._project_id = project_id
    workforce._agent_type = agent_type
    
    logger.info("✅ Workforce assembled successfully")
    logger.info(f"📊 Summary: Project={project_id}, Mode={agent_type}, Checkpoints={ENABLE_HUMAN_CHECKPOINTS}")
    
    return workforce
'''

# Write the fixed enhanced builder
with open('spinscribe/workforce/enhanced_builder.py', 'w') as f:
    f.write(enhanced_builder_content)

print("✅ Enhanced builder fixed to use standard agents when checkpoints disabled")
