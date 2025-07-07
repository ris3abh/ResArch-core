# File: spinscribe/agents/content_generation.py
from camel.agents import ChatAgent
from camel.models import ModelFactory
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

def create_content_generation_agent():
    """Agent that writes draft content using outline and style guidelines."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are a Content Generation Agent specialized in creating high-quality content. "
        "Your responsibilities:\n"
        "1. Use the provided outline and client style patterns to write well-structured draft content\n"
        "2. Apply language codes and brand voice patterns from the Style Analysis Agent\n"
        "3. Follow content structure from the Content Planning Agent\n"
        "4. Access factual information from the knowledge base as needed\n"
        "5. Maintain consistency with previous client content\n"
        "6. Produce content that matches the client's unique voice and style\n\n"
        "When generating content:\n"
        "- Follow the approved outline structure exactly\n"
        "- Apply the language code patterns consistently\n"
        "- Use appropriate tone and vocabulary for the target audience\n"
        "- Ensure factual accuracy by referencing knowledge base\n"
        "- Maintain brand voice consistency throughout"
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent