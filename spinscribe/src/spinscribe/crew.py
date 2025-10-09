#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SpinScribe Content Creation Crew - Cloud Deployment Ready

A multi-agent AI system for creating high-quality, brand-aligned content
with dual workflow modes (CREATION and REVISION).

Author: SpinScribe Team
Version: 3.0.0 - Cloud Deployment (Phase 1 - No HITL)
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff
from crewai_tools import SerperDevTool

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global execution ID for tracking workflows
_current_execution_id = None


# =============================================================================
# SPINSCRIBE CREW DEFINITION
# =============================================================================

@CrewBase
class SpinscribeCrew:
    """
    SpinScribe Content Creation Crew - Cloud Deployment Ready
    
    A multi-agent system with 7 specialized agents working sequentially to create
    high-quality, brand-aligned content with dual workflow mode support:
    - CREATION: Build content from scratch (no initial_draft provided)
    - REVISION: Enhance existing draft (initial_draft provided)
    
    Workflow mode is automatically detected based on inputs.
    """
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        """Initialize the crew and validate environment."""
        super().__init__()
        self._validate_environment()
        
    def _validate_environment(self):
        """Validate required environment variables."""
        required_vars = ['OPENAI_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)
        
        # Check for SerperDev API key (recommended for web search)
        if not os.getenv('SERPER_API_KEY'):
            logger.warning("⚠️  SERPER_API_KEY not set - web search tools may not work optimally")
        
        logger.info("✅ Environment validation complete")

    # =========================================================================
    # INPUT PREPROCESSING - Workflow Mode Detection
    # =========================================================================
    
    @before_kickoff
    def prepare_workflow(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect workflow mode and enrich inputs before crew execution.
        
        Automatically determines whether to use CREATION or REVISION mode based
        on the presence of initial_draft input.
        
        Args:
            inputs: Raw input dictionary from API or CLI
            
        Returns:
            Enriched inputs with workflow mode and metadata
        """
        global _current_execution_id
        
        # Generate unique execution ID
        _current_execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info("="*80)
        logger.info("🚀 SPINSCRIBE WORKFLOW INITIALIZATION")
        logger.info("="*80)
        logger.info(f"🔗 Execution ID: {_current_execution_id}")
        
        # Extract initial draft
        initial_draft = inputs.get('initial_draft', '').strip()
        has_initial_draft = bool(initial_draft)
        
        # Determine workflow mode
        # Priority: explicit workflow_mode > auto-detect from initial_draft
        explicit_mode = inputs.get('workflow_mode', '').lower()
        
        if explicit_mode in ['revision', 'creation', 'refinement']:
            # Map 'refinement' to 'revision' for consistency
            workflow_mode = 'revision' if explicit_mode in ['refinement', 'revision'] else 'creation'
        else:
            # Auto-detect based on initial_draft presence
            workflow_mode = 'revision' if has_initial_draft else 'creation'
        
        # Enrich inputs with mode and metadata
        inputs['workflow_mode'] = workflow_mode
        inputs['has_initial_draft'] = has_initial_draft
        
        if has_initial_draft:
            # Revision mode metadata
            inputs['draft_length'] = len(initial_draft)
            inputs['draft_word_count'] = len(initial_draft.split())
            inputs['draft_source'] = inputs.get('draft_source', 'human_provided')
            
            logger.info(f"📝 WORKFLOW MODE: REVISION")
            logger.info(f"   ├─ Draft Length: {inputs['draft_length']} characters")
            logger.info(f"   ├─ Word Count: {inputs['draft_word_count']} words")
            logger.info(f"   └─ Source: {inputs['draft_source']}")
        else:
            # Creation mode metadata
            inputs['draft_length'] = 0
            inputs['draft_word_count'] = 0
            inputs['initial_draft'] = ""  # Ensure empty string, not None
            inputs['draft_source'] = 'ai_generated'
            
            logger.info(f"✨ WORKFLOW MODE: CREATION")
            logger.info(f"   └─ Generating content from scratch")
        
        # Set defaults for optional fields
        inputs.setdefault('content_length', '1500')
        inputs.setdefault('ai_language_code', '/TN/A3,P4/VL4/SC3/FL2/LF3')
        inputs.setdefault('client_knowledge_directory', 
                         f"./knowledge/clients/{inputs.get('client_name', 'default')}")
        
        # Log configuration
        logger.info(f"🎯 Configuration:")
        logger.info(f"   ├─ Client: {inputs.get('client_name', 'N/A')}")
        logger.info(f"   ├─ Topic: {inputs.get('topic', 'N/A')}")
        logger.info(f"   ├─ Content Type: {inputs.get('content_type', 'N/A')}")
        logger.info(f"   ├─ Audience: {inputs.get('audience', 'N/A')}")
        logger.info(f"   └─ AI Language Code: {inputs.get('ai_language_code', 'N/A')}")
        logger.info("="*80)
        
        return inputs

    # =========================================================================
    # AGENTS - Matching agents.yaml exactly
    # =========================================================================

    @agent
    def content_researcher(self) -> Agent:
        """Content Research & Competitive Analysis Specialist"""
        return Agent(
            config=self.agents_config['content_researcher'],
            tools=[SerperDevTool()],
            verbose=True
        )

    @agent
    def brand_voice_specialist(self) -> Agent:
        """Brand Voice Analysis Expert"""
        return Agent(
            config=self.agents_config['brand_voice_specialist'],
            verbose=True
        )

    @agent
    def content_strategist(self) -> Agent:
        """Content Strategy & Planning Specialist"""
        return Agent(
            config=self.agents_config['content_strategist'],
            tools=[SerperDevTool()],
            verbose=True
        )

    @agent
    def content_writer(self) -> Agent:
        """Expert Content Writer & Brand Storyteller"""
        return Agent(
            config=self.agents_config['content_writer'],
            tools=[SerperDevTool()],
            verbose=True
        )

    @agent
    def seo_specialist(self) -> Agent:
        """SEO Optimization Specialist & Search Strategy Expert"""
        return Agent(
            config=self.agents_config['seo_specialist'],
            tools=[SerperDevTool()],
            verbose=True
        )

    @agent
    def style_compliance_agent(self) -> Agent:
        """Style Guidelines & Standards Enforcer"""
        return Agent(
            config=self.agents_config['style_compliance_agent'],
            verbose=True
        )

    @agent
    def quality_assurance_editor(self) -> Agent:
        """Senior Editorial Quality Assurance Specialist"""
        return Agent(
            config=self.agents_config['quality_assurance_editor'],
            verbose=True
        )

    # =========================================================================
    # TASKS - Matching tasks.yaml exactly
    # =========================================================================

    @task
    def content_research_task(self) -> Task:
        """Task 1: Content Research & Competitive Analysis"""
        return Task(
            config=self.tasks_config['content_research_task']
        )

    @task
    def brand_voice_analysis_task(self) -> Task:
        """Task 2: Brand Voice Analysis"""
        return Task(
            config=self.tasks_config['brand_voice_analysis_task']
        )

    @task
    def content_strategy_task(self) -> Task:
        """Task 3: Content Strategy & Outline Creation"""
        return Task(
            config=self.tasks_config['content_strategy_task']
        )

    @task
    def content_generation_task(self) -> Task:
        """Task 4: Content Generation"""
        return Task(
            config=self.tasks_config['content_generation_task']
        )

    @task
    def seo_optimization_task(self) -> Task:
        """Task 5: SEO Optimization & Enhancement"""
        return Task(
            config=self.tasks_config['seo_optimization_task']
        )

    @task
    def style_compliance_review_task(self) -> Task:
        """Task 6: Style Compliance Review"""
        return Task(
            config=self.tasks_config['style_compliance_review_task']
        )

    @task
    def final_quality_assurance_task(self) -> Task:
        """Task 7: Final Quality Assurance"""
        return Task(
            config=self.tasks_config['final_quality_assurance_task']
        )

    # =========================================================================
    # CREW DEFINITION
    # =========================================================================

    @crew
    def crew(self) -> Crew:
        """
        Creates the SpinScribe crew with sequential workflow.
        
        Returns:
            Crew: Configured crew with 7 agents and 7 tasks
        """
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

def run():
    """
    Entry point for the SpinScribe crew.
    
    This function is called by:
    - CLI: `crewai run`
    - API: crew.kickoff(inputs={...})
    """
    try:
        # Initialize crew
        crew_instance = SpinscribeCrew()
        
        # Example inputs for testing
        # In production, these come from API or CLI
        inputs = {
            'client_name': 'Yanmar',
            'topic': 'The Future of AI in Agriculture and Robotics',
            'content_type': 'blog',
            'audience': 'Agricultural Business Executives and Technology Decision-Makers',
            'ai_language_code': '/TN/A3,P4,EMP2/VL4/SC3/FL2/LF3',
            'content_length': '2000',
            # For REVISION mode, uncomment and provide initial_draft:
            # 'initial_draft': 'Your existing draft content here...',
        }
        
        logger.info("🚀 Starting SpinScribe crew execution...")
        
        # Execute crew
        result = crew_instance.crew().kickoff(inputs=inputs)
        
        logger.info("="*80)
        logger.info("✅ SPINSCRIBE EXECUTION COMPLETE")
        logger.info("="*80)
        logger.info(f"📊 Result preview: {str(result)[:200]}...")
        logger.info("="*80)
        
        return result
        
    except Exception as e:
        logger.error("="*80)
        logger.error("❌ SPINSCRIBE EXECUTION FAILED")
        logger.error("="*80)
        logger.error(f"Error: {str(e)}")
        logger.error("="*80)
        raise


# =============================================================================
# TRAINING AND TESTING FUNCTIONS (OPTIONAL)
# =============================================================================

def train():
    """
    Train the crew for improved performance.
    Usage: crewai train <n_iterations> <filename>
    """
    inputs = {
        "topic": "AI in Healthcare",
        "audience": "Healthcare Executives",
        "content_type": "blog",
        "client_name": "TestClient"
    }
    try:
        SpinscribeCrew().crew().train(
            n_iterations=int(sys.argv[1]),
            filename=sys.argv[2],
            inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    Usage: crewai replay <task_id>
    """
    try:
        SpinscribeCrew().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    Usage: crewai test <n_iterations> <openai_model_name>
    """
    inputs = {
        "topic": "Test Topic",
        "audience": "Test Audience",
        "content_type": "blog",
        "client_name": "TestClient"
    }
    try:
        SpinscribeCrew().crew().test(
            n_iterations=int(sys.argv[1]),
            openai_model_name=sys.argv[2],
            inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


if __name__ == "__main__":
    run()