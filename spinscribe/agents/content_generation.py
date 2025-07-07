from camel.agents import ChatAgent
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG
from camel.models import ModelFactory

def create_content_generation_agent():
    """Agent that writes draft content using outline and style guidelines."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are a Content Generation Agent. "
        "Using the provided outline and client style patterns, write a well-structured draft of the content."  
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent