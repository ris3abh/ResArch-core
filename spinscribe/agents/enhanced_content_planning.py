# ─── UPDATE FILE: spinscribe/agents/enhanced_content_planning.py ───

"""
Enhanced Content Planning Agent with RAG and checkpoint integration.
FIXED VERSION with proper tool integration.
"""

import logging
from typing import Dict, Any, List, Optional

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.messages import BaseMessage

from spinscribe.memory.memory_setup import get_memory
from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
from spinscribe.checkpoints.enhanced_agents import CheckpointEnabledAgent
from spinscribe.checkpoints.checkpoint_manager import CheckpointType, Priority
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

logger = logging.getLogger(__name__)

class EnhancedContentPlanningAgent(CheckpointEnabledAgent, ChatAgent):
    """
    Enhanced Content Planning Agent with RAG knowledge and human checkpoints.
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
            "You are an Enhanced Content Planning Agent specialized in strategic outline creation. "
            
            "Your responsibilities:\n"
            "1. Use your knowledge access tools to gather brand guidelines and strategy documents\n"
            "2. Create structured content outlines using client knowledge base insights\n"
            "3. Reference existing brand guidelines and marketing strategies\n"
            "4. Ensure alignment with client's target audience and objectives\n"
            "5. Incorporate SEO requirements and content strategy documents\n"
            "6. Request human review for strategic content decisions\n\n"
            
            "Available Tools:\n"
            "- search_brand_documents: Search for relevant brand documents and guidelines\n"
            "- get_style_guidelines: Retrieve detailed style and brand guidelines\n"
            "- analyze_sample_content: Access sample content for reference patterns\n"
            "- get_comprehensive_knowledge: Get complete overview of client knowledge\n\n"
            
            "Workflow Process:\n"
            "1. ALWAYS start by using get_comprehensive_knowledge to understand the brand\n"
            "2. Use search_brand_documents to find specific strategy information\n"
            "3. Retrieve detailed guidelines with get_style_guidelines\n"
            "4. Review sample content patterns with analyze_sample_content\n"
            "5. Create structured, strategic content outline based on gathered information\n\n"
            
            "When creating outlines:\n"
            "- Always use your tools to access brand and strategy information first\n"
            "- Search for relevant strategic documents and guidelines\n"
            "- Ensure brand voice consistency throughout structure\n"
            "- Include specific audience targeting considerations\n"
            "- Request strategic approval for complex content plans\n"
            "- Create detailed section-by-section breakdowns\n\n"
            
            "IMPORTANT: You have access to processed client documents and brand guidelines "
            "through your tools. Always use them to create accurate, brand-aligned content outlines."
        )
        
        # Initialize memory
        try:
            memory = get_memory()
            logger.info("✅ Memory initialized for Enhanced Content Planning Agent")
        except Exception as e:
            logger.warning(f"⚠️ Memory initialization failed: {e}")
            memory = None
        
        # Create knowledge access toolkit
        try:
            self.knowledge_toolkit = KnowledgeAccessToolkit(project_id=self.project_id)
            tools_list = self.knowledge_toolkit.get_tools()
            logger.info(f"✅ Knowledge toolkit created with {len(tools_list)} tools")
        except Exception as e:
            logger.error(f"❌ Failed to create knowledge toolkit: {e}")
            tools_list = []
        
        # Initialize ChatAgent with tools
        super(ChatAgent, self).__init__()
        ChatAgent.__init__(
            self,
            system_message=sys_msg,
            model=model,
            memory=memory,
            tools=tools_list
        )
        
        # Initialize checkpoint integration
        try:
            CheckpointEnabledAgent.__init__(self, project_id=self.project_id)
            logger.info("✅ Checkpoint integration initialized")
        except Exception as e:
            logger.warning(f"⚠️ Checkpoint integration failed: {e}")
    
    def create_enhanced_outline(self, content_brief: str, content_type: str = "article") -> Dict[str, Any]:
        """
        Create enhanced content outline using RAG knowledge and brand guidelines.
        
        Args:
            content_brief: Brief describing content requirements
            content_type: Type of content (article, landing_page, etc.)
            
        Returns:
            Dict with outline and analysis information
        """
        try:
            logger.info(f"📋 Creating enhanced outline for {content_type}")
            
            # Create outline prompt that instructs the agent to use its tools
            outline_prompt = f"""
            Create a comprehensive content outline for: {content_type}
            
            Content Brief: {content_brief}
            Project: {self.project_id}
            
            Please follow this process:
            
            1. Use get_comprehensive_knowledge() to understand the brand and strategy
            2. Use search_brand_documents() to find specific brand voice and strategy information
            3. Use get_style_guidelines() to access detailed writing and formatting requirements
            4. Use analyze_sample_content() to understand successful content patterns
            5. Create a detailed, strategic content outline that includes:
               - Clear content structure with headings and subheadings
               - Brand voice and tone specifications for each section
               - Target audience considerations
               - Key messaging and value propositions
               - SEO considerations and keywords
               - Call-to-action recommendations
               - Specific content guidelines for each section
            
            Base your outline on the retrieved brand information and guidelines.
            Ensure the outline maintains brand consistency and strategic alignment.
            """
            
            # Send the prompt to the agent (it will use its tools automatically)
            response = self.step(outline_prompt)
            
            # Extract the content from the response
            if response and response.msgs:
                outline_content = response.msgs[0].content
                
                outline_result = {
                    "project_id": self.project_id,
                    "content_type": content_type,
                    "content_brief": content_brief,
                    "outline_content": outline_content,
                    "tools_used": len(self.tools) if hasattr(self, 'tools') else 0,
                    "success": True,
                    "tool_calls": response.info.get('tool_calls', []),
                    "timestamp": self._get_current_timestamp()
                }
                
                logger.info("✅ Enhanced outline creation completed successfully")
                return outline_result
            else:
                raise Exception("No response received from agent")
                
        except Exception as e:
            logger.error(f"❌ Outline creation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "project_id": self.project_id,
                "fallback_outline": self._get_fallback_outline(content_type)
            }
    
    def _get_fallback_outline(self, content_type: str) -> Dict[str, Any]:
        """Provide fallback outline when primary creation fails."""
        return {
            "message": f"Fallback {content_type} outline based on available information",
            "structure": [
                "Introduction - Hook and value proposition",
                "Problem Statement - Address target audience pain points",
                "Solution Overview - Present approach and benefits", 
                "Detailed Analysis - Deep dive into key components",
                "Implementation - Practical steps and considerations",
                "Conclusion - Summary and clear call-to-action"
            ],
            "brand_alignment": "Professional, confident, solution-oriented approach",
            "tone": "Educational yet engaging, authoritative but approachable",
            "status": "Outline ready for content generation"
        }
    
    def _get_current_timestamp(self):
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# ─── Factory Function ───

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
        logger.info(f"🔧 Agent has {len(agent.tools) if hasattr(agent, 'tools') else 0} tools attached")
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create Enhanced Content Planning Agent: {e}")
        raise


# ─── Direct Test Function ───

def test_enhanced_planning_agent_with_tools(project_id: str = "test-camel-fix"):
    """Test the enhanced content planning agent with tools."""
    try:
        print(f"🧪 Testing Enhanced Content Planning Agent for project: {project_id}")
        
        # Create agent
        agent = create_enhanced_content_planning_agent(project_id)
        print(f"✅ Agent created with {len(agent.tools) if hasattr(agent, 'tools') else 0} tools")
        
        # Test outline creation
        result = agent.create_enhanced_outline(
            content_brief="Create an article about how AI transforms business operations",
            content_type="article"
        )
        
        print("🎯 Test Results:")
        print(f"Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"Tools Used: {result.get('tools_used', 0)}")
            print(f"Outline Length: {len(result.get('outline_content', ''))}")
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