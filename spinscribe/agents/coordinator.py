# ═══════════════════════════════════════════════════════════════════════════════
# FILE: spinscribe/agents/coordinator.py
# STATUS: UPDATE (FIXED - HumanToolkit only, no HumanLayer dependency)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Coordinator Agent with CAMEL's native HumanToolkit integration.
FIXED VERSION - Using only CAMEL's built-in human interaction capabilities.
"""

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import HumanToolkit
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

def create_coordinator_agent():
    """Agent that orchestrates task assignment with human oversight."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    
    # Initialize CAMEL's built-in HumanToolkit (always available)
    human_toolkit = HumanToolkit()
    
    sys_msg = (
        "You are the Coordinator Agent responsible for workflow management with "
        "human interaction capabilities. "
        "Your responsibilities:\n"
        "1. Orchestrate the content creation workflow across specialized agents\n"
        "2. Assign subtasks to style_analysis, content_planning, content_generation, and qa agents\n"
        "3. Monitor progress and ensure smooth collaboration\n"
        "4. Maintain overall project context and requirements\n"
        "5. Track content status across the workflow\n"
        "6. Manage information flow between agents\n\n"
        "Workflow sequence to follow:\n"
        "1. Enhanced Style Analysis - Extract brand voice and create language codes\n"
        "2. Enhanced Content Planning - Create structured outlines with strategy\n"
        "3. Enhanced Content Generation - Produce draft content with RAG verification\n"
        "4. Quality Assurance - Review and refine content with human feedback\n\n"
        "Ensure each step is completed before moving to the next.\n\n"
        "HUMAN INTERACTION: You can ask humans for project guidance, "
        "priority changes, strategic decisions, and workflow adjustments using "
        "your available tools. Human input happens via console interaction - "
        "ask questions directly when you need guidance or approval."
    )
    
    # Create agent with HumanToolkit
    agent = ChatAgent(
        system_message=sys_msg, 
        model=model,
        tools=[*human_toolkit.get_tools()]
    )
    agent.memory = get_memory()
    return agent