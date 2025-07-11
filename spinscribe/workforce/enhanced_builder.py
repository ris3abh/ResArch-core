# ─── UPDATE FILE: spinscribe/workforce/enhanced_builder.py ───

"""
Enhanced workforce builder with proper tool integration and checkpoint support.
FIXED VERSION - Ensures agents have proper knowledge access tools.
"""

import logging
from camel.societies.workforce import Workforce
from camel.toolkits import HumanToolkit

from spinscribe.agents.enhanced_style_analysis import create_enhanced_style_analysis_agent
from spinscribe.agents.enhanced_content_planning import EnhancedContentPlanningAgent
from spinscribe.agents.enhanced_content_generation import EnhancedContentGenerationAgent
from spinscribe.agents.qa import create_qa_agent
from spinscribe.agents.coordinator import create_coordinator_agent
from spinscribe.agents.task_planner import create_task_planner_agent

from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
from spinscribe.checkpoints.checkpoint_manager import CheckpointManager
from spinscribe.checkpoints.workflow_integration import WorkflowCheckpointIntegration
from spinscribe.checkpoints.mock_reviewer import MockReviewer
from spinscribe.utils.enhanced_logging import workflow_tracker

from config.settings import ENABLE_HUMAN_CHECKPOINTS, ENABLE_MOCK_REVIEWER

logger = logging.getLogger(__name__)

