from camel.agents import ChatAgent
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG
from camel.models import ModelFactory

def create_qa_agent():
    """Agent that reviews drafts for quality, consistency, and brand alignment."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are a QA Agent. "
        "Review the draft content for grammar, style consistency, and alignment with the client's brand voice and provide feedback."  
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent