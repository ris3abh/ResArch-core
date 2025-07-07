from camel.agents import ChatAgent
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG
from camel.models import ModelFactory

def create_style_analysis_agent():
    """Agent that analyzes client style guidelines."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are a Style Analysis Agent. "
        "Analyze the provided client materials and extract brand voice patterns, tone, and key vocabulary."  
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent