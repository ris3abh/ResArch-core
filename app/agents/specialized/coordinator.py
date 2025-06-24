# app/agents/specialized/coordinator.py
"""
Production Coordinator Agent for SpinScribe
Built on CAMEL AI Framework with Workforce integration

The Coordinator Agent orchestrates the entire content creation workflow,
managing task assignment, progress tracking, and human checkpoints.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
import json

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.tasks import Task, TaskManager
from camel.societies.workforce import Workforce
from camel.types import TaskState

from app.agents.base.agent_factory import agent_factory, AgentType
from app.database.connection import SessionLocal
from app.database.models.project import Project
from app.database.models.chat_instance import ChatInstance
from app.database.models.human_checkpoint import HumanCheckpoint
from app.knowledge.base.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

class WorkflowState(Enum):
    """Workflow states for content creation process"""
    INITIALIZING = "initializing"
    STYLE_ANALYSIS = "style_analysis"
    CONTENT_PLANNING = "content_planning"
    CONTENT_GENERATION = "content_generation"
    EDITING_QA = "editing_qa"
    HUMAN_REVIEW = "human_review"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class ProductionCoordinatorAgent(ChatAgent):
    """
    Production-grade Coordinator Agent that orchestrates multi-agent workflows
    for content creation using CAMEL's Workforce system.
    """
    
    def __init__(self, project_id: str, **kwargs):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{project_id}")
        
        # Initialize system message for coordinator role
        system_message = self._create_coordinator_system_message()
        super().__init__(system_message=system_message, **kwargs)
        
        # Initialize components
        self.workforce = None
        self.task_manager = None
        self.knowledge_base = KnowledgeBase(project_id) if project_id else None
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.agent_pool: Dict[AgentType, ChatAgent] = {}
        
        # Workflow configuration
        self.workflow_config = self._load_workflow_config()
        
        # Human checkpoint configuration
        self.human_checkpoint_config = {
            "style_analysis_approval": True,
            "content_outline_approval": True,
            "draft_review": True,
            "final_approval": True
        }
        
        # Performance tracking
        self.metrics = {
            "workflows_completed": 0,
            "average_completion_time": 0,
            "error_count": 0,
            "human_interventions": 0
        }
    
    def _create_coordinator_system_message(self) -> BaseMessage:
        """Create comprehensive system message for coordinator role"""
        content = f"""
            You are the Production Coordinator Agent for SpinScribe, a multi-agent content creation system.

            CORE RESPONSIBILITIES:
            • Orchestrate complex content creation workflows across specialized agents
            • Manage task assignment, progress tracking, and quality assurance
            • Handle human checkpoints and approval processes
            • Ensure brand voice consistency throughout the content creation process
            • Coordinate with database systems for project context and status updates
            • Monitor workflow performance and identify optimization opportunities

            SPECIALIZED AGENTS UNDER YOUR COORDINATION:
            • Style Analyzer: Extracts brand voice patterns and creates language codes
            • Content Planner: Creates structured outlines and content strategies
            • Content Generator: Produces draft content following brand guidelines
            • Editor/QA: Reviews and refines content for quality and consistency

            WORKFLOW MANAGEMENT PRINCIPLES:
            • Always maintain project context from database (Project ID: {self.project_id})
            • Ensure each workflow step is completed before proceeding to the next
            • Implement human checkpoints at critical decision points
            • Track and report progress transparently
            • Handle errors gracefully with fallback strategies
            • Optimize for both quality and efficiency

            COMMUNICATION STYLE:
            • Clear, professional, and action-oriented
            • Provide detailed status updates and progress reports
            • Present information in structured, easily digestible formats
            • Escalate issues promptly when human intervention is required

            You have access to the project knowledge base and can coordinate with all specialized agents to deliver high-quality content that matches the client's brand voice and requirements.
            """
        
        return BaseMessage.make_assistant_message(
            role_name="production_coordinator",
            content=content
        )
    
    def _load_workflow_config(self) -> Dict[str, Any]:
        """Load workflow configuration for content creation"""
        return {
            "max_parallel_tasks": 3,
            "task_timeout_minutes": 30,
            "retry_attempts": 2,
            "quality_threshold": 0.8,
            "human_checkpoint_timeout_hours": 24,
            "workflow_steps": [
                {
                    "name": "style_analysis",
                    "agent_type": AgentType.STYLE_ANALYZER,
                    "required": True,
                    "human_checkpoint": True,
                    "timeout_minutes": 15
                },
                {
                    "name": "content_planning",
                    "agent_type": AgentType.CONTENT_PLANNER,
                    "required": True,
                    "human_checkpoint": True,
                    "timeout_minutes": 20,
                    "depends_on": ["style_analysis"]
                },
                {
                    "name": "content_generation",
                    "agent_type": AgentType.CONTENT_GENERATOR,
                    "required": True,
                    "human_checkpoint": False,
                    "timeout_minutes": 25,
                    "depends_on": ["content_planning"]
                },
                {
                    "name": "editing_qa",
                    "agent_type": AgentType.EDITOR_QA,
                    "required": True,
                    "human_checkpoint": True,
                    "timeout_minutes": 20,
                    "depends_on": ["content_generation"]
                }
            ]
        }
    
    async def initialize_workforce(self):
        """Initialize CAMEL Workforce with specialized agents"""
        try:
            self.logger.info("Initializing workforce for content creation")
            
            # Create workforce instance
            self.workforce = Workforce("SpinScribe Content Creation Workforce")
            
            # Initialize specialized agents
            await self._initialize_agent_pool()
            
            # Add agents to workforce
            self._add_agents_to_workforce()
            
            self.logger.info("Workforce initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize workforce: {e}")
            raise
    
    async def _initialize_agent_pool(self):
        """Initialize pool of specialized agents"""
        for agent_type in [AgentType.STYLE_ANALYZER, AgentType.CONTENT_PLANNER, 
                          AgentType.CONTENT_GENERATOR, AgentType.EDITOR_QA]:
            try:
                agent = agent_factory.create_agent(
                    agent_type=agent_type,
                    project_id=self.project_id,
                    custom_instructions=f"Specialized agent for {agent_type.value} in project {self.project_id}"
                )
                self.agent_pool[agent_type] = agent
                self.logger.info(f"Initialized {agent_type.value} agent")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize {agent_type.value} agent: {e}")
                raise
    
    def _add_agents_to_workforce(self):
        """Add specialized agents to workforce with descriptions"""
        agent_descriptions = {
            AgentType.STYLE_ANALYZER: "Specialized agent for analyzing brand voice patterns, extracting linguistic features, and generating style guides and language codes",
            AgentType.CONTENT_PLANNER: "Expert agent for creating structured content outlines, SEO optimization, and content strategy development",
            AgentType.CONTENT_GENERATOR: "Creative agent for generating high-quality content that follows brand guidelines and style requirements",
            AgentType.EDITOR_QA: "Quality assurance agent for reviewing, editing, and ensuring content meets brand standards and requirements"
        }
        
        for agent_type, agent in self.agent_pool.items():
            description = agent_descriptions[agent_type]
            self.workforce.add_single_agent_worker(description, worker=agent)
    
    async def start_content_workflow(self, 
                                   workflow_request: Dict[str, Any]) -> str:
        """
        Start a new content creation workflow
        
        Args:
            workflow_request: Dictionary containing workflow parameters
            
        Returns:
            workflow_id: Unique identifier for the started workflow
        """
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.project_id}"
        
        try:
            self.logger.info(f"Starting content workflow: {workflow_id}")
            
            # Initialize workforce if not already done
            if self.workforce is None:
                await self.initialize_workforce()
            
            # Create workflow context
            workflow_context = {
                "workflow_id": workflow_id,
                "project_id": self.project_id,
                "request": workflow_request,
                "state": WorkflowState.INITIALIZING,
                "created_at": datetime.now(),
                "steps_completed": [],
                "current_step": None,
                "results": {},
                "human_checkpoints": [],
                "errors": []
            }
            
            # Store workflow
            self.active_workflows[workflow_id] = workflow_context
            
            # Start workflow execution
            await self._execute_workflow(workflow_id)
            
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"Failed to start workflow {workflow_id}: {e}")
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["state"] = WorkflowState.FAILED
                self.active_workflows[workflow_id]["errors"].append(str(e))
            raise
    
    async def _execute_workflow(self, workflow_id: str):
        """Execute the content creation workflow"""
        context = self.active_workflows[workflow_id]
        
        try:
            # Execute workflow steps in sequence
            for step_config in self.workflow_config["workflow_steps"]:
                await self._execute_workflow_step(workflow_id, step_config)
            
            # Mark workflow as completed
            context["state"] = WorkflowState.COMPLETED
            context["completed_at"] = datetime.now()
            
            self.logger.info(f"Workflow {workflow_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Workflow {workflow_id} failed: {e}")
            context["state"] = WorkflowState.FAILED
            context["errors"].append(str(e))
            raise
    
    async def _execute_workflow_step(self, 
                                   workflow_id: str, 
                                   step_config: Dict[str, Any]):
        """Execute a single workflow step"""
        context = self.active_workflows[workflow_id]
        step_name = step_config["name"]
        
        self.logger.info(f"Executing step '{step_name}' for workflow {workflow_id}")
        
        try:
            # Check dependencies
            if "depends_on" in step_config:
                for dependency in step_config["depends_on"]:
                    if dependency not in context["steps_completed"]:
                        raise ValueError(f"Dependency '{dependency}' not completed for step '{step_name}'")
            
            # Update workflow state
            context["current_step"] = step_name
            context["state"] = WorkflowState(step_name)
            
            # Create task for the step
            task = await self._create_step_task(workflow_id, step_config)
            
            # Execute task using workforce
            completed_task = self.workforce.process_task(task)
            
            # Store results
            context["results"][step_name] = {
                "task_id": task.id,
                "result": completed_task.result,
                "completed_at": datetime.now(),
                "agent_type": step_config["agent_type"].value
            }
            
            # Handle human checkpoint if required
            if step_config.get("human_checkpoint", False):
                await self._create_human_checkpoint(workflow_id, step_name, completed_task.result)
            
            # Mark step as completed
            context["steps_completed"].append(step_name)
            
            self.logger.info(f"Step '{step_name}' completed for workflow {workflow_id}")
            
        except Exception as e:
            self.logger.error(f"Step '{step_name}' failed for workflow {workflow_id}: {e}")
            context["errors"].append(f"Step {step_name}: {str(e)}")
            raise
    
    async def _create_step_task(self, 
                              workflow_id: str, 
                              step_config: Dict[str, Any]) -> Task:
        """Create a task for a workflow step"""
        context = self.active_workflows[workflow_id]
        step_name = step_config["name"]
        
        # Get project context from database
        project_context = await self._get_project_context()
        
        # Create task content based on step type
        task_content = await self._generate_task_content(step_name, context, project_context)
        
        # Create task
        task = Task(
            content=task_content,
            id=f"{workflow_id}_{step_name}_{datetime.now().strftime('%H%M%S')}"
        )
        
        return task
    
    async def _generate_task_content(self, 
                                   step_name: str, 
                                   workflow_context: Dict[str, Any],
                                   project_context: Dict[str, Any]) -> str:
        """Generate task content for specific workflow step"""
        
        base_context = f"""
            Project Context:
            - Project ID: {self.project_id}
            - Client: {project_context.get('client_name', 'Unknown')}
            - Brand Voice: {project_context.get('configuration', {}).get('brand_voice', 'Not specified')}
            - Target Audience: {project_context.get('configuration', {}).get('target_audience', 'General')}

            Workflow Request: {json.dumps(workflow_context['request'], indent=2)}
            """
        
        if step_name == "style_analysis":
            return f"""
                {base_context}

                TASK: Perform comprehensive style analysis for this project.

                REQUIREMENTS:
                1. Analyze all available content samples in the project knowledge base
                2. Extract linguistic patterns, vocabulary preferences, and sentence structures
                3. Identify brand voice characteristics and tone patterns
                4. Generate a detailed language code following the team's format
                5. Create implementation guidelines for content creation

                DELIVERABLES:
                - Comprehensive style analysis report
                - Brand voice profile with specific characteristics
                - Language code in the format: CF=X, LF=Y, VL=Z, etc.
                - Style guide for content creators
                - Confidence score for the analysis

                Ensure the analysis is thorough and actionable for the content creation team.
                """
                        
        elif step_name == "content_planning":
            style_results = workflow_context["results"].get("style_analysis", {})
            return f"""
                {base_context}

                Previous Step Results:
                {json.dumps(style_results, indent=2)}

                TASK: Create a detailed content plan and outline.

                REQUIREMENTS:
                1. Use the style analysis results to inform content structure
                2. Consider SEO requirements and keyword integration
                3. Plan content flow and logical progression
                4. Ensure alignment with brand voice and target audience
                5. Include clear section descriptions and objectives

                DELIVERABLES:
                - Detailed content outline with sections and subsections
                - SEO strategy and keyword recommendations
                - Content flow and structure recommendations
                - Brand voice integration guidelines
                - Estimated word count and content specifications

                Create a comprehensive plan that guides the content generation process.
                """
        
        elif step_name == "content_generation":
            style_results = workflow_context["results"].get("style_analysis", {})
            planning_results = workflow_context["results"].get("content_planning", {})
            return f"""
                {base_context}

                Previous Step Results:
                Style Analysis: {json.dumps(style_results, indent=2)}
                Content Planning: {json.dumps(planning_results, indent=2)}

                TASK: Generate high-quality content following the approved outline and style guide.

                REQUIREMENTS:
                1. Follow the content outline precisely
                2. Maintain consistent brand voice throughout
                3. Integrate keywords naturally and effectively
                4. Ensure content engages the target audience
                5. Meet all specified quality requirements

                DELIVERABLES:
                - Complete draft content following the outline
                - Brand voice consistency verification
                - Keyword integration confirmation
                - Content quality assessment
                - Recommendations for enhancement

                Create engaging, high-quality content that matches the client's brand voice perfectly.
                """
        
        elif step_name == "editing_qa":
            previous_results = {k: v for k, v in workflow_context["results"].items() 
                              if k != "editing_qa"}
            return f"""
                {base_context}

                Previous Step Results:
                {json.dumps(previous_results, indent=2)}

                TASK: Review and refine the generated content for quality and brand consistency.

                REQUIREMENTS:
                1. Check adherence to brand guidelines and style
                2. Verify content accuracy and clarity
                3. Ensure consistency with previous content
                4. Identify areas for improvement
                5. Validate compliance with all requirements

                DELIVERABLES:
                - Comprehensive content review report
                - Quality assessment with specific scores
                - List of identified improvements
                - Final edited content version
                - Compliance verification checklist

                Ensure the content meets the highest quality standards before human review.
                """
        
        else:
            return f"Execute {step_name} task for project {self.project_id}"
    
    async def _create_human_checkpoint(self, 
                                     workflow_id: str, 
                                     step_name: str, 
                                     step_result: str):
        """Create a human checkpoint for workflow step approval"""
        try:
            db = SessionLocal()
            
            checkpoint = HumanCheckpoint(
                project_id=self.project_id,
                workflow_id=workflow_id,
                checkpoint_type=step_name,
                content=step_result,
                status="pending",
                created_at=datetime.now(),
                metadata={
                    "step_name": step_name,
                    "workflow_context": self.active_workflows[workflow_id]["request"]
                }
            )
            
            db.add(checkpoint)
            db.commit()
            
            # Store checkpoint reference in workflow context
            self.active_workflows[workflow_id]["human_checkpoints"].append({
                "checkpoint_id": checkpoint.checkpoint_id,
                "step_name": step_name,
                "status": "pending",
                "created_at": datetime.now()
            })
            
            self.logger.info(f"Created human checkpoint for {step_name} in workflow {workflow_id}")
            
            db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to create human checkpoint: {e}")
            if 'db' in locals():
                db.rollback()
                db.close()
            raise
    
    async def _get_project_context(self) -> Dict[str, Any]:
        """Get project context from database"""
        try:
            db = SessionLocal()
            project = db.query(Project).filter(Project.project_id == self.project_id).first()
            
            if not project:
                return {"error": "Project not found"}
            
            context = {
                "project_id": project.project_id,
                "client_name": project.client_name,
                "description": project.description,
                "configuration": project.configuration,
                "status": project.status,
                "created_at": project.created_at
            }
            
            db.close()
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get project context: {e}")
            if 'db' in locals():
                db.close()
            return {"error": str(e)}
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current status of a workflow"""
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}
        
        context = self.active_workflows[workflow_id]
        
        # Calculate progress
        total_steps = len(self.workflow_config["workflow_steps"])
        completed_steps = len(context["steps_completed"])
        progress_percentage = (completed_steps / total_steps) * 100
        
        # Calculate duration
        duration = None
        if "completed_at" in context:
            duration = (context["completed_at"] - context["created_at"]).total_seconds()
        else:
            duration = (datetime.now() - context["created_at"]).total_seconds()
        
        return {
            "workflow_id": workflow_id,
            "state": context["state"].value,
            "progress_percentage": progress_percentage,
            "steps_completed": context["steps_completed"],
            "current_step": context["current_step"],
            "duration_seconds": duration,
            "human_checkpoints": context["human_checkpoints"],
            "error_count": len(context["errors"]),
            "last_updated": datetime.now()
        }
    
    async def pause_workflow(self, workflow_id: str):
        """Pause an active workflow"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]["state"] = WorkflowState.PAUSED
            self.logger.info(f"Workflow {workflow_id} paused")
    
    async def resume_workflow(self, workflow_id: str):
        """Resume a paused workflow"""
        if workflow_id in self.active_workflows:
            context = self.active_workflows[workflow_id]
            if context["state"] == WorkflowState.PAUSED:
                # Resume from current step
                await self._execute_workflow(workflow_id)
                self.logger.info(f"Workflow {workflow_id} resumed")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get coordinator performance metrics"""
        return {
            "workflows_completed": self.metrics["workflows_completed"],
            "average_completion_time": self.metrics["average_completion_time"],
            "error_count": self.metrics["error_count"],
            "human_interventions": self.metrics["human_interventions"],
            "active_workflows": len(self.active_workflows),
            "agent_pool_size": len(self.agent_pool)
        }
    
    def process_task(self, task):
        """Legacy method for backwards compatibility"""
        response = self.step(task)
        return response


# Factory function for easy instantiation
async def create_coordinator_agent(project_id: str) -> ProductionCoordinatorAgent:
    """
    Factory function to create and initialize a ProductionCoordinatorAgent
    
    Args:
        project_id: Project ID for database integration
        
    Returns:
        Initialized ProductionCoordinatorAgent instance
    """
    coordinator = ProductionCoordinatorAgent(project_id)
    await coordinator.initialize_workforce()
    return coordinator


# Export main classes
__all__ = [
    'ProductionCoordinatorAgent',
    'WorkflowState',
    'TaskPriority',
    'create_coordinator_agent'
]