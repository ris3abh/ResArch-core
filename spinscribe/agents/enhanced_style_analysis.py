# ─── FILE: spinscribe/agents/enhanced_style_analysis.py ─────────
"""
Enhanced Style Analysis Agent with RAG and checkpoint integration.
REPLACES: spinscribe/agents/style_analysis.py
"""

import logging
import asyncio
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.messages import BaseMessage

from spinscribe.memory.memory_setup import get_memory
from spinscribe.knowledge.integration import search_client_knowledge, get_brand_voice_analysis
from spinscribe.checkpoints.enhanced_agents import CheckpointEnabledAgent
from spinscribe.checkpoints.checkpoint_manager import CheckpointType, Priority
from spinscribe.utils.enhanced_logging import workflow_tracker, log_execution_time
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

class EnhancedStyleAnalysisAgent(CheckpointEnabledAgent, ChatAgent):
    """
    Enhanced Style Analysis Agent with RAG knowledge and human checkpoints.
    Includes comprehensive logging and debugging.
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
        
        # Setup logging
        self.logger = logging.getLogger('agent.style_analysis')
        self.agent_name = "StyleAnalysisAgent"
        
        self.logger.info(f"🤖 Initializing {self.agent_name} for project: {project_id}")
        workflow_tracker.track_agent_activity(
            self.agent_name, 
            "initialized", 
            {"project_id": project_id}
        )
    
    async def analyze_style_with_knowledge(self, content: str, request_approval: bool = True) -> dict:
        """
        Enhanced style analysis with detailed logging and RAG integration.
        
        Args:
            content: Content to analyze
            request_approval: Whether to request human approval
            
        Returns:
            Dict with analysis results and approval status
        """
        
        self.logger.info(f"🔍 Starting enhanced style analysis")
        self.logger.info(f"📊 Content length: {len(content)} chars, Approval required: {request_approval}")
        
        workflow_tracker.track_agent_activity(
            self.agent_name,
            "style_analysis_started",
            {"content_length": len(content), "approval_required": request_approval}
        )
        
        # Step 1: RAG Knowledge Retrieval
        with log_execution_time("RAG Knowledge Retrieval", self.logger.name):
            existing_knowledge = ""
            if self.project_id:
                self.logger.info(f"🔍 Searching for existing brand knowledge in project: {self.project_id}")
                try:
                    existing_knowledge = await get_brand_voice_analysis(self.project_id)
                    self.logger.info(f"📚 Retrieved {len(existing_knowledge)} chars of brand knowledge")
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to retrieve brand knowledge: {e}")
                    existing_knowledge = ""
            else:
                self.logger.warning("⚠️ No project_id set - skipping knowledge retrieval")
        
        # Step 2: Enhanced Style Analysis
        with log_execution_time("Style Analysis Processing", self.logger.name):
            self.logger.info("🧠 Performing style analysis with RAG context")
            
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
            
            self.logger.debug(f"📝 Enhanced prompt created (length: {len(enhanced_prompt)})")
            
            analysis_message = BaseMessage.make_assistant_message(
                role_name="Enhanced Style Analyst",
                content=enhanced_prompt
            )
            
            self.logger.info("🤖 Executing style analysis with CAMEL agent")
            response = self.step(analysis_message)
            analysis_result = response.msg.content
            
            self.logger.info(f"✅ Style analysis completed (result length: {len(analysis_result)})")
            workflow_tracker.track_agent_activity(
                self.agent_name,
                "style_analysis_completed",
                {"result_length": len(analysis_result)}
            )
        
        # Step 3: Human Checkpoint Processing
        approval_result = {'approved': True, 'skipped': True}
        
        if request_approval:
            self.logger.info("✋ Checking if checkpoint integration is available")
            
            if self.checkpoint_integration:
                self.logger.info("🛑 Requesting human approval for style analysis")
                workflow_tracker.track_agent_activity(
                    self.agent_name,
                    "checkpoint_requested",
                    {"checkpoint_type": "style_guide_approval"}
                )
                
                with log_execution_time("Human Checkpoint Processing", self.logger.name):
                    try:
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
                        
                        self.logger.info(f"✅ Checkpoint response received: {approval_result}")
                        workflow_tracker.track_agent_activity(
                            self.agent_name,
                            "checkpoint_resolved",
                            {"approved": approval_result.get('approved', False)}
                        )
                        
                    except Exception as e:
                        self.logger.error(f"❌ Checkpoint request failed: {e}")
                        approval_result = {'approved': False, 'error': str(e)}
            else:
                self.logger.warning("⚠️ No checkpoint integration available - skipping human approval")
                workflow_tracker.track_agent_activity(
                    self.agent_name,
                    "checkpoint_skipped",
                    {"reason": "no_integration"}
                )
        else:
            self.logger.info("⏭️ Human approval not requested - continuing without checkpoint")
        
        # Prepare result
        result = {
            'analysis': analysis_result,
            'existing_knowledge': existing_knowledge,
            'approval': approval_result,
            'enhanced': True
        }
        
        self.logger.info("🎉 Enhanced style analysis completed successfully")
        self.logger.debug(f"📊 Final result summary: analysis={len(analysis_result)} chars, "
                         f"knowledge_used={len(existing_knowledge) > 0}, "
                         f"approved={approval_result.get('approved', 'unknown')}")
        
        return result
