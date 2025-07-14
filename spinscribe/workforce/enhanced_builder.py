# File: spinscribe/workforce/enhanced_builder.py
"""
Enhanced workforce builder with CAMEL's HumanToolkit integration.
Replaces custom checkpoint system with native human interaction.
"""

import logging
from typing import Dict, Any, Optional
from camel.agents import ChatAgent
from camel.toolkits import HumanToolkit
from camel.models import BaseModelBackend
from camel.societies import RolePlaying
from camel.memories import ContextualMemory

# Remove checkpoint imports - use only CAMEL native
from spinscribe.memory.memory_setup import get_memory
from spinscribe.knowledge.knowledge_manager import KnowledgeManager

logger = logging.getLogger('spinscribe.enhanced_builder')

async def build_enhanced_content_workflow(
    title: str,
    content_type: str, 
    project_id: str,
    model: BaseModelBackend,
    human_toolkit: Optional[HumanToolkit] = None,
    first_draft: str = None
) -> RolePlaying:
    """
    Build enhanced content creation workflow with HumanToolkit integration.
    
    Args:
        title: Content title
        content_type: Type of content (article, landing_page, etc.)
        project_id: Project identifier for knowledge isolation
        model: CAMEL model backend
        human_toolkit: HumanToolkit for human interaction (optional)
        first_draft: Existing content to enhance (optional)
        
    Returns:
        RolePlaying society with human interaction capabilities
    """
    
    logger.info(f"🏗️ Building enhanced workflow for: {title}")
    logger.info(f"🤖 Human interaction: {'✅ Enabled' if human_toolkit else '❌ Disabled'}")
    
    # Initialize knowledge manager
    knowledge_manager = KnowledgeManager()
    
    # Get shared memory for context
    memory = get_memory()
    
    # Build tools list - include HumanToolkit if available
    base_tools = []
    if human_toolkit:
        base_tools.extend(human_toolkit.get_tools())
        logger.info(f"🛠️ Added {len(human_toolkit.get_tools())} human interaction tools")
    
    # Create Content Planner Agent with Human Interaction
    planner_system_message = f"""
    You are a Content Planning Agent specialized in creating strategic content outlines.
    
    Your responsibilities:
    1. Analyze project requirements and create detailed content outlines
    2. Develop content strategy and structure
    3. Plan content flow and key messaging points
    4. Consider SEO and engagement factors
    5. Create comprehensive content briefs
    
    Project Details:
    - Title: {title}
    - Content Type: {content_type}
    - Project ID: {project_id}
    
    HUMAN INTERACTION GUIDELINES:
    - Ask humans for clarification on content strategy and target audience
    - Request approval for content outlines before proceeding
    - Seek guidance on tone and messaging priorities
    - Use available human interaction tools to get feedback
    
    When you need human input, ask direct questions like:
    - "What should be the primary goal of this content?"
    - "Who is the target audience for this piece?"
    - "Do you approve this content outline? [yes/no]"
    - "What tone should this content have? (professional/casual/technical/etc.)"
    """
    
    content_planner = ChatAgent(
        system_message=planner_system_message,
        model=model,
        tools=base_tools,
        memory=memory
    )
    
    # Create Content Generator Agent with Human Interaction
    generator_system_message = f"""
    You are a Content Generation Agent specialized in creating high-quality written content.
    
    Your responsibilities:
    1. Transform content outlines into complete, engaging content
    2. Write in the appropriate style and tone for the target audience
    3. Ensure content flows naturally and meets quality standards
    4. Incorporate SEO best practices and readability optimization
    5. Create compelling headlines and calls-to-action
    
    Project Details:
    - Title: {title}
    - Content Type: {content_type}
    - Project ID: {project_id}
    {f"- Existing Draft to Enhance: Available" if first_draft else "- Creating New Content"}
    
    HUMAN INTERACTION GUIDELINES:
    - Ask humans for style and tone preferences
    - Request feedback on draft sections before completing
    - Seek approval for final content before finishing
    - Get guidance on specific messaging or technical details
    
    Example questions to ask humans:
    - "Does this introduction capture the right tone?"
    - "Should I include more technical details or keep it accessible?"
    - "Do you approve this content draft? [yes/no]"
    - "What changes would you like me to make?"
    """
    
    content_generator = ChatAgent(
        system_message=generator_system_message,
        model=model,
        tools=base_tools,
        memory=memory
    )
    
    # Create Style Analyst Agent with Human Interaction
    style_analyst_system_message = f"""
    You are a Style Analysis Agent specialized in brand voice and content consistency.
    
    Your responsibilities:
    1. Analyze existing brand materials for voice and tone patterns
    2. Extract style guidelines and linguistic preferences
    3. Ensure content consistency with brand standards
    4. Provide style recommendations and corrections
    5. Maintain brand voice throughout content creation
    
    Project Details:
    - Title: {title}
    - Content Type: {content_type}
    - Project ID: {project_id}
    
    HUMAN INTERACTION GUIDELINES:
    - Ask humans for brand voice interpretation and clarification
    - Request approval for style guides and brand voice analysis
    - Seek feedback on style consistency and tone matching
    - Get confirmation on style decisions
    
    Questions to ask humans:
    - "Does this style guide accurately reflect your brand voice?"
    - "Should the tone be more formal or conversational?"
    - "Do you approve this style analysis? [yes/no]"
    - "Are there specific words or phrases to avoid/include?"
    """
    
    style_analyst = ChatAgent(
        system_message=style_analyst_system_message,
        model=model,
        tools=base_tools,
        memory=memory
    )
    
    # Create Quality Assurance Agent with Human Interaction
    qa_system_message = f"""
    You are a Quality Assurance Agent specialized in content review and optimization.
    
    Your responsibilities:
    1. Review content for accuracy, clarity, and engagement
    2. Check grammar, spelling, and readability
    3. Ensure content meets quality standards and requirements
    4. Provide recommendations for improvements
    5. Validate final content before delivery
    
    Project Details:
    - Title: {title}
    - Content Type: {content_type}
    - Project ID: {project_id}
    
    HUMAN INTERACTION GUIDELINES:
    - Ask humans for final approval and feedback
    - Request clarification on quality standards and preferences
    - Seek guidance on content improvements and revisions
    - Get confirmation before finalizing content
    
    Questions to ask humans:
    - "Does this content meet your quality expectations?"
    - "Are there any sections that need revision?"
    - "Do you approve this final content? [yes/no]"
    - "What final changes would you like me to make?"
    """
    
    qa_agent = ChatAgent(
        system_message=qa_system_message,
        model=model,
        tools=base_tools,
        memory=memory
    )
    
    # Create RolePlaying society for coordinated workflow
    # Use the content planner as the primary assistant and content generator as user
    role_playing = RolePlaying(
        assistant_role_name="Content Creation Team Lead",
        user_role_name="Content Strategy Director", 
        assistant_agent=content_planner,
        user_agent=content_generator,
        task_prompt=f"""
        Collaborate to create high-quality {content_type} content titled "{title}".
        
        Workflow Process:
        1. Content Strategy Director: Define content strategy and outline
        2. Content Creation Team Lead: Plan detailed content structure
        3. Work together to generate content that meets requirements
        4. Incorporate style analysis and quality assurance throughout
        5. Use human interaction tools to get feedback and approval at key points
        
        Project Context:
        - Project ID: {project_id}
        - Content Type: {content_type}
        - Human Interaction: {'Available' if human_toolkit else 'Not Available'}
        {f"- Existing Draft: Enhance and improve provided content" if first_draft else "- New Content: Create from scratch"}
        
        CRITICAL: Use human interaction tools to:
        - Get approval for content strategy and outline
        - Request feedback on draft content
        - Seek clarification on requirements and preferences
        - Obtain final approval before completion
        
        {f"Starting Point - Existing Draft to Enhance:\\n{first_draft}" if first_draft else ""}
        """,
        with_task_specify=True,
        task_specify_agent=style_analyst,  # Use style analyst for task specification
        with_task_planner=True,
        task_planner_agent=qa_agent  # Use QA agent for task planning
    )
    
    logger.info("✅ Enhanced workflow built successfully with human interaction capabilities")
    
    return role_playing