def build_enhanced_workforce(
    project_id: str = "default",
    client_docs_path: str = None
) -> Workforce:
    """
    Build enhanced workforce with RAG and checkpoint integration.
    FIXED VERSION with proper tool attachment.
    
    Args:
        project_id: Project identifier for knowledge isolation
        client_docs_path: Path to client documents (optional)
        
    Returns:
        Fully configured workforce with enhanced agents
    """
    
    logger.info(f"🏗️ Building enhanced workforce for project: {project_id}")
    
    # **FIX 1: Initialize checkpoint system first**
    checkpoint_manager = None
    checkpoint_integration = None
    
    try:
        logger.info("✋ Initializing human checkpoint system")
        checkpoint_manager = CheckpointManager()
        
        if ENABLE_MOCK_REVIEWER:
            mock_reviewer = MockReviewer()
            checkpoint_manager.add_notification_handler(mock_reviewer.handle_notification)
            logger.info("🤖 Mock reviewer enabled for automatic checkpoint responses")
        
        checkpoint_integration = WorkflowCheckpointIntegration(
            checkpoint_manager=checkpoint_manager,
            project_id=project_id
        )
        logger.info("✅ Human checkpoint system initialized")
        
    except Exception as e:
        logger.warning(f"⚠️ Checkpoint system initialization failed: {e}")
    
    # **FIX 2: Create enhanced agents with proper tool integration**
    logger.info("🤖 Creating enhanced agents with knowledge tools...")
    
    try:
        # Create Enhanced Style Analysis Agent with tools
        enhanced_style_agent = create_enhanced_style_analysis_agent(project_id=project_id)
        logger.info(f"✅ Enhanced Style Analysis Agent created with {len(enhanced_style_agent.tools) if hasattr(enhanced_style_agent, 'tools') else 0} tools")
    except Exception as e:
        logger.warning(f"⚠️ Failed to create enhanced style agent: {e}")
        # Fallback to basic agent
        from spinscribe.agents.style_analysis import create_style_analysis_agent
        enhanced_style_agent = create_style_analysis_agent()
        logger.info("🔄 Using fallback style analysis agent")
    
    try:
        # Create Enhanced Content Planning Agent with tools
        enhanced_planning_agent = EnhancedContentPlanningAgent(project_id=project_id)
        
        # Add knowledge toolkit to planning agent
        knowledge_toolkit = KnowledgeAccessToolkit(project_id=project_id)
        if hasattr(enhanced_planning_agent, 'tools'):
            enhanced_planning_agent.tools.extend(knowledge_toolkit.get_tools())
        else:
            enhanced_planning_agent.tools = knowledge_toolkit.get_tools()
        
        logger.info(f"✅ Enhanced Content Planning Agent created with {len(enhanced_planning_agent.tools) if hasattr(enhanced_planning_agent, 'tools') else 0} tools")
    except Exception as e:
        logger.warning(f"⚠️ Failed to create enhanced planning agent: {e}")
        # Fallback to basic agent
        from spinscribe.agents.content_planning import create_content_planning_agent
        enhanced_planning_agent = create_content_planning_agent()
        logger.info("🔄 Using fallback content planning agent")
    
    try:
        # Create Enhanced Content Generation Agent with tools
        enhanced_generation_agent = EnhancedContentGenerationAgent(project_id=project_id)
        
        # Add knowledge toolkit to generation agent
        knowledge_toolkit = KnowledgeAccessToolkit(project_id=project_id)
        if hasattr(enhanced_generation_agent, 'tools'):
            enhanced_generation_agent.tools.extend(knowledge_toolkit.get_tools())
        else:
            enhanced_generation_agent.tools = knowledge_toolkit.get_tools()
        
        logger.info(f"✅ Enhanced Content Generation Agent created with {len(enhanced_generation_agent.tools) if hasattr(enhanced_generation_agent, 'tools') else 0} tools")
    except Exception as e:
        logger.warning(f"⚠️ Failed to create enhanced generation agent: {e}")
        # Fallback to basic agent
        from spinscribe.agents.content_generation import create_content_generation_agent
        enhanced_generation_agent = create_content_generation_agent()
        logger.info("🔄 Using fallback content generation agent")
    
    # **FIX 3: Connect agents to checkpoint system**
    if checkpoint_integration:
        logger.info("🔗 Connecting agents to checkpoint system...")
        try:
            if hasattr(enhanced_style_agent, 'set_checkpoint_integration'):
                enhanced_style_agent.set_checkpoint_integration(checkpoint_integration)
                logger.info("✅ Style agent connected to checkpoints")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect style agent to checkpoints: {e}")
        
        try:
            if hasattr(enhanced_planning_agent, 'set_checkpoint_integration'):
                enhanced_planning_agent.set_checkpoint_integration(checkpoint_integration)
                logger.info("✅ Planning agent connected to checkpoints")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect planning agent to checkpoints: {e}")
        
        try:
            if hasattr(enhanced_generation_agent, 'set_checkpoint_integration'):
                enhanced_generation_agent.set_checkpoint_integration(checkpoint_integration)
                logger.info("✅ Generation agent connected to checkpoints")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect generation agent to checkpoints: {e}")
    
    # **FIX 4: Create coordinator and task planner with human interaction support**
    logger.info("🏗️ Assembling workforce...")
    
    try:
        coordinator_agent = create_coordinator_agent()
        task_planner_agent = create_task_planner_agent()
        
        # Add HumanToolkit to agents that need human interaction
        human_toolkit = HumanToolkit()
        
        if hasattr(coordinator_agent, 'tools'):
            coordinator_agent.tools.extend(human_toolkit.get_tools())
        else:
            coordinator_agent.tools = human_toolkit.get_tools()
        logger.info("🤝 HumanToolkit added to coordinator agent")
        
        if hasattr(task_planner_agent, 'tools'):
            task_planner_agent.tools.extend(human_toolkit.get_tools())
        else:
            task_planner_agent.tools = human_toolkit.get_tools()
        logger.info("🤝 HumanToolkit added to task planner agent")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to add HumanToolkit: {e}")
    
    # **FIX 5: Create workforce with proper configuration**
    try:
        workforce = Workforce(
            description="SpinScribe Enhanced Multi-Agent Content Creation with RAG and Human Checkpoints",
            coordinator_agent=coordinator_agent,
            task_agent=task_planner_agent,
            graceful_shutdown_timeout=30.0,
            share_memory=True
        )
        
        # **FIX 6: Add agents with updated descriptions that mention tool capabilities**
        workforce.add_single_agent_worker(
            description=(
                "Enhanced Style Analysis Agent: Analyzes brand voice, writing style, "
                "and content patterns using RAG-enhanced memory. Has knowledge access tools to "
                "search client documents, retrieve style guides, and analyze sample content. "
                "Can request human approval for style decisions."
            ),
            worker=enhanced_style_agent,
            pool_max_size=3
        ).add_single_agent_worker(
            description=(
                "Enhanced Content Planning Agent: Creates structured content outlines "
                "and strategies using brand guidelines and RAG knowledge. Has tools to "
                "access audience information, content strategy documents, and brand guidelines. "
                "Can request human approval for content direction."
            ),
            worker=enhanced_planning_agent,
            pool_max_size=3
        ).add_single_agent_worker(
            description=(
                "Enhanced Content Generation Agent: Produces draft content in the "
                "client's brand voice using RAG-enhanced memory and approved outlines. "
                "Has tools to access style guides, factual references, and knowledge base. "
                "Can request human approval for content decisions."
            ),
            worker=enhanced_generation_agent,
            pool_max_size=3
        ).add_single_agent_worker(
            description=(
                "Quality Assurance Agent: Reviews and refines content for quality, "
                "accuracy, and brand alignment. Performs final checks and can request "
                "human approval for final content."
            ),
            worker=create_qa_agent(),
            pool_max_size=2
        )
        
        # **FIX 7: Attach checkpoint system to workforce**
        if checkpoint_manager:
            workforce._checkpoint_manager = checkpoint_manager
            logger.info("✅ Checkpoint system attached to workforce")
        
        if checkpoint_integration:
            workforce._checkpoint_integration = checkpoint_integration
            logger.info("✅ Checkpoint integration attached to workforce")
        
        logger.info("✅ Workforce assembled successfully")
        logger.info(f"📊 Summary: Project={project_id}, Agents=4, Checkpoints={'Enabled' if checkpoint_manager else 'Disabled'}")
        
        return workforce
        
    except Exception as e:
        logger.error(f"❌ Failed to create workforce: {e}")
        raise


def test_workforce_with_tools(project_id: str = "test-camel-fix"):
    """Test the enhanced workforce with tool integration."""
    try:
        print(f"🧪 Testing Enhanced Workforce for project: {project_id}")
        
        # Build workforce
        workforce = build_enhanced_workforce(project_id=project_id)
        print("✅ Workforce built successfully")
        
        # Check tool integration
        workers = workforce._workers if hasattr(workforce, '_workers') else []
        print(f"📊 Workforce has {len(workers)} worker types")
        
        for i, worker in enumerate(workers):
            if hasattr(worker, 'tools'):
                print(f"Worker {i+1}: {len(worker.tools)} tools attached")
            else:
                print(f"Worker {i+1}: No tools found")
        
        return workforce
        
    except Exception as e:
        print(f"❌ Workforce test failed: {e}")
        return None


if __name__ == "__main__":
    # Test workforce
    test_workforce = test_workforce_with_tools()
    if test_workforce:
        print("\n" + "="*60)
        print("Enhanced Workforce Test Complete")
        print("="*60)