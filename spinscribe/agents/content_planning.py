# File: spinscribe/agents/content_planning.py
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import HumanToolkit, FunctionTool
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

# Import HumanLayer for tool approval
try:
    from humanlayer.core.approval import HumanLayer
    import os
    humanlayer_api_key = os.getenv("HUMANLAYER_API_KEY")
    if humanlayer_api_key:
        hl = HumanLayer(api_key=humanlayer_api_key, verbose=True)
    else:
        hl = None
except ImportError:
    hl = None

def create_content_planning_agent():
    """Agent that generates structured content outlines with human approval."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    
    # Initialize HumanToolkit for human interaction
    human_toolkit = HumanToolkit()
    
    # Define outline approval function
    if hl:
        @hl.require_approval()
        def approve_content_outline(outline: str) -> str:
            """Approve the content outline - requires human approval"""
            return f"Content outline approved: {outline}"
        
        approval_tools = [FunctionTool(approve_content_outline)]
    else:
        approval_tools = []
    
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
        "- Create detailed section-by-section breakdowns\n\n"
        "HUMAN INTERACTION: You can ask humans for feedback on content strategy "
        "and request approval for outlines using available tools."
    )
    
    # Create agent with HumanToolkit and approval tools
    all_tools = [*human_toolkit.get_tools()] + approval_tools
    agent = ChatAgent(
        system_message=sys_msg, 
        model=model,
        tools=all_tools
    )
    agent.memory = get_memory()
    return agent