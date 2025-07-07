# File: spinscribe/agents/qa.py
from camel.agents import ChatAgent
from camel.models import ModelFactory
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

def create_qa_agent():
    """Agent that reviews drafts for quality, consistency, and brand alignment."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    sys_msg = (
        "You are a Quality Assurance Agent responsible for content refinement. "
        "Your responsibilities:\n"
        "1. Review draft content for grammar, style consistency, and brand alignment\n"
        "2. Verify adherence to brand voice patterns and language codes\n"
        "3. Check factual accuracy against knowledge base references\n"
        "4. Ensure consistency with previous client content\n"
        "5. Validate compliance with style guidelines\n"
        "6. Identify potential improvements based on past performance\n"
        "7. Provide specific, actionable feedback for revisions\n\n"
        "Quality checks to perform:\n"
        "- Grammar and spelling accuracy\n"
        "- Brand voice consistency\n"
        "- Style guide compliance\n"
        "- Factual accuracy\n"
        "- Content structure and flow\n"
        "- Target audience appropriateness\n"
        "- Overall content quality and effectiveness"
    )
    agent = ChatAgent(system_message=sys_msg, model=model)
    agent.memory = get_memory()
    return agent