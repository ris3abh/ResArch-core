# app/agents/base/agent_factory.py - Fixed for CAMEL compatibility
from typing import Dict, Any, Optional, List
import logging
import os
from enum import Enum
from sqlalchemy.orm import Session

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.messages import BaseMessage
from camel.toolkits import FunctionTool
from camel.configs import ChatGPTConfig, AnthropicConfig

from app.core.config import settings
from app.database.connection import SessionLocal
from app.database.models.project import Project

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
    Now includes database integration for project-specific context.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._model_cache = {}
        self._ensure_environment_variables()
        
    def _ensure_environment_variables(self):
        """Ensure API keys are properly set as environment variables for CAMEL"""
        
        # Set OpenAI API key if available
        if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
            os.environ['OPENAI_API_KEY'] = settings.openai_api_key
            self.logger.debug("OpenAI API key set in environment")
        
        # Set Anthropic API key if available
        if settings.anthropic_api_key and settings.anthropic_api_key != "your_anthropic_api_key_here":
            os.environ['ANTHROPIC_API_KEY'] = settings.anthropic_api_key
            self.logger.debug("Anthropic API key set in environment")
        
        # Set other API keys
        if hasattr(settings, 'mistral_api_key') and settings.mistral_api_key:
            os.environ['MISTRAL_API_KEY'] = settings.mistral_api_key
            self.logger.debug("Mistral API key set in environment")
        
        if hasattr(settings, 'google_api_key') and settings.google_api_key:
            os.environ['GOOGLE_API_KEY'] = settings.google_api_key
            self.logger.debug("Google API key set in environment")
        
    def create_model(self, 
                    model_platform: str = None, 
                    model_type: str = None,
                    model_config: Dict[str, Any] = None) -> Any:
        """
        Create a CAMEL model instance with caching.
        
        Args:
            model_platform: Platform type (openai, anthropic, etc.)
            model_type: Specific model (gpt-4o-mini, claude-3-sonnet, etc.)
            model_config: Additional model configuration (no API keys!)
            
        Returns:
            CAMEL model instance
        """
        # Use defaults from settings if not provided
        platform = model_platform or settings.default_model_platform
        model = model_type or settings.default_model_type
        
        # Create proper CAMEL config based on platform
        if model_config:
            config = model_config
        else:
            config = self._get_default_model_config(platform)
        
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
            
            # Create proper config object based on platform
            if platform == "openai":
                model_config_obj = ChatGPTConfig(**config)
            elif platform == "anthropic":
                model_config_obj = AnthropicConfig(**config)
            else:
                # For other platforms, use the dict directly
                model_config_obj = config
            
            # Create the model - CAMEL will get API keys from environment
            camel_model = ModelFactory.create(
                model_platform=platform_type,
                model_type=model_type_enum,
                model_config_dict=model_config_obj.as_dict() if hasattr(model_config_obj, 'as_dict') else model_config_obj,
            )
            
            # Cache the model
            self._model_cache[cache_key] = camel_model
            self.logger.info(f"Created and cached model: {platform}:{model}")
            
            return camel_model
            
        except Exception as e:
            self.logger.error(f"Failed to create model {platform}:{model}: {e}")
            
            # Fallback to a basic model with minimal config
            try:
                fallback_config = ChatGPTConfig(temperature=0.7, max_tokens=1000)
                fallback_model = ModelFactory.create(
                    model_platform=ModelPlatformType.OPENAI,
                    model_type=ModelType.GPT_4O_MINI,
                    model_config_dict=fallback_config.as_dict(),
                )
                self.logger.info("Using fallback model configuration")
                return fallback_model
            except Exception as fallback_error:
                self.logger.error(f"Even fallback model failed: {fallback_error}")
                raise fallback_error
    
    def _get_default_model_config(self, platform: str) -> Dict[str, Any]:
        """Get default configuration for a specific platform"""
        
        base_config = {
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        
        if platform == "openai":
            return {
                **base_config,
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            }
        elif platform == "anthropic":
            return {
                "max_tokens": 2000,
                "temperature": 0.7,
                "top_p": 1.0,
            }
        elif platform == "mistral":
            return {
                **base_config,
                "top_p": 1.0,
                "safe_prompt": False,
            }
        else:
            return base_config
    
    def get_project_context(self, project_id: str) -> Dict[str, Any]:
        """
        Retrieve project context from database for agent initialization.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dictionary containing project context data
        """
        if not project_id:
            return {}
        
        try:
            db = SessionLocal()
            project = db.query(Project).filter(Project.project_id == project_id).first()
            
            if not project:
                self.logger.warning(f"Project {project_id} not found in database")
                return {"project_id": project_id, "error": "Project not found"}
            
            project_context = {
                "project_id": project.project_id,
                "client_name": project.client_name,
                "description": project.description,
                "status": project.status,
                "configuration": project.configuration or {},
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "last_activity": project.last_activity_at.isoformat() if project.last_activity_at else None,
            }
            
            db.close()
            return project_context
            
        except Exception as e:
            self.logger.error(f"Error retrieving project context for {project_id}: {e}")
            return {"project_id": project_id, "error": str(e)}
    
    def create_agent(self, 
                    agent_type: AgentType,
                    project_id: str = None,
                    custom_instructions: str = None,
                    tools: List[FunctionTool] = None,
                    **kwargs) -> ChatAgent:
        """
        Create a specialized agent based on type with project context.
        
        Args:
            agent_type: Type of agent to create
            project_id: Project ID for context and database access
            custom_instructions: Additional instructions for the agent
            tools: List of tools to give the agent
            **kwargs: Additional configuration
            
        Returns:
            Configured ChatAgent instance with project context
        """
        self.logger.info(f"Creating agent of type: {agent_type.value} for project: {project_id}")
        
        # Get project context from database
        project_context = self.get_project_context(project_id) if project_id else {}
        
        # Create model for the agent
        model = self.create_model()
        
        # Get agent-specific configuration
        agent_config = self._get_agent_config(agent_type)
        
        # Create system message with project context
        system_message = self._create_system_message(
            agent_type, 
            project_context,
            custom_instructions,
            agent_config
        )
        
        # Combine tools
        agent_tools = []
        if tools:
            agent_tools.extend(tools)
        
        # Add agent-specific tools (including database access tools)
        specific_tools = self._get_agent_tools(agent_type, project_context)
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
            
            # Add enhanced metadata with project context
            agent._spinscribe_metadata = {
                "agent_type": agent_type.value,
                "project_id": project_id,
                "project_context": project_context,
                "created_at": "now",  # You could use datetime here
                "version": "1.0",
                "has_database_access": bool(project_id),
                "client_name": project_context.get("client_name"),
            }
            
            # Add database session for agents that need it
            if project_id and agent_type in [AgentType.STYLE_ANALYZER, AgentType.CONTENT_PLANNER]:
                agent._db_session_factory = SessionLocal
                agent._project_id = project_id
            
            self.logger.info(f"Successfully created {agent_type.value} agent with project context")
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
                    "Human-agent communication",
                    "Project status tracking"
                ],
                "database_access": ["projects", "chat_instances", "human_checkpoints"]
            },
            AgentType.STYLE_ANALYZER: {
                "role": "Brand Voice & Style Analyst",
                "primary_function": "Analyze and extract brand voice patterns from client content",
                "capabilities": [
                    "Stylometric analysis",
                    "Brand voice extraction",
                    "Language pattern recognition",
                    "Style guide generation",
                    "Content sample analysis"
                ],
                "database_access": ["projects", "knowledge_items"]
            },
            AgentType.CONTENT_PLANNER: {
                "role": "Content Strategy Planner",
                "primary_function": "Create structured content plans and outlines",
                "capabilities": [
                    "Content outline creation",
                    "SEO optimization planning",
                    "Audience targeting",
                    "Content structure design",
                    "Project requirement analysis"
                ],
                "database_access": ["projects", "knowledge_items"]
            },
            AgentType.CONTENT_GENERATOR: {
                "role": "Content Generation Specialist",
                "primary_function": "Generate high-quality content following brand guidelines",
                "capabilities": [
                    "Brand-aligned content creation",
                    "Multi-format content generation",
                    "Voice consistency maintenance",
                    "Creative adaptation",
                    "Style guide adherence"
                ],
                "database_access": ["projects", "knowledge_items"]
            },
            AgentType.EDITOR_QA: {
                "role": "Content Editor & Quality Assurance",
                "primary_function": "Review, edit, and ensure content quality",
                "capabilities": [
                    "Content editing and refinement",
                    "Quality assurance",
                    "Brand compliance checking",
                    "Final review and approval",
                    "Error detection and correction"
                ],
                "database_access": ["projects", "knowledge_items"]
            },
            AgentType.HUMAN_INTERFACE: {
                "role": "Human-AI Interface Coordinator",
                "primary_function": "Facilitate smooth human-agent collaboration",
                "capabilities": [
                    "Human feedback integration",
                    "Communication facilitation",
                    "Checkpoint management",
                    "Collaboration optimization",
                    "Status reporting"
                ],
                "database_access": ["projects", "chat_instances", "human_checkpoints"]
            }
        }
        
        return configs.get(agent_type, {})
    
    def _create_system_message(self, 
                              agent_type: AgentType,
                              project_context: Dict[str, Any] = None,
                              custom_instructions: str = None,
                              agent_config: Dict[str, Any] = None) -> BaseMessage:
        """Create a system message for the agent with project context."""
        
        config = agent_config or {}
        role = config.get("role", "SpinScribe Agent")
        primary_function = config.get("primary_function", "Assist with content creation")
        capabilities = config.get("capabilities", [])
        database_access = config.get("database_access", [])
        
        # Base instructions
        instructions = f"""You are a {role} in the SpinScribe content creation system.

        PRIMARY FUNCTION: {primary_function}

        KEY CAPABILITIES:
        {chr(10).join(f"• {cap}" for cap in capabilities)}

        DATABASE ACCESS: You have access to the following data sources:
        {chr(10).join(f"• {access}" for access in database_access)}

        OPERATIONAL GUIDELINES:
        • Always maintain professional, helpful communication
        • Focus on quality and brand consistency
        • Collaborate effectively with other agents and humans
        • Follow project-specific guidelines when provided
        • Ask for clarification when instructions are unclear
        • Provide clear, actionable outputs
        • Use project context to inform your responses

        SPINSCRIBE SYSTEM CONTEXT:
        • You are part of a multi-agent content creation system
        • Your work contributes to a larger collaborative workflow
        • Quality and consistency are paramount
        • Human oversight and approval are integrated throughout the process
        • You have access to project-specific knowledge and configuration"""

        # Add project-specific context
        if project_context and not project_context.get("error"):
            client_name = project_context.get("client_name", "Unknown Client")
            description = project_context.get("description", "No description available")
            config_data = project_context.get("configuration", {})
            
            instructions += f"""

                PROJECT CONTEXT:
                • Client: {client_name}
                • Project ID: {project_context.get("project_id")}
                • Description: {description}
                • Status: {project_context.get("status", "unknown")}"""

            # Add configuration details if available
            if config_data:
                instructions += f"\n• Project Configuration:"
                for key, value in config_data.items():
                    instructions += f"\n  - {key}: {value}"
        
        # Add custom instructions
        if custom_instructions:
            instructions += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"
        
        # Add agent-specific instructions
        agent_specific = self._get_agent_specific_instructions(agent_type, project_context)
        if agent_specific:
            instructions += f"\n\nSPECIALIZED INSTRUCTIONS:\n{agent_specific}"
        
        return BaseMessage.make_assistant_message(
            role_name=role,
            content=instructions
        )
    
    def _get_agent_specific_instructions(self, agent_type: AgentType, project_context: Dict[str, Any] = None) -> str:
        """Get specialized instructions for each agent type with project awareness."""
        
        base_instructions = {
            AgentType.COORDINATOR: """
                • Monitor workflow progress and identify bottlenecks
                • Assign tasks to appropriate specialized agents
                • Ensure all human checkpoints are properly handled
                • Maintain clear communication between all participants
                • Escalate issues that require human intervention
                • Track project milestones and deadlines
                • Coordinate with database to update project status""",
            
            AgentType.STYLE_ANALYZER: """
                • Analyze provided content samples for stylistic patterns
                • Identify key linguistic markers and brand voice elements
                • Generate detailed style guides and language codes
                • Ensure analysis is thorough and actionable
                • Highlight unique brand voice characteristics
                • Access project knowledge base for style samples
                • Store analysis results for future reference""",
            
            AgentType.CONTENT_PLANNER: """
                • Create detailed, structured content outlines
                • Consider SEO requirements and keyword integration
                • Plan content flow and logical progression
                • Ensure outlines align with brand voice and audience
                • Include clear section descriptions and objectives
                • Reference project configuration for content guidelines
                • Plan content that fits the client's target audience""",
            
            AgentType.CONTENT_GENERATOR: """
                • Follow provided outlines and style guides precisely
                • Maintain consistent brand voice throughout content
                • Create engaging, high-quality content
                • Integrate keywords naturally and effectively
                • Ensure content meets all specified requirements
                • Reference project style guidelines from database
                • Adapt tone to match client's brand voice""",
            
            AgentType.EDITOR_QA: """
                • Review content for accuracy, clarity, and consistency
                • Check adherence to brand guidelines and style
                • Identify areas for improvement or refinement
                • Ensure content meets quality standards
                • Provide constructive feedback and suggestions
                • Verify compliance with project requirements
                • Cross-reference against client style guidelines""",
            
            AgentType.HUMAN_INTERFACE: """
                • Facilitate clear communication between humans and agents
                • Present information in easily digestible formats
                • Manage checkpoint processes and approvals
                • Collect and integrate human feedback effectively
                • Ensure smooth collaboration and workflow progression
                • Update project status in database as needed
                • Coordinate human review schedules and deadlines"""
        }
        
        instructions = base_instructions.get(agent_type, "")
        
        # Add project-specific context if available
        if project_context and not project_context.get("error"):
            config = project_context.get("configuration", {})
            
            if config:
                instructions += f"\n\nPROJECT-SPECIFIC GUIDANCE:"
                
                if "brand_voice" in config:
                    instructions += f"\n• Brand Voice: {config['brand_voice']}"
                
                if "target_audience" in config:
                    instructions += f"\n• Target Audience: {config['target_audience']}"
                
                if "content_types" in config:
                    instructions += f"\n• Content Types: {', '.join(config['content_types'])}"
                
                if "style_guidelines" in config:
                    instructions += f"\n• Style Guidelines: {config['style_guidelines']}"
        
        return instructions
    
    def _get_agent_tools(self, agent_type: AgentType, project_context: Dict[str, Any] = None) -> List[FunctionTool]:
        """Get specialized tools for each agent type, including database access tools."""
        tools = []
        
        # Database access tools for agents that need them
        if project_context and not project_context.get("error"):
            
            # Project information access tool
            def get_project_info() -> str:
                """
                Get current project information and configuration.
                
                Returns:
                    str: Formatted project information including client name, description, status, and configuration
                """
                try:
                    project_id = project_context.get("project_id")
                    if not project_id:
                        return "No project ID available"
                    
                    # Get fresh project data
                    fresh_context = self.get_project_context(project_id)
                    if fresh_context.get("error"):
                        return f"Error accessing project: {fresh_context['error']}"
                    
                    return f"""Project Information:
                    Client: {fresh_context.get('client_name', 'Unknown')}
                    Description: {fresh_context.get('description', 'No description')}
                    Status: {fresh_context.get('status', 'unknown')}
                    Configuration: {fresh_context.get('configuration', {})}
                    Last Activity: {fresh_context.get('last_activity', 'Unknown')}"""
                    
                except Exception as e:
                    return f"Error retrieving project info: {str(e)}"
            
            tools.append(FunctionTool(get_project_info))
            
            # Update project activity tool (for coordinators and human interface)
            if agent_type in [AgentType.COORDINATOR, AgentType.HUMAN_INTERFACE]:
                def update_project_activity() -> str:
                    """
                    Update the project's last activity timestamp.
                    
                    Returns:
                        str: Success or error message about the activity update
                    """
                    try:
                        project_id = project_context.get("project_id")
                        if not project_id:
                            return "No project ID available"
                        
                        db = SessionLocal()
                        project = db.query(Project).filter(Project.project_id == project_id).first()
                        
                        if project:
                            project.update_activity()
                            db.commit()
                            db.close()
                            return "Project activity updated successfully"
                        else:
                            db.close()
                            return "Project not found"
                            
                    except Exception as e:
                        return f"Error updating project activity: {str(e)}"
                
                tools.append(FunctionTool(update_project_activity))
        
        # Agent-specific tools with better documentation
        if agent_type == AgentType.STYLE_ANALYZER:
            def analyze_text_style(text: str) -> str:
                """
                Analyze the style characteristics of provided text.
                
                Args:
                    text (str): The text content to analyze for style patterns
                    
                Returns:
                    str: Detailed style analysis including metrics and characteristics
                """
                # Basic style analysis - can be enhanced with more sophisticated analysis
                words = text.split()
                sentences = text.split('.')
                
                avg_words_per_sentence = len(words) / max(len(sentences), 1)
                word_lengths = [len(word.strip('.,!?;:')) for word in words if word.strip('.,!?;:')]
                avg_word_length = sum(word_lengths) / max(len(word_lengths), 1)
                
                analysis = f"""Style Analysis Results:
                Text Length: {len(text)} characters
                Word Count: {len(words)}
                Sentence Count: {len(sentences)}
                Average Words per Sentence: {avg_words_per_sentence:.1f}
                Average Word Length: {avg_word_length:.1f} characters
                
                Style Characteristics:
                - Sentence Complexity: {'High' if avg_words_per_sentence > 20 else 'Medium' if avg_words_per_sentence > 15 else 'Low'}
                - Vocabulary Sophistication: {'High' if avg_word_length > 6 else 'Medium' if avg_word_length > 4 else 'Basic'}
                """
                
                return analysis
            
            tools.append(FunctionTool(analyze_text_style))
        
        elif agent_type == AgentType.CONTENT_PLANNER:
            def create_content_outline(topic: str, content_type: str = "blog", target_length: int = 1000) -> str:
                """
                Create a structured outline for content creation.
                
                Args:
                    topic (str): The main topic or subject for the content
                    content_type (str): Type of content (blog, article, social_media, etc.)
                    target_length (int): Target word count for the content
                    
                Returns:
                    str: Structured content outline with sections and word count distribution
                """
                
                # Basic outline structure based on content type
                if content_type.lower() == "blog":
                    outline = f"""Content Outline: {topic}
                    
                    I. Introduction (10% - ~{int(target_length * 0.1)} words)
                       - Hook: Engaging opening statement
                       - Context: Background information
                       - Thesis: Main point or value proposition
                    
                    II. Main Content (75% - ~{int(target_length * 0.75)} words)
                       - Section 1: Key Point A
                       - Section 2: Key Point B  
                       - Section 3: Key Point C
                       - Supporting examples and evidence
                    
                    III. Conclusion (15% - ~{int(target_length * 0.15)} words)
                       - Summary of key points
                       - Call to action
                       - Next steps or recommendations
                    
                    SEO Considerations:
                    - Primary keyword: {topic}
                    - Target length: {target_length} words
                    - Include relevant subheadings
                    - Natural keyword integration"""
                
                else:
                    outline = f"""Content Outline: {topic} ({content_type})
                    
                    Structure will be adapted based on content type: {content_type}
                    Target length: {target_length} words
                    
                    Key sections to include:
                    - Opening/Hook
                    - Main content body
                    - Conclusion/CTA
                    
                    Please specify content type for more detailed outline."""
                
                return outline
            
            tools.append(FunctionTool(create_content_outline))
        
        elif agent_type == AgentType.CONTENT_GENERATOR:
            def generate_content_section(section_title: str, key_points: str, word_count: int = 200) -> str:
                """
                Generate content for a specific section based on title and key points.
    
                Args:
                    section_title (str): The title or heading for this content section
                    key_points (str): Key points or topics to cover in this section
                    word_count (int): Target word count for the generated section
                    
                Returns:
                    str: Generated content template for the specified section
                """
                
                # This is a placeholder - in practice, this might use the LLM itself
                # or integrate with other content generation tools
                
                template = f"""Section: {section_title}

                [This is a content generation template. In the actual implementation, 
                this would generate {word_count} words of content covering:]

                Key Points to Address:
                {key_points}

                Target Word Count: {word_count}
                
                [The generated content would maintain brand voice consistency 
                and follow project guidelines as specified in the agent's context.]"""
                
                return template
            
            tools.append(FunctionTool(generate_content_section))
        
        elif agent_type == AgentType.EDITOR_QA:
            def check_content_quality(content: str) -> str:
                """
                Perform basic quality checks on content.
                
                Args:
                    content (str): The content text to analyze for quality metrics
                    
                Returns:
                    str: Quality assessment report with metrics and recommendations
                """
                
                # Basic quality metrics
                word_count = len(content.split())
                char_count = len(content)
                sentence_count = len([s for s in content.split('.') if s.strip()])
                paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
                
                # Simple readability check
                avg_sentence_length = word_count / max(sentence_count, 1)
                readability = "Easy" if avg_sentence_length < 15 else "Medium" if avg_sentence_length < 25 else "Complex"
                
                quality_report = f"""Content Quality Assessment:
                
                Metrics:
                - Word Count: {word_count}
                - Character Count: {char_count}
                - Sentences: {sentence_count}
                - Paragraphs: {paragraph_count}
                - Average Sentence Length: {avg_sentence_length:.1f} words
                - Readability: {readability}
                
                Quality Checks:
                - Length appropriate: {'✓' if 300 <= word_count <= 3000 else '⚠'}
                - Paragraph structure: {'✓' if paragraph_count >= 3 else '⚠'}
                - Sentence variety: {'✓' if 10 <= avg_sentence_length <= 25 else '⚠'}
                
                Recommendations:
                {'Content length is good' if 300 <= word_count <= 3000 else 'Consider adjusting content length'}
                {'Good paragraph structure' if paragraph_count >= 3 else 'Consider adding more paragraph breaks'}
                {'Good sentence length variety' if 10 <= avg_sentence_length <= 25 else 'Consider varying sentence lengths'}
                """
                
                return quality_report
            
            tools.append(FunctionTool(check_content_quality))
        
        return tools
    
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
    
    def get_project_agents(self, project_id: str) -> Dict[str, Any]:
        """Get information about agents created for a specific project."""
        # This could be enhanced to track active agents per project
        project_context = self.get_project_context(project_id)
        
        return {
            "project_id": project_id,
            "project_context": project_context,
            "available_agent_types": self.get_available_agent_types(),
            "recommended_agents": self._get_recommended_agents_for_project(project_context)
        }
    
    def _get_recommended_agents_for_project(self, project_context: Dict[str, Any]) -> List[str]:
        """Recommend agent types based on project configuration."""
        if project_context.get("error"):
            return ["coordinator"]  # Default recommendation
        
        config = project_context.get("configuration", {})
        content_types = config.get("content_types", [])
        
        # Basic recommendation logic
        recommended = ["coordinator"]  # Always recommend coordinator
        
        if content_types:
            recommended.extend(["style_analyzer", "content_planner", "content_generator", "editor_qa"])
        
        if config.get("human_review_required", True):
            recommended.append("human_interface")
        
        return list(set(recommended))  # Remove duplicates
    
    def check_api_status(self) -> Dict[str, bool]:
        """Check which API keys are properly configured"""
        status = {}
        
        # Check OpenAI
        openai_key = os.getenv('OPENAI_API_KEY')
        status['openai'] = bool(openai_key and openai_key != "your_openai_api_key_here")
        
        # Check Anthropic
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        status['anthropic'] = bool(anthropic_key and anthropic_key != "your_anthropic_api_key_here")
        
        # Check others
        status['mistral'] = bool(os.getenv('MISTRAL_API_KEY'))
        status['google'] = bool(os.getenv('GOOGLE_API_KEY'))
        
        return status

# Global factory instance
agent_factory = SpinScribeAgentFactory()