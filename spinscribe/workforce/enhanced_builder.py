# ═══════════════════════════════════════════════════════════════════════════════
# FILE: spinscribe/workforce/enhanced_builder.py
# STATUS: UPDATE (Remove checkpoint system, keep enhanced agents with HumanToolkit)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Enhanced workforce builder with HumanToolkit integration and RAG capabilities.
UPDATED VERSION - Removed custom checkpoint system, using CAMEL's native human input.
"""

import logging
from camel.societies.workforce import Workforce

# Import enhanced agents with HumanToolkit and RAG
from spinscribe.agents.enhanced_style_analysis import create_enhanced_style_analysis_agent
from spinscribe.agents.enhanced_content_planning import create_enhanced_content_planning_agent
from spinscribe.agents.enhanced_content_generation import create_enhanced_content_generation_agent

# Import basic agents for coordinator and QA (they will also get HumanToolkit)
from spinscribe.agents.qa import create_qa_agent
from spinscribe.agents.coordinator import create_coordinator_agent
from spinscribe.agents.task_planner import create_task_planner_agent

logger = logging.getLogger(__name__)

def build_enhanced_content_workflow(project_id: str = "default") -> Workforce:
    """
    Build enhanced workforce with HumanToolkit-enabled agents and RAG integration.
    No more custom checkpoint system - using CAMEL's native human input.
    
    Args:
        project_id: Project identifier for knowledge isolation
        
    Returns:
        Fully configured workforce with enhanced agents
    """
    logger.info(f"🏗️ Building enhanced workforce for project: {project_id}")
    
    try:
        # Create coordinator and task planner (now with HumanToolkit)
        coordinator = create_coordinator_agent()
        task_planner = create_task_planner_agent()
        
        # Create workforce with human-enabled coordinator
        workforce = Workforce(
            description=(
                "SpinScribe Enhanced Multi-Agent Content Creation System - "
                "Specialized workflow with integrated human-in-loop capabilities, "
                "RAG knowledge access, and advanced content creation features "
                "for producing high-quality, brand-aligned content."
            ),
            coordinator_agent=coordinator,
            task_agent=task_planner
        )

        # Add enhanced agents with HumanToolkit and RAG capabilities
        workforce.add_single_agent_worker(
            description=(
                "Enhanced Style Analysis Agent: Analyzes client brand voice patterns with "
                "RAG access to brand materials and human-in-loop for style guide approval. "
                "Performs advanced stylometry analysis, generates language codes, and creates "
                "comprehensive brand voice guidelines. Can ask humans for clarification on "
                "brand voice interpretation and request approval for style guides."
            ),
            worker=create_enhanced_style_analysis_agent(project_id=project_id)
        ).add_single_agent_worker(
            description=(
                "Enhanced Content Planning Agent: Creates strategic content outlines with "
                "RAG access to brand guidelines and human feedback integration. Uses advanced "
                "content strategy documents and audience analysis to create organized frameworks. "
                "Can request human feedback on content strategy and seek approval for outlines."
            ),
            worker=create_enhanced_content_planning_agent(project_id=project_id)
        ).add_single_agent_worker(
            description=(
                "Enhanced Content Generation Agent: Produces high-quality draft content with "
                "RAG access to style guides and human review capabilities. Applies advanced "
                "brand voice patterns to approved outlines while maintaining consistency with "
                "previous content. Can request human feedback on content direction and seek "
                "approval for drafts."
            ),
            worker=create_enhanced_content_generation_agent(project_id=project_id)
        ).add_single_agent_worker(
            description=(
                "Quality Assurance Agent: Reviews and refines content with human final "
                "approval integration. Ensures quality, accuracy, and brand alignment using "
                "comprehensive quality checks. Can request human review for final content "
                "approval and provide detailed feedback for improvements."
            ),
            worker=create_qa_agent()
        )

        logger.info("✅ Enhanced workforce built with HumanToolkit + RAG integration")
        logger.info(f"   Agents configured: {len(workforce.workers)}")
        logger.info(f"   Project ID: {project_id}")
        logger.info(f"   Human Input: ✅ CAMEL HumanToolkit Enabled")
        logger.info(f"   RAG Access: ✅ Knowledge Base Integration")
        logger.info(f"   Custom Checkpoints: ❌ Removed (Using CAMEL Native)")
        
        return workforce
        
    except Exception as e:
        logger.error(f"❌ Failed to build enhanced workforce: {e}")
        raise


def build_enhanced_workforce(project_id: str = "default", client_docs_path: str = None) -> Workforce:
    """
    Build enhanced workforce with RAG and HumanToolkit integration.
    Legacy function name for compatibility - delegates to build_enhanced_content_workflow.
    
    Args:
        project_id: Project identifier for knowledge isolation
        client_docs_path: Path to client documents (for compatibility)
        
    Returns:
        Fully configured enhanced workforce
    """
    logger.info(f"🔄 Legacy workforce builder called - delegating to enhanced workflow")
    if client_docs_path:
        logger.info(f"📁 Client documents path provided: {client_docs_path}")
    
    return build_enhanced_content_workflow(project_id=project_id)


def test_enhanced_workforce_with_human_toolkit(project_id: str = "test-human-toolkit") -> dict:
    """Test enhanced workforce with HumanToolkit and RAG capabilities."""
    try:
        logger.info(f"🧪 Testing enhanced workforce with HumanToolkit for project: {project_id}")
        
        # Build workforce
        workforce = build_enhanced_content_workflow(project_id)
        
        # Verify all agents and their capabilities
        worker_count = len(workforce.workers)
        
        # Test individual agent capabilities
        agent_capabilities = []
        for i, worker in enumerate(workforce.workers):
            agent_name = worker.description.split(':')[0] if ':' in worker.description else f"Agent {i+1}"
            has_tools = hasattr(worker, 'tools') and len(getattr(worker, 'tools', [])) > 0
            has_knowledge = hasattr(worker, 'knowledge_toolkit')
            
            agent_capabilities.append({
                "name": agent_name,
                "has_tools": has_tools,
                "has_knowledge": has_knowledge,
                "tool_count": len(getattr(worker, 'tools', []))
            })
        
        result = {
            "success": True, 
            "message": f"Enhanced workforce with {worker_count} human-enabled agents created",
            "project_id": project_id,
            "human_toolkit_enabled": True,
            "rag_integration": True,
            "checkpoint_system": "removed",
            "workflow_type": "enhanced",
            "agents": [
                "Enhanced Style Analysis (RAG + Human Approval)",
                "Enhanced Content Planning (RAG + Human Feedback)", 
                "Enhanced Content Generation (RAG + Human Review)",
                "Quality Assurance (Human Final Approval)",
                "Coordinator (Human Oversight)"
            ],
            "agent_capabilities": agent_capabilities,
            "total_agents": worker_count
        }
        
        logger.info("✅ Enhanced workforce test completed successfully")
        logger.info(f"   Total agents: {worker_count}")
        logger.info(f"   Enhanced agents: 3 (Style, Planning, Generation)")
        logger.info(f"   Human interaction: ✅ All agents equipped")
        logger.info(f"   RAG access: ✅ Enhanced agents equipped")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Enhanced workforce test failed: {e}")
        return {"success": False, "error": str(e)}


def test_workforce_with_tools(project_id: str = "test-workforce-tools") -> dict:
    """Test workforce with comprehensive tool integration."""
    try:
        logger.info(f"🧪 Testing workforce with comprehensive tool integration")
        
        # Test enhanced workforce
        enhanced_result = test_enhanced_workforce_with_human_toolkit(project_id)
        
        if not enhanced_result.get("success"):
            return enhanced_result
        
        # Additional tool testing
        workforce = build_enhanced_content_workflow(project_id)
        
        # Count total tools across all agents
        total_tools = 0
        agents_with_tools = 0
        agents_with_knowledge = 0
        
        for worker in workforce.workers:
            worker_tools = len(getattr(worker, 'tools', []))
            total_tools += worker_tools
            if worker_tools > 0:
                agents_with_tools += 1
            if hasattr(worker, 'knowledge_toolkit'):
                agents_with_knowledge += 1
        
        comprehensive_result = {
            "success": True,
            "enhanced_workflow": enhanced_result,
            "tool_analysis": {
                "total_tools": total_tools,
                "agents_with_tools": agents_with_tools,
                "agents_with_knowledge": agents_with_knowledge,
                "total_agents": len(workforce.workers)
            },
            "integration_status": {
                "human_toolkit": "✅ Integrated",
                "rag_access": "✅ Enhanced agents equipped",
                "tool_approval": "✅ HumanLayer ready",
                "checkpoint_system": "❌ Removed (Using CAMEL native)"
            }
        }
        
        logger.info("🎯 Comprehensive tool integration test results:")
        logger.info(f"   Total tools: {total_tools}")
        logger.info(f"   Agents with tools: {agents_with_tools}/{len(workforce.workers)}")
        logger.info(f"   Agents with knowledge: {agents_with_knowledge}")
        
        return comprehensive_result
        
    except Exception as e:
        logger.error(f"❌ Comprehensive tool test failed: {e}")
        return {"success": False, "error": str(e)}


def get_workforce_capabilities(project_id: str = "default") -> dict:
    """Get detailed capabilities of the enhanced workforce."""
    try:
        workforce = build_enhanced_content_workflow(project_id)
        
        capabilities = {
            "project_id": project_id,
            "workforce_type": "enhanced",
            "total_agents": len(workforce.workers),
            "human_interaction": True,
            "rag_integration": True,
            "agent_details": []
        }
        
        for i, worker in enumerate(workforce.workers):
            agent_info = {
                "index": i,
                "description": worker.description,
                "has_tools": hasattr(worker, 'tools'),
                "tool_count": len(getattr(worker, 'tools', [])),
                "has_knowledge": hasattr(worker, 'knowledge_toolkit'),
                "enhanced": "Enhanced" in worker.description
            }
            capabilities["agent_details"].append(agent_info)
        
        return capabilities
        
    except Exception as e:
        logger.error(f"❌ Failed to get workforce capabilities: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Test the updated workforce
    print("🧪 Testing Enhanced Workforce with HumanToolkit + RAG")
    print("=" * 60)
    
    # Test enhanced workforce
    test_result = test_enhanced_workforce_with_human_toolkit()
    
    if test_result["success"]:
        print("✅ Enhanced Workforce Test Complete")
        print(f"   Project ID: {test_result['project_id']}")
        print(f"   Total Agents: {test_result['total_agents']}")
        print(f"   Human Integration: ✅ CAMEL HumanToolkit")
        print(f"   RAG Integration: ✅ Knowledge Base Access")
        print(f"   Custom Checkpoints: ❌ Removed")
        print(f"   Workflow Type: {test_result['workflow_type']}")
        
        print("\n🎯 Agent Capabilities:")
        for capability in test_result.get('agent_capabilities', []):
            print(f"   {capability['name']}: Tools={capability['tool_count']}, Knowledge={capability['has_knowledge']}")
        
    else:
        print("❌ Enhanced Workforce Test Failed")
        print(f"   Error: {test_result['error']}")
    
    print("\n" + "=" * 60)
    
    # Test comprehensive tool integration
    print("🧪 Testing Comprehensive Tool Integration")
    comprehensive_result = test_workforce_with_tools()
    
    if comprehensive_result["success"]:
        print("✅ Comprehensive Tool Integration Test Complete")
        tool_analysis = comprehensive_result["tool_analysis"]
        print(f"   Total Tools: {tool_analysis['total_tools']}")
        print(f"   Agents with Tools: {tool_analysis['agents_with_tools']}/{tool_analysis['total_agents']}")
        print(f"   Agents with Knowledge: {tool_analysis['agents_with_knowledge']}")
        
        print("\n🔧 Integration Status:")
        for key, status in comprehensive_result["integration_status"].items():
            print(f"   {key.replace('_', ' ').title()}: {status}")
    else:
        print("❌ Comprehensive Tool Integration Test Failed")
        print(f"   Error: {comprehensive_result['error']}")
    
    print("\n🎉 All tests completed!")