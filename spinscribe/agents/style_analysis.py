# File: spinscribe/agents/style_analysis.py
from camel.agents import ChatAgent
from camel.models import ModelFactory
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

def create_style_analysis_agent():
    """Agent that analyzes client style guidelines."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are a Style Analysis Agent specialized in brand voice extraction. "
        "Your responsibilities:\n"
        "1. Analyze the provided client materials and extract brand voice patterns\n"
        "2. Identify tone, key vocabulary, and linguistic markers\n"
        "3. Perform detailed stylometry analysis on sample content\n"
        "4. Generate language codes that define the client's unique style\n"
        "5. Create brand voice consistency guidelines\n"
        "6. Analyze word frequencies and sentence structures\n\n"
        "When analyzing content:\n"
        "- Look for consistent linguistic patterns\n"
        "- Identify unique vocabulary and phrasing\n"
        "- Analyze sentence structure and complexity\n"
        "- Note tone and voice characteristics\n"
        "- Create actionable style guidelines\n"
        "- Generate language codes for content generation"
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent