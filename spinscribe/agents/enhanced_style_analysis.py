# ─── UPDATE FILE: spinscribe/agents/enhanced_style_analysis.py ───

"""
Enhanced Style Analysis Agent with RAG and checkpoint integration.
FIXED VERSION with proper tool integration following CAMEL patterns.
"""

import logging
from typing import Dict, Any, List, Optional

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.messages import BaseMessage
from camel.toolkits import FunctionTool

from spinscribe.memory.memory_setup import get_memory
from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
from spinscribe.checkpoints.enhanced_agents import CheckpointEnabledAgent
from spinscribe.checkpoints.checkpoint_manager import CheckpointType, Priority
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

logger = logging.getLogger(__name__)

class EnhancedStyleAnalysisAgent(CheckpointEnabledAgent, ChatAgent):
    """
    Enhanced Style Analysis Agent with RAG knowledge and human checkpoints.
    FIXED VERSION with proper tool integration.
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or "default"
        
        # Create model
        model = ModelFactory.create(
            model_platform=MODEL_PLATFORM,
            model_type=MODEL_TYPE,
            model_config_dict=MODEL_CONFIG,
        )
        
        # Enhanced system message with tool usage instructions
        sys_msg = (
            "You are an Enhanced Style Analysis Agent specialized in extracting and codifying brand voice patterns. "
            
            "Your responsibilities:\n"
            "1. Use your knowledge access tools to gather client documents and style guides\n"
            "2. Analyze brand voice, writing style, and content patterns using available information\n"
            "3. Generate actionable style guidelines and language codes\n"
            "4. Create brand voice consistency recommendations\n"
            "5. Provide detailed analysis for content creation teams\n\n"
            
            "Available Tools:\n"
            "- search_brand_documents: Search for relevant client documents and brand materials\n"
            "- get_style_guidelines: Retrieve style guide information and voice patterns\n"
            "- analyze_sample_content: Access and analyze sample content for voice patterns\n"
            "- get_comprehensive_knowledge: Get complete overview of all client knowledge\n\n"
            
            "Workflow Process:\n"
            "1. ALWAYS start by using get_comprehensive_knowledge to gather all available information\n"
            "2. Use search_brand_documents to find specific brand voice information\n"
            "3. Retrieve style guidelines using get_style_guidelines\n"
            "4. Analyze sample content patterns with analyze_sample_content\n"
            "5. Generate comprehensive style analysis and recommendations\n\n"
            
            "When performing style analysis:\n"
            "- Always use your tools to access processed client knowledge\n"
            "- Extract specific language patterns, tone characteristics, and vocabulary\n"
            "- Identify brand voice consistency requirements\n"
            "- Generate actionable guidelines for content creation\n"
            "- Provide specific examples and recommendations\n\n"
            
            "IMPORTANT: You have access to processed client documents through your tools. "
            "Use them to provide detailed, accurate style analysis based on actual client materials."
        )
        
        # Initialize memory
        try:
            memory = get_memory()
            logger.info("✅ Memory initialized for Enhanced Style Analysis Agent")
        except Exception as e:
            logger.warning(f"⚠️ Memory initialization failed: {e}")
            memory = None
        
        # Create knowledge access toolkit with tools
        try:
            self.knowledge_toolkit = KnowledgeAccessToolkit(project_id=self.project_id)
            tools_list = self.knowledge_toolkit.get_tools()
            logger.info(f"✅ Knowledge toolkit created with {len(tools_list)} tools")
        except Exception as e:
            logger.error(f"❌ Failed to create knowledge toolkit: {e}")
            tools_list = []
        
        # Initialize ChatAgent with tools (CAMEL pattern)
        super(ChatAgent, self).__init__()
        ChatAgent.__init__(
            self,
            system_message=sys_msg,
            model=model,
            memory=memory,
            tools=tools_list  # This is the key fix - attaching tools properly
        )
        
        # Initialize checkpoint integration
        try:
            CheckpointEnabledAgent.__init__(self, project_id=self.project_id)
            logger.info("✅ Checkpoint integration initialized")
        except Exception as e:
            logger.warning(f"⚠️ Checkpoint integration failed: {e}")
    
    def perform_enhanced_style_analysis(self, task_content: str = None) -> Dict[str, Any]:
        """
        Perform comprehensive style analysis using available tools and knowledge.
        
        Args:
            task_content: Optional task description
            
        Returns:
            Comprehensive style analysis results
        """
        try:
            logger.info(f"🎨 Starting enhanced style analysis for project: {self.project_id}")
            
            # Create analysis prompt that instructs the agent to use its tools
            analysis_prompt = f"""
            Perform enhanced style analysis for project: {self.project_id}
            
            Task: {task_content or 'Complete brand voice and style analysis'}
            
            Please follow this process:
            
            1. Use get_comprehensive_knowledge() to gather all available client information
            2. Use search_brand_documents() to find specific brand voice patterns
            3. Use get_style_guidelines() to access detailed style requirements
            4. Use analyze_sample_content() to extract voice patterns from examples
            5. Generate comprehensive style analysis with:
               - Brand voice characteristics
               - Tone and style patterns
               - Key vocabulary and language patterns
               - Writing style recommendations
               - Brand consistency guidelines
            
            Provide detailed, actionable analysis based on the retrieved information.
            """
            
            # Send the prompt to the agent (it will use its tools automatically)
            response = self.step(analysis_prompt)
            
            # Extract the content from the response
            if response and response.msgs:
                analysis_content = response.msgs[0].content
                
                analysis_result = {
                    "project_id": self.project_id,
                    "task_content": task_content,
                    "analysis_content": analysis_content,
                    "tools_used": len(self.tools) if hasattr(self, 'tools') else 0,
                    "success": True,
                    "tool_calls": response.info.get('tool_calls', []),
                    "timestamp": self._get_current_timestamp()
                }
                
                logger.info("✅ Enhanced style analysis completed successfully")
                return analysis_result
            else:
                raise Exception("No response received from agent")
                
        except Exception as e:
            logger.error(f"❌ Style analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "project_id": self.project_id,
                "fallback_analysis": self._get_fallback_analysis()
            }
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Provide fallback analysis when primary analysis fails."""
        return {
            "message": "Fallback style analysis based on available information",
            "brand_voice": "Professional, confident, solution-oriented",
            "key_elements": ["innovation", "excellence", "collaboration", "results"],
            "tone": "Straightforward yet comprehensive",
            "recommendations": [
                "Maintain professional tone with approachable language",
                "Use confident, solution-focused messaging",
                "Emphasize collaboration and transparency",
                "Include specific examples and case studies"
            ],
            "status": "Analysis completed with available resources"
        }
    
    def _get_current_timestamp(self):
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# ─── Factory Function ───

