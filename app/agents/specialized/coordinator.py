# app/agents/specialized/coordinator.py
"""
Production Coordinator Agent for SpinScribe
Built on CAMEL AI Framework with Workforce integration

The Coordinator Agent orchestrates the entire content creation workflow,
managing task assignment, progress tracking, and human checkpoints.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType, RoleType
from camel.configs import ChatGPTConfig

from app.agents.base.agent_factory import AgentType
from app.database.connection import SessionLocal
from app.database.models.project import Project
from app.database.models.chat_instance import ChatInstance
from app.database.models.human_checkpoint import HumanCheckpoint
from app.core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """Workflow status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(Enum):
    """Task type enumeration"""
    STYLE_ANALYSIS = "style_analysis"
    CONTENT_PLANNING = "content_planning"
    CONTENT_GENERATION = "content_generation"
    CONTENT_EDITING = "content_editing"
    HUMAN_REVIEW = "human_review"

@dataclass
class WorkflowTask:
    """Data structure for workflow tasks"""
    task_id: str
    task_type: TaskType
    agent_type: AgentType
    input_data: Dict[str, Any]
    dependencies: List[str]
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    human_checkpoint: bool = False

@dataclass
class ContentWorkflow:
    """Complete content creation workflow"""
    workflow_id: str
    project_id: str
    content_type: str
    requirements: Dict[str, Any]
    tasks: List[WorkflowTask]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

