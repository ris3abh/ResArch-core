# ─── UPDATE FILE: spinscribe/agents/enhanced_content_generation.py ─
"""
Enhanced Content Generation Agent with RAG and checkpoint integration.
"""

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.messages import BaseMessage

from spinscribe.memory.memory_setup import get_memory
from spinscribe.knowledge.integration import search_client_knowledge, get_sample_content
from spinscribe.checkpoints.enhanced_agents import CheckpointEnabledAgent
from spinscribe.checkpoints.checkpoint_manager import CheckpointType, Priority
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

import logging

logger = logging.getLogger(__name__)

class EnhancedContentGenerationAgent(CheckpointEnabledAgent, ChatAgent):
    """
    Enhanced Content Generation Agent with RAG knowledge and human checkpoints.
    """
    
    def __init__(self, project_id: str = None):
        model = ModelFactory.create(
            model_platform=MODEL_PLATFORM,
            model_type=MODEL_TYPE,
            model_config_dict=MODEL_CONFIG,
        )
        
        sys_msg = (
            "You are an Enhanced Content Generation Agent specialized in brand-consistent content creation. "
            "Your responsibilities:\n"
            "1. Generate content using approved outlines and brand voice patterns\n"
            "2. Reference client knowledge base for factual accuracy and tone\n"
            "3. Apply language codes and style patterns consistently\n"
            "4. Learn from sample content and successful previous work\n"
            "5. Request human review for content quality assurance\n"
            "6. Maintain brand voice throughout all generated content\n\n"
            "Enhanced capabilities:\n"
            "- Access to comprehensive style guidelines and samples\n"
            "- Integration with human quality review checkpoints\n"
            "- Factual verification against knowledge base\n"
            "- Consistency checking with previous content\n\n"
            "When generating content:\n"
            "- Follow approved outline structure exactly\n"
            "- Apply brand voice patterns from knowledge base\n"
            "- Reference factual information from client documents\n"
            "- Request quality review for important content pieces"
        )
        
        super().__init__(system_message=sys_msg, model=model)
        self.memory = get_memory()
        self.project_id = project_id
    
    async def generate_enhanced_content(
        self, 
        outline: str, 
        style_analysis: str,
        content_type: str,
        request_approval: bool = True
    ) -> dict:
        """
        Generate content using RAG knowledge and optional human checkpoint.
        
        Args:
            outline: Approved content outline
            style_analysis: Brand voice analysis
            content_type: Type of content being generated
            request_approval: Whether to request human approval
            
        Returns:
            Dict with generated content and approval status
        """
        logger.info(f"✍️ Generating enhanced content for {content_type}")
        
        # Step 1: Gather relevant knowledge for content generation
        relevant_knowledge = ""
        if self.project_id:
            # Get sample content for reference
            sample_knowledge = await get_sample_content(self.project_id, content_type)
            
            # Search for factual information and references
            factual_knowledge = await search_client_knowledge(
                query=f"facts data information {content_type}",
                project_id=self.project_id,
                knowledge_types=['reference_document', 'marketing_materials'],
                limit=3
            )
            
            relevant_knowledge = f"{sample_knowledge}\n\n{factual_knowledge}"
            logger.info(f"Retrieved {len(relevant_knowledge)} chars of content knowledge")
        
        # Step 2: Generate content with enhanced context
        enhanced_prompt = f"""
        TASK: Generate high-quality {content_type} content following the approved outline and brand voice.
        
        APPROVED OUTLINE:
        {outline}
        
        BRAND VOICE ANALYSIS:
        {style_analysis}
        
        RELEVANT KNOWLEDGE & SAMPLES:
        {relevant_knowledge}
        
        INSTRUCTIONS:
        1. Follow the outline structure exactly
        2. Apply the brand voice patterns consistently throughout
        3. Use factual information from the knowledge base
        4. Reference successful content patterns from samples
        5. Ensure engaging, high-quality writing
        6. Maintain consistency with client's established voice
        
        Generate complete, publication-ready content that exemplifies the brand voice.
        """
        
        generation_message = BaseMessage.make_assistant_message(
            role_name="Enhanced Content Generator",
            content=enhanced_prompt
        )
        
        response = self.step(generation_message)
        content_result = response.msg.content
        
        logger.info("✅ Enhanced content generated")
        
        # Step 3: Request human approval if enabled
        approval_result = {'approved': True, 'skipped': True}
        
        if request_approval and self.checkpoint_integration:
            logger.info("🛑 Requesting human approval for content draft")
            
            approval_result = await self.request_checkpoint(
                checkpoint_type=CheckpointType.DRAFT_REVIEW,
                title=f"Content Draft Review - {content_type}",
                description="Please review the content draft for quality, brand alignment, and accuracy",
                content=f"""
                GENERATED CONTENT:
                {content_result}

                OUTLINE FOLLOWED:
                {outline[:500]}{'...' if len(outline) > 500 else ''}

                BRAND VOICE APPLIED:
                {style_analysis[:300]}{'...' if len(style_analysis) > 300 else ''}
                                """,
                priority=Priority.HIGH
            )
        
        return {
            'content': content_result,
            'knowledge_used': relevant_knowledge,
            'approval': approval_result,
            'enhanced': True
        }