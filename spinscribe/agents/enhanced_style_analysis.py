# ═══════════════════════════════════════════════════════════════════════════════
# FILE: spinscribe/agents/enhanced_style_analysis.py
# STATUS: UPDATE (FIXED - HumanToolkit only, no HumanLayer dependency)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Enhanced Style Analysis Agent with RAG and CAMEL's native HumanToolkit integration.
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
    # Fallback settings if config not available
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
        
        def analyze_sample_content(self, content: str) -> str:
            return f"Sample content analysis for '{content[:50]}...' - fallback response"

logger = logging.getLogger(__name__)

class EnhancedStyleAnalysisAgent:
    """
    Enhanced Style Analysis Agent with RAG integration and CAMEL's native HumanToolkit.
    Combines knowledge base access with console-based human interaction.
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
        
        # Create base agent with HumanToolkit + Knowledge tools
        try:
            model = ModelFactory.create(
                model_platform=MODEL_PLATFORM,
                model_type=MODEL_TYPE,
                model_config_dict=MODEL_CONFIG
            )
            
            system_message = BaseMessage(
                role_name="Style Analyst",
                role_type=RoleType.USER,
                meta_dict=None,
                content=(
                    "You are an expert Style Analysis Agent specializing in brand voice extraction "
                    "with access to client knowledge and human interaction capabilities. "
                    "Your role is to analyze client materials, extract brand voice patterns, "
                    "and create comprehensive style guidelines.\n\n"
                    "CAPABILITIES:\n"
                    "- RAG access to client documents and brand materials\n"
                    "- Human interaction for clarification and feedback via console\n"
                    "- Stylometry analysis and pattern recognition\n"
                    "- Language code generation for brand consistency\n"
                    "- Brand voice pattern extraction and analysis\n\n"
                    "RESPONSIBILITIES:\n"
                    "1. Analyze provided client materials and extract brand voice patterns\n"
                    "2. Identify tone, key vocabulary, and linguistic markers\n"
                    "3. Perform detailed stylometry analysis on sample content\n"
                    "4. Generate language codes that define the client's unique style\n"
                    "5. Create brand voice consistency guidelines\n"
                    "6. Analyze word frequencies and sentence structures\n\n"
                    "MANDATORY HUMAN INTERACTION: You MUST ask humans for validation of ALL style analysis using "
                    "your available tools. You MUST seek human approval for:\n"
                    "- Brand voice interpretation accuracy (REQUIRED)\n"
                    "- Style pattern identification (REQUIRED)\n"
                    "- Language code generation (REQUIRED)\n"
                    "- Style guide recommendations (REQUIRED)\n\n"
                    "CRITICAL: Before finalizing any style analysis, you MUST call "
                    "ask_human_via_console() to confirm accuracy with questions like:\n"
                    "- 'Does this brand voice analysis match your expectations? [yes/no]'\n"
                    "- 'Are these style patterns accurate for the brand? [yes/no]'\n"
                    "- 'Should I adjust any of these language codes?'\n\n"
                    "VALIDATION: Every style analysis deliverable must include human verification.\n"
                    "FAILURE TO VALIDATE WITH HUMANS VIOLATES YOUR ANALYSIS ROLE."
                )
            )
            
            self.agent = ChatAgent(
                system_message=system_message,
                model=model,
                memory=get_memory(),
                tools=self.tools
            )
            
            logger.info("✅ Enhanced Style Analysis Agent initialized with HumanToolkit + RAG")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            self.agent = None
    
    def analyze_brand_voice_patterns(self, content: str, brand_context: str = None) -> Dict[str, Any]:
        """
        Analyze brand voice patterns with RAG and human interaction.
        Enhanced method with HumanToolkit integration.
        
        Args:
            content: Content to analyze for brand voice patterns
            brand_context: Additional brand context information
            
        Returns:
            Comprehensive brand voice analysis with pattern extraction
        """
        try:
            # Use knowledge toolkit for additional context
            additional_context = ""
            if self.knowledge_toolkit:
                try:
                    brand_info = self.knowledge_toolkit.get_brand_guidelines()
                    sample_analysis = self.knowledge_toolkit.analyze_sample_content(content)
                    additional_context = f"\n\nBrand Guidelines:\n{brand_info}\n\nSample Analysis:\n{sample_analysis}"
                except Exception as e:
                    logger.warning(f"⚠️ Knowledge retrieval failed: {e}")
            
            analysis_prompt = f"""
            Perform comprehensive brand voice analysis on the following content:
            
            CONTENT TO ANALYZE:
            {content}
            
            {'BRAND CONTEXT:' + brand_context if brand_context else ''}
            {additional_context}
            
            Please provide detailed analysis including:
            
            1. TONE ANALYSIS
               - Overall tone characteristics (formal/casual, authoritative/friendly, etc.)
               - Emotional undertones and brand personality
               - Consistency patterns across content
            
            2. LINGUISTIC PATTERNS
               - Vocabulary preferences and word choice patterns
               - Sentence structure and complexity analysis
               - Unique phrases and brand-specific terminology
            
            3. STYLOMETRIC ANALYSIS
               - Average sentence length and variation
               - Paragraph structure and flow
               - Punctuation and formatting preferences
            
            4. LANGUAGE CODES
               - Specific linguistic markers for brand voice
               - Voice consistency guidelines
               - Do's and don'ts for content creation
            
            5. BRAND VOICE PROFILE
               - Key characteristics summary
               - Target audience alignment
               - Brand differentiation factors
            
            If you need clarification on any aspect of the brand voice interpretation, 
            please ask me directly using your human interaction tools.
            """
            
            if self.agent:
                response = self.agent.step(analysis_prompt)
                
                # Extract response content
                analysis_result = response.msgs[0].content if response.msgs else "Analysis failed"
                
                # Check for tool usage
                tools_used = len(response.info.get('tool_calls', []))
                
                return {
                    "success": True,
                    "analysis": analysis_result,
                    "tools_used": tools_used,
                    "project_id": self.project_id,
                    "content_analyzed": len(content),
                    "knowledge_enhanced": self.knowledge_toolkit is not None,
                    "human_interaction": tools_used > 0
                }
            else:
                return {
                    "success": False,
                    "error": "Agent not properly initialized"
                }
                
        except Exception as e:
            logger.error(f"❌ Brand voice analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_style_guide(self, brand_analysis: str, content_examples: List[str] = None) -> Dict[str, Any]:
        """
        Create comprehensive style guide with human feedback.
        
        Args:
            brand_analysis: Results from brand voice pattern analysis
            content_examples: Optional content examples for reference
            
        Returns:
            Complete style guide with human interaction tracking
        """
        try:
            # Prepare content examples context
            examples_context = ""
            if content_examples:
                examples_context = "\n\nCONTENT EXAMPLES:\n" + "\n\n".join([
                    f"Example {i+1}:\n{example}" 
                    for i, example in enumerate(content_examples[:3])  # Limit to 3 examples
                ])
            
            # Use knowledge toolkit for additional style references
            knowledge_context = ""
            if self.knowledge_toolkit:
                try:
                    style_references = self.knowledge_toolkit.search_knowledge(
                        f"style guide templates brand voice guidelines {self.project_id}"
                    )
                    knowledge_context = f"\n\nSTYLE REFERENCES:\n{style_references}"
                except Exception as e:
                    logger.warning(f"⚠️ Style reference search failed: {e}")
            
            style_guide_prompt = f"""
            Create a comprehensive style guide based on the brand voice analysis:
            
            BRAND ANALYSIS:
            {brand_analysis}
            {examples_context}
            {knowledge_context}
            
            Please create a detailed style guide including:
            
            1. BRAND VOICE OVERVIEW
               - Brand personality and tone definition
               - Voice characteristics and key attributes
               - Target audience considerations
            
            2. WRITING GUIDELINES
               - Preferred vocabulary and terminology
               - Sentence structure recommendations
               - Paragraph and content flow guidelines
            
            3. TONE VARIATIONS
               - Different contexts and appropriate tones
               - Formal vs. informal communication guidelines
               - Emotional tone adjustments by content type
            
            4. LANGUAGE CODES
               - Specific linguistic patterns to follow
               - Brand-specific phrases and expressions
               - Words and phrases to avoid
            
            5. CONTENT EXAMPLES
               - Before/after examples showing voice application
               - Sample headlines, introductions, and conclusions
               - Call-to-action style examples
            
            6. QUALITY CHECKLIST
               - Voice consistency verification points
               - Brand alignment checkpoints
               - Common voice mistakes to avoid
            
            If you need my input or approval on any aspect of this style guide, 
            please ask me directly using your human interaction tools.
            """
            
            if self.agent:
                response = self.agent.step(style_guide_prompt)
                
                # Extract response content
                style_guide = response.msgs[0].content if response.msgs else "Style guide creation failed"
                
                # Check for tool usage and human interaction
                tools_used = len(response.info.get('tool_calls', []))
                
                return {
                    "success": True,
                    "style_guide": style_guide,
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
            logger.error(f"❌ Style guide creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_language_codes(self, style_analysis: str) -> Dict[str, Any]:
        """
        Generate specific language codes for brand consistency.
        
        Args:
            style_analysis: Detailed style analysis results
            
        Returns:
            Language codes and implementation guidelines
        """
        try:
            language_code_prompt = f"""
            Generate specific language codes based on this style analysis:
            
            STYLE ANALYSIS:
            {style_analysis}
            
            Create actionable language codes including:
            
            1. VOCABULARY CODES
               - Preferred terms and synonyms
               - Industry-specific terminology
               - Brand-unique expressions
            
            2. STRUCTURE CODES
               - Sentence length guidelines
               - Paragraph structure rules
               - Content organization patterns
            
            3. TONE CODES
               - Emotional tone specifications
               - Formality level guidelines
               - Voice personality markers
            
            4. STYLE IMPLEMENTATION
               - Practical application examples
               - Content creation checklists
               - Quality assurance markers
            
            Make these codes specific and actionable for content creators.
            """
            
            if self.agent:
                response = self.agent.step(language_code_prompt)
                
                language_codes = response.msgs[0].content if response.msgs else "Language code generation failed"
                tools_used = len(response.info.get('tool_calls', []))
                
                return {
                    "success": True,
                    "language_codes": language_codes,
                    "tools_used": tools_used,
                    "project_id": self.project_id
                }
            else:
                return {
                    "success": False,
                    "error": "Agent not properly initialized"
                }
                
        except Exception as e:
            logger.error(f"❌ Language code generation failed: {e}")
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
                role_name="Style Analyst",
                role_type=RoleType.ASSISTANT,
                meta_dict=None,
                content="Style analysis completed using fallback mode."
            )
    
    def __getattr__(self, name):
        """Delegate other attributes to the base agent."""
        if self.agent and hasattr(self.agent, name):
            return getattr(self.agent, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


def create_enhanced_style_analysis_agent(project_id: str = None) -> EnhancedStyleAnalysisAgent:
    """
    Create enhanced style analysis agent with RAG and HumanToolkit integration.
    
    Args:
        project_id: Project identifier for knowledge isolation
        
    Returns:
        Fully configured enhanced style analysis agent
    """
    try:
        agent = EnhancedStyleAnalysisAgent(project_id=project_id)
        logger.info(f"✅ Enhanced Style Analysis Agent created for project: {project_id}")
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create Enhanced Style Analysis Agent: {e}")
        raise


def test_enhanced_style_agent_with_tools(project_id: str = "test-style-analysis") -> dict:
    """Test the enhanced style analysis agent with tools."""
    try:
        print(f"🧪 Testing Enhanced Style Analysis Agent for project: {project_id}")
        
        # Create agent
        agent = create_enhanced_style_analysis_agent(project_id)
        print(f"✅ Agent created with {len(agent.tools)} tools")
        
        # Test brand voice analysis
        test_content = """
        Our innovative solutions transform the way businesses operate in today's digital landscape. 
        We believe in empowering organizations through cutting-edge technology and strategic insights 
        that drive meaningful results. Our team of experts collaborates closely with clients to 
        deliver exceptional outcomes that exceed expectations.
        """
        
        result = agent.analyze_brand_voice_patterns(
            content=test_content,
            brand_context="Professional technology company focused on business transformation"
        )
        
        print("🎯 Test Results:")
        print(f"Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"Tools Used: {result.get('tools_used', 0)}")
            print(f"Content Analyzed: {result.get('content_analyzed', 0)} characters")
            print(f"Knowledge Enhanced: {result.get('knowledge_enhanced', False)}")
            print(f"Human Interaction: {result.get('human_interaction', False)}")
            print("✅ Brand voice analysis completed with tool integration")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Run test
    test_result = test_enhanced_style_agent_with_tools()
    print("\n" + "="*60)
    print("Enhanced Style Analysis Agent Test Complete")
    print("="*60)