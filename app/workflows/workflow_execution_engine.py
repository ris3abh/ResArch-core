# app/workflows/workflow_execution_engine.py
"""
Complete Workflow Execution Engine for SpinScribe
Manages multi-agent content creation workflows with state management and coordination.
"""

from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
import json
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from app.services.base_service import BaseService
from app.services.project_service import get_project_service
from app.services.knowledge_service import get_knowledge_service
from app.agents.base.agent_factory import agent_factory, AgentType
from app.database.models.chat_instance import ChatInstance
from app.database.models.chat_message import ChatMessage
from app.database.models.human_checkpoint import HumanCheckpoint
from app.database.connection import get_db_session
from app.core.exceptions import (
    WorkflowError, 
    WorkflowStateError, 
    WorkflowTimeoutError,
    ValidationError,
    AgentError
)

logger = logging.getLogger(__name__)

class WorkflowState(Enum):
    """Workflow execution states"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    STYLE_ANALYSIS = "style_analysis"
    CONTENT_PLANNING = "content_planning"
    CONTENT_GENERATION = "content_generation"
    EDITING_QA = "editing_qa"
    HUMAN_REVIEW = "human_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class TaskType(Enum):
    """Types of workflow tasks"""
    STYLE_ANALYSIS = "style_analysis"
    CONTENT_PLANNING = "content_planning"
    CONTENT_GENERATION = "content_generation"
    CONTENT_EDITING = "content_editing"
    HUMAN_CHECKPOINT = "human_checkpoint"
    COORDINATION = "coordination"

class TaskStatus(Enum):
    """Individual task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_HUMAN = "waiting_human"
    SKIPPED = "skipped"

@dataclass
class WorkflowTask:
    """Individual workflow task definition"""
    task_id: str
    task_type: TaskType
    agent_type: AgentType
    input_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    timeout_minutes: int = 30
    retry_attempts: int = 2
    human_checkpoint: bool = False
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0

@dataclass
class WorkflowDefinition:
    """Complete workflow definition template"""
    name: str
    description: str
    workflow_type: str
    tasks: List[WorkflowTask]
    max_parallel_tasks: int = 2
    total_timeout_hours: int = 24
    auto_advance: bool = True
    required_checkpoints: List[str] = field(default_factory=list)

@dataclass
class WorkflowExecution:
    """Active workflow execution instance"""
    workflow_id: str
    project_id: str
    chat_instance_id: str
    definition: WorkflowDefinition
    state: WorkflowState = WorkflowState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    active_tasks: Dict[str, WorkflowTask] = field(default_factory=dict)
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    human_checkpoints: List[str] = field(default_factory=list)

