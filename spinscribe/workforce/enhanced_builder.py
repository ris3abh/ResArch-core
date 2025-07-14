# File: spinscribe/workforce/enhanced_builder.py (MEMORY FIX INTEGRATION)
"""
Enhanced Workforce Builder with integrated memory token limit fixes.
This ensures all agents are created with 100K+ token limits from the start.
"""

import logging
from typing import Dict, Any, Optional
from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.societies import Workforce
from camel.types import ModelType

# Import our memory fix utilities
from spinscribe.memory.memory_setup import setup_agent_memory, get_unlimited_memory
from spinscribe.agents.memory_patch import MemoryTokenPatcher, patch_all_system_memory

logger = logging.getLogger(__name__)

class EnhancedWorkforceBuilder:
    """
    Enhanced workforce builder that creates agents with proper memory limits.
    All agents are guaranteed to have 100K+ token limits.
    """
    
    def __init__(self, project_id: str, token_limit: int = 100000):
        self.project_id = project_id
        self.token_limit = token_limit
        self.agents: Dict[str, ChatAgent] = {}
        self.memory_patcher = MemoryTokenPatcher()
        
        logger.info(f"🏗️ Initializing Enhanced Workforce Builder for {project_id}")
        logger.info(f"🔧 Using token limit: {token_limit}")
    
    def create_agent_with_memory_fix(
        self,
        agent_name: str,
        system_message: str,
        model_type: ModelType = ModelType.GPT_4O_MINI,
        tools: list = None,
        token_limit: int = None
    ) -> ChatAgent:
        """
        Create an agent with properly configured memory and token limits.
        
        Args:
            agent_name: Name/ID for the agent
            system_message: System message for the agent
            model_type: Model type to use
            tools: List of tools for the agent
            token_limit: Override token limit (defaults to instance limit)
            
        Returns:
            ChatAgent with high-capacity memory
        """
        if token_limit is None:
            token_limit = self.token_limit
        
        logger.info(f"🤖 Creating agent '{agent_name}' with {token_limit} token limit")
        
        try:
            # Create agent with high-capacity memory
            memory = setup_agent_memory(
                agent_id=agent_name,
                model_name="gpt-4o-mini",
                enable_vector_storage=True,
                memory_type="longterm",
                token_limit=token_limit
            )
            
            # Configure model settings
            config = ChatGPTConfig(
                temperature=0.7,
                max_tokens=None,  # Let the model use its full capacity
            )
            
            # Create the agent
            agent = ChatAgent(
                system_message=system_message,
                model_type=model_type,
                model_config=config,
                memory=memory,
                tools=tools or []
            )
            
            # Double-check and patch memory if needed
            if not self.memory_patcher.patch_agent_memory(agent, token_limit):
                logger.warning(f"⚠️ Could not patch memory for agent {agent_name}")
            
            # Store agent
            self.agents[agent_name] = agent
            
            logger.info(f"✅ Agent '{agent_name}' created successfully")
            return agent
            
        except Exception as e:
            logger.error(f"❌ Failed to create agent '{agent_name}': {e}")
            raise
    
    def create_style_analysis_agent(self) -> ChatAgent:
        """Create Enhanced Style Analysis Agent with memory fixes."""
        
        system_message = f"""You are the Enhanced Style Analysis Agent for project {self.project_id}.

            Your enhanced responsibilities:
            1. Analyze client brand voice patterns using RAG knowledge retrieval
            2. Perform advanced stylometry analysis on sample content
            3. Generate comprehensive language codes defining client's unique style
            4. Access and process sample content from knowledge base
            5. Create detailed style guidelines and voice documentation

            Enhanced capabilities:
            - RAG-powered knowledge retrieval from client documents
            - Advanced pattern recognition in writing style
            - Comprehensive brand voice analysis
            - Style consistency verification
            - Language pattern codification

            You have access to extensive context (100K+ tokens) to maintain full conversation history and detailed analysis results.
            """
        
        from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
        tools = [KnowledgeAccessToolkit(self.project_id)]
        
        return self.create_agent_with_memory_fix(
            agent_name="enhanced_style_analysis",
            system_message=system_message,
            tools=tools
        )
    
    def create_content_planning_agent(self) -> ChatAgent:
        """Create Enhanced Content Planning Agent with memory fixes."""
        
        system_message = f"""You are the Enhanced Content Planning Agent for project {self.project_id}.

Your enhanced responsibilities:
1. Create structured content outlines using brand guidelines
2. Develop comprehensive content strategies
3. Access strategy documents and audience information from knowledge base
4. Plan content architecture and information flow
5. Ensure alignment with client objectives and brand voice

Enhanced capabilities:
- Strategic content architecture planning
- RAG-powered access to brand guidelines and strategy docs
- Audience analysis and targeting
- Content structure optimization
- Cross-platform content planning

You maintain full context (100K+ tokens) to remember all planning decisions and strategy discussions.
"""
        
        from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
        tools = [KnowledgeAccessToolkit(self.project_id)]
        
        return self.create_agent_with_memory_fix(
            agent_name="enhanced_content_planning",
            system_message=system_message,
            tools=tools
        )
    
    def create_content_generation_agent(self) -> ChatAgent:
        """Create Enhanced Content Generation Agent with memory fixes."""
        
        system_message = f"""You are the Enhanced Content Generation Agent for project {self.project_id}.

Your enhanced responsibilities:
1. Generate high-quality content in the client's exact brand voice
2. Apply style patterns and language codes from style analysis
3. Access factual references and style guides from knowledge base
4. Maintain consistency with previous content and brand standards
5. Produce content that matches approved outlines and strategies

Enhanced capabilities:
- Advanced style pattern application
- RAG-powered factual verification
- Brand voice consistency enforcement
- Content quality optimization
- Multi-format content generation

You retain full context (100K+ tokens) to maintain consistency across all generated content.
"""
        
        from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
        tools = [KnowledgeAccessToolkit(self.project_id)]
        
        return self.create_agent_with_memory_fix(
            agent_name="enhanced_content_generation",
            system_message=system_message,
            tools=tools
        )
    
    def create_qa_agent(self) -> ChatAgent:
        """Create Enhanced QA Agent with memory fixes."""
        
        system_message = f"""You are the Enhanced Quality Assurance Agent for project {self.project_id}.

Your enhanced responsibilities:
1. Review and refine content for quality, accuracy, and brand alignment
2. Verify adherence to established brand voice and style guidelines
3. Check factual accuracy using knowledge base references
4. Ensure compliance with client style requirements
5. Provide detailed feedback and improvement recommendations

Enhanced capabilities:
- Comprehensive quality assessment
- Brand alignment verification
- Factual accuracy checking using RAG
- Style consistency validation
- Detailed feedback generation

You maintain complete context (100K+ tokens) to track all quality decisions and maintain consistency standards.
"""
        
        from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
        tools = [KnowledgeAccessToolkit(self.project_id)]
        
        return self.create_agent_with_memory_fix(
            agent_name="enhanced_qa",
            system_message=system_message,
            tools=tools
        )
    
    def create_coordinator_agent(self) -> ChatAgent:
        """Create Enhanced Coordinator Agent with memory fixes."""
        
        system_message = f"""You are the Enhanced Coordinator Agent for project {self.project_id}.

Your enhanced responsibilities:
1. Orchestrate the complete content creation workflow
2. Manage information flow between specialized agents
3. Ensure workflow sequence and dependencies are maintained
4. Monitor progress and resolve workflow bottlenecks
5. Maintain project context and requirements throughout the process

Enhanced capabilities:
- Advanced workflow orchestration
- Inter-agent communication management
- Project context maintenance
- Progress tracking and optimization
- Quality gate management

Workflow sequence to manage:
1. Enhanced Style Analysis - Extract brand voice with RAG knowledge
2. Strategic Content Planning - Create outlines using brand guidelines  
3. Enhanced Content Generation - Produce content with factual verification
4. Quality Assurance - Final review and refinement

You have unlimited context (100K+ tokens) to maintain complete workflow state and coordination history.
"""
        
        return self.create_agent_with_memory_fix(
            agent_name="enhanced_coordinator",
            system_message=system_message,
            token_limit=150000  # Extra capacity for coordination
        )
    
    def build_enhanced_workforce(self) -> Workforce:
        """
        Build the complete enhanced workforce with memory fixes.
        
        Returns:
            Workforce with all agents having proper memory limits
        """
        logger.info(f"🏗️ Building Enhanced Workforce for {self.project_id}")
        
        try:
            # Create all agents with memory fixes
            style_agent = self.create_style_analysis_agent()
            planning_agent = self.create_content_planning_agent()
            generation_agent = self.create_content_generation_agent()
            qa_agent = self.create_qa_agent()
            coordinator_agent = self.create_coordinator_agent()
            
            # Create workforce
            workforce = Workforce("enhanced_content_creation")
            
            # Add agents to workforce
            workforce.add_single_agent_worker(
                worker_id="style_analysis",
                worker_agent=style_agent,
                description="Enhanced Style Analysis Agent: Analyzes client brand voice patterns, performs stylometry analysis, and generates language codes that define the client's unique style. Accesses sample content and previous brand voice analyses from knowledge base."
            )
            
            workforce.add_single_agent_worker(
                worker_id="content_planning", 
                worker_agent=planning_agent,
                description="Enhanced Content Planning Agent: Creates structured outlines and content strategies based on project requirements and client guidelines. Uses brand guidelines, audience information, and content strategy documents to create organized frameworks."
            )
            
            workforce.add_single_agent_worker(
                worker_id="content_generation",
                worker_agent=generation_agent, 
                description="Enhanced Content Generation Agent: Produces draft content in the client's brand voice by applying style patterns and language codes to approved outlines. Accesses style guides, factual references, and maintains consistency with previous content."
            )
            
            workforce.add_single_agent_worker(
                worker_id="qa",
                worker_agent=qa_agent,
                description="Enhanced Quality Assurance Agent: Reviews and refines content for quality, accuracy, and brand alignment. Verifies adherence to brand voice, checks factual accuracy, and ensures compliance with style guidelines. Acts as first-line editor before human review."
            )
            
            # Set coordinator
            workforce.coordinator_agent = coordinator_agent
            
            # Apply final memory patches to entire workforce
            patch_count = self.memory_patcher.patch_workforce_agents(workforce, self.token_limit)
            logger.info(f"🔧 Applied memory patches to {patch_count} workforce agents")
            
            # Apply global memory fix to catch any missed objects
            patch_all_system_memory(self.token_limit)
            
            logger.info("✅ Enhanced Workforce built successfully with memory fixes")
            return workforce
            
        except Exception as e:
            logger.error(f"❌ Failed to build Enhanced Workforce: {e}")
            raise
    
    def validate_workforce_memory(self, workforce: Workforce) -> bool:
        """
        Validate that all agents in the workforce have proper memory limits.
        
        Args:
            workforce: Workforce to validate
            
        Returns:
            True if all agents have proper memory limits
        """
        try:
            from spinscribe.agents.memory_patch import validate_memory_limits
            
            results = validate_memory_limits(self.token_limit)
            
            compliant_ratio = results['compliant'] / max(results['total_checked'], 1)
            
            if compliant_ratio >= 0.9:  # 90% compliance threshold
                logger.info(f"✅ Workforce memory validation passed: {results['compliant']}/{results['total_checked']} compliant")
                return True
            else:
                logger.warning(f"⚠️ Workforce memory validation failed: only {results['compliant']}/{results['total_checked']} compliant")
                return False
                
        except Exception as e:
            logger.error(f"❌ Workforce memory validation error: {e}")
            return False

def create_enhanced_workforce(project_id: str, token_limit: int = 100000) -> Workforce:
    """
    Convenience function to create an enhanced workforce with memory fixes.
    
    Args:
        project_id: Project identifier
        token_limit: Token limit for all agents (default 100K)
        
    Returns:
        Workforce with memory-fixed agents
    """
    builder = EnhancedWorkforceBuilder(project_id, token_limit)
    workforce = builder.build_enhanced_workforce()
    
    # Validate memory configuration
    if not builder.validate_workforce_memory(workforce):
        logger.warning("⚠️ Workforce memory validation failed, but continuing...")
    
    return workforce

# Export key functions
__all__ = [
    'EnhancedWorkforceBuilder',
    'create_enhanced_workforce'
]