def create_enhanced_style_analysis_agent(project_id: str = None) -> EnhancedStyleAnalysisAgent:
    """
    Create enhanced style analysis agent with proper tool integration.
    CORRECTED VERSION.
    """
    try:
        agent = EnhancedStyleAnalysisAgent(project_id=project_id)
        logger.info(f"✅ Enhanced Style Analysis Agent created for project: {project_id}")
        logger.info(f"🔧 Agent has {len(agent.tools) if hasattr(agent, 'tools') else 0} tools attached")
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create Enhanced Style Analysis Agent: {e}")
        raise


# ─── Direct Test Function ───

def test_enhanced_style_agent_with_tools(project_id: str = "test-camel-fix"):
    """Test the enhanced style analysis agent with tools."""
    try:
        print(f"🧪 Testing Enhanced Style Analysis Agent for project: {project_id}")
        
        # Create agent
        agent = create_enhanced_style_analysis_agent(project_id)
        tool_count = len(agent.tools) if hasattr(agent, 'tools') else 0
        print(f"✅ Agent created with {tool_count} tools")
        
        if tool_count == 0:
            print("⚠️ WARNING: Agent has 0 tools - tool attachment failed")
            return {"success": False, "error": "No tools attached to agent"}
        
        # Test a simple analysis request
        try:
            test_message = "Please use your tools to perform a comprehensive style analysis for this project."
            response = agent.step(test_message)
            
            if response and response.msgs:
                analysis_content = response.msgs[0].content
                tool_calls = response.info.get('tool_calls', [])
                
                result = {
                    "success": True,
                    "tools_used": len(tool_calls),
                    "analysis_content": analysis_content,
                    "agent_tools_count": tool_count
                }
                
                print(f"✅ Analysis completed - {len(tool_calls)} tool calls made")
                return result
            else:
                return {"success": False, "error": "No response from agent"}
                
        except Exception as e:
            print(f"❌ Agent step failed: {e}")
            return {"success": False, "error": f"Agent execution failed: {e}"}
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Run test
    test_result = test_enhanced_style_agent_with_tools()
    print("\n" + "="*60)
    print("Enhanced Style Analysis Agent Test Complete")
    print("="*60)