class WorkflowExecutionEngine:
    """
    Complete workflow execution engine that orchestrates multi-agent content creation.
    Handles task scheduling, agent coordination, and state management.
    """
    
    def __init__(self):
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.task_executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize workflow templates
        self._initialize_workflow_templates()
        
        logger.info("WorkflowExecutionEngine initialized")
    
    def _initialize_workflow_templates(self) -> None:
        """Initialize predefined workflow templates"""
        
        # Blog Post Creation Workflow
        blog_workflow = WorkflowDefinition(
            name="Blog Post Creation",
            description="Complete blog post creation with style analysis, planning, generation, and review",
            workflow_type="blog_post",
            tasks=[
                WorkflowTask(
                    task_id="style_analysis",
                    task_type=TaskType.STYLE_ANALYSIS,
                    agent_type=AgentType.STYLE_ANALYZER,
                    input_data={"analysis_type": "blog_content"},
                    timeout_minutes=15
                ),
                WorkflowTask(
                    task_id="content_planning",
                    task_type=TaskType.CONTENT_PLANNING,
                    agent_type=AgentType.CONTENT_PLANNER,
                    input_data={"content_type": "blog_post"},
                    dependencies=["style_analysis"],
                    timeout_minutes=20,
                    human_checkpoint=True
                ),
                WorkflowTask(
                    task_id="content_generation",
                    task_type=TaskType.CONTENT_GENERATION,
                    agent_type=AgentType.CONTENT_GENERATOR,
                    input_data={"content_type": "blog_post"},
                    dependencies=["content_planning"],
                    timeout_minutes=45
                ),
                WorkflowTask(
                    task_id="content_editing",
                    task_type=TaskType.CONTENT_EDITING,
                    agent_type=AgentType.EDITOR_QA,
                    input_data={"editing_type": "comprehensive"},
                    dependencies=["content_generation"],
                    timeout_minutes=25,
                    human_checkpoint=True
                )
            ],
            required_checkpoints=["content_planning", "content_editing"]
        )
        
        # Social Media Campaign Workflow
        social_workflow = WorkflowDefinition(
            name="Social Media Campaign",
            description="Multi-platform social media content creation",
            workflow_type="social_media",
            tasks=[
                WorkflowTask(
                    task_id="style_analysis",
                    task_type=TaskType.STYLE_ANALYSIS,
                    agent_type=AgentType.STYLE_ANALYZER,
                    input_data={"analysis_type": "social_content"},
                    timeout_minutes=10
                ),
                WorkflowTask(
                    task_id="campaign_planning",
                    task_type=TaskType.CONTENT_PLANNING,
                    agent_type=AgentType.CONTENT_PLANNER,
                    input_data={"content_type": "social_campaign"},
                    dependencies=["style_analysis"],
                    timeout_minutes=30,
                    human_checkpoint=True
                ),
                WorkflowTask(
                    task_id="content_generation",
                    task_type=TaskType.CONTENT_GENERATION,
                    agent_type=AgentType.CONTENT_GENERATOR,
                    input_data={"content_type": "social_posts"},
                    dependencies=["campaign_planning"],
                    timeout_minutes=35
                ),
                WorkflowTask(
                    task_id="content_review",
                    task_type=TaskType.CONTENT_EDITING,
                    agent_type=AgentType.EDITOR_QA,
                    input_data={"editing_type": "social_media"},
                    dependencies=["content_generation"],
                    timeout_minutes=15,
                    human_checkpoint=True
                )
            ]
        )
        
        # Website Content Workflow
        website_workflow = WorkflowDefinition(
            name="Website Content Creation",
            description="SEO-optimized website content creation",
            workflow_type="website_content",
            tasks=[
                WorkflowTask(
                    task_id="style_analysis",
                    task_type=TaskType.STYLE_ANALYSIS,
                    agent_type=AgentType.STYLE_ANALYZER,
                    input_data={"analysis_type": "website_content"},
                    timeout_minutes=20
                ),
                WorkflowTask(
                    task_id="seo_planning",
                    task_type=TaskType.CONTENT_PLANNING,
                    agent_type=AgentType.CONTENT_PLANNER,
                    input_data={"content_type": "website", "focus": "seo"},
                    dependencies=["style_analysis"],
                    timeout_minutes=35,
                    human_checkpoint=True
                ),
                WorkflowTask(
                    task_id="content_generation",
                    task_type=TaskType.CONTENT_GENERATION,
                    agent_type=AgentType.CONTENT_GENERATOR,
                    input_data={"content_type": "website", "seo_focus": True},
                    dependencies=["seo_planning"],
                    timeout_minutes=60
                ),
                WorkflowTask(
                    task_id="seo_optimization",
                    task_type=TaskType.CONTENT_EDITING,
                    agent_type=AgentType.EDITOR_QA,
                    input_data={"editing_type": "seo_optimization"},
                    dependencies=["content_generation"],
                    timeout_minutes=30,
                    human_checkpoint=True
                )
            ]
        )
        
        # Store workflow definitions
        self.workflow_definitions = {
            "blog_post": blog_workflow,
            "social_media": social_workflow,
            "website_content": website_workflow
        }
        
        logger.info(f"Initialized {len(self.workflow_definitions)} workflow templates")
    
    async def start_workflow(
        self, 
        workflow_type: str, 
        project_id: str, 
        chat_instance_id: str,
        content_requirements: Dict[str, Any],
        custom_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new workflow execution"""
        
        # Validate inputs
        if workflow_type not in self.workflow_definitions:
            raise WorkflowError(f"Unknown workflow type: {workflow_type}")
        
        # Generate workflow ID
        workflow_id = f"workflow_{workflow_type}_{uuid.uuid4().hex[:8]}"
        
        # Get workflow definition
        definition = self.workflow_definitions[workflow_type]
        
        # Apply custom configuration if provided
        if custom_config:
            definition = self._apply_custom_config(definition, custom_config)
        
        # Enhance tasks with project context
        enhanced_tasks = await self._enhance_tasks_with_context(
            definition.tasks, 
            project_id, 
            content_requirements
        )
        
        # Create workflow execution
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            project_id=project_id,
            chat_instance_id=chat_instance_id,
            definition=WorkflowDefinition(
                name=definition.name,
                description=definition.description,
                workflow_type=definition.workflow_type,
                tasks=enhanced_tasks,
                max_parallel_tasks=definition.max_parallel_tasks,
                total_timeout_hours=definition.total_timeout_hours,
                auto_advance=definition.auto_advance,
                required_checkpoints=definition.required_checkpoints
            ),
            state=WorkflowState.PENDING,
            metadata={
                "content_requirements": content_requirements,
                "custom_config": custom_config or {},
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        # Store workflow
        self.active_workflows[workflow_id] = execution
        
        # Start execution asynchronously
        asyncio.create_task(self._execute_workflow(workflow_id))
        
        logger.info(f"Started workflow {workflow_id} for project {project_id}")
        return workflow_id
    
    async def _execute_workflow(self, workflow_id: str) -> None:
        """Execute a workflow from start to completion"""
        try:
            execution = self.active_workflows[workflow_id]
            execution.state = WorkflowState.INITIALIZING
            execution.started_at = datetime.utcnow()
            
            logger.info(f"Executing workflow {workflow_id}")
            
            # Process tasks based on dependencies
            while not self._is_workflow_complete(execution):
                # Get ready tasks (dependencies satisfied)
                ready_tasks = self._get_ready_tasks(execution)
                
                if not ready_tasks:
                    # Check if waiting for human checkpoints
                    waiting_checkpoints = self._get_waiting_checkpoints(execution)
                    if waiting_checkpoints:
                        execution.state = WorkflowState.HUMAN_REVIEW
                        logger.info(f"Workflow {workflow_id} waiting for human checkpoints")
                        await asyncio.sleep(30)  # Check again in 30 seconds
                        continue
                    else:
                        # No ready tasks and no waiting checkpoints - check for deadlock
                        if self._detect_deadlock(execution):
                            raise WorkflowError("Workflow deadlock detected")
                        await asyncio.sleep(10)  # Brief pause before checking again
                        continue
                
                # Execute ready tasks (respecting parallel limits)
                active_count = len([t for t in execution.active_tasks.values() 
                                  if t.status == TaskStatus.IN_PROGRESS])
                
                tasks_to_start = ready_tasks[:execution.definition.max_parallel_tasks - active_count]
                
                for task in tasks_to_start:
                    await self._execute_task(execution, task)
                
                # Brief pause between task scheduling
                await asyncio.sleep(5)
            
            # Workflow completed
            await self._complete_workflow(execution)
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            await self._fail_workflow(workflow_id, str(e))
    
    async def _execute_task(self, execution: WorkflowExecution, task: WorkflowTask) -> None:
        """Execute a single workflow task"""
        try:
            logger.info(f"Starting task {task.task_id} in workflow {execution.workflow_id}")
            
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.utcnow()
            execution.active_tasks[task.task_id] = task
            
            # Update workflow state based on task type
            execution.state = self._get_workflow_state_for_task(task.task_type)
            
            # Create agent for task
            agent = agent_factory.create_agent(
                agent_type=task.agent_type,
                project_id=execution.project_id,
                custom_instructions=self._get_task_instructions(task, execution)
            )
            
            # Prepare task input with context
            task_input = await self._prepare_task_input(task, execution)
            
            # Execute task with timeout
            result = await asyncio.wait_for(
                self._run_agent_task(agent, task_input),
                timeout=task.timeout_minutes * 60
            )
            
            # Process result
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            # Remove from active tasks
            del execution.active_tasks[task.task_id]
            execution.completed_tasks.append(task.task_id)
            
            # Create human checkpoint if required
            if task.human_checkpoint:
                await self._create_human_checkpoint(execution, task)
            
            # Log task completion
            await self._log_task_completion(execution, task)
            
            logger.info(f"Completed task {task.task_id} in workflow {execution.workflow_id}")
            
        except asyncio.TimeoutError:
            await self._handle_task_timeout(execution, task)
        except Exception as e:
            await self._handle_task_failure(execution, task, str(e))
    
    async def _run_agent_task(self, agent, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Run agent task and return structured result"""
        try:
            # Format input for agent
            input_message = self._format_agent_input(task_input)
            
            # Run agent in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.task_executor,
                lambda: agent.step(input_message)
            )
            
            # Process agent response
            return self._process_agent_response(response, task_input)
            
        except Exception as e:
            logger.error(f"Agent task execution failed: {e}")
            raise AgentError(f"Agent execution failed: {e}")
    
    def _format_agent_input(self, task_input: Dict[str, Any]) -> str:
        """Format task input for agent consumption"""
        content_type = task_input.get("content_type", "content")
        requirements = task_input.get("content_requirements", {})
        context = task_input.get("context", {})
        
        input_parts = []
        
        # Add content requirements
        if requirements:
            input_parts.append("CONTENT REQUIREMENTS:")
            for key, value in requirements.items():
                input_parts.append(f"- {key}: {value}")
            input_parts.append("")
        
        # Add project context
        if context:
            input_parts.append("PROJECT CONTEXT:")
            for key, value in context.items():
                if isinstance(value, (str, int, float)):
                    input_parts.append(f"- {key}: {value}")
            input_parts.append("")
        
        # Add task-specific instructions
        task_type = task_input.get("task_type", "")
        if task_type == "style_analysis":
            input_parts.append("TASK: Analyze the provided content samples to identify brand voice patterns, tone, and style guidelines.")
        elif task_type == "content_planning":
            input_parts.append("TASK: Create a detailed content outline based on the requirements and style analysis.")
        elif task_type == "content_generation":
            input_parts.append("TASK: Generate high-quality content following the provided outline and style guidelines.")
        elif task_type == "content_editing":
            input_parts.append("TASK: Review and edit the content for quality, accuracy, and brand alignment.")
        
        return "\n".join(input_parts)
    
    def _process_agent_response(self, response, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process agent response into structured result"""
        # Extract text content from agent response
        if hasattr(response, 'content'):
            content = response.content
        elif hasattr(response, 'text'):
            content = response.text
        else:
            content = str(response)
        
        # Create structured result
        result = {
            "content": content,
            "task_type": task_input.get("task_type", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "agent_type": task_input.get("agent_type", "unknown"),
            "metadata": {
                "word_count": len(content.split()) if isinstance(content, str) else 0,
                "processing_time": task_input.get("processing_time", 0)
            }
        }
        
        return result
    
    async def _prepare_task_input(self, task: WorkflowTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Prepare comprehensive input for task execution"""
        # Get project context
        project_service = get_project_service()
        knowledge_service = get_knowledge_service()
        
        with get_db_session() as db:
            # Get project information
            project = project_service.get_by_id_or_raise(execution.project_id, db)
            
            # Get relevant knowledge
            knowledge_items = knowledge_service.get_by_project_id(execution.project_id, db)
            
            # Get previous task results
            previous_results = {}
            for dep_task_id in task.dependencies:
                if dep_task_id in execution.completed_tasks:
                    for completed_task in execution.definition.tasks:
                        if completed_task.task_id == dep_task_id and completed_task.result:
                            previous_results[dep_task_id] = completed_task.result
        
        # Prepare task input
        task_input = {
            **task.input_data,
            "task_type": task.task_type.value,
            "agent_type": task.agent_type.value,
            "project_id": execution.project_id,
            "content_requirements": execution.metadata.get("content_requirements", {}),
            "context": {
                "project_name": project.client_name,
                "project_config": project.configuration,
                "knowledge_count": len(knowledge_items),
                "previous_results": previous_results
            }
        }
        
        return task_input
    
    async def _create_human_checkpoint(self, execution: WorkflowExecution, task: WorkflowTask) -> None:
        """Create a human checkpoint for task review"""
        try:
            with get_db_session() as db:
                checkpoint = HumanCheckpoint(
                    checkpoint_id=f"checkpoint_{task.task_id}_{uuid.uuid4().hex[:8]}",
                    chat_id=execution.chat_instance_id,
                    checkpoint_type=task.task_type.value,
                    content_reference=task.task_id,
                    status="pending",
                    created_at=datetime.utcnow()
                )
                
                db.add(checkpoint)
                db.commit()
                
                execution.human_checkpoints.append(checkpoint.checkpoint_id)
                
                logger.info(f"Created human checkpoint {checkpoint.checkpoint_id} for task {task.task_id}")
                
        except Exception as e:
            logger.error(f"Failed to create human checkpoint: {e}")
    
    async def _log_task_completion(self, execution: WorkflowExecution, task: WorkflowTask) -> None:
        """Log task completion to chat"""
        try:
            with get_db_session() as db:
                message = ChatMessage(
                    message_id=f"msg_{task.task_id}_{uuid.uuid4().hex[:8]}",
                    chat_id=execution.chat_instance_id,
                    sender_id=task.agent_type.value,
                    sender_type="agent",
                    content={
                        "type": "task_completion",
                        "task_id": task.task_id,
                        "task_type": task.task_type.value,
                        "result_summary": task.result.get("content", "")[:200] + "..." if task.result else "No result",
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None
                    },
                    created_at=datetime.utcnow()
                )
                
                db.add(message)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to log task completion: {e}")
    
    def _get_ready_tasks(self, execution: WorkflowExecution) -> List[WorkflowTask]:
        """Get tasks that are ready to execute (dependencies satisfied)"""
        ready_tasks = []
        
        for task in execution.definition.tasks:
            # Skip if already completed, failed, or in progress
            if (task.task_id in execution.completed_tasks or 
                task.task_id in execution.failed_tasks or
                task.task_id in execution.active_tasks):
                continue
            
            # Check if all dependencies are completed
            dependencies_met = all(
                dep_id in execution.completed_tasks 
                for dep_id in task.dependencies
            )
            
            if dependencies_met:
                ready_tasks.append(task)
        
        return ready_tasks
    
    def _get_waiting_checkpoints(self, execution: WorkflowExecution) -> List[str]:
        """Get checkpoints waiting for human review"""
        try:
            with get_db_session() as db:
                pending_checkpoints = db.query(HumanCheckpoint).filter(
                    HumanCheckpoint.chat_id == execution.chat_instance_id,
                    HumanCheckpoint.status == "pending"
                ).all()
                
                return [cp.checkpoint_id for cp in pending_checkpoints]
                
        except Exception as e:
            logger.error(f"Failed to get waiting checkpoints: {e}")
            return []
    
    def _is_workflow_complete(self, execution: WorkflowExecution) -> bool:
        """Check if workflow is complete"""
        total_tasks = len(execution.definition.tasks)
        completed_tasks = len(execution.completed_tasks)
        failed_tasks = len(execution.failed_tasks)
        
        return completed_tasks + failed_tasks >= total_tasks
    
    def _detect_deadlock(self, execution: WorkflowExecution) -> bool:
        """Detect if workflow is in deadlock state"""
        # Simple deadlock detection: no active tasks and no ready tasks
        return (len(execution.active_tasks) == 0 and 
                len(self._get_ready_tasks(execution)) == 0 and
                not self._is_workflow_complete(execution))
    
    async def _complete_workflow(self, execution: WorkflowExecution) -> None:
        """Complete workflow execution"""
        execution.state = WorkflowState.COMPLETED
        execution.completed_at = datetime.utcnow()
        
        logger.info(f"Workflow {execution.workflow_id} completed successfully")
        
        # Log final completion message
        try:
            with get_db_session() as db:
                completion_message = ChatMessage(
                    message_id=f"msg_workflow_complete_{uuid.uuid4().hex[:8]}",
                    chat_id=execution.chat_instance_id,
                    sender_id="system",
                    sender_type="system",
                    content={
                        "type": "workflow_completion",
                        "workflow_id": execution.workflow_id,
                        "workflow_type": execution.definition.workflow_type,
                        "completed_tasks": len(execution.completed_tasks),
                        "failed_tasks": len(execution.failed_tasks),
                        "duration_minutes": (execution.completed_at - execution.started_at).total_seconds() / 60 if execution.started_at else 0
                    },
                    created_at=datetime.utcnow()
                )
                
                db.add(completion_message)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to log workflow completion: {e}")
    
    async def _fail_workflow(self, workflow_id: str, error_message: str) -> None:
        """Fail workflow execution"""
        if workflow_id in self.active_workflows:
            execution = self.active_workflows[workflow_id]
            execution.state = WorkflowState.FAILED
            execution.metadata["error"] = error_message
            execution.metadata["failed_at"] = datetime.utcnow().isoformat()
            
            logger.error(f"Workflow {workflow_id} failed: {error_message}")
    
    async def _handle_task_timeout(self, execution: WorkflowExecution, task: WorkflowTask) -> None:
        """Handle task timeout"""
        task.retry_count += 1
        
        if task.retry_count <= task.retry_attempts:
            logger.warning(f"Task {task.task_id} timed out, retrying ({task.retry_count}/{task.retry_attempts})")
            task.status = TaskStatus.PENDING
            if task.task_id in execution.active_tasks:
                del execution.active_tasks[task.task_id]
        else:
            logger.error(f"Task {task.task_id} failed after {task.retry_attempts} retry attempts")
            task.status = TaskStatus.FAILED
            task.error_message = "Task timeout exceeded retry limit"
            if task.task_id in execution.active_tasks:
                del execution.active_tasks[task.task_id]
            execution.failed_tasks.append(task.task_id)
    
    async def _handle_task_failure(self, execution: WorkflowExecution, task: WorkflowTask, error_message: str) -> None:
        """Handle task failure"""
        task.retry_count += 1
        
        if task.retry_count <= task.retry_attempts:
            logger.warning(f"Task {task.task_id} failed, retrying ({task.retry_count}/{task.retry_attempts}): {error_message}")
            task.status = TaskStatus.PENDING
            if task.task_id in execution.active_tasks:
                del execution.active_tasks[task.task_id]
        else:
            logger.error(f"Task {task.task_id} failed permanently: {error_message}")
            task.status = TaskStatus.FAILED
            task.error_message = error_message
            if task.task_id in execution.active_tasks:
                del execution.active_tasks[task.task_id]
            execution.failed_tasks.append(task.task_id)
    
    def _get_workflow_state_for_task(self, task_type: TaskType) -> WorkflowState:
        """Get workflow state based on current task type"""
        state_mapping = {
            TaskType.STYLE_ANALYSIS: WorkflowState.STYLE_ANALYSIS,
            TaskType.CONTENT_PLANNING: WorkflowState.CONTENT_PLANNING,
            TaskType.CONTENT_GENERATION: WorkflowState.CONTENT_GENERATION,
            TaskType.CONTENT_EDITING: WorkflowState.EDITING_QA,
            TaskType.HUMAN_CHECKPOINT: WorkflowState.HUMAN_REVIEW
        }
        return state_mapping.get(task_type, WorkflowState.INITIALIZING)
    
    def _get_task_instructions(self, task: WorkflowTask, execution: WorkflowExecution) -> str:
        """Get specific instructions for task execution"""
        base_instructions = {
            TaskType.STYLE_ANALYSIS: "Analyze the provided content samples to extract brand voice patterns and create detailed style guidelines.",
            TaskType.CONTENT_PLANNING: "Create a comprehensive content outline that follows the established style guidelines and meets all requirements.",
            TaskType.CONTENT_GENERATION: "Generate high-quality content that strictly follows the provided outline and maintains consistent brand voice.",
            TaskType.CONTENT_EDITING: "Review and edit the content for quality, accuracy, brand alignment, and overall effectiveness."
        }
        
        return base_instructions.get(task.task_type, "Execute the assigned task according to project requirements.")
    
    async def _enhance_tasks_with_context(
        self, 
        tasks: List[WorkflowTask], 
        project_id: str, 
        content_requirements: Dict[str, Any]
    ) -> List[WorkflowTask]:
        """Enhance task definitions with project-specific context"""
        enhanced_tasks = []
        
        for task in tasks:
            enhanced_task = WorkflowTask(
                task_id=f"{task.task_id}_{uuid.uuid4().hex[:8]}",
                task_type=task.task_type,
                agent_type=task.agent_type,
                input_data={
                    **task.input_data,
                    "project_id": project_id,
                    "content_requirements": content_requirements
                },
                dependencies=task.dependencies,
                timeout_minutes=task.timeout_minutes,
                retry_attempts=task.retry_attempts,
                human_checkpoint=task.human_checkpoint
            )
            enhanced_tasks.append(enhanced_task)
        
        return enhanced_tasks
    
    def _apply_custom_config(self, definition: WorkflowDefinition, config: Dict[str, Any]) -> WorkflowDefinition:
        """Apply custom configuration to workflow definition"""
        # Create a copy of the definition with custom settings
        custom_definition = WorkflowDefinition(
            name=definition.name,
            description=definition.description,
            workflow_type=definition.workflow_type,
            tasks=definition.tasks.copy(),
            max_parallel_tasks=config.get("max_parallel_tasks", definition.max_parallel_tasks),
            total_timeout_hours=config.get("total_timeout_hours", definition.total_timeout_hours),
            auto_advance=config.get("auto_advance", definition.auto_advance),
            required_checkpoints=config.get("required_checkpoints", definition.required_checkpoints)
        )
        
        return custom_definition
    
    # Public API methods
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status"""
        if workflow_id not in self.active_workflows:
            raise WorkflowError(f"Workflow {workflow_id} not found")
        
        execution = self.active_workflows[workflow_id]
        
        return {
            "workflow_id": workflow_id,
            "state": execution.state.value,
            "project_id": execution.project_id,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "total_tasks": len(execution.definition.tasks),
            "completed_tasks": len(execution.completed_tasks),
            "failed_tasks": len(execution.failed_tasks),
            "active_tasks": len(execution.active_tasks),
            "pending_checkpoints": len(execution.human_checkpoints),
            "metadata": execution.metadata
        }
    
    def get_available_workflows(self) -> List[Dict[str, Any]]:
        """Get list of available workflow types"""
        return [
            {
                "workflow_type": wf_type,
                "name": definition.name,
                "description": definition.description,
                "estimated_duration": sum(task.timeout_minutes for task in definition.tasks),
                "requires_checkpoints": len(definition.required_checkpoints) > 0
            }
            for wf_type, definition in self.workflow_definitions.items()
        ]
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel an active workflow"""
        if workflow_id not in self.active_workflows:
            return False
        
        execution = self.active_workflows[workflow_id]
        execution.state = WorkflowState.CANCELLED
        execution.metadata["cancelled_at"] = datetime.utcnow().isoformat()
        
        # Cancel any active tasks
        for task in execution.active_tasks.values():
            task.status = TaskStatus.FAILED
            task.error_message = "Workflow cancelled"
        
        logger.info(f"Cancelled workflow {workflow_id}")
        return True
    
    async def approve_checkpoint(self, workflow_id: str, checkpoint_id: str, feedback: Optional[str] = None) -> bool:
        """Approve a human checkpoint"""
        try:
            with get_db_session() as db:
                checkpoint = db.get(HumanCheckpoint, checkpoint_id)
                if not checkpoint:
                    return False
                
                checkpoint.status = "approved"
                checkpoint.resolved_at = datetime.utcnow()
                if feedback:
                    checkpoint.feedback = feedback
                
                db.commit()
                
                logger.info(f"Approved checkpoint {checkpoint_id} for workflow {workflow_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to approve checkpoint: {e}")
            return False

# Global workflow engine instance
workflow_engine = WorkflowExecutionEngine()

# Export main classes and functions
__all__ = [
    'WorkflowExecutionEngine',
    'WorkflowState',
    'TaskType', 
    'TaskStatus',
    'WorkflowTask',
    'WorkflowDefinition',
    'WorkflowExecution',
    'workflow_engine'
]