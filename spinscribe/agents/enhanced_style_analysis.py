# File: spinscribe/agents/enhanced_style_analysis.py (UPDATED)
"""
Enhanced Style Analysis Agent with synchronous execution.
Removes async blocking that causes workforce to hang.
"""

import logging
from typing import Dict, Any, Optional
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.messages import BaseMessage
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

logger = logging.getLogger(__name__)

class EnhancedStyleAnalysisAgent(ChatAgent):
    """
    Enhanced Style Analysis Agent that works synchronously with CAMEL Workforce.
    Removes async operations that cause blocking.
    """
    
    def __init__(self, project_id: str):
        # Create model and memory
        model = ModelFactory.create(
            model_platform=MODEL_PLATFORM,
            model_type=MODEL_TYPE,
            model_config_dict=MODEL_CONFIG,
        )
        
        # Enhanced system message
        system_message = BaseMessage.make_assistant_message(
            role_name="Enhanced Style Analysis Agent",
            content=(
                "You are an expert brand voice analyst specializing in extracting "
                "and codifying writing styles from client materials.\n\n"
                "Your responsibilities:\n"
                "1. Analyze provided client materials to extract brand voice patterns\n"
                "2. Identify tone, key vocabulary, and linguistic markers\n"
                "3. Generate style guidelines and language codes\n"
                "4. Create brand voice consistency recommendations\n"
                "5. Provide actionable style analysis for content creation\n\n"
                "Work efficiently and provide detailed analysis without requiring "
                "external approvals or additional resources."
            )
        )
        
        # Initialize ChatAgent
        super().__init__(
            system_message=system_message,
            model=model,
            memory=get_memory()
        )
        
        self.project_id = project_id
        self.checkpoint_integration = None
        
        logger.info(f"✅ Enhanced Style Analysis Agent initialized for project: {project_id}")
    
    def set_checkpoint_integration(self, integration, project_id: str):
        """
        Set checkpoint integration (kept for compatibility).
        In sync mode, this is a no-op.
        """
        self.checkpoint_integration = integration
        logger.info(f"📝 Checkpoint integration set for {project_id} (sync mode)")
    
    def analyze_style(self, content: str) -> Dict[str, Any]:
        """
        Analyze style synchronously without blocking operations.
        """
        try:
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze the following content and extract the brand voice patterns:
            
            Content:
            {content}
            
            Please provide:
            1. Tone analysis (professional, casual, technical, etc.)
            2. Key vocabulary and phrases
            3. Sentence structure patterns
            4. Voice characteristics
            5. Style guidelines for consistency
            
            Format your response as a structured analysis.
            """
            
            logger.info(f"🔍 Analyzing style for project: {self.project_id}")
            
            # Get response synchronously
            response = self.step(analysis_prompt)
            
            # Extract content from response
            if hasattr(response, 'msgs') and response.msgs:
                analysis_result = response.msgs[0].content
            else:
                analysis_result = str(response)
            
            logger.info(f"✅ Style analysis completed for project: {self.project_id}")
            
            return {
                'analysis': analysis_result,
                'project_id': self.project_id,
                'status': 'completed',
                'approved': True  # Auto-approve in sync mode
            }
            
        except Exception as e:
            logger.error(f"❌ Style analysis failed for project {self.project_id}: {e}")
            return {
                'analysis': f"Error during style analysis: {str(e)}",
                'project_id': self.project_id,
                'status': 'failed',
                'approved': False
            }

# Keep the same pattern for other enhanced agents
class EnhancedContentPlanningAgent(ChatAgent):
    """Enhanced Content Planning Agent - Synchronous Version"""
    
    def __init__(self, project_id: str):
        model = ModelFactory.create(
            model_platform=MODEL_PLATFORM,
            model_type=MODEL_TYPE,
            model_config_dict=MODEL_CONFIG,
        )
        
        system_message = BaseMessage.make_assistant_message(
            role_name="Enhanced Content Planning Agent",
            content=(
                "You are an expert content strategist specializing in creating "
                "structured content outlines and strategic frameworks.\n\n"
                "Your responsibilities:\n"
                "1. Create detailed content outlines based on requirements\n"
                "2. Develop strategic content frameworks\n"
                "3. Ensure content aligns with brand voice and objectives\n"
                "4. Provide clear structure for content generation\n"
                "5. Consider audience needs and content goals\n\n"
                "Work efficiently and provide comprehensive planning without "
                "requiring external approvals."
            )
        )
        
        super().__init__(
            system_message=system_message,
            model=model,
            memory=get_memory()
        )
        
        self.project_id = project_id
        self.checkpoint_integration = None
        
        logger.info(f"✅ Enhanced Content Planning Agent initialized for project: {project_id}")
    
    def set_checkpoint_integration(self, integration, project_id: str):
        """Set checkpoint integration (sync mode no-op)"""
        self.checkpoint_integration = integration
        logger.info(f"📝 Checkpoint integration set for {project_id} (sync mode)")
    
    def create_content_plan(self, requirements: str, style_guide: str = "") -> Dict[str, Any]:
        """Create content plan synchronously"""
        try:
            planning_prompt = f"""
            Create a comprehensive content plan based on these requirements:
            
            Requirements:
            {requirements}
            
            Style Guide:
            {style_guide}
            
            Please provide:
            1. Content outline with main sections
            2. Key points for each section
            3. Tone and style recommendations
            4. Target audience considerations
            5. Content goals and objectives
            
            Format as a structured content plan.
            """
            
            logger.info(f"📋 Creating content plan for project: {self.project_id}")
            
            response = self.step(planning_prompt)
            
            if hasattr(response, 'msgs') and response.msgs:
                plan_result = response.msgs[0].content
            else:
                plan_result = str(response)
            
            logger.info(f"✅ Content plan completed for project: {self.project_id}")
            
            return {
                'plan': plan_result,
                'project_id': self.project_id,
                'status': 'completed',
                'approved': True
            }
            
        except Exception as e:
            logger.error(f"❌ Content planning failed for project {self.project_id}: {e}")
            return {
                'plan': f"Error during content planning: {str(e)}",
                'project_id': self.project_id,
                'status': 'failed',
                'approved': False
            }

class EnhancedContentGenerationAgent(ChatAgent):
    """Enhanced Content Generation Agent - Synchronous Version"""
    
    def __init__(self, project_id: str):
        model = ModelFactory.create(
            model_platform=MODEL_PLATFORM,
            model_type=MODEL_TYPE,
            model_config_dict=MODEL_CONFIG,
        )
        
        system_message = BaseMessage.make_assistant_message(
            role_name="Enhanced Content Generation Agent",
            content=(
                "You are an expert content creator specializing in generating "
                "high-quality, brand-consistent content.\n\n"
                "Your responsibilities:\n"
                "1. Generate content based on approved outlines\n"
                "2. Apply brand voice and style guidelines consistently\n"
                "3. Create engaging, well-structured content\n"
                "4. Ensure content meets quality standards\n"
                "5. Adapt content for target audience\n\n"
                "Work efficiently and produce high-quality content without "
                "requiring external approvals during generation."
            )
        )
        
        super().__init__(
            system_message=system_message,
            model=model,
            memory=get_memory()
        )
        
        self.project_id = project_id
        self.checkpoint_integration = None
        
        logger.info(f"✅ Enhanced Content Generation Agent initialized for project: {project_id}")
    
    def set_checkpoint_integration(self, integration, project_id: str):
        """Set checkpoint integration (sync mode no-op)"""
        self.checkpoint_integration = integration
        logger.info(f"📝 Checkpoint integration set for {project_id} (sync mode)")
    
    def generate_content(self, outline: str, style_guide: str = "", requirements: str = "") -> Dict[str, Any]:
        """Generate content synchronously"""
        try:
            generation_prompt = f"""
            Generate high-quality content based on this outline and style guide:
            
            Content Outline:
            {outline}
            
            Style Guide:
            {style_guide}
            
            Additional Requirements:
            {requirements}
            
            Please create:
            1. Complete content following the outline structure
            2. Consistent brand voice throughout
            3. Engaging and well-written text
            4. Proper formatting and flow
            5. Content that meets the specified requirements
            
            Generate the final content ready for review.
            """
            
            logger.info(f"✍️ Generating content for project: {self.project_id}")
            
            response = self.step(generation_prompt)
            
            if hasattr(response, 'msgs') and response.msgs:
                content_result = response.msgs[0].content
            else:
                content_result = str(response)
            
            logger.info(f"✅ Content generation completed for project: {self.project_id}")
            
            return {
                'content': content_result,
                'project_id': self.project_id,
                'status': 'completed',
                'approved': True
            }
            
        except Exception as e:
            logger.error(f"❌ Content generation failed for project {self.project_id}: {e}")
            return {
                'content': f"Error during content generation: {str(e)}",
                'project_id': self.project_id,
                'status': 'failed',
                'approved': False
            }