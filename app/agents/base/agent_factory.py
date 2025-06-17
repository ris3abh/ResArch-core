# app/agents/base/agent_factory.py
from typing import Dict, Any, Optional, List
import logging
from enum import Enum

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.messages import BaseMessage
from camel.toolkits import FunctionTool

from app.core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

class AgentType(Enum):
    """Enumeration of available agent types in SpinScribe"""
    COORDINATOR = "coordinator"
    STYLE_ANALYZER = "style_analyzer"
    CONTENT_PLANNER = "content_planner"
    CONTENT_GENERATOR = "content_generator"
    EDITOR_QA = "editor_qa"
    HUMAN_INTERFACE = "human_interface"

class SpinScribeAgentFactory:
    """
    Factory class for creating and managing CAMEL-powered agents in SpinScribe.
    Each agent type has specialized capabilities for content creation workflows.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._model_cache = {}
        
    def create_model(self, 
                    model_platform: str = None, 
                    model_type: str = None,
                    model_config: Dict[str, Any] = None) -> Any:
        """
        Create a CAMEL model instance with caching.
        
        Args:
            model_platform: Platform type (openai, anthropic, etc.)
            model_type: Specific model (gpt-4o-mini, claude-3-sonnet, etc.)
            model_config: Additional model configuration
            
        Returns:
            CAMEL model instance
        """
        # Use defaults from settings if not provided
        platform = model_platform or settings.default_model_platform
        model = model_type or settings.default_model_type
        config = model_config or settings.get_model_config()
        
        # Create cache key
        cache_key = f"{platform}:{model}:{hash(str(sorted(config.items())))}"
        
        if cache_key in self._model_cache:
            self.logger.debug(f"Using cached model: {cache_key}")
            return self._model_cache[cache_key]
        
        try:
            # Map platform strings to CAMEL types
            platform_map = {
                "openai": ModelPlatformType.OPENAI,
                "anthropic": ModelPlatformType.ANTHROPIC,
                "mistral": ModelPlatformType.MISTRAL,
                "google": ModelPlatformType.GEMINI,
            }
            
            # Map model strings to CAMEL types (add more as needed)
            model_map = {
                "gpt-4o-mini": ModelType.GPT_4O_MINI,
                "gpt-4o": ModelType.GPT_4O,
                "gpt-4": ModelType.GPT_4,
                "gpt-3.5-turbo": ModelType.GPT_3_5_TURBO,
                # Add more model mappings as needed
            }
            
            platform_type = platform_map.get(platform, ModelPlatformType.OPENAI)
            model_type_enum = model_map.get(model, ModelType.GPT_4O_MINI)
            
            # Create the model
            camel_model = ModelFactory.create(
                model_platform=platform_type,
                model_type=model_type_enum,
                model_config_dict=config,
            )
            
            # Cache the model
            self._model_cache[cache_key] = camel_model
            self.logger.info(f"Created and cached model: {platform}:{model}")
            
            return camel_model
            
        except Exception as e:
            self.logger.error(f"Failed to create model {platform}:{model}: {e}")
            # Fallback to a basic model
            fallback_model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
            )
            return fallback_model
    
    def create_agent(self, 
                    agent_type: AgentType,
                    project_id: str = None,
                    custom_instructions: str = None,
                    tools: List[FunctionTool] = None,
                    **kwargs) -> ChatAgent:
        """
        Create a specialized agent based on type.
        
        Args:
            agent_type: Type of agent to create
            project_id: Project ID for context
            custom_instructions: Additional instructions for the agent
            tools: List of tools to give the agent
            **kwargs: Additional configuration
            
        Returns:
            Configured ChatAgent instance
        """
        self.logger.info(f"Creating agent of type: {agent_type.value}")
        
        # Create model for the agent
        model = self.create_model()
        
        # Get agent-specific configuration
        agent_config = self._get_agent_config(agent_type)
        
        # Create system message
        system_message = self._create_system_message(
            agent_type, 
            project_id, 
            custom_instructions,
            agent_config
        )
        
        # Combine tools
        agent_tools = []
        if tools:
            agent_tools.extend(tools)
        
        # Add agent-specific tools
        specific_tools = self._get_agent_tools(agent_type, project_id)
        if specific_tools:
            agent_tools.extend(specific_tools)
        
        try:
            # Create the ChatAgent
            agent = ChatAgent(
                system_message=system_message,
                model=model,
                tools=agent_tools if agent_tools else None,
                **kwargs
            )
            
            # Add metadata
            agent._spinscribe_metadata = {
                "agent_type": agent_type.value,
                "project_id": project_id,
                "created_at": "now",  # You could use datetime here
                "version": "1.0"
            }
            
            self.logger.info(f"Successfully created {agent_type.value} agent")
            return agent
            
        except Exception as e:
            self.logger.error(f"Failed to create {agent_type.value} agent: {e}")
            raise
    
    def _get_agent_config(self, agent_type: AgentType) -> Dict[str, Any]:
        """Get configuration for a specific agent type."""
        configs = {
            AgentType.COORDINATOR: {
                "role": "Content Creation Coordinator",
                "primary_function": "Orchestrate multi-agent content creation workflows",
                "capabilities": [
                    "Task assignment and coordination",
                    "Workflow management",
                    "Quality assurance oversight",
                    "Human-agent communication"
                ]
            },
            AgentType.STYLE_ANALYZER: {
                "role": "Brand Voice & Style Analyst",
                "primary_function": "Analyze and extract brand voice patterns from client content",
                "capabilities": [
                    "Stylometric analysis",
                    "Brand voice extraction",
                    "Language pattern recognition",
                    "Style guide generation"
                ]
            },
            AgentType.CONTENT_PLANNER: {
                "role": "Content Strategy Planner",
                "primary_function": "Create structured content plans and outlines",
                "capabilities": [
                    "Content outline creation",
                    "SEO optimization planning",
                    "Audience targeting",
                    "Content structure design"
                ]
            },
            AgentType.CONTENT_GENERATOR: {
                "role": "Content Generation Specialist",
                "primary_function": "Generate high-quality content following brand guidelines",
                "capabilities": [
                    "Brand-aligned content creation",
                    "Multi-format content generation",
                    "Voice consistency maintenance",
                    "Creative adaptation"
                ]
            },
            AgentType.EDITOR_QA: {
                "role": "Content Editor & Quality Assurance",
                "primary_function": "Review, edit, and ensure content quality",
                "capabilities": [
                    "Content editing and refinement",
                    "Quality assurance",
                    "Brand compliance checking",
                    "Final review and approval"
                ]
            },
            AgentType.HUMAN_INTERFACE: {
                "role": "Human-AI Interface Coordinator",
                "primary_function": "Facilitate smooth human-agent collaboration",
                "capabilities": [
                    "Human feedback integration",
                    "Communication facilitation",
                    "Checkpoint management",
                    "Collaboration optimization"
                ]
            }
        }
        
        return configs.get(agent_type, {})
    
    def _create_system_message(self, 
                              agent_type: AgentType,
                              project_id: str = None,
                              custom_instructions: str = None,
                              agent_config: Dict[str, Any] = None) -> BaseMessage:
        """Create a system message for the agent."""
        
        config = agent_config or {}
        role = config.get("role", "SpinScribe Agent")
        primary_function = config.get("primary_function", "Assist with content creation")
        capabilities = config.get("capabilities", [])
        
        # Base instructions
        instructions = f"""You are a {role} in the SpinScribe content creation system.

            PRIMARY FUNCTION: {primary_function}

            KEY CAPABILITIES:
            {chr(10).join(f"• {cap}" for cap in capabilities)}

            OPERATIONAL GUIDELINES:
            • Always maintain professional, helpful communication
            • Focus on quality and brand consistency
            • Collaborate effectively with other agents and humans
            • Follow project-specific guidelines when provided
            • Ask for clarification when instructions are unclear
            • Provide clear, actionable outputs

            SPINSCRIBE SYSTEM CONTEXT:
            • You are part of a multi-agent content creation system
            • Your work contributes to a larger collaborative workflow
            • Quality and consistency are paramount
            • Human oversight and approval are integrated throughout the process"""

        # Add project-specific context
        if project_id:
            instructions += f"\n\nPROJECT CONTEXT:\n• Working on project: {project_id}"
        
        # Add custom instructions
        if custom_instructions:
            instructions += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"
        
        # Add agent-specific instructions
        agent_specific = self._get_agent_specific_instructions(agent_type)
        if agent_specific:
            instructions += f"\n\nSPECIALIZED INSTRUCTIONS:\n{agent_specific}"
        
        return BaseMessage.make_assistant_message(
            role_name=role,
            content=instructions
        )
    
    def _get_agent_specific_instructions(self, agent_type: AgentType) -> str:
        """Get specialized instructions for each agent type."""
        
        instructions = {
            AgentType.COORDINATOR: """
                • Monitor workflow progress and identify bottlenecks
                • Assign tasks to appropriate specialized agents
                • Ensure all human checkpoints are properly handled
                • Maintain clear communication between all participants
                • Escalate issues that require human intervention""",
            
            AgentType.STYLE_ANALYZER: """
                • Analyze provided content samples for stylistic patterns
                • Identify key linguistic markers and brand voice elements
                • Generate detailed style guides and language codes
                • Ensure analysis is thorough and actionable
                • Highlight unique brand voice characteristics""",
            
            AgentType.CONTENT_PLANNER: """
                • Create detailed, structured content outlines
                • Consider SEO requirements and keyword integration
                • Plan content flow and logical progression
                • Ensure outlines align with brand voice and audience
                • Include clear section descriptions and objectives""",
            
            AgentType.CONTENT_GENERATOR: """
                • Follow provided outlines and style guides precisely
                • Maintain consistent brand voice throughout content
                • Create engaging, high-quality content
                • Integrate keywords naturally and effectively
                • Ensure content meets all specified requirements""",
            
            AgentType.EDITOR_QA: """
                • Review content for accuracy, clarity, and consistency
                • Check adherence to brand guidelines and style
                • Identify areas for improvement or refinement
                • Ensure content meets quality standards
                • Provide constructive feedback and suggestions""",
            
            AgentType.HUMAN_INTERFACE: """
                • Facilitate clear communication between humans and agents
                • Present information in easily digestible formats
                • Manage checkpoint processes and approvals
                • Collect and integrate human feedback effectively
                • Ensure smooth collaboration and workflow progression"""
        }
        
        return instructions.get(agent_type, "")
    
    def _get_agent_tools(self, agent_type: AgentType, project_id: str = None) -> List[FunctionTool]:
        """Get specialized tools for each agent type."""
        # This will be expanded as we create more tools
        # For now, return empty list - we'll add tools in subsequent files
        return []
    
    def create_agent_by_name(self, agent_name: str, **kwargs) -> ChatAgent:
        """Create an agent by string name (convenience method)."""
        try:
            agent_type = AgentType(agent_name.lower())
            return self.create_agent(agent_type, **kwargs)
        except ValueError:
            raise ValueError(f"Unknown agent type: {agent_name}. Available types: {[t.value for t in AgentType]}")
    
    def get_available_agent_types(self) -> List[str]:
        """Get list of available agent types."""
        return [agent_type.value for agent_type in AgentType]
    
    def clear_model_cache(self):
        """Clear the model cache (useful for testing or memory management)."""
        self._model_cache.clear()
        self.logger.info("Model cache cleared")

# Global factory instance
agent_factory = SpinScribeAgentFactory()