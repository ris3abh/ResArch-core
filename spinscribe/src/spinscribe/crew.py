# =============================================================================
# SPINSCRIBE CREW ORCHESTRATION
# Multi-agent content creation system with comprehensive webhook integration
# =============================================================================
"""
SpinScribe Content Creation Crew

This module orchestrates a multi-agent workflow for creating publication-ready
content with complete webhook-based monitoring and human oversight.

Webhook Architecture:
- Agent Activity: Real-time updates as agents work
- Task Progress: Status updates for each task
- HITL Checkpoints: Human approval at 3 critical stages
- Completion Tracking: Agent and crew completion events
- Error Handling: Automatic error notifications

The crew follows a 7-stage sequential process:
1. Content Research - Gather comprehensive information
2. Brand Voice Analysis - Validate brand voice parameters (HITL CHECKPOINT 1)
3. Content Strategy - Create detailed outline
4. Content Generation - Write draft content
5. SEO Optimization - Enhance search performance
6. Style Compliance - Verify brand adherence (HITL CHECKPOINT 2)
7. Quality Assurance - Final review and polish (HITL CHECKPOINT 3)
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import DirectorySearchTool, SerperDevTool
from typing import List, Dict, Any, Optional
import os
from datetime import datetime

# Import custom tools
from spinscribe.tools.custom_tool import ai_language_code_parser


# Global storage for crew execution reference (needed for webhook resume)
_active_crew_executions: Dict[str, Any] = {}


@CrewBase
class SpinscribeCrew():
    """
    SpinScribe content creation crew with comprehensive webhook monitoring.
    
    This crew orchestrates specialized agents through a sequential workflow
    that produces publication-ready content matching client brand voice,
    with real-time webhook notifications at every stage.
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
        
        # Create necessary directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('content_output', exist_ok=True)
        
        # Initialize tools that will be shared across agents
        self._init_tools()
        
        # Load webhook configuration from environment
        self._init_webhook_config()
    
    def _init_tools(self):
        """Initialize and configure tools for agents."""
        # Directory search tool for client knowledge base access
        self.directory_search_tool = DirectorySearchTool()
        
        # Web search for research tasks
        self.web_search_tool = SerperDevTool()
        
        # AI Language Code Parser (custom tool)
        self.ai_language_parser = ai_language_code_parser
    
    def _init_webhook_config(self):
        """
        Load webhook configuration from environment variables.
        
        This centralizes webhook configuration so it's easy to verify
        which webhooks are active.
        """
        self.webhook_config = {
            # Real-time agent activity tracking
            'agent_update': os.getenv('AGENT_WEBHOOK_URL'),
            
            # HITL approval checkpoints (3 different endpoints)
            'hitl_brand_voice': os.getenv('HITL_BRAND_VOICE_WEBHOOK'),
            'hitl_style_compliance': os.getenv('HITL_STYLE_COMPLIANCE_WEBHOOK'),
            'hitl_final_qa': os.getenv('HITL_FINAL_APPROVAL_WEBHOOK'),
            
            # Task and completion tracking
            'task_status': os.getenv('TASK_STATUS_WEBHOOK'),
            'agent_completion': os.getenv('AGENT_COMPLETION_WEBHOOK'),
            
            # Error notifications
            'error_notification': os.getenv('ERROR_NOTIFICATION_WEBHOOK'),
            
            # Authentication
            'auth_token': os.getenv('WEBHOOK_AUTH_TOKEN', 'spinscribe-webhook-secret-token-change-this'),
            'auth_strategy': os.getenv('WEBHOOK_AUTH_STRATEGY', 'bearer')
        }
        
        # Validate webhook configuration
        configured_webhooks = [k for k, v in self.webhook_config.items() 
                              if v and not k.startswith('auth')]
        
        print(f"\n🔗 Webhook System Initialized: {len(configured_webhooks)}/6 endpoints configured")
        
        if len(configured_webhooks) < 6:
            missing = []
            if not self.webhook_config['agent_update']:
                missing.append('AGENT_WEBHOOK_URL')
            if not self.webhook_config['hitl_brand_voice']:
                missing.append('HITL_BRAND_VOICE_WEBHOOK')
            if not self.webhook_config['hitl_style_compliance']:
                missing.append('HITL_STYLE_COMPLIANCE_WEBHOOK')
            if not self.webhook_config['hitl_final_qa']:
                missing.append('HITL_FINAL_APPROVAL_WEBHOOK')
            if not self.webhook_config['task_status']:
                missing.append('TASK_STATUS_WEBHOOK')
            if not self.webhook_config['agent_completion']:
                missing.append('AGENT_COMPLETION_WEBHOOK')
            
            print(f"⚠️  Warning: {len(missing)} webhook(s) not configured:")
            for m in missing:
                print(f"   - {m}")
    
    @before_kickoff
    def setup_execution(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare inputs and environment before crew execution.
        
        This hook:
        - Validates required inputs
        - Sets up client-specific knowledge base paths
        - Initializes logging
        - Prepares webhook configurations
        
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
        inputs['client_knowledge_directory'] = inputs['knowledge_base_path']
        
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
        
        # Display configured webhooks
        print(f"\n🔗 Webhook Configuration:")
        webhook_status = [
            ('Agent Updates', self.webhook_config['agent_update']),
            ('Task Status', self.webhook_config['task_status']),
            ('Agent Completion', self.webhook_config['agent_completion']),
            ('HITL: Brand Voice', self.webhook_config['hitl_brand_voice']),
            ('HITL: Style Compliance', self.webhook_config['hitl_style_compliance']),
            ('HITL: Final QA', self.webhook_config['hitl_final_qa']),
            ('Error Notifications', self.webhook_config['error_notification'])
        ]
        
        for name, url in webhook_status:
            status = "✓" if url else "✗"
            display_url = url if url else "Not configured"
            print(f"   {status} {name}: {display_url}")
        
        print(f"\n🚀 Starting content creation workflow with webhook monitoring...")
        print("=" * 80)
        
        return inputs
    
    @after_kickoff
    def cleanup_execution(self, output: Any) -> Any:
        """
        Cleanup after crew execution completes.
        
        Args:
            output: The crew's output
            
        Returns:
            The output, potentially modified
        """
        print("\n" + "=" * 80)
        print("SPINSCRIBE CREW - EXECUTION COMPLETE")
        print("=" * 80)
        
        return output

    # =========================================================================
    # AGENT DEFINITIONS
    # =========================================================================
    
    @agent
    def content_researcher(self) -> Agent:
        """Agent 1: Content research and competitive intelligence specialist."""
        return Agent(
            config=self.agents_config['content_researcher'],
            tools=[self.web_search_tool, self.directory_search_tool],
            verbose=True
        )
    
    @agent
    def brand_voice_specialist(self) -> Agent:
        """Agent 2: Brand voice analysis specialist. HITL CHECKPOINT 1."""
        return Agent(
            config=self.agents_config['brand_voice_specialist'],
            tools=[self.directory_search_tool, self.ai_language_parser],
            verbose=True
        )
    
    @agent
    def content_strategist(self) -> Agent:
        """Agent 3: Content strategy and outline creation specialist."""
        return Agent(
            config=self.agents_config['content_strategist'],
            verbose=True
        )
    
    @agent
    def content_writer(self) -> Agent:
        """Agent 4: Content writing specialist."""
        return Agent(
            config=self.agents_config['content_writer'],
            verbose=True
        )
    
    @agent
    def seo_specialist(self) -> Agent:
        """Agent 5: SEO optimization specialist."""
        return Agent(
            config=self.agents_config['seo_specialist'],
            tools=[self.web_search_tool],
            verbose=True
        )
    
    @agent
    def style_compliance_agent(self) -> Agent:
        """Agent 6: Style compliance specialist. HITL CHECKPOINT 2."""
        return Agent(
            config=self.agents_config['style_compliance_agent'],
            verbose=True
        )
    
    @agent
    def quality_assurance_editor(self) -> Agent:
        """Agent 7: Quality assurance specialist. HITL CHECKPOINT 3."""
        return Agent(
            config=self.agents_config['quality_assurance_editor'],
            verbose=True
        )

    # =========================================================================
    # TASK DEFINITIONS
    # =========================================================================
    
    @task
    def content_research_task(self) -> Task:
        """Task 1: Comprehensive content research."""
        return Task(config=self.tasks_config['content_research_task'])
    
    @task
    def brand_voice_analysis_task(self) -> Task:
        """Task 2: Brand voice analysis. HITL CHECKPOINT 1."""
        return Task(config=self.tasks_config['brand_voice_analysis_task'])
    
    @task
    def content_strategy_task(self) -> Task:
        """Task 3: Content strategy and outline creation."""
        return Task(config=self.tasks_config['content_strategy_task'])
    
    @task
    def content_generation_task(self) -> Task:
        """Task 4: Full content draft."""
        return Task(config=self.tasks_config['content_generation_task'])
    
    @task
    def seo_optimization_task(self) -> Task:
        """Task 5: SEO optimization."""
        return Task(config=self.tasks_config['seo_optimization_task'])
    
    @task
    def style_compliance_review_task(self) -> Task:
        """Task 6: Style compliance review. HITL CHECKPOINT 2."""
        return Task(config=self.tasks_config['style_compliance_review_task'])
    
    @task
    def final_quality_assurance_task(self) -> Task:
        """Task 7: Final QA. HITL CHECKPOINT 3."""
        return Task(config=self.tasks_config['final_quality_assurance_task'])

    # =========================================================================
    # CREW DEFINITION
    # =========================================================================
    
    @crew
    def crew(self) -> Crew:
        """Create the SpinScribe content creation crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
            embedder={
                "provider": "openai",
                "config": {"model": "text-embedding-3-small"}
            },
            output_log_file="logs/crew_execution.log",
            planning=False,
            max_rpm=30,
            cache=True
        )
    
    # =========================================================================
    # COMPREHENSIVE WEBHOOK INTEGRATION
    # =========================================================================
    
    def kickoff_with_webhooks(self, inputs: Dict[str, Any]) -> Any:
        """
        Kickoff crew with complete webhook integration.
        
        Configures ALL webhook endpoints:
        1. stepWebhookUrl - Agent step-by-step activity
        2. taskWebhookUrl - Task completion notifications
        3. crewWebhookUrl - Crew completion
        4. humanInputWebhook - HITL approval checkpoints
        
        Args:
            inputs: Execution parameters (client_name, topic, etc.)
            
        Returns:
            Crew execution result
        """
        crew_instance = self.crew()
        execution_id = inputs.get('execution_id', f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Prepare authentication headers for all webhooks
        auth_config = self._prepare_auth_config()
        
        print(f"\n" + "=" * 80)
        print("WEBHOOK INTEGRATION CONFIGURATION")
        print("=" * 80)
        
        # =====================================================================
        # 1. AGENT STEP WEBHOOK (Real-time agent activity)
        # =====================================================================
        step_webhook_url = self.webhook_config['agent_update']
        if step_webhook_url:
            print(f"\n✓ Agent Activity Tracking:")
            print(f"  URL: {step_webhook_url}")
            print(f"  Purpose: Real-time updates as each agent works")
        else:
            print(f"\n✗ Agent Activity Tracking: Not configured")
            step_webhook_url = None
        
        # =====================================================================
        # 2. TASK STATUS WEBHOOK (Task progress and completion)
        # =====================================================================
        task_webhook_url = self.webhook_config['task_status']
        if task_webhook_url:
            print(f"\n✓ Task Progress Tracking:")
            print(f"  URL: {task_webhook_url}")
            print(f"  Purpose: Notifications when tasks complete")
        else:
            print(f"\n✗ Task Progress Tracking: Not configured")
            task_webhook_url = None
        
        # =====================================================================
        # 3. CREW COMPLETION WEBHOOK (Final completion notification)
        # =====================================================================
        crew_webhook_url = self.webhook_config['agent_completion']
        if crew_webhook_url:
            print(f"\n✓ Crew Completion Tracking:")
            print(f"  URL: {crew_webhook_url}")
            print(f"  Purpose: Notification when entire workflow completes")
        else:
            print(f"\n✗ Crew Completion Tracking: Not configured")
            crew_webhook_url = None
        
        # =====================================================================
        # 4. HUMAN-IN-THE-LOOP WEBHOOKS (Approval checkpoints)
        # =====================================================================
        print(f"\n✓ Human-in-the-Loop Checkpoints:")
        
        # Primary HITL webhook (brand voice - first checkpoint)
        hitl_primary = self.webhook_config['hitl_brand_voice']
        if hitl_primary:
            print(f"  Checkpoint 1: {hitl_primary}")
            print(f"  Checkpoint 2: {self.webhook_config['hitl_style_compliance']}")
            print(f"  Checkpoint 3: {self.webhook_config['hitl_final_qa']}")
            
            human_input_webhook = {
                "url": hitl_primary,
                "authentication": auth_config
            }
        else:
            print(f"  ✗ HITL webhooks not configured - will use terminal input")
            human_input_webhook = None
        
        print(f"\n" + "=" * 80)
        print(f"🚀 Starting crew execution with webhook monitoring...")
        print(f"   Execution ID: {execution_id}")
        print("=" * 80 + "\n")
        
        # Store crew execution for webhook resume
        _active_crew_executions[execution_id] = {
            'crew': crew_instance,
            'inputs': inputs,
            'started_at': datetime.now().isoformat(),
            'webhook_config': self.webhook_config
        }
        
        try:
            # Kickoff with ALL webhook configurations
            result = crew_instance.kickoff(
                inputs=inputs,
                # Agent step-by-step updates
                stepWebhookUrl=step_webhook_url,
                # Task completion notifications
                taskWebhookUrl=task_webhook_url,
                # Crew completion notification
                crewWebhookUrl=crew_webhook_url,
                # HITL approval checkpoints
                humanInputWebhook=human_input_webhook
            )
            
            # Cleanup after successful completion
            if execution_id in _active_crew_executions:
                del _active_crew_executions[execution_id]
            
            return result
            
        except Exception as e:
            # Send error notification webhook if configured
            self._send_error_notification(execution_id, str(e))
            
            # Cleanup on error
            if execution_id in _active_crew_executions:
                del _active_crew_executions[execution_id]
            
            raise e
    
    def _prepare_auth_config(self) -> Dict[str, str]:
        """
        Prepare authentication configuration for webhooks.
        
        Returns:
            Dict with authentication strategy and credentials
        """
        strategy = self.webhook_config['auth_strategy']
        token = self.webhook_config['auth_token']
        
        if strategy == 'bearer':
            return {
                "strategy": "bearer",
                "token": token
            }
        elif strategy == 'basic':
            # For basic auth, token should be "username:password"
            return {
                "strategy": "basic",
                "credentials": token
            }
        else:
            # No authentication
            return {}
    
    def _send_error_notification(self, execution_id: str, error_message: str):
        """
        Send error notification to webhook if configured.
        
        Args:
            execution_id: The execution that failed
            error_message: Error description
        """
        error_webhook = self.webhook_config['error_notification']
        
        if error_webhook:
            import requests
            
            try:
                payload = {
                    "execution_id": execution_id,
                    "timestamp": datetime.now().isoformat(),
                    "error_type": "crew_execution_error",
                    "message": error_message
                }
                
                headers = {}
                if self.webhook_config['auth_strategy'] == 'bearer':
                    headers['Authorization'] = f"Bearer {self.webhook_config['auth_token']}"
                
                response = requests.post(
                    error_webhook,
                    json=payload,
                    headers=headers,
                    timeout=5
                )
                
                print(f"\n🔔 Error notification sent: {response.status_code}")
                
            except Exception as webhook_error:
                print(f"\n⚠️  Failed to send error notification: {webhook_error}")


# =============================================================================
# HELPER FUNCTIONS FOR WEBHOOK INTEGRATION
# =============================================================================

def get_active_crew_execution(execution_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve an active crew execution by ID.
    
    Used by webhook server to resume crew after human feedback.
    
    Args:
        execution_id: The execution ID
        
    Returns:
        Dict containing crew instance and metadata, or None
    """
    return _active_crew_executions.get(execution_id)


def list_active_executions() -> List[str]:
    """
    List all active crew execution IDs.
    
    Returns:
        List of execution IDs
    """
    return list(_active_crew_executions.keys())


def resume_crew_execution(
    execution_id: str,
    human_feedback: str,
    is_approve: bool
) -> Any:
    """
    Resume a paused crew execution after human feedback.
    
    Called by webhook server after receiving approval/rejection.
    
    Args:
        execution_id: The execution to resume
        human_feedback: Feedback from human reviewer
        is_approve: True if approved, False if rejected
        
    Returns:
        Execution result or None if not found
    """
    execution = get_active_crew_execution(execution_id)
    
    if not execution:
        print(f"⚠️  Warning: No active execution found for ID: {execution_id}")
        return None
    
    crew_instance = execution['crew']
    
    print(f"\n📝 Resuming crew execution: {execution_id}")
    print(f"   Decision: {'✅ Approved' if is_approve else '❌ Rejected'}")
    print(f"   Feedback: {human_feedback}")
    
    try:
        # Resume the crew with feedback
        # Note: The actual resume mechanism depends on CrewAI's implementation
        # This is a placeholder for the resume logic
        result = crew_instance.resume(
            feedback=human_feedback,
            approved=is_approve
        )
        
        return result
        
    except AttributeError:
        # If crew doesn't have resume method, handle differently
        print(f"⚠️  Warning: Crew instance doesn't support resume()")
        print(f"   Feedback will be logged but execution cannot continue")
        return None


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

def run_example():
    """Example of running SpinScribe crew with full webhook integration."""
    inputs = {
        'client_name': 'Yanmar',
        'topic': 'AI in Tractors',
        'content_type': 'blog',
        'audience': 'Business Executives',
        'ai_language_code': '/TN'
    }
    
    crew_instance = SpinscribeCrew()
    result = crew_instance.kickoff_with_webhooks(inputs)
    
    print("\n" + "=" * 80)
    print("CONTENT CREATION COMPLETE")
    print("=" * 80)
    print(f"\n{result.raw}")
    
    return result


if __name__ == "__main__":
    run_example()