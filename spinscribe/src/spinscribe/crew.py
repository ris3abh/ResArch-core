#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SpinScribe Content Creation Crew

A multi-agent AI system for creating high-quality, brand-aligned content
with Human-in-the-Loop (HITL) approval checkpoints.

Author: SpinScribe Team
Version: 2.0.0 - Webhook Integration with Callbacks
"""

import os
import sys
import requests
import time
from datetime import datetime
from typing import Dict, Any

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global execution ID for tracking workflows across callbacks
_current_execution_id = None


# =============================================================================
# CALLBACK FUNCTIONS FOR WEBHOOK INTEGRATION
# =============================================================================

def agent_step_callback(step_output):
    """
    Callback executed after each agent step.
    Sends webhook to: AGENT_WEBHOOK_URL
    """
    webhook_url = os.getenv("AGENT_WEBHOOK_URL")
    if not webhook_url:
        return

    try:
        # Handle both dict or object formats
        agent_name = (
            getattr(step_output, "agent", None) and getattr(step_output.agent, "role", "Unknown Agent")
        ) or "Unknown Agent"

        output_str = str(getattr(step_output, "output", None) or step_output)

        payload = {
            "workflow_id": os.getenv("EXECUTION_ID", "unknown"),
            "agent_name": agent_name,
            "step_type": "agent_step",
            "step_data": output_str,
            "timestamp": datetime.utcnow().isoformat()
        }

        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        logger.debug(f"📤 Agent step webhook sent: {response.status_code}")

    except Exception as e:
        logger.warning(f"⚠️  Failed to send agent step webhook: {e}")


def task_status_callback(task_output):
    """
    Callback executed after each task completes.
    Sends webhook to: TASK_STATUS_WEBHOOK
    """
    webhook_url = os.getenv("TASK_STATUS_WEBHOOK")
    if not webhook_url:
        return

    try:
        task_obj = getattr(task_output, "task", None)
        task_id = getattr(task_obj, "id", "unknown")
        task_description = getattr(task_obj, "description", "No description")

        output_text = (
            getattr(task_output, "output", None)
            or getattr(task_output, "raw", None)
            or "No output"
        )

        payload = {
            "workflow_id": os.getenv("EXECUTION_ID", "unknown"),
            "task_id": str(task_id),
            "task_description": task_description,
            "status": "completed",
            "output_preview": output_text[:500],  # Preview only
            "timestamp": datetime.utcnow().isoformat()
        }

        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f"✅ Task completed webhook sent: {response.status_code}")

    except Exception as e:
        logger.warning(f"⚠️  Failed to send task status webhook: {e}")



# =============================================================================
# HITL (Human-in-the-Loop) CHECKPOINT CALLBACKS
# =============================================================================

def wait_for_approval(execution_id: str, checkpoint_name: str, timeout: int = 3600) -> Dict[str, Any]:
    """
    Poll webhook server for human approval decision.
    """
    print("\n" + "="*80)
    print(f"⏸️  PAUSED at checkpoint: {checkpoint_name}")
    print("="*80)
    print(f"🔗 Review at: http://localhost:8000/dashboard")
    print("⏳ Waiting for human approval...")
    print("="*80 + "\n")
    
    start_time = time.time()
    poll_interval = 5
    
    while (time.time() - start_time) < timeout:
        try:
            response = requests.get(
                f"http://localhost:8000/workflows/{execution_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                workflow = response.json()
                status = workflow.get("status")
                
                if status == "approved":
                    approval_response = workflow.get("approval_response", {})
                    feedback = approval_response.get("feedback", "Approved")
                    
                    print("\n" + "="*80)
                    print(f"✅ CHECKPOINT APPROVED: {checkpoint_name}")
                    print("="*80)
                    print(f"📝 Feedback: {feedback}")
                    print("="*80 + "\n")
                    
                    return approval_response
                
                elif status == "rejected":
                    approval_response = workflow.get("approval_response", {})
                    feedback = approval_response.get("feedback", "Rejected")
                    
                    print("\n" + "="*80)
                    print(f"❌ CHECKPOINT REJECTED: {checkpoint_name}")
                    print("="*80)
                    print(f"📝 Reason: {feedback}")
                    print("="*80 + "\n")
                    
                    raise Exception(f"Workflow rejected at {checkpoint_name}: {feedback}")
                
                elif status == "revision_requested":
                    approval_response = workflow.get("approval_response", {})
                    feedback = approval_response.get("feedback", "Revision requested")
                    
                    print("\n" + "="*80)
                    print(f"🔄 REVISION REQUESTED: {checkpoint_name}")
                    print("="*80)
                    print(f"📝 Changes needed: {feedback}")
                    print("="*80 + "\n")
                    
                    raise Exception(f"Revision requested at {checkpoint_name}: {feedback}")
            
            time.sleep(poll_interval)
            
        except requests.RequestException as e:
            logger.warning(f"⚠️  Error polling for approval: {e}")
            time.sleep(poll_interval)
            continue
    
    raise TimeoutError(f"No approval received for {checkpoint_name} within {timeout} seconds")


def brand_voice_hitl_callback(task_output):
    """HITL Checkpoint 1: Brand Voice Analysis"""
    logger.info("📋 Brand Voice Analysis complete - triggering HITL checkpoint")
    
    webhook_url = os.getenv("HITL_BRAND_VOICE_WEBHOOK")
    if not webhook_url:
        logger.warning("⚠️  No brand voice webhook configured, skipping HITL")
        return task_output
    
    payload = {
        "workflow_id": _current_execution_id,
        "checkpoint_type": "brand_voice",
        "content": task_output.raw,
        "metadata": {
            "task_description": task_output.description,
            "timestamp": datetime.utcnow().isoformat()
        },
        "agent_name": "brand_voice_specialist"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ HITL checkpoint webhook sent successfully")
            approval = wait_for_approval(_current_execution_id, "brand_voice")
            logger.info(f"📥 Human feedback received: {approval.get('feedback', 'N/A')}")
        else:
            logger.warning(f"⚠️  Webhook returned status {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error in HITL checkpoint: {e}")
        raise
    
    return task_output


def style_compliance_hitl_callback(task_output):
    """HITL Checkpoint 2: Style Compliance Review"""
    logger.info("📋 Style Compliance Review complete - triggering HITL checkpoint")
    
    webhook_url = os.getenv("HITL_STYLE_COMPLIANCE_WEBHOOK")
    if not webhook_url:
        logger.warning("⚠️  No style compliance webhook configured, skipping HITL")
        return task_output
    
    payload = {
        "workflow_id": _current_execution_id,
        "checkpoint_type": "style_compliance",
        "content": task_output.raw,
        "metadata": {
            "task_description": task_output.description,
            "timestamp": datetime.utcnow().isoformat()
        },
        "agent_name": "style_compliance_agent"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ HITL checkpoint webhook sent successfully")
            approval = wait_for_approval(_current_execution_id, "style_compliance")
            logger.info(f"📥 Human feedback received: {approval.get('feedback', 'N/A')}")
        else:
            logger.warning(f"⚠️  Webhook returned status {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error in HITL checkpoint: {e}")
        raise
    
    return task_output


def final_qa_hitl_callback(task_output):
    """HITL Checkpoint 3: Final Quality Assurance"""
    logger.info("📋 Final QA complete - triggering HITL checkpoint")
    
    webhook_url = os.getenv("HITL_FINAL_APPROVAL_WEBHOOK")
    if not webhook_url:
        logger.warning("⚠️  No final QA webhook configured, skipping HITL")
        return task_output
    
    payload = {
        "workflow_id": _current_execution_id,
        "checkpoint_type": "final_qa",
        "content": task_output.raw,
        "metadata": {
            "task_description": task_output.description,
            "timestamp": datetime.utcnow().isoformat()
        },
        "agent_name": "quality_assurance_editor"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ HITL checkpoint webhook sent successfully")
            approval = wait_for_approval(_current_execution_id, "final_qa")
            logger.info(f"📥 Human feedback received: {approval.get('feedback', 'N/A')}")
        else:
            logger.warning(f"⚠️  Webhook returned status {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error in HITL checkpoint: {e}")
        raise
    
    return task_output


# =============================================================================
# SPINSCRIBE CREW DEFINITION
# =============================================================================

@CrewBase
class SpinscribeCrew:
    """
    SpinScribe Content Creation Crew
    
    A multi-agent system with 7 specialized agents working sequentially to create
    high-quality, brand-aligned content with three HITL approval checkpoints.
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
        
        # Check for webhook URLs (optional but recommended)
        webhook_vars = [
            'AGENT_WEBHOOK_URL',
            'TASK_STATUS_WEBHOOK',
            'HITL_BRAND_VOICE_WEBHOOK',
            'HITL_STYLE_COMPLIANCE_WEBHOOK',
            'HITL_FINAL_APPROVAL_WEBHOOK'
        ]
        
        configured_webhooks = [var for var in webhook_vars if os.getenv(var)]
        logger.info(f"✅ {len(configured_webhooks)}/{len(webhook_vars)} webhooks configured")

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
    # TASKS - Matching tasks.yaml exactly with HITL callbacks
    # =========================================================================

    @task
    def content_research_task(self) -> Task:
        """Task 1: Content Research & Competitive Analysis"""
        return Task(
            config=self.tasks_config['content_research_task']
        )

    @task
    def brand_voice_analysis_task(self) -> Task:
        """Task 2: Brand Voice Analysis with HITL checkpoint"""
        return Task(
            config=self.tasks_config['brand_voice_analysis_task'],
            callback=brand_voice_hitl_callback  # ← HITL Checkpoint 1
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
        """Task 6: Style Compliance Review with HITL checkpoint"""
        return Task(
            config=self.tasks_config['style_compliance_review_task'],
            callback=style_compliance_hitl_callback  # ← HITL Checkpoint 2
        )

    @task
    def final_quality_assurance_task(self) -> Task:
        """Task 7: Final Quality Assurance with HITL checkpoint"""
        return Task(
            config=self.tasks_config['final_quality_assurance_task'],
            callback=final_qa_hitl_callback  # ← HITL Checkpoint 3
        )

    # =========================================================================
    # CREW DEFINITION WITH CALLBACKS
    # =========================================================================

    @crew
    def crew(self) -> Crew:
        """
        Creates the SpinScribe crew with webhook monitoring callbacks.
        
        Returns:
            Crew: Configured crew with 7 agents, 7 tasks, and callback functions
        """
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            step_callback=agent_step_callback,  # ← Monitor agent steps
            task_callback=task_status_callback,  # ← Monitor task completions
        )

    # =========================================================================
    # EXECUTION METHODS
    # =========================================================================

    def get_inputs(self) -> Dict[str, Any]:
        """Collect inputs from user for content creation."""
        print("\n" + "="*80)
        print("SPINSCRIBE CONTENT CREATION - INPUT COLLECTION")
        print("="*80)
        print("\nPlease provide the following information:")
        print("(Press Enter to use default values shown in brackets)\n")
        
        client_name = input("Client Name [Demo Client]: ").strip() or "Demo Client"
        topic = input("Content Topic [Artificial Intelligence in Modern Business]: ").strip() or "Artificial Intelligence in Modern Business"
        
        print("\nContent Type Options: blog, landing_page, local_article")
        content_type = input("Content Type [blog]: ").strip() or "blog"
        
        audience = input("Target Audience [Business executives and technology decision makers]: ").strip() or "Business executives and technology decision makers"
        
        print("\nAI Language Code defines tone, vocabulary, and style.")
        print("Example: /TN/P3,A2/VL3/SC3/FL2/LF3")
        ai_language_code = input("AI Language Code [/TN/P3,A2/VL3/SC3/FL2/LF3]: ").strip() or "/TN/P3,A2/VL3/SC3/FL2/LF3"

        print("\n📄 Initial Draft (Optional):")
        print("Do you have an initial draft to refine? [Y/n]: ", end="")
        has_draft = input().strip().lower() in ['y', 'yes', '']
        
        initial_draft = None
        draft_source = None
        
        if has_draft:
            print("\nHow would you like to provide the draft?")
            print("1. Paste text directly")
            print("2. Provide file path")
            print("3. Provide URL")
            draft_option = input("Choose option [1/2/3]: ").strip() or "1"
            
            if draft_option == "1":
                print("\nPaste your draft (press Ctrl+D or Ctrl+Z when done):")
                print("-" * 80)
                lines = []
                try:
                    while True:
                        lines.append(input())
                except EOFError:
                    pass
                initial_draft = "\n".join(lines)
                draft_source = "pasted_text"
                
            elif draft_option == "2":
                file_path = input("Enter file path: ").strip()
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        initial_draft = f.read()
                    draft_source = f"file:{file_path}"
                except Exception as e:
                    print(f"⚠️  Error reading file: {e}")
                    print("Proceeding without initial draft...")
                    has_draft = False
                    
            elif draft_option == "3":
                url = input("Enter URL: ").strip()
                try:
                    import requests
                    response = requests.get(url, timeout=10)
                    initial_draft = response.text
                    draft_source = f"url:{url}"
                except Exception as e:
                    print(f"⚠️  Error fetching URL: {e}")
                    print("Proceeding without initial draft...")
                    has_draft = False

        # Add client_knowledge_directory based on client_name
        client_knowledge_directory = f"knowledge/clients/{client_name.replace(' ', '_').lower()}"
        
        inputs = {
            'client_name': client_name,
            'topic': topic,
            'content_type': content_type,
            'audience': audience,
            'ai_language_code': ai_language_code,
            'client_knowledge_directory': client_knowledge_directory,
            "has_initial_draft": has_draft,
            "initial_draft": initial_draft if has_draft else "",
            "draft_source": draft_source if has_draft else "none",
            "workflow_mode": "refinement" if has_draft else "creation"
        }
        
        print("\n" + "="*80)
        print("INPUT SUMMARY")
        print("="*80)
        print(f"   Client Name: {client_name}")
        print(f"   Topic: {topic}")
        print(f"   Content Type: {content_type}")
        print(f"   Audience: {audience}")
        print(f"   AI Language Code: {ai_language_code}")
        print(f"   Knowledge Directory: {client_knowledge_directory}")
        print(f"   Workflow Mode: {'🔄 Refinement (with draft)' if has_draft else '✨ Creation (from scratch)'}")
        if has_draft:
            print(f"   Draft Source: {draft_source}")
            print(f"   Draft Length: {len(initial_draft)} characters")
        print("="*80)
        print("="*80 + "\n")
        
        confirm = input("Proceed with these inputs? [Y/n]: ").strip().lower()
        if confirm and confirm != 'y':
            print("❌ Execution cancelled by user")
            sys.exit(0)
        
        return inputs

    def run(self, inputs: Dict[str, Any]) -> str:
        """Execute the SpinScribe crew with webhook monitoring."""
        global _current_execution_id
        
        try:
            # Generate unique execution ID
            _current_execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logger.info("🚀 Starting SpinScribe crew execution...")
            logger.info(f"   Execution ID: {_current_execution_id}")
            
            # ✅ Use inputs passed as parameter, don't collect again
            
            # Get crew instance
            crew_instance = self.crew()
            
            print("\n" + "="*80)
            print("🚀 Starting crew execution with webhook monitoring...")
            print(f"   Execution ID: {_current_execution_id}")
            print("="*80 + "\n")
            
            print("💡 TIP: Keep browser open to http://localhost:8000/dashboard")
            print("        You'll need it to approve HITL checkpoints\n")
            
            # Execute crew with standard kickoff (callbacks handle webhooks!)
            result = crew_instance.kickoff(inputs=inputs)
            
            logger.info("✅ Crew execution completed successfully")
            
            # Send completion webhook
            completion_webhook = os.getenv("AGENT_COMPLETION_WEBHOOK")
            if completion_webhook:
                try:
                    requests.post(
                        completion_webhook,
                        json={
                            "workflow_id": _current_execution_id,
                            "status": "completed",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        timeout=5
                    )
                    logger.info("📤 Completion notification sent")
                except:
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error during crew execution: {str(e)}")
            
            # Send error webhook
            error_webhook = os.getenv("ERROR_NOTIFICATION_WEBHOOK")
            if error_webhook:
                try:
                    requests.post(
                        error_webhook,
                        json={
                            "workflow_id": _current_execution_id or "unknown",
                            "error_type": type(e).__name__,
                            "message": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        timeout=5
                    )
                except:
                    pass
            
            raise


def run():
    """
    Entry point for the SpinScribe crew.
    
    This function is called by the CLI: `crewai run`
    """
    SpinscribeCrew().run()


if __name__ == "__main__":
    run()