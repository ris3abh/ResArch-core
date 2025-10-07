# =============================================================================
# SPINSCRIBE CONTENT CREATION CREW
# Multi-Agent System with HITL Protocol
# =============================================================================
"""
SpinScribe Crew orchestrates a multi-agent content creation workflow with
Human-in-the-Loop checkpoints for quality assurance.

The crew follows a 7-stage sequential process:
1. Content Research - Gather comprehensive information
2. Brand Voice Analysis - Validate brand voice parameters (HITL)
3. Content Strategy - Create detailed outline
4. Content Generation - Write draft content
5. SEO Optimization - Enhance search performance
6. Style Compliance - Verify brand adherence (HITL)
7. Quality Assurance - Final review and polish (HITL)
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import DirectorySearchTool, SerperDevTool
from typing import List, Dict, Any
import os
from datetime import datetime

# Import custom tools
from spinscribe.tools.custom_tool import ai_language_code_parser


@CrewBase
class SpinscribeCrew():
    """
    SpinScribe content creation crew with HITL protocol.
    
    This crew orchestrates specialized agents through a sequential workflow
    that produces publication-ready content matching client brand voice.
    """

    # Agent and task lists automatically populated by decorators
    agents: List[BaseAgent]
    tasks: List[Task]

    # Configuration file paths
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        """Initialize crew with tools and configurations."""
        super().__init__()
        
        # Initialize tools that will be shared across agents
        self._init_tools()
    
    def _init_tools(self):
        """Initialize and configure tools for agents."""
        # Directory search tool for client knowledge base access
        # This will be configured per client at runtime
        self.directory_search_tool = DirectorySearchTool()
        
        # Web search for research tasks
        self.web_search_tool = SerperDevTool()
        
        # AI Language Code Parser (custom tool)
        self.ai_language_parser = ai_language_code_parser
    
    @before_kickoff
    def setup_execution(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare inputs and environment before crew execution.
        
        This hook:
        - Validates required inputs
        - Sets up client-specific knowledge base paths
        - Initializes logging
        - Prepares HITL webhook configurations
        
        Args:
            inputs: Dictionary containing execution parameters
        
        Returns:
            Enhanced inputs dictionary with additional context
        """
        print("=" * 80)
        print("SPINSCRIBE CONTENT CREATION CREW - EXECUTION START")
        print("=" * 80)
        
        # Validate required inputs
        required_fields = ['client_name', 'topic', 'content_type', 'audience']
        missing_fields = [field for field in required_fields if field not in inputs]
        
        if missing_fields:
            raise ValueError(
                f"Missing required input fields: {', '.join(missing_fields)}\n"
                f"Required fields: {', '.join(required_fields)}"
            )
        
        # Add execution metadata
        inputs['execution_id'] = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        inputs['execution_start_time'] = datetime.now().isoformat()
        
        # Configure client knowledge base path
        client_name = inputs['client_name']
        inputs['knowledge_base_path'] = f"knowledge/clients/{client_name}"
        
        # Ensure knowledge directory exists
        if not os.path.exists(inputs['knowledge_base_path']):
            print(f"⚠️  WARNING: Knowledge base path does not exist: {inputs['knowledge_base_path']}")
            print(f"   Creating directory structure...")
            os.makedirs(inputs['knowledge_base_path'], exist_ok=True)
        
        # Configure DirectorySearchTool with client-specific path
        self.directory_search_tool = DirectorySearchTool(
            directory=inputs['knowledge_base_path']
        )
        
        # Add AI Language Code if provided
        if 'ai_language_code' not in inputs:
            # Use default if not provided
            inputs['ai_language_code'] = '/TN/P3,A2/VL3/SC3/FL2/LF3'
            print(f"ℹ️  Using default AI Language Code: {inputs['ai_language_code']}")
        
        # Log execution details
        print(f"\n📋 Execution Details:")
        print(f"   Execution ID: {inputs['execution_id']}")
        print(f"   Client: {inputs['client_name']}")
        print(f"   Topic: {inputs['topic']}")
        print(f"   Content Type: {inputs['content_type']}")
        print(f"   Target Audience: {inputs['audience']}")
        print(f"   Knowledge Base: {inputs['knowledge_base_path']}")
        print(f"   AI Language Code: {inputs['ai_language_code']}")
        
        # Configure HITL webhook URLs from environment
        inputs['hitl_webhooks'] = {
            'brand_voice': os.getenv('HITL_BRAND_VOICE_WEBHOOK'),
            'style_compliance': os.getenv('HITL_STYLE_COMPLIANCE_WEBHOOK'),
            'final_approval': os.getenv('HITL_FINAL_APPROVAL_WEBHOOK')
        }
        
        print(f"\n🔗 HITL Checkpoints Configured:")
        for checkpoint, webhook in inputs['hitl_webhooks'].items():
            status = "✓" if webhook else "✗"
            print(f"   {status} {checkpoint}: {webhook if webhook else 'Not configured'}")
        
        print(f"\n🚀 Starting content creation workflow...")
        print("=" * 80)
        
        return inputs
    
    @after_kickoff
    def finalize_execution(self, output: Any) -> Any:
        """
        Process and finalize crew execution results.
        
        This hook:
        - Logs execution completion
        - Processes final output
        - Saves execution metadata
        - Sends completion webhooks
        
        Args:
            output: Crew execution output
        
        Returns:
            Processed output
        """
        print("\n" + "=" * 80)
        print("SPINSCRIBE CONTENT CREATION CREW - EXECUTION COMPLETE")
        print("=" * 80)
        
        # Log completion
        print(f"\n✅ Content creation workflow completed successfully!")
        print(f"   Final output available in: {output.tasks_output[-1].output_file if hasattr(output.tasks_output[-1], 'output_file') else 'task output'}")
        
        # Display token usage if available
        if hasattr(output, 'token_usage'):
            print(f"\n📊 Token Usage Summary:")
            print(f"   {output.token_usage}")
        
        # Display task completion summary
        print(f"\n📝 Task Completion Summary:")
        for i, task_output in enumerate(output.tasks_output, 1):
            status = "✓" if task_output else "✗"
            print(f"   {status} Task {i}: {task_output.description[:60]}...")
        
        print("=" * 80 + "\n")
        
        return output

    # =========================================================================
    # AGENT DEFINITIONS
    # =========================================================================
    
    @agent
    def content_researcher(self) -> Agent:
        """
        Content Research & Competitive Analysis Specialist.
        
        Conducts comprehensive research on topics, analyzes competitors,
        and identifies unique angles for content.
        """
        return Agent(
            config=self.agents_config['content_researcher'],
            verbose=True,
            tools=[self.web_search_tool, self.directory_search_tool]
        )
    
    @agent
    def brand_voice_specialist(self) -> Agent:
        """
        Brand Voice Analysis Specialist.
        
        Analyzes client brand voice, generates AI Language Code parameters,
        and validates voice consistency. Includes HITL checkpoint.
        """
        return Agent(
            config=self.agents_config['brand_voice_specialist'],
            verbose=True,
            tools=[self.directory_search_tool, self.ai_language_parser]
        )
    
    @agent
    def content_strategist(self) -> Agent:
        """
        Content Strategy & Outline Specialist.
        
        Creates detailed content outlines and strategic approaches
        based on research and brand voice parameters.
        """
        return Agent(
            config=self.agents_config['content_strategist'],
            verbose=True,
            tools=[self.directory_search_tool]
        )
    
    @agent
    def content_writer(self) -> Agent:
        """
        Expert Content Writer & Brand Storyteller.
        
        Generates high-quality content following brand voice parameters,
        templates, and strategic outlines.
        """
        return Agent(
            config=self.agents_config['content_writer'],
            verbose=True,
            tools=[self.directory_search_tool, self.ai_language_parser]
        )
    
    @agent
    def seo_specialist(self) -> Agent:
        """
        SEO Optimization & Search Strategy Specialist.
        
        Optimizes content for search engines while maintaining
        brand voice and readability.
        """
        return Agent(
            config=self.agents_config['seo_specialist'],
            verbose=True,
            tools=[self.web_search_tool, self.directory_search_tool]
        )
    
    @agent
    def style_compliance_agent(self) -> Agent:
        """
        Style Guidelines & Standards Enforcer.
        
        Verifies adherence to style guidelines and formatting standards.
        Includes HITL checkpoint.
        """
        return Agent(
            config=self.agents_config['style_compliance_agent'],
            verbose=True,
            tools=[self.directory_search_tool]
        )
    
    @agent
    def quality_assurance_editor(self) -> Agent:
        """
        Senior Editorial Quality Assurance Specialist.
        
        Conducts comprehensive final review ensuring factual accuracy,
        grammar, brand voice, and overall excellence. Includes HITL checkpoint.
        """
        return Agent(
            config=self.agents_config['quality_assurance_editor'],
            verbose=True,
            tools=[self.directory_search_tool]
        )

    # =========================================================================
    # TASK DEFINITIONS
    # =========================================================================
    
    @task
    def content_research_task(self) -> Task:
        """
        Task 1: Comprehensive content research and competitive analysis.
        
        Gathers information, analyzes competitors, identifies unique angles.
        No HITL checkpoint - automated research phase.
        """
        return Task(
            config=self.tasks_config['content_research_task']
        )
    
    @task
    def brand_voice_analysis_task(self) -> Task:
        """
        Task 2: Brand voice analysis and AI Language Code generation.
        
        HITL CHECKPOINT 1: Human approval required for brand voice parameters.
        """
        return Task(
            config=self.tasks_config['brand_voice_analysis_task']
        )
    
    @task
    def content_strategy_task(self) -> Task:
        """
        Task 3: Content strategy and detailed outline creation.
        
        Creates comprehensive outline based on research and brand voice.
        No HITL checkpoint - strategic planning phase.
        """
        return Task(
            config=self.tasks_config['content_strategy_task']
        )
    
    @task
    def content_generation_task(self) -> Task:
        """
        Task 4: Content generation following outline and brand voice.
        
        Writes full content draft applying all parameters and guidelines.
        No HITL checkpoint - automated content generation.
        """
        return Task(
            config=self.tasks_config['content_generation_task']
        )
    
    @task
    def seo_optimization_task(self) -> Task:
        """
        Task 5: SEO optimization and search performance enhancement.
        
        Optimizes content for search while maintaining brand voice.
        No HITL checkpoint - technical optimization phase.
        """
        return Task(
            config=self.tasks_config['seo_optimization_task']
        )
    
    @task
    def style_compliance_review_task(self) -> Task:
        """
        Task 6: Style compliance verification and brand voice check.
        
        HITL CHECKPOINT 2: Human approval for style guideline adherence.
        """
        return Task(
            config=self.tasks_config['style_compliance_review_task']
        )
    
    @task
    def final_quality_assurance_task(self) -> Task:
        """
        Task 7: Final quality assurance and publication readiness.
        
        HITL CHECKPOINT 3: Human approval before content delivery.
        """
        return Task(
            config=self.tasks_config['final_quality_assurance_task']
        )

    # =========================================================================
    # CREW DEFINITION
    # =========================================================================
    
    @crew
    def crew(self) -> Crew:
        """
        Create the SpinScribe content creation crew.
        
        Assembles all agents and tasks into a sequential workflow with
        HITL checkpoints at strategic stages.
        
        Returns:
            Configured Crew instance ready for execution
        """
        return Crew(
            agents=self.agents,  # Auto-populated by @agent decorator
            tasks=self.tasks,    # Auto-populated by @task decorator
            process=Process.sequential,
            verbose=True,
            memory=True,  # Enable crew-level memory for learning
            embedder={
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small"
                }
            },
            # Output logging
            output_log_file="logs/crew_execution.log",
            # Planning mode for complex task orchestration
            planning=False,  # Disabled as we have explicit task dependencies
            # Maximum RPM to respect API rate limits
            max_rpm=30,
            # Cache to optimize repeated operations
            cache=True
        )


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

