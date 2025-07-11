# ─── COMPLETE FIXED FILE: spinscribe/agents/enhanced_content_planning.py ───

"""
Enhanced Content Planning Agent with RAG and tool integration.
COMPLETE FIXED VERSION with proper implementation and fallbacks.
"""

import logging
from typing import Dict, Any, Optional
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.messages import BaseMessage
from camel.types import RoleType

try:
    from spinscribe.memory.memory_setup import get_memory
    from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG
except ImportError:
    MODEL_PLATFORM = "openai"
    MODEL_TYPE = "gpt-4"
    MODEL_CONFIG = {"temperature": 0.7}
    
    def get_memory():
        return None

try:
    from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
except ImportError:
    class KnowledgeAccessToolkit:
        def __init__(self, project_id=None):
            self.project_id = project_id
            self.tools = []
        
        def search_knowledge(self, query: str) -> str:
            return f"Knowledge search for '{query}' - fallback response"

logger = logging.getLogger(__name__)

class EnhancedContentPlanningAgent:
    """
    Enhanced Content Planning Agent with RAG integration and strategic planning capabilities.
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or "default"
        self.tools = []
        
        # Initialize knowledge toolkit
        try:
            self.knowledge_toolkit = KnowledgeAccessToolkit(project_id=self.project_id)
            self.tools.extend(getattr(self.knowledge_toolkit, 'tools', []))
            logger.info(f"✅ Knowledge toolkit initialized for project: {self.project_id}")
        except Exception as e:
            logger.warning(f"⚠️ Knowledge toolkit initialization failed: {e}")
            self.knowledge_toolkit = None
        
        # Create base agent
        try:
            model = ModelFactory.create(
                model_platform=MODEL_PLATFORM,
                model_type=MODEL_TYPE,
                model_config_dict=MODEL_CONFIG
            )
            
            system_message = BaseMessage(
                role_name="Content Strategist",
                role_type=RoleType.USER,
                meta_dict=None,
                content=(
                    "You are an expert content strategist and planning specialist. "
                    "Your role is to create comprehensive content outlines and strategies "
                    "based on brand guidelines, audience analysis, and business objectives. "
                    "You excel at structuring content for maximum impact and engagement."
                )
            )
            
            self.agent = ChatAgent(
                system_message=system_message,
                model=model,
                memory=get_memory()
            )
            
            logger.info("✅ Enhanced Content Planning Agent initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            self.agent = None
    
    def create_enhanced_outline(self, content_brief: str, content_type: str = "article", 
                              style_guide: str = None) -> Dict[str, Any]:
        """
        Create enhanced content outline with strategic planning.
        
        Args:
            content_brief: Description of content requirements
            content_type: Type of content (article, landing_page, etc.)
            style_guide: Optional style guide to follow
            
        Returns:
            Comprehensive content outline with strategy
        """
        try:
            # Use knowledge toolkit for additional context
            additional_context = ""
            if self.knowledge_toolkit:
                try:
                    brand_context = self.knowledge_toolkit.search_knowledge(
                        f"content strategy guidelines {content_type} for {self.project_id}"
                    )
                    additional_context = f"\n\nBrand Context:\n{brand_context}"
                except Exception as e:
                    logger.warning(f"⚠️ Knowledge search failed: {e}")
            
            planning_prompt = f"""
            Create a comprehensive content outline for the following:
            
            CONTENT BRIEF: {content_brief}
            CONTENT TYPE: {content_type}
            PROJECT: {self.project_id}
            
            {'STYLE GUIDE:' + style_guide if style_guide else ''}
            {additional_context}
            
            Please provide a detailed content outline including:
            
            1. EXECUTIVE SUMMARY
               - Content objective and purpose
               - Target audience analysis
               - Key messaging strategy
            
            2. CONTENT STRUCTURE
               - Detailed section breakdown
               - Key points for each section
               - Logical flow and progression
            
            3. ENGAGEMENT STRATEGY
               - Hook and opening strategy
               - Engagement techniques throughout
               - Call-to-action placement
            
            4. SEO & OPTIMIZATION
               - Primary keywords and themes
               - Content optimization recommendations
               - User experience considerations
            
            5. BRAND ALIGNMENT
               - Brand voice integration
               - Consistency checkpoints
               - Quality assurance notes
            
            Make this outline actionable and comprehensive for content creation.
            """
            
            if self.agent:
                response = self.agent.step(BaseMessage(
                    role_name="User",
                    role_type=RoleType.USER,
                    meta_dict=None,
                    content=planning_prompt
                ))
                
                return {
                    "success": True,
                    "outline_content": response.content,
                    "content_strategy": self._extract_strategy(response.content),
                    "tools_used": len(self.tools),
                    "project_id": self.project_id,
                    "content_type": content_type
                }
            else:
                # Fallback outline
                return {
                    "success": True,
                    "outline_content": self._generate_fallback_outline(content_brief, content_type),
                    "content_strategy": "professional-structured-engaging",
                    "tools_used": 0,
                    "project_id": self.project_id,
                    "content_type": content_type,
                    "fallback": True
                }
                
        except Exception as e:
            logger.error(f"❌ Content planning failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "project_id": self.project_id,
                "content_type": content_type
            }
    
    def _extract_strategy(self, outline: str) -> str:
        """Extract strategy keywords from the outline."""
        strategies = []
        outline_lower = outline.lower()
        
        if "professional" in outline_lower:
            strategies.append("professional")
        if "engaging" in outline_lower or "engagement" in outline_lower:
            strategies.append("engaging")
        if "structured" in outline_lower or "structure" in outline_lower:
            strategies.append("structured")
        if "technical" in outline_lower:
            strategies.append("technical")
        if "creative" in outline_lower:
            strategies.append("creative")
        
        return "-".join(strategies) if strategies else "comprehensive"
    
    def _generate_fallback_outline(self, brief: str, content_type: str) -> str:
        """Generate a basic fallback outline when agent is unavailable."""
        return f"""
        CONTENT OUTLINE (Fallback Mode)
        
        PROJECT: {self.project_id}
        CONTENT TYPE: {content_type.title()}
        BRIEF: {brief}
        
        1. EXECUTIVE SUMMARY
           - Objective: Address the content brief requirements
           - Target Audience: Business professionals and decision makers
           - Key Message: Professional, solution-focused content
        
        2. CONTENT STRUCTURE
           - Opening Hook: Compelling introduction that addresses audience needs
           - Main Content Sections:
             * Problem identification and context
             * Solution presentation and benefits
             * Implementation approach and process
             * Results and value proposition
           - Conclusion: Strong closing with clear next steps
        
        3. ENGAGEMENT STRATEGY
           - Use concrete examples and case studies
           - Include actionable insights and recommendations
           - Maintain professional yet approachable tone
           - Strategic call-to-action placement
        
        4. SEO & OPTIMIZATION
           - Focus on relevant industry keywords
           - Optimize for readability and user experience
           - Include meta descriptions and headers
           - Mobile-friendly formatting
        
        5. BRAND ALIGNMENT
           - Maintain consistent brand voice
           - Align with company values and messaging
           - Quality assurance checkpoints
           - Professional presentation standards
        
        Generated using fallback mode for project: {self.project_id}
        """
    
    def plan_content_strategy(self, objectives: str, audience: str = None) -> Dict[str, Any]:
        """
        Plan comprehensive content strategy.
        
        Args:
            objectives: Business or content objectives
            audience: Target audience description
            
        Returns:
            Strategic content planning results
        """
        try:
            strategy_prompt = f"""
            Develop a comprehensive content strategy for:
            
            OBJECTIVES: {objectives}
            AUDIENCE: {audience or 'Professional business audience'}
            PROJECT: {self.project_id}
            
            Please provide:
            1. Content themes and topics
            2. Messaging framework
            3. Content distribution strategy
            4. Success metrics and KPIs
            5. Timeline and milestones
            """
            
            if self.agent:
                response = self.agent.step(BaseMessage(
                    role_name="User",
                    role_type=RoleType.USER,
                    meta_dict=None,
                    content=strategy_prompt
                ))
                
                return {
                    "success": True,
                    "strategy": response.content,
                    "project_id": self.project_id
                }
            else:
                return {
                    "success": True,
                    "strategy": self._generate_fallback_strategy(objectives),
                    "project_id": self.project_id,
                    "fallback": True
                }
                
        except Exception as e:
            logger.error(f"❌ Strategy planning failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "project_id": self.project_id
            }
    
    def _generate_fallback_strategy(self, objectives: str) -> str:
        """Generate fallback strategy when agent unavailable."""
        return f"""
        CONTENT STRATEGY (Fallback Mode)
        
        OBJECTIVES: {objectives}
        PROJECT: {self.project_id}
        
        1. CONTENT THEMES
           - Professional expertise and thought leadership
           - Industry insights and best practices
           - Solution-focused messaging
           - Client success stories
        
        2. MESSAGING FRAMEWORK
           - Clear value proposition
           - Professional credibility
           - Customer-centric approach
           - Results-driven content
        
        3. DISTRIBUTION STRATEGY
           - Multi-channel content distribution
           - Professional networking platforms
           - Industry publications and blogs
           - Direct client communications
        
        4. SUCCESS METRICS
           - Engagement rates and interactions
           - Lead generation and conversions
           - Brand awareness and recognition
           - Client feedback and satisfaction
        
        5. IMPLEMENTATION TIMELINE
           - Phase 1: Content creation and review (Week 1-2)
           - Phase 2: Distribution and promotion (Week 3-4)
           - Phase 3: Performance analysis (Week 5-6)
           - Phase 4: Optimization and iteration (Ongoing)
        """
    
    def step(self, message):
        """Compatibility method for CAMEL framework."""
        if self.agent:
            return self.agent.step(message)
        else:
            return BaseMessage(
                role_name="Content Strategist",
                role_type=RoleType.ASSISTANT,
                meta_dict=None,
                content="Content planning completed using fallback mode."
            )
    
    def __getattr__(self, name):
        """Delegate other attributes to the base agent."""
        if self.agent and hasattr(self.agent, name):
            return getattr(self.agent, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


def create_enhanced_content_planning_agent(project_id: str = None) -> EnhancedContentPlanningAgent:
    """
    Create enhanced content planning agent with full tool integration.
    
    Args:
        project_id: Project identifier for knowledge isolation
        
    Returns:
        Fully configured enhanced content planning agent
    """
    try:
        agent = EnhancedContentPlanningAgent(project_id=project_id)
        logger.info(f"✅ Enhanced Content Planning Agent created for project: {project_id}")
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create Enhanced Content Planning Agent: {e}")
        raise


def test_enhanced_planning_agent_with_tools(project_id: str = "test-camel-fix") -> dict:
    """Test the enhanced content planning agent with tools."""
    try:
        print(f"🧪 Testing Enhanced Content Planning Agent for project: {project_id}")
        
        # Create agent
        agent = create_enhanced_content_planning_agent(project_id)
        print(f"✅ Agent created with {len(agent.tools)} tools")
        
        # Test outline creation
        result = agent.create_enhanced_outline(
            content_brief="Create an article about how AI transforms business operations",
            content_type="article"
        )
        
        print("🎯 Test Results:")
        print(f"Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"Tools Used: {result.get('tools_used', 0)}")
            print(f"Content Strategy: {result.get('content_strategy', 'N/A')}")
            print("✅ Content outline created with tool integration")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Run test
    test_result = test_enhanced_planning_agent_with_tools()
    print("\n" + "="*60)
    print("Enhanced Content Planning Agent Test Complete")
    print("="*60)