# ─── UPDATE FILE: spinscribe/agents/enhanced_content_planning.py ─
"""
Enhanced Content Planning Agent with RAG and checkpoint integration.
"""

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.messages import BaseMessage

from spinscribe.memory.memory_setup import get_memory
from spinscribe.knowledge.integration import search_client_knowledge, get_style_guidelines
from spinscribe.checkpoints.enhanced_agents import CheckpointEnabledAgent
from spinscribe.checkpoints.checkpoint_manager import CheckpointType, Priority
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

import logging

logger = logging.getLogger(__name__)

class EnhancedContentPlanningAgent(CheckpointEnabledAgent, ChatAgent):
    """
    Enhanced Content Planning Agent with RAG knowledge and human checkpoints.
    """
    
    def __init__(self, project_id: str = None):
        model = ModelFactory.create(
            model_platform=MODEL_PLATFORM,
            model_type=MODEL_TYPE,
            model_config_dict=MODEL_CONFIG,
        )
        
        sys_msg = (
            "You are an Enhanced Content Planning Agent specialized in strategic outline creation. "
            "Your responsibilities:\n"
            "1. Create structured outlines using client knowledge base insights\n"
            "2. Reference existing brand guidelines and marketing strategies\n"
            "3. Ensure alignment with client's target audience and objectives\n"
            "4. Incorporate SEO requirements and content strategy documents\n"
            "5. Request human review for strategic content decisions\n"
            "6. Learn from approved outlines for future planning\n\n"
            "Enhanced capabilities:\n"
            "- Access to comprehensive client knowledge base\n"
            "- Integration with human strategy review checkpoints\n"
            "- Cross-reference with successful previous content\n"
            "- Strategic alignment with business objectives\n\n"
            "When creating outlines:\n"
            "- Search for relevant strategic documents and guidelines\n"
            "- Ensure brand voice consistency throughout structure\n"
            "- Include specific audience targeting considerations\n"
            "- Request strategic approval for complex content plans"
        )
        
        super().__init__(system_message=sys_msg, model=model)
        self.memory = get_memory()
        self.project_id = project_id
    
    async def create_enhanced_outline(
        self, 
        content_brief: str, 
        content_type: str,
        request_approval: bool = True
    ) -> dict:
        """
        Create content outline using RAG knowledge and optional human checkpoint.
        
        Args:
            content_brief: Brief describing content requirements
            content_type: Type of content (article, landing_page, etc.)
            request_approval: Whether to request human approval
            
        Returns:
            Dict with outline and approval status
        """
        logger.info(f"📋 Creating enhanced outline for {content_type}")
        
        # Step 1: Search for relevant knowledge
        relevant_knowledge = ""
        if self.project_id:
            # Get style guidelines
            style_knowledge = await get_style_guidelines(self.project_id)
            
            # Search for content strategy and examples
            strategy_knowledge = await search_client_knowledge(
                query=f"content strategy {content_type} examples",
                project_id=self.project_id,
                knowledge_types=['marketing_materials', 'sample_content', 'reference_document'],
                limit=3
            )
            
            relevant_knowledge = f"{style_knowledge}\n\n{strategy_knowledge}"
            logger.info(f"Retrieved {len(relevant_knowledge)} chars of strategic knowledge")
        
        # Step 2: Create enhanced outline with RAG context
        enhanced_prompt = f"""
        TASK: Create a detailed content outline for {content_type}.
        
        CONTENT BRIEF:
        {content_brief}
        
        RELEVANT CLIENT KNOWLEDGE:
        {relevant_knowledge}
        
        REQUIREMENTS:
        1. Structure the outline based on content type best practices
        2. Integrate brand voice and style requirements from client knowledge
        3. Include specific audience targeting from brief
        4. Ensure strategic alignment with business objectives
        5. Add SEO considerations where applicable
        6. Reference successful content patterns from knowledge base
        
        Create a comprehensive, actionable outline that maintains brand consistency.
        """
        
        outline_message = BaseMessage.make_assistant_message(
            role_name="Enhanced Content Planner",
            content=enhanced_prompt
        )
        
        response = self.step(outline_message)
        outline_result = response.msg.content
        
        logger.info("✅ Enhanced outline created")
        
        # Step 3: Request human approval if enabled
        approval_result = {'approved': True, 'skipped': True}
        
        if request_approval and self.checkpoint_integration:
            logger.info("🛑 Requesting human approval for content outline")
            
            approval_result = await self.request_checkpoint(
                checkpoint_type=CheckpointType.OUTLINE_REVIEW,
                title=f"Content Outline Review - {content_type}",
                description="Please review the content outline for strategic alignment and completeness",
                content=f"""
                CONTENT OUTLINE:
                {outline_result}

                ORIGINAL BRIEF:
                {content_brief}

                KNOWLEDGE USED:
                {relevant_knowledge[:800]}{'...' if len(relevant_knowledge) > 800 else ''}
                """,
                priority=Priority.MEDIUM
            )
        
        return {
            'outline': outline_result,
            'knowledge_used': relevant_knowledge,
            'approval': approval_result,
            'enhanced': True
        }