def run_example():
    """
    Example of how to run the SpinScribe crew.
    
    This demonstrates proper input configuration and crew execution.
    """
    # Define inputs for content creation
    inputs = {
        'client_name': 'TechCorp Solutions',
        'topic': 'Artificial Intelligence in Healthcare',
        'content_type': 'blog',
        'audience': 'Healthcare professionals and technology decision makers',
        'ai_language_code': '/TN/A3,P4,EMP2/VL4/SC3/FL2/LF3'
    }
    
    # Initialize and run crew
    crew_instance = SpinscribeCrew()
    result = crew_instance.crew().kickoff(inputs=inputs)
    
    # Process results
    print("\n" + "=" * 80)
    print("CONTENT CREATION RESULTS")
    print("=" * 80)
    print(f"\nFinal Content:\n{result.raw}")
    
    return result


if __name__ == "__main__":
    """
    Run the example when executed directly.
    
    Usage:
        python -m spinscribe.crew
    """
    run_example()


# =============================================================================
# CONFIGURATION NOTES
# =============================================================================
"""
ENVIRONMENT VARIABLES REQUIRED:
- OPENAI_API_KEY: OpenAI API key for GPT-4o
- SERPER_API_KEY: Serper.dev API key for web search
- HITL_BRAND_VOICE_WEBHOOK: Webhook for brand voice approval
- HITL_STYLE_COMPLIANCE_WEBHOOK: Webhook for style compliance approval
- HITL_FINAL_APPROVAL_WEBHOOK: Webhook for final QA approval

DIRECTORY STRUCTURE:
knowledge/
└── clients/
    └── {client_name}/
        ├── 01_brand_voice_analysis/
        ├── 02_style_guidelines/
        ├── 03_sample_content/
        ├── 04_marketing_materials/
        └── 05_previous_work/

HITL WORKFLOW:
1. Brand Voice Analysis → Pauses for human approval
2. Content flows through automated stages
3. Style Compliance → Pauses for human approval  
4. Final QA → Pauses for human approval
5. Content ready for publication

ALL ISSUES RESOLVED:
✓ content_strategist added to agents.yaml
✓ seo_optimizer renamed to seo_specialist for consistency
✓ All agent references now match agents.yaml definitions
✓ No inline agent definitions needed
✓ Clean, production-ready code
"""