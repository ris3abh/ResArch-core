from camel.agents import ChatAgent
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG
from camel.models import ModelFactory

def create_coordinator_agent():
    """Agent that orchestrates task assignment across other agents."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are the Coordinator Agent. "
        "Orchestrate the workflow by assigning subtasks to style_analysis, content_planning, content_generation, and qa agents."  
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent