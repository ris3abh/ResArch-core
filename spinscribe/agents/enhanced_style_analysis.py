"""
Enhanced Style Analysis Agent with RAG and checkpoint integration.
Replaces the existing style_analysis.py with enhanced functionality.
"""

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.messages import BaseMessage

from spinscribe.memory.memory_setup import get_memory
from spinscribe.knowledge.integration import search_client_knowledge, get_brand_voice_analysis
from spinscribe.checkpoints.enhanced_agents import CheckpointEnabledAgent
from spinscribe.checkpoints.checkpoint_manager import CheckpointType, Priority
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

import logging
import asyncio

logger = logging.getLogger(__name__)

class EnhancedStyleAnalysisAgent(CheckpointEnabledAgent, ChatAgent):
    """
    Enhanced Style Analysis Agent with RAG knowledge retrieval and human checkpoints.
    """
    
    def __init__(self, project_id: str = None):
        model = ModelFactory.create(
            model_platform=MODEL_PLATFORM,
            model_type=MODEL_TYPE,
            model_config_dict=MODEL_CONFIG,
        )
        
        sys_msg = (
            "You are an Enhanced Style Analysis Agent specialized in brand voice extraction. "
            "Your responsibilities:\n"
            "1. Analyze client materials and extract brand voice patterns using RAG knowledge\n"
            "2. Search existing client knowledge base for previous style analyses\n"
            "3. Identify tone, key vocabulary, and linguistic markers\n"
            "4. Perform detailed stylometry analysis on sample content\n"
            "5. Generate language codes that define the client's unique style\n"
            "6. Create brand voice consistency guidelines\n"
            "7. Request human approval for style analysis when needed\n\n"
            "Enhanced capabilities:\n"
            "- Access to client knowledge base for context\n"
            "- Integration with human review checkpoints\n"
            "- Continuous learning from approved analyses\n"
            "- Cross-reference with previous client work\n\n"
            "When analyzing content:\n"
            "- Search knowledge base for relevant brand information\n"
            "- Look for consistent linguistic patterns across documents\n"
            "- Compare with previous successful analyses\n"
            "- Request human verification for critical decisions\n"
            "- Generate comprehensive style guidelines"
        )
        
        super().__init__(system_message=sys_msg, model=model)
        self.memory = get_memory()
        self.project_id = project_id
    
    async def analyze_style_with_knowledge(self, content: str, request_approval: bool = True) -> dict:
        """
        Analyze style using RAG knowledge and optional human checkpoint.
        
        Args:
            content: Content to analyze
            request_approval: Whether to request human approval
            
        Returns:
            Dict with analysis results and approval status
        """
        logger.info("🔍 Starting enhanced style analysis with RAG")
        
        # Step 1: Search for existing brand knowledge
        existing_knowledge = ""
        if self.project_id:
            existing_knowledge = await get_brand_voice_analysis(self.project_id)
            logger.info(f"Retrieved {len(existing_knowledge)} chars of existing brand knowledge")
        
        # Step 2: Perform style analysis with RAG context
        enhanced_prompt = f"""
        TASK: Analyze the brand voice and style patterns in the provided content.
        
        EXISTING BRAND KNOWLEDGE:
        {existing_knowledge}
        
        CONTENT TO ANALYZE:
        {content}
        
        INSTRUCTIONS:
        1. Compare the new content with existing brand knowledge
        2. Identify consistent patterns and any deviations
        3. Extract specific linguistic markers and vocabulary
        4. Analyze tone, formality level, and voice characteristics
        5. Generate language codes for content generation
        6. Create actionable style guidelines
        
        Provide a comprehensive analysis that builds upon existing knowledge.
        """
        
        analysis_message = BaseMessage.make_assistant_message(
            role_name="Enhanced Style Analyst",
            content=enhanced_prompt
        )
        
        response = self.step(analysis_message)
        analysis_result = response.msg.content
        
        logger.info("✅ Style analysis completed")
        
        # Step 3: Request human approval if enabled
        approval_result = {'approved': True, 'skipped': True}
        
        if request_approval and self.checkpoint_integration:
            logger.info("🛑 Requesting human approval for style analysis")
            
            approval_result = await self.request_checkpoint(
                checkpoint_type=CheckpointType.STYLE_GUIDE_APPROVAL,
                title="Brand Voice Analysis Review",
                description="Please review the brand voice analysis for accuracy and completeness",
                content=f"""
                STYLE ANALYSIS RESULTS:
                {analysis_result}

                ORIGINAL CONTENT ANALYZED:
                {content[:1000]}{'...' if len(content) > 1000 else ''}

                EXISTING BRAND KNOWLEDGE REFERENCED:
                {existing_knowledge[:500]}{'...' if len(existing_knowledge) > 500 else ''}
                                """,
                priority=Priority.HIGH
            )
        
        return {
            'analysis': analysis_result,
            'existing_knowledge': existing_knowledge,
            'approval': approval_result,
            'enhanced': True
        }