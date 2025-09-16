# File: spinscribe/workforce/enhanced_builder.py (MEMORY FIX + WEBSOCKET INTEGRATION)
"""
Enhanced Workforce Builder with integrated memory token limit fixes and WebSocket support.
This ensures all agents are created with 100K+ token limits from the start and can broadcast messages.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.societies.workforce import Workforce  # FIXED: Correct import path for CAMEL 0.2.70
from camel.types import ModelType
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.toolkits import FunctionTool

# Import our memory fix utilities
from spinscribe.memory.memory_setup import setup_agent_memory, get_unlimited_memory
from spinscribe.agents.memory_patch import MemoryTokenPatcher, patch_all_system_memory

logger = logging.getLogger(__name__)

class EnhancedWorkforceBuilder:
    """
    Enhanced workforce builder that creates agents with proper memory limits and WebSocket support.
    All agents are guaranteed to have 100K+ token limits and can broadcast messages.
    """
    
    def __init__(self, project_id: str, token_limit: int = 100000, websocket_interceptor=None):
        self.project_id = project_id
        self.token_limit = token_limit
        self.agents: Dict[str, ChatAgent] = {}
        self.memory_patcher = MemoryTokenPatcher()
        self.websocket_interceptor = websocket_interceptor  # NEW: Store WebSocket interceptor
        
        logger.info(f"🏗️ Initializing Enhanced Workforce Builder for {project_id}")
        logger.info(f"🔧 Using token limit: {token_limit}")
        logger.info(f"📡 WebSocket: {'ENABLED' if websocket_interceptor else 'DISABLED'}")  # NEW: Log WebSocket status
    
    def wrap_agent_with_websocket(self, agent: ChatAgent, agent_name: str, agent_role: str):
        """
        NEW METHOD: Wrap an agent's step method to broadcast messages via WebSocket.
        
        Citation: Based on the WebSocket interceptor pattern from websocket_interceptor.py
        which requires intercepting agent messages for real-time frontend updates.
        
        Args:
            agent: The ChatAgent to wrap
            agent_name: Internal name for logging
            agent_role: Human-readable role for display
        """
        if not self.websocket_interceptor:
            return  # No interceptor, nothing to wrap
        
        original_step = agent.step
        interceptor = self.websocket_interceptor
        
        # Handle both sync and async step methods
        if asyncio.iscoroutinefunction(original_step):
            # Async step method
            async def wrapped_step(input_message):
                # Broadcast incoming message
                try:
                    await interceptor.intercept_message(
                        message={"content": f"Processing request..."},
                        agent_type=agent_role,
                        stage="processing"
                    )
                except Exception as e:
                    logger.debug(f"WebSocket broadcast error: {e}")
                
                # Call original step
                result = await original_step(input_message)
                
                # Broadcast outgoing response
                try:
                    if result and hasattr(result, 'msg') and result.msg:
                        content = result.msg.content if hasattr(result.msg, 'content') else str(result.msg)
                        await interceptor.intercept_message(
                            message={"content": content},
                            agent_type=agent_role,
                            stage="responding"
                        )
                except Exception as e:
                    logger.debug(f"WebSocket broadcast error: {e}")
                
                return result
            
            agent.step = wrapped_step
        else:
            # Sync step method
            def wrapped_step(input_message):
                # Try to broadcast in sync context
                if interceptor:
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(
                                interceptor.intercept_message(
                                    message={"content": f"Processing request..."},
                                    agent_type=agent_role,
                                    stage="processing"
                                )
                            )
                    except Exception as e:
                        logger.debug(f"WebSocket broadcast error: {e}")
                
                # Call original step
                result = original_step(input_message)
                
                # Try to broadcast response
                if interceptor and result:
                    try:
                        if hasattr(result, 'msg') and result.msg:
                            content = result.msg.content if hasattr(result.msg, 'content') else str(result.msg)
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(
                                    interceptor.intercept_message(
                                        message={"content": content},
                                        agent_type=agent_role,
                                        stage="responding"
                                    )
                                )
                    except Exception as e:
                        logger.debug(f"WebSocket broadcast error: {e}")
                
                return result
            
            agent.step = wrapped_step
        
        logger.info(f"   ✅ Wrapped {agent_role} with WebSocket interceptor")
    
    def create_agent_with_memory_fix(
        self,
        agent_name: str,
        system_message: str,
        model_type: ModelType = ModelType.GPT_4O_MINI,
        tools: list = None,
        token_limit: int = None,
        agent_role: str = None  # NEW: Add role for WebSocket display
    ) -> ChatAgent:
        """
        Create an agent with properly configured memory and token limits, plus WebSocket support.
        
        MODIFIED: Added agent_role parameter for WebSocket message broadcasting
        Citation: Extended to support WebSocket based on requirements from enhanced_process.py
        
        Args:
            agent_name: Name/ID for the agent
            system_message: System message for the agent
            model_type: Model type to use
            tools: List of tools for the agent
            token_limit: Override token limit (defaults to instance limit)
            agent_role: Human-readable role for WebSocket messages (NEW)
            
        Returns:
            ChatAgent with high-capacity memory and WebSocket support
        """
        if token_limit is None:
            token_limit = self.token_limit
        
        logger.info(f"🤖 Creating agent '{agent_name}' with {token_limit} token limit")
        
        try:
            # Create agent with high-capacity memory (existing code)
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
            
            # Create the model object first
            model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=model_type,
                model_config_dict=config.as_dict()
            )
            
            # Create the agent with the model object
            agent = ChatAgent(
                system_message=system_message,
                model=model,  # Pass model object instead of model_type
                memory=memory,
                tools=tools or []
            )
            
            # Double-check and patch memory if needed
            if not self.memory_patcher.patch_agent_memory(agent, token_limit):
                logger.warning(f"⚠️ Could not patch memory for agent {agent_name}")
            
            # NEW: Wrap with WebSocket if interceptor available
            if self.websocket_interceptor and agent_role:
                self.wrap_agent_with_websocket(agent, agent_name, agent_role)
            
            # Store agent
            self.agents[agent_name] = agent
            
            logger.info(f"✅ Agent '{agent_name}' created successfully")
            return agent
            
        except Exception as e:
            logger.error(f"❌ Failed to create agent '{agent_name}': {e}")
            raise
    
    def _extract_tools_from_toolkit(self, toolkit):
        """
        Extract and properly format tools from KnowledgeAccessToolkit.
        Based on CAMEL documentation, tools must be wrapped with FunctionTool.
        """
        tools = []
        
        # First try direct method access (preferred approach)
        if hasattr(toolkit, 'search_knowledge'):
            tools.append(FunctionTool(toolkit.search_knowledge))
        if hasattr(toolkit, 'get_brand_guidelines'):
            tools.append(FunctionTool(toolkit.get_brand_guidelines))
        if hasattr(toolkit, 'get_content_strategy'):
            tools.append(FunctionTool(toolkit.get_content_strategy))
        if hasattr(toolkit, 'analyze_sample_content'):
            tools.append(FunctionTool(toolkit.analyze_sample_content))
        
        # Fallback: if no direct methods found, try extracting from tools list
        if not tools and hasattr(toolkit, 'tools'):
            toolkit_tools = toolkit.tools
            if isinstance(toolkit_tools, list):
                for tool in toolkit_tools:
                    if isinstance(tool, dict) and 'function' in tool:
                        # Extract function from dictionary and wrap with FunctionTool
                        tools.append(FunctionTool(tool['function']))
                    elif callable(tool):
                        # If already callable, wrap with FunctionTool
                        tools.append(FunctionTool(tool))
        
        return tools
    
    def create_style_analysis_agent(self) -> ChatAgent:
        """Create Enhanced Style Analysis Agent with memory fixes and WebSocket support."""
        
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
        knowledge_toolkit = KnowledgeAccessToolkit(self.project_id)
        
        # Extract and properly format tools
        tools = self._extract_tools_from_toolkit(knowledge_toolkit)
        
        return self.create_agent_with_memory_fix(
            agent_name="enhanced_style_analysis",
            system_message=system_message,
            tools=tools,
            agent_role="Style Analysis Agent"  # NEW: Add role for WebSocket
        )
    
    def create_content_planning_agent(self) -> ChatAgent:
        """Create Enhanced Content Planning Agent with memory fixes and WebSocket support."""
        
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
        knowledge_toolkit = KnowledgeAccessToolkit(self.project_id)
        
        # Extract and properly format tools
        tools = self._extract_tools_from_toolkit(knowledge_toolkit)
        
        return self.create_agent_with_memory_fix(
            agent_name="enhanced_content_planning",
            system_message=system_message,
            tools=tools,
            agent_role="Content Planning Agent"  # NEW: Add role for WebSocket
        )
    
    def create_content_generation_agent(self) -> ChatAgent:
        """Create Enhanced Content Generation Agent with memory fixes and WebSocket support."""
        
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
        knowledge_toolkit = KnowledgeAccessToolkit(self.project_id)
        
        # Extract and properly format tools
        tools = self._extract_tools_from_toolkit(knowledge_toolkit)
        
        return self.create_agent_with_memory_fix(
            agent_name="enhanced_content_generation",
            system_message=system_message,
            tools=tools,
            agent_role="Content Generation Agent"  # NEW: Add role for WebSocket
        )
    
    def create_qa_agent(self) -> ChatAgent:
        """Create Enhanced QA Agent with memory fixes and WebSocket support."""
        
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
        knowledge_toolkit = KnowledgeAccessToolkit(self.project_id)
        
        # Extract and properly format tools
        tools = self._extract_tools_from_toolkit(knowledge_toolkit)
        
        return self.create_agent_with_memory_fix(
            agent_name="enhanced_qa",
            system_message=system_message,
            tools=tools,
            agent_role="Quality Assurance Agent"  # NEW: Add role for WebSocket
        )
    
    def create_coordinator_agent(self) -> ChatAgent:
        """Create Enhanced Coordinator Agent with memory fixes and WebSocket support."""
        
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
            token_limit=150000,  # Extra capacity for coordination
            agent_role="Coordinator Agent"  # NEW: Add role for WebSocket
        )
    
    def build_enhanced_workforce(self) -> Workforce:
        """
        Build the complete enhanced workforce with memory fixes and WebSocket support.
        
        MODIFIED: Now includes WebSocket integration for all agents
        Citation: Extended based on requirements from enhanced_process.py which needs
        real-time agent message broadcasting to frontend
        
        Returns:
            Workforce with all agents having proper memory limits and WebSocket support
        """
        logger.info(f"🏗️ Building Enhanced Workforce for {self.project_id}")
        
        # NEW: Broadcast workforce building start if interceptor available
        if self.websocket_interceptor:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self.websocket_interceptor.intercept_message(
                            message={"content": "Initializing specialized agents..."},
                            agent_type="System",
                            stage="initialization"
                        )
                    )
            except Exception as e:
                logger.debug(f"Could not send initialization message: {e}")
        
        try:
            # Create all agents with memory fixes and WebSocket wrapping
            style_agent = self.create_style_analysis_agent()
            planning_agent = self.create_content_planning_agent()
            generation_agent = self.create_content_generation_agent()
            qa_agent = self.create_qa_agent()
            coordinator_agent = self.create_coordinator_agent()
            
            # Create workforce
            workforce = Workforce("enhanced_content_creation")
            
            # Add agents to workforce (FIXED: removed worker_id parameter)
            workforce.add_single_agent_worker(
                worker=style_agent,
                description="Enhanced Style Analysis Agent: Analyzes client brand voice patterns, performs stylometry analysis, and generates language codes that define the client's unique style. Accesses sample content and previous brand voice analyses from knowledge base."
            )
            
            workforce.add_single_agent_worker(
                worker=planning_agent,
                description="Enhanced Content Planning Agent: Creates structured outlines and content strategies based on project requirements and client guidelines. Uses brand guidelines, audience information, and content strategy documents to create organized frameworks."
            )
            
            workforce.add_single_agent_worker(
                worker=generation_agent, 
                description="Enhanced Content Generation Agent: Produces draft content in the client's brand voice by applying style patterns and language codes to approved outlines. Accesses style guides, factual references, and maintains consistency with previous content."
            )
            
            workforce.add_single_agent_worker(
                worker=qa_agent,
                description="Enhanced Quality Assurance Agent: Reviews and refines content for quality, accuracy, and brand alignment. Verifies adherence to brand voice, checks factual accuracy, and ensures compliance with style guidelines. Acts as first-line editor before human review."
            )
            
            # Set coordinator
            workforce.coordinator_agent = coordinator_agent
            
            # Apply final memory patches to entire workforce
            patch_count = self.memory_patcher.patch_workforce_agents(workforce, self.token_limit)
            logger.info(f"🔧 Applied memory patches to {patch_count} workforce agents")
            
            # Apply global memory fix to catch any missed objects
            patch_all_system_memory(self.token_limit)
            
            # NEW: Store WebSocket interceptor reference in workforce
            workforce.websocket_interceptor = self.websocket_interceptor
            
            logger.info("✅ Enhanced Workforce built successfully with memory fixes and WebSocket support")
            
            # NEW: Broadcast completion if interceptor available
            if self.websocket_interceptor:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(
                            self.websocket_interceptor.intercept_message(
                                message={"content": "Workforce initialized with 4 specialized agents"},
                                agent_type="System",
                                stage="initialization"
                            )
                        )
                except Exception as e:
                    logger.debug(f"Could not send completion message: {e}")
            
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

def create_enhanced_workforce(
    project_id: str, 
    token_limit: int = 100000,
    websocket_interceptor=None  # NEW: Add WebSocket interceptor parameter
) -> Workforce:
    """
    Convenience function to create an enhanced workforce with memory fixes and WebSocket support.
    
    MODIFIED: Added websocket_interceptor parameter
    Citation: Extended based on enhanced_process.py which needs to pass WebSocket
    interceptor to enable real-time agent message broadcasting
    
    Args:
        project_id: Project identifier
        token_limit: Token limit for all agents (default 100K)
        websocket_interceptor: Optional WebSocket interceptor for real-time updates (NEW)
        
    Returns:
        Workforce with memory-fixed agents and optional WebSocket support
    """
    builder = EnhancedWorkforceBuilder(project_id, token_limit, websocket_interceptor)
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