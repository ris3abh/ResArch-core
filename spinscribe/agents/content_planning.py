from camel.agents import ChatAgent
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG
from camel.models import ModelFactory

def create_content_planning_agent():
    """Agent that generates structured content outlines based on type and style."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are a Content Planning Agent. "
        "Given a topic, content type (landing_page, article, local_article), and brand style, produce a detailed outline with headings and subpoints."  
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent