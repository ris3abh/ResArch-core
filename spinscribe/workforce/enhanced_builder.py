# File: spinscribe/workforce/enhanced_builder.py (FIXED VERSION)
"""
Enhanced workforce builder with proper async support and checkpoint integration.
FIXED VERSION - Resolves hanging issues and improves workflow stability.
"""

import logging
from camel.societies.workforce import Workforce
from camel.toolkits import HumanToolkit

from spinscribe.agents.enhanced_style_analysis import EnhancedStyleAnalysisAgent
from spinscribe.agents.enhanced_content_planning import EnhancedContentPlanningAgent
from spinscribe.agents.enhanced_content_generation import EnhancedContentGenerationAgent
from spinscribe.agents.qa import create_qa_agent
from spinscribe.agents.coordinator import create_coordinator_agent
from spinscribe.agents.task_planner import create_task_planner_agent

from spinscribe.checkpoints.checkpoint_manager import CheckpointManager
from spinscribe.checkpoints.workflow_integration import WorkflowCheckpointIntegration
from spinscribe.checkpoints.mock_reviewer import MockReviewer
from spinscribe.utils.enhanced_logging import workflow_tracker

from config.settings import ENABLE_HUMAN_CHECKPOINTS, ENABLE_MOCK_REVIEWER

def build_enhanced_content_workflow(project_id: str = "default") -> Workforce:
    """
    Build enhanced workforce with RAG and checkpoint integration plus proper async handling.
    
    Args:
        project_id: Project identifier for knowledge isolation
        
    Returns:
        Enhanced Workforce with integrated systems and logging
    """
    
    logger = logging.getLogger('spinscribe.workforce_builder')
    logger.info(f"🏗️ Building enhanced workflow for project: {project_id}")
    
    # **FIX 1: Initialize checkpoint system with better error handling**
    checkpoint_manager = None
    checkpoint_integration = None
    
    if ENABLE_HUMAN_CHECKPOINTS:
        logger.info("✋ Initializing human checkpoint system")
        try:
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
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize checkpoint system: {e}")
            logger.info("📝 Continuing without checkpoint system")
            checkpoint_manager = None
            checkpoint_integration = None
    else:
        logger.warning("⚠️ Human checkpoint system disabled in configuration")
    
    # **FIX 2: Create enhanced agents with better error handling**
    logger.info("🤖 Creating enhanced agents...")
    
    try:
        enhanced_style_agent = EnhancedStyleAnalysisAgent(project_id=project_id)
        logger.info("✅ Enhanced Style Analysis Agent created")
    except Exception as e:
        logger.warning(f"⚠️ Failed to create enhanced style agent: {e}")
        # Fallback to basic agent
        from spinscribe.agents.style_analysis import create_style_analysis_agent
        enhanced_style_agent = create_style_analysis_agent()
        logger.info("🔄 Using fallback style analysis agent")
    
    try:
        enhanced_planning_agent = EnhancedContentPlanningAgent(project_id=project_id)
        logger.info("✅ Enhanced Content Planning Agent created")
    except Exception as e:
        logger.warning(f"⚠️ Failed to create enhanced planning agent: {e}")
        # Fallback to basic agent
        from spinscribe.agents.content_planning import create_content_planning_agent
        enhanced_planning_agent = create_content_planning_agent()
        logger.info("🔄 Using fallback content planning agent")
    
    try:
        enhanced_generation_agent = EnhancedContentGenerationAgent(project_id=project_id)
        logger.info("✅ Enhanced Content Generation Agent created")
    except Exception as e:
        logger.warning(f"⚠️ Failed to create enhanced generation agent: {e}")
        # Fallback to basic agent
        from spinscribe.agents.content_generation import create_content_generation_agent
        enhanced_generation_agent = create_content_generation_agent()
        logger.info("🔄 Using fallback content generation agent")
    
    # **FIX 3: Set checkpoint integration for enhanced agents with error handling**
    if checkpoint_integration:
        logger.info("🔗 Connecting agents to checkpoint system...")
        
        try:
            if hasattr(enhanced_style_agent, 'set_checkpoint_integration'):
                enhanced_style_agent.set_checkpoint_integration(
                    checkpoint_integration, project_id
                )
                logger.info("✅ Style agent connected to checkpoints")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect style agent to checkpoints: {e}")
        
        try:
            if hasattr(enhanced_planning_agent, 'set_checkpoint_integration'):
                enhanced_planning_agent.set_checkpoint_integration(
                    checkpoint_integration, project_id
                )
                logger.info("✅ Planning agent connected to checkpoints")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect planning agent to checkpoints: {e}")
        
        try:
            if hasattr(enhanced_generation_agent, 'set_checkpoint_integration'):
                enhanced_generation_agent.set_checkpoint_integration(
                    checkpoint_integration, project_id
                )
                logger.info("✅ Generation agent connected to checkpoints")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect generation agent to checkpoints: {e}")
    
    # **FIX 4: Create workforce with proper HumanToolkit integration**
    logger.info("🏗️ Assembling workforce...")
    
    try:
        # Create custom agents for coordinator and task planner that support human interaction
        coordinator_agent = create_coordinator_agent()
        task_planner_agent = create_task_planner_agent()
        
        # **FIX 5: Add HumanToolkit to agents that need human interaction**
        try:
            human_toolkit = HumanToolkit()
            
            # Add HumanToolkit to agents that may need human input
            if hasattr(coordinator_agent, 'tools'):
                coordinator_agent.tools.append(human_toolkit)
                logger.info("🤝 HumanToolkit added to coordinator agent")
            
            if hasattr(task_planner_agent, 'tools'):
                task_planner_agent.tools.append(human_toolkit)
                logger.info("🤝 HumanToolkit added to task planner agent")
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to add HumanToolkit: {e}")
        
        # Create workforce with proper timeout and graceful shutdown
        workforce = Workforce(
            description="SpinScribe Enhanced Multi-Agent Content Creation Workflow with RAG and Human Checkpoints",
            coordinator_agent=coordinator_agent,
            task_agent=task_planner_agent,
            graceful_shutdown_timeout=30.0,  # 30 seconds for graceful shutdown
            share_memory=True  # Enable memory sharing between agents
        )
        
        # **FIX 6: Add agents to workforce with better descriptions**
        workforce.add_single_agent_worker(
            description=(
                "Enhanced Style Analysis Agent: Analyzes brand voice, writing style, "
                "and content patterns using RAG-enhanced memory. Accesses client "
                "documents, style guides, and previous content to understand brand voice. "
                "Can request human approval for style decisions."
            ),
            worker=enhanced_style_agent,
            pool_max_size=5  # Smaller pool for faster startup
        ).add_single_agent_worker(
            description=(
                "Enhanced Content Planning Agent: Creates structured content outlines "
                "and strategies using brand guidelines and RAG knowledge. Accesses "
                "audience information, content strategy documents, and can request "
                "human approval for content direction."
            ),
            worker=enhanced_planning_agent,
            pool_max_size=5
        ).add_single_agent_worker(
            description=(
                "Enhanced Content Generation Agent: Produces draft content in the "
                "client's brand voice using RAG-enhanced memory and approved outlines. "
                "Can access style guides, factual references, and request human "
                "approval for content decisions."
            ),
            worker=enhanced_generation_agent,
            pool_max_size=5
        ).add_single_agent_worker(
            description=(
                "Quality Assurance Agent: Reviews and refines content for quality, "
                "accuracy, and brand alignment. Performs final checks and can "
                "request human approval for final content."
            ),
            worker=create_qa_agent(),
            pool_max_size=3
        )
        
        # **FIX 7: Attach checkpoint manager to workforce**
        if checkpoint_manager:
            workforce._checkpoint_manager = checkpoint_manager
            workforce._checkpoint_integration = checkpoint_integration
            logger.info("✅ Checkpoint system attached to workforce")
        
        logger.info("✅ Workforce assembled successfully")
        logger.info(f"📊 Summary: Project={project_id}, Agents=4, Checkpoints={'Enabled' if checkpoint_manager else 'Disabled'}")
        
        return workforce
        
    except Exception as e:
        logger.error(f"💥 Failed to create workforce: {e}")
        # **FIX 8: Fallback to basic workforce**
        logger.info("🔄 Creating fallback basic workforce...")
        
        from spinscribe.workforce.builder import build_content_workflow
        basic_workforce = build_content_workflow()
        
        # Attach checkpoint manager if available
        if checkpoint_manager:
            basic_workforce._checkpoint_manager = checkpoint_manager
            basic_workforce._checkpoint_integration = checkpoint_integration
        
        logger.info("✅ Fallback workforce created")
        return basic_workforce


def build_workforce_with_mode(project_id: str, mode: str = "enhanced") -> Workforce:
    """
    Build workforce with specified mode for testing different configurations.
    
    Args:
        project_id: Project identifier
        mode: 'enhanced', 'standard', or 'basic'
        
    Returns:
        Configured workforce
    """
    logger = logging.getLogger('spinscribe.workforce_builder')
    
    if mode == "enhanced":
        return build_enhanced_content_workflow(project_id)
    elif mode == "standard":
        # Standard mode with some enhancements but no checkpoints
        from spinscribe.workforce.builder import build_content_workflow
        return build_content_workflow()
    elif mode == "basic":
        # Basic mode for testing
        from camel.societies.workforce import Workforce
        from spinscribe.agents.content_generation import create_content_generation_agent
        
        basic_workforce = Workforce("Basic SpinScribe Workflow")
        basic_workforce.add_single_agent_worker(
            "Content Generation Agent",
            create_content_generation_agent()
        )
        return basic_workforce
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'enhanced', 'standard', or 'basic'")