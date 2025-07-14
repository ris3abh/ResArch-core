# File: spinscribe/agents/style_analysis.py
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

def create_style_analysis_agent():
    """Agent that analyzes client style guidelines with human-in-loop capabilities."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    
    # Initialize HumanToolkit for human interaction
    human_toolkit = HumanToolkit()
    
    # Define style guide approval function
    if hl:
        @hl.require_approval()
        def approve_style_guide(style_analysis: str) -> str:
            """Approve the generated style guide - requires human approval"""
            return f"Style guide approved: {style_analysis}"
        
        approval_tools = [FunctionTool(approve_style_guide)]
    else:
        approval_tools = []
    
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
        "- Generate language codes for content generation\n\n"
        "HUMAN INTERACTION: You can ask humans for clarification on brand voice "
        "interpretation and request approval for style guides using available tools."
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