class ProductionCoordinatorAgent:
    """
    Production-ready Coordinator Agent for SpinScribe
    
    This agent orchestrates the entire content creation workflow by:
    - Managing task assignment and scheduling
    - Coordinating between specialized agents
    - Handling human checkpoints and approvals
    - Tracking workflow progress and status
    - Managing error recovery and fallback strategies
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize CAMEL agent
        self.agent = self._initialize_camel_agent()
        
        # Active workflows tracking
        self.active_workflows: Dict[str, ContentWorkflow] = {}
        
        # Agent registry for task assignment
        self.agent_registry: Dict[AgentType, Any] = {}
        
        # Performance metrics
        self.metrics = {
            "workflows_completed": 0,
            "tasks_assigned": 0,
            "human_checkpoints_handled": 0,
            "average_completion_time": 0.0
        }
        
        self.logger.info(f"Coordinator Agent initialized for project: {project_id}")
    
    def _initialize_camel_agent(self) -> ChatAgent:
        """Initialize the underlying CAMEL ChatAgent"""
        try:
            # Create model for the coordinator
            model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                model_config_dict=ChatGPTConfig(
                    temperature=0.3,  # Lower temperature for consistent coordination
                    max_tokens=2000
                ).as_dict()
            )
            
            # Create system message for coordinator role
            system_message = BaseMessage.make_assistant_message(
                role_name="Content Creation Coordinator",
                content=f"""
                You are the Coordinator Agent for SpinScribe, a multi-agent content creation system.
                
                CORE RESPONSIBILITIES:
                • Orchestrate complex content creation workflows across specialized agents
                • Manage task assignment, progress tracking, and quality assurance
                • Handle human checkpoints and approval processes
                • Ensure brand voice consistency throughout the content creation process
                • Coordinate with database systems for project context (Project ID: {self.project_id})
                • Monitor workflow performance and identify optimization opportunities

                SPECIALIZED AGENTS UNDER YOUR COORDINATION:
                • Style Analyzer: Extracts brand voice patterns and creates language codes
                • Content Planner: Creates structured outlines and content strategies
                • Content Generator: Produces draft content following brand guidelines
                • Editor/QA: Reviews and refines content for quality and consistency

                WORKFLOW MANAGEMENT PRINCIPLES:
                • Always maintain project context from database
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
            )
            
            # Initialize the CAMEL agent
            agent = ChatAgent(
                system_message=system_message,
                model=model,
                message_window_size=50  # Increased for workflow context
            )
            
            return agent
            
        except Exception as e:
            self.logger.error(f"Failed to initialize CAMEL agent: {e}")
            raise
    
    async def start_content_workflow(self, 
                                   content_type: str, 
                                   requirements: Dict[str, Any],
                                   workflow_id: str = None) -> str:
        """
        Start a new content creation workflow
        
        Args:
            content_type: Type of content to create (blog_post, social_media, etc.)
            requirements: Content requirements and specifications
            workflow_id: Optional workflow ID (auto-generated if not provided)
            
        Returns:
            str: Workflow ID for tracking
        """
        try:
            if workflow_id is None:
                workflow_id = f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{content_type}"
            
            # Create workflow tasks based on content type
            tasks = self._create_workflow_tasks(content_type, requirements)
            
            # Create workflow instance
            workflow = ContentWorkflow(
                workflow_id=workflow_id,
                project_id=self.project_id,
                content_type=content_type,
                requirements=requirements,
                tasks=tasks
            )
            
            # Store workflow
            self.active_workflows[workflow_id] = workflow
            
            self.logger.info(f"Started workflow {workflow_id} for {content_type}")
            
            # Begin workflow execution
            await self._execute_workflow(workflow_id)
            
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"Failed to start workflow: {e}")
            raise
    
    def _create_workflow_tasks(self, content_type: str, requirements: Dict[str, Any]) -> List[WorkflowTask]:
        """Create workflow tasks based on content type and requirements"""
        tasks = []
        
        # Task 1: Style Analysis (if needed)
        if requirements.get("analyze_style", True):
            tasks.append(WorkflowTask(
                task_id=f"task_style_analysis_{datetime.utcnow().strftime('%H%M%S')}",
                task_type=TaskType.STYLE_ANALYSIS,
                agent_type=AgentType.STYLE_ANALYZER,
                input_data={
                    "project_id": self.project_id,
                    "content_samples": requirements.get("content_samples", []),
                    "analysis_depth": requirements.get("analysis_depth", "comprehensive")
                },
                dependencies=[],
                human_checkpoint=requirements.get("approve_style_analysis", False)
            ))
        
        # Task 2: Content Planning
        planning_dependencies = []
        if tasks:  # If we have style analysis
            planning_dependencies.append(tasks[0].task_id)
        
        tasks.append(WorkflowTask(
            task_id=f"task_content_planning_{datetime.utcnow().strftime('%H%M%S')}",
            task_type=TaskType.CONTENT_PLANNING,
            agent_type=AgentType.CONTENT_PLANNER,
            input_data={
                "project_id": self.project_id,
                "content_type": content_type,
                "target_audience": requirements.get("target_audience", "general"),
                "key_topics": requirements.get("key_topics", []),
                "seo_keywords": requirements.get("seo_keywords", []),
                "word_count": requirements.get("word_count", 1000),
                "tone": requirements.get("tone", "professional")
            },
            dependencies=planning_dependencies,
            human_checkpoint=requirements.get("approve_outline", True)
        ))
        
        # Task 3: Content Generation
        generation_dependencies = [tasks[-1].task_id]  # Depends on planning
        
        tasks.append(WorkflowTask(
            task_id=f"task_content_generation_{datetime.utcnow().strftime('%H%M%S')}",
            task_type=TaskType.CONTENT_GENERATION,
            agent_type=AgentType.CONTENT_GENERATOR,
            input_data={
                "project_id": self.project_id,
                "content_type": content_type,
                "requirements": requirements
            },
            dependencies=generation_dependencies,
            human_checkpoint=False
        ))
        
        # Task 4: Content Editing/QA
        editing_dependencies = [tasks[-1].task_id]  # Depends on generation
        
        tasks.append(WorkflowTask(
            task_id=f"task_content_editing_{datetime.utcnow().strftime('%H%M%S')}",
            task_type=TaskType.CONTENT_EDITING,
            agent_type=AgentType.EDITOR_QA,
            input_data={
                "project_id": self.project_id,
                "content_type": content_type,
                "quality_standards": requirements.get("quality_standards", "high")
            },
            dependencies=editing_dependencies,
            human_checkpoint=True  # Always require human approval for final content
        ))
        
        return tasks
    
    async def _execute_workflow(self, workflow_id: str):
        """Execute workflow by managing task dependencies and assignments"""
        try:
            workflow = self.active_workflows[workflow_id]
            workflow.status = WorkflowStatus.IN_PROGRESS
            
            # Execute tasks based on dependencies
            completed_tasks = set()
            
            while len(completed_tasks) < len(workflow.tasks):
                # Find tasks that can be executed (dependencies met)
                ready_tasks = [
                    task for task in workflow.tasks 
                    if task.status == WorkflowStatus.PENDING and 
                    all(dep_id in completed_tasks for dep_id in task.dependencies)
                ]
                
                if not ready_tasks:
                    # Check if we're waiting for human input
                    waiting_tasks = [
                        task for task in workflow.tasks 
                        if task.status == WorkflowStatus.WAITING_HUMAN
                    ]
                    
                    if waiting_tasks:
                        self.logger.info(f"Workflow {workflow_id} waiting for human checkpoints")
                        workflow.status = WorkflowStatus.WAITING_HUMAN
                        break
                    else:
                        self.logger.error(f"Workflow {workflow_id} has no ready tasks - possible deadlock")
                        workflow.status = WorkflowStatus.FAILED
                        break
                
                # Execute ready tasks
                for task in ready_tasks:
                    await self._execute_task(workflow_id, task)
                    
                    if task.status == WorkflowStatus.COMPLETED:
                        completed_tasks.add(task.task_id)
                    elif task.status == WorkflowStatus.WAITING_HUMAN:
                        # Task needs human checkpoint
                        await self._create_human_checkpoint(workflow_id, task)
            
            # Update workflow status
            if len(completed_tasks) == len(workflow.tasks):
                workflow.status = WorkflowStatus.COMPLETED
                self.metrics["workflows_completed"] += 1
                self.logger.info(f"Workflow {workflow_id} completed successfully")
            
            workflow.updated_at = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            workflow.status = WorkflowStatus.FAILED
            raise
    
    async def _execute_task(self, workflow_id: str, task: WorkflowTask):
        """Execute a specific task using the appropriate agent"""
        try:
            task.status = WorkflowStatus.IN_PROGRESS
            task.assigned_at = datetime.utcnow()
            
            # Get the appropriate agent for this task
            agent = await self._get_agent_for_task(task.agent_type)
            
            # Prepare task input with context
            task_input = self._prepare_task_input(workflow_id, task)
            
            # Execute task
            if task.task_type == TaskType.STYLE_ANALYSIS:
                result = await self._execute_style_analysis(agent, task_input)
            elif task.task_type == TaskType.CONTENT_PLANNING:
                result = await self._execute_content_planning(agent, task_input)
            elif task.task_type == TaskType.CONTENT_GENERATION:
                result = await self._execute_content_generation(agent, task_input)
            elif task.task_type == TaskType.CONTENT_EDITING:
                result = await self._execute_content_editing(agent, task_input)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            # Store task result
            task.result = result
            task.completed_at = datetime.utcnow()
            
            # Check if human checkpoint is needed
            if task.human_checkpoint:
                task.status = WorkflowStatus.WAITING_HUMAN
            else:
                task.status = WorkflowStatus.COMPLETED
            
            self.metrics["tasks_assigned"] += 1
            self.logger.info(f"Task {task.task_id} executed successfully")
            
        except Exception as e:
            task.status = WorkflowStatus.FAILED
            task.error_message = str(e)
            self.logger.error(f"Task {task.task_id} failed: {e}")
            raise
    
    async def _get_agent_for_task(self, agent_type: AgentType):
        """Get or create agent instance for task execution"""
        if agent_type not in self.agent_registry:
            # Import and create agent dynamically
            if agent_type == AgentType.STYLE_ANALYZER:
                from app.agents.specialized.style_analyzer import ProductionStyleAnalyzerAgent
                self.agent_registry[agent_type] = ProductionStyleAnalyzerAgent(self.project_id)
            elif agent_type == AgentType.CONTENT_PLANNER:
                from app.agents.specialized.content_planner import ProductionContentPlannerAgent
                self.agent_registry[agent_type] = ProductionContentPlannerAgent(self.project_id)
            elif agent_type == AgentType.CONTENT_GENERATOR:
                from app.agents.specialized.content_generator import ProductionContentGeneratorAgent
                self.agent_registry[agent_type] = ProductionContentGeneratorAgent(self.project_id)
            elif agent_type == AgentType.EDITOR_QA:
                from app.agents.specialized.editor_qa import ProductionEditorQAAgent
                self.agent_registry[agent_type] = ProductionEditorQAAgent(self.project_id)
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
        
        return self.agent_registry[agent_type]
    
    def _prepare_task_input(self, workflow_id: str, task: WorkflowTask) -> Dict[str, Any]:
        """Prepare input data for task execution with workflow context"""
        workflow = self.active_workflows[workflow_id]
        
        # Get dependency results
        dependency_results = {}
        for dep_id in task.dependencies:
            dep_task = next((t for t in workflow.tasks if t.task_id == dep_id), None)
            if dep_task and dep_task.result:
                dependency_results[dep_id] = dep_task.result
        
        # Combine task input with context
        return {
            **task.input_data,
            "workflow_id": workflow_id,
            "workflow_context": {
                "content_type": workflow.content_type,
                "requirements": workflow.requirements,
                "dependency_results": dependency_results
            }
        }
    
    async def _execute_style_analysis(self, agent, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute style analysis task using your production analyzer"""
        return await agent.analyze_style(
            content_samples=task_input.get("content_samples", []),
            analysis_depth=task_input.get("analysis_depth", "comprehensive")
        )
    
    async def _execute_content_planning(self, agent, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content planning task"""
        return await agent.create_content_plan(
            content_type=task_input["content_type"],
            requirements=task_input["workflow_context"]["requirements"],
            style_context=task_input["workflow_context"]["dependency_results"]
        )
    
    async def _execute_content_generation(self, agent, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content generation task"""
        return await agent.generate_content(
            content_plan=task_input["workflow_context"]["dependency_results"],
            requirements=task_input["workflow_context"]["requirements"]
        )
    
    async def _execute_content_editing(self, agent, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content editing task"""
        return await agent.edit_content(
            content=task_input["workflow_context"]["dependency_results"],
            quality_standards=task_input.get("quality_standards", "high")
        )
    
    async def _create_human_checkpoint(self, workflow_id: str, task: WorkflowTask):
        """Create human checkpoint for task approval"""
        try:
            db = SessionLocal()
            
            # Create human checkpoint record
            checkpoint = HumanCheckpoint(
                checkpoint_id=f"checkpoint_{task.task_id}",
                project_id=self.project_id,
                workflow_id=workflow_id,
                task_id=task.task_id,
                checkpoint_type=task.task_type.value,
                content_reference=json.dumps(task.result) if task.result else None,
                status="pending",
                created_at=datetime.utcnow()
            )
            
            db.add(checkpoint)
            db.commit()
            
            self.metrics["human_checkpoints_handled"] += 1
            self.logger.info(f"Created human checkpoint for task {task.task_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create human checkpoint: {e}")
            raise
        finally:
            db.close()
    
    async def handle_human_feedback(self, checkpoint_id: str, approved: bool, feedback: str = None):
        """Handle human feedback on checkpoints"""
        try:
            db = SessionLocal()
            
            # Get checkpoint
            checkpoint = db.query(HumanCheckpoint).filter(
                HumanCheckpoint.checkpoint_id == checkpoint_id
            ).first()
            
            if not checkpoint:
                raise ValueError(f"Checkpoint {checkpoint_id} not found")
            
            # Update checkpoint
            checkpoint.status = "approved" if approved else "rejected"
            checkpoint.feedback = feedback
            checkpoint.resolved_at = datetime.utcnow()
            
            db.commit()
            
            # Update task status
            workflow = self.active_workflows.get(checkpoint.workflow_id)
            if workflow:
                task = next((t for t in workflow.tasks if t.task_id == checkpoint.task_id), None)
                if task:
                    if approved:
                        task.status = WorkflowStatus.COMPLETED
                        # Continue workflow execution
                        await self._execute_workflow(checkpoint.workflow_id)
                    else:
                        task.status = WorkflowStatus.FAILED
                        task.error_message = f"Human rejection: {feedback}"
                        workflow.status = WorkflowStatus.FAILED
            
            self.logger.info(f"Processed human feedback for checkpoint {checkpoint_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle human feedback: {e}")
            raise
        finally:
            db.close()
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current status of a workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "content_type": workflow.content_type,
            "progress": {
                "total_tasks": len(workflow.tasks),
                "completed_tasks": len([t for t in workflow.tasks if t.status == WorkflowStatus.COMPLETED]),
                "failed_tasks": len([t for t in workflow.tasks if t.status == WorkflowStatus.FAILED]),
                "waiting_human": len([t for t in workflow.tasks if t.status == WorkflowStatus.WAITING_HUMAN])
            },
            "tasks": [
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "status": task.status.value,
                    "human_checkpoint": task.human_checkpoint,
                    "assigned_at": task.assigned_at.isoformat() if task.assigned_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "error_message": task.error_message
                }
                for task in workflow.tasks
            ],
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get coordinator performance metrics"""
        return {
            **self.metrics,
            "active_workflows": len(self.active_workflows),
            "agent_registry_size": len(self.agent_registry)
        }

# Backwards compatibility wrapper
class coordinatorAgent(ProductionCoordinatorAgent):
    """Backwards compatibility wrapper for existing code"""
    pass

# Factory function for easy instantiation
async def create_coordinator_agent(project_id: str = None) -> ProductionCoordinatorAgent:
    """
    Factory function to create and initialize a ProductionCoordinatorAgent
    
    Args:
        project_id: Optional project ID for database integration
        
    Returns:
        Initialized ProductionCoordinatorAgent instance
    """
    coordinator = ProductionCoordinatorAgent(project_id)
    return coordinator

# Export main classes
__all__ = [
    'ProductionCoordinatorAgent',
    'coordinatorAgent',  # For backwards compatibility
    'WorkflowStatus',
    'TaskType',
    'WorkflowTask',
    'ContentWorkflow',
    'create_coordinator_agent'
]