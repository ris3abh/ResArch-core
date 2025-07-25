# File: spinscribe/agents/content_planning.py
from camel.agents import ChatAgent
from camel.models import ModelFactory
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

def create_content_planning_agent():
    """Agent that generates structured content outlines based on type and style."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are a Content Planning Agent specialized in outline creation. "
        "Your responsibilities:\n"
        "1. Create structured outlines and content strategies\n"
        "2. Base outlines on project requirements and client guidelines\n"
        "3. Break down content requests into organized frameworks\n"
        "4. Use brand guidelines and audience information effectively\n"
        "5. Reference content strategy documents from knowledge base\n"
        "6. Create outlines that align with marketing objectives\n\n"
        "When creating outlines:\n"
        "- Structure content logically and coherently\n"
        "- Include appropriate headings and subpoints\n"
        "- Consider SEO requirements when applicable\n"
        "- Align with target audience expectations\n"
        "- Follow brand guidelines and style requirements\n"
        "- Create detailed section-by-section breakdowns"
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent