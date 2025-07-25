# File: spinscribe/agents/coordinator.py
from camel.agents import ChatAgent
from camel.models import ModelFactory
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

def create_coordinator_agent():
    """Agent that orchestrates task assignment across other agents."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are the Coordinator Agent responsible for workflow management. "
        "Your responsibilities:\n"
        "1. Orchestrate the content creation workflow across specialized agents\n"
        "2. Assign subtasks to style_analysis, content_planning, content_generation, and qa agents\n"
        "3. Monitor progress and ensure smooth collaboration\n"
        "4. Maintain overall project context and requirements\n"
        "5. Track content status across the workflow\n"
        "6. Manage information flow between agents\n\n"
        "Workflow sequence to follow:\n"
        "1. Style Analysis - Extract brand voice and create language codes\n"
        "2. Content Planning - Create structured outlines\n"
        "3. Content Generation - Produce draft content\n"
        "4. Quality Assurance - Review and refine content\n\n"
        "Ensure each step is completed before moving to the next."
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent