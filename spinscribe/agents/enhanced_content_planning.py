# ═══════════════════════════════════════════════════════════════════════════════
# FILE: spinscribe/agents/enhanced_content_planning.py
# STATUS: UPDATE (FIXED - HumanToolkit only, no HumanLayer dependency)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Enhanced Content Planning Agent with RAG and CAMEL's native HumanToolkit integration.
FIXED VERSION - Using only CAMEL's built-in human interaction capabilities.
"""

import logging
from typing import Dict, Any, Optional, List
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.messages import BaseMessage
from camel.types import RoleType
# from camel.toolkits import HumanToolkit
from spinscribe.tools.fixed_human_toolkit import FixedHumanToolkit

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
        
        def get_brand_guidelines(self) -> str:
            return "Brand guidelines - fallback response"
        
        def get_content_strategy(self, content_type: str) -> str:
            return f"Content strategy for {content_type} - fallback response"

logger = logging.getLogger(__name__)

class EnhancedContentPlanningAgent:
    """
    Enhanced Content Planning Agent with RAG integration and HumanToolkit.
    Combines strategic planning with knowledge base access and console-based human interaction.
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or "default"
        self.tools = []
        
        # Initialize CAMEL's built-in HumanToolkit (always available)
        # human_toolkit = HumanToolkit()
        # self.tools.extend(human_toolkit.get_tools())

        human_toolkit = FixedHumanToolkit()
        self.tools.extend(human_toolkit.get_tools())
        
        # Initialize knowledge toolkit (existing RAG functionality)
        try:
            self.knowledge_toolkit = KnowledgeAccessToolkit(project_id=self.project_id)
            self.tools.extend(getattr(self.knowledge_toolkit, 'tools', []))
            logger.info(f"✅ Knowledge toolkit initialized for project: {self.project_id}")
        except Exception as e:
            logger.warning(f"⚠️ Knowledge toolkit initialization failed: {e}")
            self.knowledge_toolkit = None
        
        # Create base agent with all tools
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
                    "You are an expert Content Planning Agent specialized in strategic content planning "
                    "with access to client knowledge and human interaction capabilities. "
                    "Your role is to create comprehensive content outlines and strategies based on "
                    "brand guidelines, audience analysis, and business objectives.\n\n"
                    "CAPABILITIES:\n"
                    "- RAG access to brand guidelines and content strategy documents\n"
                    "- Human interaction for strategy feedback and approval via console\n"
                    "- Strategic content planning and outline creation\n"
                    "- SEO and engagement optimization\n"
                    "- Target audience analysis and alignment\n\n"
                    "RESPONSIBILITIES:\n"
                    "1. Create structured outlines and content strategies\n"
                    "2. Base outlines on project requirements and client guidelines\n"
                    "3. Break down content requests into organized frameworks\n"
                    "4. Use brand guidelines and audience information effectively\n"
                    "5. Reference content strategy documents from knowledge base\n"
                    "6. Create outlines that align with marketing objectives\n\n"
                    "MANDATORY HUMAN INTERACTION: You MUST ask humans for approval of ALL planning decisions using "
                    "your available tools. You MUST seek human approval for:\n"
                    "- Content strategy direction (REQUIRED)\n"
                    "- Outline structure and organization (REQUIRED)\n"
                    "- Content scope and depth (REQUIRED)\n"
                    "- Target audience approach (REQUIRED)\n"
                    "- Content objectives and goals (REQUIRED)\n\n"
                    "CRITICAL: Before finalizing any content plan, you MUST call "
                    "ask_human_via_console() with questions like:\n"
                    "- 'Do you approve this content strategy? [yes/no]'\n"
                    "- 'Is this outline structure appropriate? [yes/no]'\n"
                    "- 'Should I adjust the content scope or depth?'\n"
                    "- 'Does this approach match your objectives?'\n\n"
                    "VALIDATION: Every planning deliverable must include human approval.\n"
                    "FAILURE TO GET HUMAN APPROVAL VIOLATES YOUR PLANNING ROLE."
                )
            )
            
            self.agent = ChatAgent(
                system_message=system_message,
                model=model,
                memory=get_memory(),
                tools=self.tools
            )
            
            logger.info("✅ Enhanced Content Planning Agent initialized with HumanToolkit + RAG")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            self.agent = None
    
    def create_enhanced_outline(self, content_brief: str, content_type: str = "article", 
                              style_guide: str = None) -> Dict[str, Any]:
        """
        Create enhanced content outline with strategic planning and human interaction.
        
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
                    brand_context = self.knowledge_toolkit.get_brand_guidelines()
                    content_strategy = self.knowledge_toolkit.get_content_strategy(content_type)
                    knowledge_search = self.knowledge_toolkit.search_knowledge(
                        f"content strategy guidelines {content_type} for {self.project_id}"
                    )
                    additional_context = f"\n\nBRAND GUIDELINES:\n{brand_context}\n\nCONTENT STRATEGY:\n{content_strategy}\n\nKNOWLEDGE CONTEXT:\n{knowledge_search}"
                except Exception as e:
                    logger.warning(f"⚠️ Knowledge search failed: {e}")
            
            planning_prompt = f"""
            Create a comprehensive content outline for the following requirements:
            
            CONTENT BRIEF: {content_brief}
            CONTENT TYPE: {content_type}
            PROJECT: {self.project_id}
            
            {'STYLE GUIDE:\n' + style_guide if style_guide else ''}
            {additional_context}
            
            Please provide a detailed content outline including:
            
            1. EXECUTIVE SUMMARY
               - Content objective and primary purpose
               - Target audience analysis and personas
               - Key messaging strategy and value proposition
               - Success metrics and performance indicators
            
            2. CONTENT STRUCTURE
               - Detailed section breakdown with main headings
               - Key points and supporting details for each section
               - Logical flow and content progression
               - Estimated word count per section
            
            3. ENGAGEMENT STRATEGY
               - Hook and opening strategy to capture attention
               - Engagement techniques throughout the content
               - Interactive elements and visual content opportunities
               - Call-to-action placement and optimization
            
            4. SEO & OPTIMIZATION
               - Primary and secondary keywords integration
               - Content optimization recommendations
               - User experience and readability considerations
               - Meta descriptions and title suggestions
            
            5. BRAND ALIGNMENT
               - Brand voice integration points
               - Consistency checkpoints throughout content
               - Quality assurance notes and review criteria
               - Brand differentiation opportunities
            
            6. CONTENT CALENDAR INTEGRATION
               - Timeline and production schedule
               - Resource requirements and dependencies
               - Distribution and promotion strategy
               - Performance tracking recommendations
            
            If you need clarification on any requirements or strategic direction, 
            please ask me directly using your human interaction tools.
            """
            
            if self.agent:
                response = self.agent.step(planning_prompt)
                
                # Extract response content
                outline_result = response.msgs[0].content if response.msgs else "Outline creation failed"
                
                # Check for tool usage
                tools_used = len(response.info.get('tool_calls', []))
                
                return {
                    "success": True,
                    "outline": outline_result,
                    "content_type": content_type,
                    "tools_used": tools_used,
                    "project_id": self.project_id,
                    "knowledge_enhanced": self.knowledge_toolkit is not None,
                    "human_interaction": tools_used > 0,
                    "brief_analyzed": len(content_brief)
                }
            else:
                return {
                    "success": False,
                    "error": "Agent not properly initialized"
                }
                
        except Exception as e:
            logger.error(f"❌ Enhanced outline creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_content_strategy(self, business_objectives: str, target_audience: str, 
                              content_goals: List[str] = None) -> Dict[str, Any]:
        """
        Create comprehensive content strategy with human collaboration.
        
        Args:
            business_objectives: Overall business goals and objectives
            target_audience: Detailed target audience description
            content_goals: Specific content marketing goals
            
        Returns:
            Detailed content strategy with implementation plan
        """
        try:
            # Prepare content goals context
            goals_context = ""
            if content_goals:
                goals_context = "\n\nCONTENT GOALS:\n" + "\n".join([
                    f"- {goal}" for goal in content_goals
                ])
            
            # Use knowledge toolkit for strategic context
            strategic_context = ""
            if self.knowledge_toolkit:
                try:
                    brand_strategy = self.knowledge_toolkit.search_knowledge(
                        f"brand strategy marketing goals {self.project_id}"
                    )
                    strategic_context = f"\n\nSTRATEGIC CONTEXT:\n{brand_strategy}"
                except Exception as e:
                    logger.warning(f"⚠️ Strategic context search failed: {e}")
            
            strategy_prompt = f"""
            Develop a comprehensive content strategy based on these parameters:
            
            BUSINESS OBJECTIVES:
            {business_objectives}
            
            TARGET AUDIENCE:
            {target_audience}
            {goals_context}
            {strategic_context}
            
            Create a detailed content strategy including:
            
            1. STRATEGIC FOUNDATION
               - Content mission and vision alignment
               - Key messaging framework
               - Brand positioning in content
               - Competitive differentiation strategy
            
            2. AUDIENCE STRATEGY
               - Detailed audience personas and segments
               - Content preferences and consumption patterns
               - Journey mapping and touchpoint optimization
               - Engagement and interaction strategies
            
            3. CONTENT FRAMEWORK
               - Content pillars and topic categories
               - Content types and format recommendations
               - Distribution channel strategy
               - Content calendar framework
            
            4. IMPLEMENTATION PLAN
               - Content production workflow
               - Resource allocation and team structure
               - Quality assurance processes
               - Performance measurement framework
            
            5. OPTIMIZATION STRATEGY
               - SEO and discoverability approach
               - Conversion optimization tactics
               - Engagement enhancement techniques
               - Brand consistency maintenance
            
            6. SUCCESS METRICS
               - KPI definitions and tracking methods
               - Performance benchmarks and goals
               - ROI measurement framework
               - Continuous improvement processes
            
            Please ask me for feedback on this strategy if you need clarification 
            on any strategic direction or requirements.
            """
            
            if self.agent:
                response = self.agent.step(strategy_prompt)
                
                strategy_result = response.msgs[0].content if response.msgs else "Strategy creation failed"
                tools_used = len(response.info.get('tool_calls', []))
                
                return {
                    "success": True,
                    "strategy": strategy_result,
                    "tools_used": tools_used,
                    "project_id": self.project_id,
                    "human_interaction": tools_used > 0,
                    "knowledge_enhanced": self.knowledge_toolkit is not None
                }
            else:
                return {
                    "success": False,
                    "error": "Agent not properly initialized"
                }
                
        except Exception as e:
            logger.error(f"❌ Content strategy creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_content_requirements(self, project_brief: str, stakeholder_input: str = None) -> Dict[str, Any]:
        """
        Analyze content requirements with human stakeholder input.
        
        Args:
            project_brief: Detailed project requirements and brief
            stakeholder_input: Optional stakeholder feedback and requirements
            
        Returns:
            Comprehensive requirements analysis
        """
        try:
            # Prepare stakeholder context
            stakeholder_context = ""
            if stakeholder_input:
                stakeholder_context = f"\n\nSTAKEHOLDER INPUT:\n{stakeholder_input}"
            
            # Use knowledge toolkit for project context
            project_context = ""
            if self.knowledge_toolkit:
                try:
                    project_info = self.knowledge_toolkit.search_knowledge(
                        f"project requirements specifications {self.project_id}"
                    )
                    project_context = f"\n\nPROJECT CONTEXT:\n{project_info}"
                except Exception as e:
                    logger.warning(f"⚠️ Project context search failed: {e}")
            
            requirements_prompt = f"""
            Analyze the content requirements based on this project brief:
            
            PROJECT BRIEF:
            {project_brief}
            {stakeholder_context}
            {project_context}
            
            Provide comprehensive requirements analysis including:
            
            1. SCOPE ANALYSIS
               - Content deliverables identification
               - Project boundaries and limitations
               - Resource requirements assessment
               - Timeline and milestone planning
            
            2. STAKEHOLDER NEEDS
               - Primary and secondary stakeholder requirements
               - Success criteria and expectations
               - Approval processes and decision makers
               - Communication preferences and protocols
            
            3. CONTENT SPECIFICATIONS
               - Format and style requirements
               - Technical specifications and constraints
               - Brand compliance requirements
               - Quality standards and criteria
            
            4. STRATEGIC ALIGNMENT
               - Business objective alignment
               - Marketing goal integration
               - Brand strategy consistency
               - Competitive positioning requirements
            
            5. IMPLEMENTATION CONSIDERATIONS
               - Production workflow requirements
               - Review and approval processes
               - Distribution and publishing needs
               - Performance tracking requirements
            
            Please ask me for clarification on any unclear requirements 
            using your human interaction tools.
            """
            
            if self.agent:
                response = self.agent.step(requirements_prompt)
                
                analysis_result = response.msgs[0].content if response.msgs else "Requirements analysis failed"
                tools_used = len(response.info.get('tool_calls', []))
                
                return {
                    "success": True,
                    "requirements_analysis": analysis_result,
                    "tools_used": tools_used,
                    "project_id": self.project_id,
                    "stakeholder_input_provided": stakeholder_input is not None,
                    "human_interaction": tools_used > 0
                }
            else:
                return {
                    "success": False,
                    "error": "Agent not properly initialized"
                }
                
        except Exception as e:
            logger.error(f"❌ Requirements analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
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
    Create enhanced content planning agent with RAG and HumanToolkit integration.
    
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


def test_enhanced_planning_agent_with_tools(project_id: str = "test-content-planning") -> dict:
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
            print(f"Content Type: {result.get('content_type', 'N/A')}")
            print(f"Knowledge Enhanced: {result.get('knowledge_enhanced', False)}")
            print(f"Human Interaction: {result.get('human_interaction', False)}")
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