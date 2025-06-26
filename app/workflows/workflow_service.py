# app/services/workflow_service.py
"""
Workflow Service - Core orchestration for SpinScribe content creation workflows.
Manages multi-agent coordination, state transitions, and workflow execution.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
import json
import uuid
import asyncio
import logging

from app.services.base_service import BaseService, ServiceRegistry
from app.services.project_service import get_project_service
from app.services.knowledge_service import get_knowledge_service
from app.database.models.chat_instance import ChatInstance
from app.database.models.chat_message import ChatMessage
from app.database.models.human_checkpoint import HumanCheckpoint
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

class WorkflowPriority(Enum):
    """Workflow priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class AgentRole(Enum):
    """Agent roles in workflow"""
    COORDINATOR = "coordinator"
    STYLE_ANALYZER = "style_analyzer"
    CONTENT_PLANNER = "content_planner"
    CONTENT_GENERATOR = "content_generator"
    EDITOR_QA = "editor_qa"

@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    name: str
    agent_role: AgentRole
    required: bool = True
    timeout_minutes: int = 30
    human_checkpoint: bool = False
    depends_on: List[str] = field(default_factory=list)
    retry_attempts: int = 2
    
@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    name: str
    description: str
    steps: List[WorkflowStep]
    max_parallel_steps: int = 2
    total_timeout_hours: int = 24
    auto_advance: bool = True

@dataclass
class WorkflowExecution:
    """Runtime workflow execution state"""
    workflow_id: str
    project_id: str
    chat_instance_id: str
    definition: WorkflowDefinition
    current_state: WorkflowState
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    step_results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    priority: WorkflowPriority = WorkflowPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowRequest:
    """Request to start a workflow"""
    project_id: str
    chat_instance_id: str
    workflow_type: str
    content_type: str
    content_requirements: Dict[str, Any]
    priority: WorkflowPriority = WorkflowPriority.NORMAL
    metadata: Optional[Dict[str, Any]] = None

class WorkflowService(BaseService):
    """
    Service for orchestrating multi-agent content creation workflows.
    
    Handles:
    - Workflow definition and execution
    - Agent coordination and task assignment
    - State management and transitions
    - Human checkpoint management
    - Error handling and recovery
    """
    
    def __init__(self):
        # Note: Not using BaseService[Model] pattern since workflows are more complex
        self.logger = logging.getLogger(__name__)
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_definitions = self._initialize_workflow_definitions()
        self.agent_registry: Dict[AgentRole, Any] = {}
        
        # Configuration
        self.config = {
            'max_concurrent_workflows': 10,
            'default_step_timeout': 30,  # minutes
            'max_retry_attempts': 3,
            'checkpoint_timeout_hours': 24,
            'cleanup_completed_workflows_hours': 168  # 1 week
        }
    
    def start_workflow(self, request: WorkflowRequest) -> str:
        """
        Start a new content creation workflow.
        
        Args:
            request: Workflow start request
            
        Returns:
            Workflow ID
        """
        # Validate request
        self._validate_workflow_request(request)
        
        # Check capacity
        if len(self.active_workflows) >= self.config['max_concurrent_workflows']:
            raise WorkflowError("Maximum concurrent workflows reached")
        
        # Get workflow definition
        workflow_def = self._get_workflow_definition(request.workflow_type)
        
        # Create workflow execution
        workflow_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            project_id=request.project_id,
            chat_instance_id=request.chat_instance_id,
            definition=workflow_def,
            current_state=WorkflowState.PENDING,
            priority=request.priority,
            metadata=request.metadata or {}
        )
        
        # Store content requirements
        execution.metadata['content_requirements'] = request.content_requirements
        execution.metadata['content_type'] = request.content_type
        
        # Register workflow
        self.active_workflows[workflow_id] = execution
        
        # Initialize workflow
        self._initialize_workflow(execution)
        
        self.logger.info(f"Started workflow {workflow_id} for project {request.project_id}")
        return workflow_id
    
    def advance_workflow(self, workflow_id: str, step_result: Optional[Dict[str, Any]] = None) -> bool:
        """
        Advance workflow to the next step.
        
        Args:
            workflow_id: Workflow ID
            step_result: Result from current step
            
        Returns:
            True if advanced successfully
        """
        execution = self._get_workflow_execution(workflow_id)
        
        try:
            # Update step result if provided
            if step_result and execution.current_step:
                execution.step_results[execution.current_step] = step_result
                execution.completed_steps.append(execution.current_step)
            
            # Determine next step
            next_step = self._get_next_step(execution)
            
            if next_step:
                # Transition to next step
                self._transition_to_step(execution, next_step)
            else:
                # Workflow complete
                self._complete_workflow(execution)
            
            execution.updated_at = datetime.utcnow()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to advance workflow {workflow_id}: {e}")
            self._fail_workflow(execution, str(e))
            return False
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status and progress."""
        execution = self._get_workflow_execution(workflow_id)
        
        # Calculate progress
        total_steps = len(execution.definition.steps)
        completed_steps = len(execution.completed_steps)
        progress_percentage = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
        
        # Get current step info
        current_step_info = None
        if execution.current_step:
            current_step_info = next(
                (step for step in execution.definition.steps if step.name == execution.current_step),
                None
            )
        
        return {
            'workflow_id': workflow_id,
            'state': execution.current_state.value,
            'current_step': execution.current_step,
            'progress_percentage': round(progress_percentage, 1),
            'completed_steps': execution.completed_steps,
            'failed_steps': execution.failed_steps,
            'created_at': execution.created_at.isoformat(),
            'updated_at': execution.updated_at.isoformat(),
            'priority': execution.priority.value,
            'estimated_completion': self._estimate_completion_time(execution),
            'current_step_info': {
                'name': current_step_info.name if current_step_info else None,
                'agent_role': current_step_info.agent_role.value if current_step_info else None,
                'timeout_minutes': current_step_info.timeout_minutes if current_step_info else None,
                'human_checkpoint': current_step_info.human_checkpoint if current_step_info else False
            } if current_step_info else None,
            'metadata': execution.metadata
        }
    
    def pause_workflow(self, workflow_id: str, reason: str) -> bool:
        """Pause workflow execution."""
        execution = self._get_workflow_execution(workflow_id)
        
        if execution.current_state in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
            raise WorkflowStateError(f"Cannot pause workflow in state: {execution.current_state.value}")
        
        execution.metadata['paused'] = True
        execution.metadata['pause_reason'] = reason
        execution.metadata['paused_at'] = datetime.utcnow().isoformat()
        execution.updated_at = datetime.utcnow()
        
        self.logger.info(f"Paused workflow {workflow_id}: {reason}")
        return True
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume paused workflow execution."""
        execution = self._get_workflow_execution(workflow_id)
        
        if not execution.metadata.get('paused'):
            raise WorkflowStateError("Workflow is not paused")
        
        execution.metadata['paused'] = False
        execution.metadata['resumed_at'] = datetime.utcnow().isoformat()
        execution.updated_at = datetime.utcnow()
        
        # Resume current step if applicable
        if execution.current_step:
            self._execute_step(execution, execution.current_step)
        
        self.logger.info(f"Resumed workflow {workflow_id}")
        return True
    
    def cancel_workflow(self, workflow_id: str, reason: str) -> bool:
        """Cancel workflow execution."""
        execution = self._get_workflow_execution(workflow_id)
        
        execution.current_state = WorkflowState.CANCELLED
        execution.metadata['cancelled'] = True
        execution.metadata['cancel_reason'] = reason
        execution.metadata['cancelled_at'] = datetime.utcnow().isoformat()
        execution.updated_at = datetime.utcnow()
        
        # Clean up resources
        self._cleanup_workflow_resources(execution)
        
        self.logger.info(f"Cancelled workflow {workflow_id}: {reason}")
        return True
    
    def retry_failed_step(self, workflow_id: str, step_name: str) -> bool:
        """Retry a failed workflow step."""
        execution = self._get_workflow_execution(workflow_id)
        
        if step_name not in execution.failed_steps:
            raise WorkflowError(f"Step {step_name} has not failed")
        
        # Remove from failed steps
        execution.failed_steps.remove(step_name)
        
        # Reset to the step
        execution.current_step = step_name
        execution.current_state = self._get_state_for_step(step_name)
        
        # Execute step
        self._execute_step(execution, step_name)
        
        self.logger.info(f"Retrying failed step {step_name} in workflow {workflow_id}")
        return True
    
    def get_active_workflows(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of active workflows, optionally filtered by project."""
        workflows = []
        
        for workflow_id, execution in self.active_workflows.items():
            if project_id and execution.project_id != project_id:
                continue
            
            workflows.append({
                'workflow_id': workflow_id,
                'project_id': execution.project_id,
                'state': execution.current_state.value,
                'current_step': execution.current_step,
                'priority': execution.priority.value,
                'created_at': execution.created_at.isoformat(),
                'updated_at': execution.updated_at.isoformat()
            })
        
        # Sort by priority and creation time
        workflows.sort(key=lambda w: (w['priority'], w['created_at']), reverse=True)
        return workflows
    
    def register_agent(self, role: AgentRole, agent_instance: Any) -> None:
        """Register an agent for workflow execution."""
        self.agent_registry[role] = agent_instance
        self.logger.info(f"Registered agent for role: {role.value}")
    
    def create_human_checkpoint(self, workflow_id: str, checkpoint_type: str, content_reference: str, instructions: str) -> str:
        """Create a human checkpoint for workflow approval."""
        execution = self._get_workflow_execution(workflow_id)
        
        with self.get_db_session() as db:
            checkpoint = HumanCheckpoint.create_workflow_checkpoint(
                chat_instance_id=execution.chat_instance_id,
                checkpoint_type=checkpoint_type,
                content_reference=content_reference,
                workflow_step=execution.current_step,
                instructions=instructions,
                metadata={
                    'workflow_id': workflow_id,
                    'project_id': execution.project_id,
                    'step_name': execution.current_step
                }
            )
            
            db.add(checkpoint)
            db.commit()
            
            # Update workflow state
            execution.current_state = WorkflowState.HUMAN_REVIEW
            execution.metadata['pending_checkpoint'] = checkpoint.checkpoint_id
            
            self.logger.info(f"Created human checkpoint {checkpoint.checkpoint_id} for workflow {workflow_id}")
            return checkpoint.checkpoint_id
    
    def resolve_human_checkpoint(self, checkpoint_id: str, approved: bool, feedback: Optional[str] = None) -> bool:
        """Resolve a human checkpoint and continue workflow."""
        with self.get_db_session() as db:
            checkpoint = db.get(HumanCheckpoint, checkpoint_id)
            if not checkpoint:
                raise ValidationError(f"Checkpoint {checkpoint_id} not found")
            
            # Update checkpoint
            checkpoint.status = 'approved' if approved else 'rejected'
            checkpoint.review_feedback = feedback
            checkpoint.completed_at = datetime.utcnow()
            
            # Get workflow
            workflow_id = checkpoint.metadata.get('workflow_id')
            if not workflow_id or workflow_id not in self.active_workflows:
                raise WorkflowError(f"Workflow not found for checkpoint {checkpoint_id}")
            
            execution = self.active_workflows[workflow_id]
            
            # Remove pending checkpoint
            execution.metadata.pop('pending_checkpoint', None)
            
            if approved:
                # Continue workflow
                self.advance_workflow(workflow_id, {'checkpoint_approved': True, 'feedback': feedback})
            else:
                # Handle rejection - might retry current step or fail workflow
                if feedback and 'retry' in feedback.lower():
                    # Retry current step
                    self._execute_step(execution, execution.current_step)
                else:
                    # Fail workflow
                    self._fail_workflow(execution, f"Human checkpoint rejected: {feedback}")
            
            db.commit()
            
        self.logger.info(f"Resolved checkpoint {checkpoint_id} - {'approved' if approved else 'rejected'}")
        return True
    
    # Internal workflow management methods
    
    def _initialize_workflow_definitions(self) -> Dict[str, WorkflowDefinition]:
        """Initialize standard workflow definitions."""
        return {
            'content_creation': WorkflowDefinition(
                name='Content Creation Workflow',
                description='Complete content creation from analysis to final output',
                steps=[
                    WorkflowStep(
                        name='style_analysis',
                        agent_role=AgentRole.STYLE_ANALYZER,
                        timeout_minutes=15,
                        human_checkpoint=True
                    ),
                    WorkflowStep(
                        name='content_planning',
                        agent_role=AgentRole.CONTENT_PLANNER,
                        timeout_minutes=20,
                        depends_on=['style_analysis'],
                        human_checkpoint=True
                    ),
                    WorkflowStep(
                        name='content_generation',
                        agent_role=AgentRole.CONTENT_GENERATOR,
                        timeout_minutes=30,
                        depends_on=['content_planning']
                    ),
                    WorkflowStep(
                        name='editing_qa',
                        agent_role=AgentRole.EDITOR_QA,
                        timeout_minutes=20,
                        depends_on=['content_generation'],
                        human_checkpoint=True
                    )
                ],
                max_parallel_steps=1,  # Sequential workflow
                total_timeout_hours=24
            ),
            'quick_content': WorkflowDefinition(
                name='Quick Content Generation',
                description='Rapid content generation with minimal checkpoints',
                steps=[
                    WorkflowStep(
                        name='content_generation',
                        agent_role=AgentRole.CONTENT_GENERATOR,
                        timeout_minutes=15
                    ),
                    WorkflowStep(
                        name='quick_review',
                        agent_role=AgentRole.EDITOR_QA,
                        timeout_minutes=10,
                        depends_on=['content_generation']
                    )
                ],
                max_parallel_steps=1,
                total_timeout_hours=2
            )
        }
    
    def _validate_workflow_request(self, request: WorkflowRequest) -> None:
        """Validate workflow start request."""
        # Check project exists
        project_service = get_project_service()
        with self.get_db_session() as db:
            project_service.get_by_id_or_raise(request.project_id, db)
            
            # Check chat instance exists
            chat = db.get(ChatInstance, request.chat_instance_id)
            if not chat:
                raise ValidationError(f"Chat instance {request.chat_instance_id} not found")
            
            if chat.project_id != request.project_id:
                raise ValidationError("Chat instance does not belong to specified project")
        
        # Validate workflow type
        if request.workflow_type not in self.workflow_definitions:
            raise ValidationError(f"Unknown workflow type: {request.workflow_type}")
        
        # Validate content requirements
        if not request.content_requirements:
            raise ValidationError("Content requirements are required")
    
    def _get_workflow_definition(self, workflow_type: str) -> WorkflowDefinition:
        """Get workflow definition by type."""
        if workflow_type not in self.workflow_definitions:
            raise WorkflowError(f"Unknown workflow type: {workflow_type}")
        return self.workflow_definitions[workflow_type]
    
    def _get_workflow_execution(self, workflow_id: str) -> WorkflowExecution:
        """Get workflow execution by ID."""
        if workflow_id not in self.active_workflows:
            raise WorkflowError(f"Workflow {workflow_id} not found or not active")
        return self.active_workflows[workflow_id]
    
    def _initialize_workflow(self, execution: WorkflowExecution) -> None:
        """Initialize workflow execution."""
        execution.current_state = WorkflowState.INITIALIZING
        
        # Start with first step
        first_step = execution.definition.steps[0]
        self._transition_to_step(execution, first_step.name)
    
    def _transition_to_step(self, execution: WorkflowExecution, step_name: str) -> None:
        """Transition workflow to specified step."""
        step = next((s for s in execution.definition.steps if s.name == step_name), None)
        if not step:
            raise WorkflowError(f"Step {step_name} not found in workflow definition")
        
        # Check dependencies
        for dep in step.depends_on:
            if dep not in execution.completed_steps:
                raise WorkflowStateError(f"Dependency {dep} not completed for step {step_name}")
        
        execution.current_step = step_name
        execution.current_state = self._get_state_for_step(step_name)
        
        # Execute step
        self._execute_step(execution, step_name)
    
    def _execute_step(self, execution: WorkflowExecution, step_name: str) -> None:
        """Execute a workflow step."""
        step = next((s for s in execution.definition.steps if s.name == step_name), None)
        if not step:
            raise WorkflowError(f"Step {step_name} not found")
        
        # Check if workflow is paused
        if execution.metadata.get('paused'):
            self.logger.info(f"Workflow {execution.workflow_id} is paused, skipping step execution")
            return
        
        try:
            # Get agent for this step
            agent = self.agent_registry.get(step.agent_role)
            if not agent:
                raise AgentError(f"No agent registered for role: {step.agent_role.value}")
            
            # Prepare step context
            context = self._prepare_step_context(execution, step)
            
            # Execute step with timeout
            self._execute_step_with_timeout(execution, step, agent, context)
            
        except Exception as e:
            self.logger.error(f"Step {step_name} failed in workflow {execution.workflow_id}: {e}")
            self._handle_step_failure(execution, step_name, str(e))
    
    def _execute_step_with_timeout(self, execution: WorkflowExecution, step: WorkflowStep, agent: Any, context: Dict[str, Any]) -> None:
        """Execute step with timeout handling."""
        # This would be implemented with actual agent execution
        # For now, we'll simulate the execution
        
        self.logger.info(f"Executing step {step.name} with agent {step.agent_role.value}")
        
        # Simulate step execution based on step type
        if step.name == 'style_analysis':
            self._execute_style_analysis_step(execution, agent, context)
        elif step.name == 'content_planning':
            self._execute_content_planning_step(execution, agent, context)
        elif step.name == 'content_generation':
            self._execute_content_generation_step(execution, agent, context)
        elif step.name == 'editing_qa':
            self._execute_editing_qa_step(execution, agent, context)
        else:
            # Generic step execution
            self._execute_generic_step(execution, step, agent, context)
    
    def _execute_style_analysis_step(self, execution: WorkflowExecution, agent: Any, context: Dict[str, Any]) -> None:
        """Execute style analysis step."""
        # Get knowledge service to analyze brand voice
        knowledge_service = get_knowledge_service()
        
        try:
            # Analyze brand voice for the project
            brand_voice_analysis = knowledge_service.analyze_brand_voice(execution.project_id)
            
            # Store result
            execution.step_results['style_analysis'] = {
                'knowledge_id': brand_voice_analysis.knowledge_id,
                'completed_at': datetime.utcnow().isoformat(),
                'status': 'completed'
            }
            
            # Check if human checkpoint is required
            step = next(s for s in execution.definition.steps if s.name == 'style_analysis')
            if step.human_checkpoint:
                self.create_human_checkpoint(
                    execution.workflow_id,
                    'style_analysis_review',
                    brand_voice_analysis.knowledge_id,
                    'Please review the brand voice analysis and approve to continue.'
                )
            else:
                # Auto-advance to next step
                self.advance_workflow(execution.workflow_id, execution.step_results['style_analysis'])
                
        except Exception as e:
            raise AgentError(f"Style analysis failed: {str(e)}")
    
    def _execute_content_planning_step(self, execution: WorkflowExecution, agent: Any, context: Dict[str, Any]) -> None:
        """Execute content planning step."""
        # This would call the content planner agent
        # For now, create a placeholder result
        
        content_requirements = execution.metadata.get('content_requirements', {})
        
        execution.step_results['content_planning'] = {
            'outline_created': True,
            'content_type': execution.metadata.get('content_type'),
            'sections': content_requirements.get('sections', []),
            'completed_at': datetime.utcnow().isoformat(),
            'status': 'completed'
        }
        
        # Check for human checkpoint
        step = next(s for s in execution.definition.steps if s.name == 'content_planning')
        if step.human_checkpoint:
            self.create_human_checkpoint(
                execution.workflow_id,
                'content_plan_review',
                'content_outline',
                'Please review the content outline and approve to continue.'
            )
        else:
            self.advance_workflow(execution.workflow_id, execution.step_results['content_planning'])
    
    def _execute_content_generation_step(self, execution: WorkflowExecution, agent: Any, context: Dict[str, Any]) -> None:
        """Execute content generation step."""
        # This would call the content generator agent
        # For now, create a placeholder result
        
        execution.step_results['content_generation'] = {
            'content_generated': True,
            'word_count': 500,  # Placeholder
            'completed_at': datetime.utcnow().isoformat(),
            'status': 'completed'
        }
        
        # Content generation typically doesn't need human checkpoint
        self.advance_workflow(execution.workflow_id, execution.step_results['content_generation'])
    
    def _execute_editing_qa_step(self, execution: WorkflowExecution, agent: Any, context: Dict[str, Any]) -> None:
        """Execute editing and QA step."""
        # This would call the editor/QA agent
        # For now, create a placeholder result
        
        execution.step_results['editing_qa'] = {
            'content_reviewed': True,
            'quality_score': 0.85,  # Placeholder
            'completed_at': datetime.utcnow().isoformat(),
            'status': 'completed'
        }
        
        # Check for human checkpoint
        step = next(s for s in execution.definition.steps if s.name == 'editing_qa')
        if step.human_checkpoint:
            self.create_human_checkpoint(
                execution.workflow_id,
                'final_review',
                'final_content',
                'Please review the final content and approve for delivery.'
            )
        else:
            self.advance_workflow(execution.workflow_id, execution.step_results['editing_qa'])
    
    def _execute_generic_step(self, execution: WorkflowExecution, step: WorkflowStep, agent: Any, context: Dict[str, Any]) -> None:
        """Execute generic workflow step."""
        # Placeholder for generic step execution
        execution.step_results[step.name] = {
            'completed_at': datetime.utcnow().isoformat(),
            'status': 'completed',
            'agent_role': step.agent_role.value
        }
        
        if step.human_checkpoint:
            self.create_human_checkpoint(
                execution.workflow_id,
                f'{step.name}_review',
                step.name,
                f'Please review the {step.name} results and approve to continue.'
            )
        else:
            self.advance_workflow(execution.workflow_id, execution.step_results[step.name])
    
    def _prepare_step_context(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict[str, Any]:
        """Prepare context for step execution."""
        return {
            'workflow_id': execution.workflow_id,
            'project_id': execution.project_id,
            'chat_instance_id': execution.chat_instance_id,
            'step_name': step.name,
            'content_requirements': execution.metadata.get('content_requirements', {}),
            'previous_results': execution.step_results,
            'workflow_metadata': execution.metadata
        }
    
    def _get_next_step(self, execution: WorkflowExecution) -> Optional[str]:
        """Determine the next step in the workflow."""
        completed_steps = set(execution.completed_steps)
        
        for step in execution.definition.steps:
            if step.name not in completed_steps and step.name not in execution.failed_steps:
                # Check if all dependencies are satisfied
                if all(dep in completed_steps for dep in step.depends_on):
                    return step.name
        
        return None
    
    def _get_state_for_step(self, step_name: str) -> WorkflowState:
        """Get workflow state for a given step."""
        state_mapping = {
            'style_analysis': WorkflowState.STYLE_ANALYSIS,
            'content_planning': WorkflowState.CONTENT_PLANNING,
            'content_generation': WorkflowState.CONTENT_GENERATION,
            'editing_qa': WorkflowState.EDITING_QA
        }
        
        return state_mapping.get(step_name, WorkflowState.PENDING)
    
    def _handle_step_failure(self, execution: WorkflowExecution, step_name: str, error: str) -> None:
        """Handle step execution failure."""
        step = next((s for s in execution.definition.steps if s.name == step_name), None)
        
        # Add to failed steps
        execution.failed_steps.append(step_name)
        
        # Check retry attempts
        retry_count = execution.metadata.get(f'{step_name}_retry_count', 0)
        max_retries = step.retry_attempts if step else self.config['max_retry_attempts']
        
        if retry_count < max_retries:
            # Retry step
            execution.metadata[f'{step_name}_retry_count'] = retry_count + 1
            self.logger.info(f"Retrying step {step_name} (attempt {retry_count + 1}/{max_retries})")
            self._execute_step(execution, step_name)
        else:
            # Fail workflow
            self._fail_workflow(execution, f"Step {step_name} failed after {max_retries} attempts: {error}")
    
    def _complete_workflow(self, execution: WorkflowExecution) -> None:
        """Complete workflow execution."""
        execution.current_state = WorkflowState.COMPLETED
        execution.current_step = None
        execution.metadata['completed_at'] = datetime.utcnow().isoformat()
        execution.updated_at = datetime.utcnow()
        
        # Log completion
        self.logger.info(f"Workflow {execution.workflow_id} completed successfully")
        
        # Send completion notification (would integrate with notification service)
        self._send_workflow_notification(execution, 'completed')
        
        # Schedule cleanup
        self._schedule_workflow_cleanup(execution)
    
    def _fail_workflow(self, execution: WorkflowExecution, error: str) -> None:
        """Fail workflow execution."""
        execution.current_state = WorkflowState.FAILED
        execution.metadata['failed_at'] = datetime.utcnow().isoformat()
        execution.metadata['failure_reason'] = error
        execution.updated_at = datetime.utcnow()
        
        # Log failure
        self.logger.error(f"Workflow {execution.workflow_id} failed: {error}")
        
        # Send failure notification
        self._send_workflow_notification(execution, 'failed', {'error': error})
        
        # Clean up resources
        self._cleanup_workflow_resources(execution)
    
    def _estimate_completion_time(self, execution: WorkflowExecution) -> Optional[str]:
        """Estimate workflow completion time."""
        if execution.current_state == WorkflowState.COMPLETED:
            return None
        
        # Calculate remaining steps
        remaining_steps = []
        completed_steps = set(execution.completed_steps)
        
        for step in execution.definition.steps:
            if step.name not in completed_steps and step.name not in execution.failed_steps:
                remaining_steps.append(step)
        
        if not remaining_steps:
            return datetime.utcnow().isoformat()
        
        # Estimate time based on step timeouts
        total_minutes = sum(step.timeout_minutes for step in remaining_steps)
        
        # Add buffer for human checkpoints
        checkpoint_steps = [step for step in remaining_steps if step.human_checkpoint]
        if checkpoint_steps:
            total_minutes += len(checkpoint_steps) * 60  # 1 hour buffer per checkpoint
        
        estimated_completion = datetime.utcnow() + timedelta(minutes=total_minutes)
        return estimated_completion.isoformat()
    
    def _send_workflow_notification(self, execution: WorkflowExecution, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Send workflow event notification."""
        # This would integrate with a notification service
        # For now, just log the notification
        
        notification = {
            'workflow_id': execution.workflow_id,
            'project_id': execution.project_id,
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data or {}
        }
        
        self.logger.info(f"Workflow notification: {notification}")
    
    def _schedule_workflow_cleanup(self, execution: WorkflowExecution) -> None:
        """Schedule workflow cleanup after completion."""
        # This would integrate with a task scheduler
        # For now, just mark for cleanup
        
        cleanup_time = datetime.utcnow() + timedelta(hours=self.config['cleanup_completed_workflows_hours'])
        execution.metadata['scheduled_cleanup'] = cleanup_time.isoformat()
        
        self.logger.info(f"Scheduled cleanup for workflow {execution.workflow_id} at {cleanup_time}")
    
    def _cleanup_workflow_resources(self, execution: WorkflowExecution) -> None:
        """Clean up workflow resources."""
        try:
            # Clean up any temporary files, cache entries, etc.
            # This would be implemented based on specific resource types
            
            # Mark as cleaned up
            execution.metadata['resources_cleaned'] = True
            execution.metadata['cleanup_completed_at'] = datetime.utcnow().isoformat()
            
            self.logger.info(f"Cleaned up resources for workflow {execution.workflow_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to clean up resources for workflow {execution.workflow_id}: {e}")
    
    def cleanup_completed_workflows(self) -> int:
        """Clean up old completed workflows."""
        cleanup_count = 0
        workflows_to_remove = []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=self.config['cleanup_completed_workflows_hours'])
        
        for workflow_id, execution in self.active_workflows.items():
            if execution.current_state in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
                if execution.updated_at < cutoff_time:
                    workflows_to_remove.append(workflow_id)
        
        # Remove old workflows
        for workflow_id in workflows_to_remove:
            execution = self.active_workflows[workflow_id]
            self._cleanup_workflow_resources(execution)
            del self.active_workflows[workflow_id]
            cleanup_count += 1
        
        if cleanup_count > 0:
            self.logger.info(f"Cleaned up {cleanup_count} completed workflows")
        
        return cleanup_count
    
    def get_workflow_metrics(self) -> Dict[str, Any]:
        """Get workflow system metrics."""
        total_workflows = len(self.active_workflows)
        
        state_counts = {}
        for execution in self.active_workflows.values():
            state = execution.current_state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        # Calculate average completion time for completed workflows
        completed_workflows = [
            ex for ex in self.active_workflows.values() 
            if ex.current_state == WorkflowState.COMPLETED and 'completed_at' in ex.metadata
        ]
        
        avg_completion_time = None
        if completed_workflows:
            completion_times = []
            for ex in completed_workflows:
                try:
                    completed_at = datetime.fromisoformat(ex.metadata['completed_at'])
                    duration = (completed_at - ex.created_at).total_seconds() / 3600  # hours
                    completion_times.append(duration)
                except:
                    continue
            
            if completion_times:
                avg_completion_time = sum(completion_times) / len(completion_times)
        
        return {
            'total_active_workflows': total_workflows,
            'workflows_by_state': state_counts,
            'average_completion_time_hours': round(avg_completion_time, 2) if avg_completion_time else None,
            'registered_agents': len(self.agent_registry),
            'agent_roles': [role.value for role in self.agent_registry.keys()],
            'workflow_definitions': len(self.workflow_definitions),
            'available_workflow_types': list(self.workflow_definitions.keys())
        }
    
    # Context manager support for database sessions
    def get_db_session(self):
        """Get database session - implementing required method from base service pattern."""
        from app.database.connection import SessionLocal
        from contextlib import contextmanager
        
        @contextmanager
        def session_context():
            db = SessionLocal()
            try:
                yield db
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        
        return session_context()


# Service instance factory
def get_workflow_service() -> WorkflowService:
    """Get WorkflowService instance from registry."""
    return ServiceRegistry.get_service(WorkflowService)


# Utility functions for workflow management

def start_content_creation_workflow(
    project_id: str, 
    chat_instance_id: str, 
    content_type: str,
    content_requirements: Dict[str, Any],
    priority: WorkflowPriority = WorkflowPriority.NORMAL
) -> str:
    """
    Convenience function to start a content creation workflow.
    
    Args:
        project_id: Project ID
        chat_instance_id: Chat instance ID
        content_type: Type of content to create
        content_requirements: Content requirements and specifications
        priority: Workflow priority
        
    Returns:
        Workflow ID
    """
    workflow_service = get_workflow_service()
    
    request = WorkflowRequest(
        project_id=project_id,
        chat_instance_id=chat_instance_id,
        workflow_type='content_creation',
        content_type=content_type,
        content_requirements=content_requirements,
        priority=priority
    )
    
    return workflow_service.start_workflow(request)


def get_project_workflow_summary(project_id: str) -> Dict[str, Any]:
    """
    Get summary of workflows for a project.
    
    Args:
        project_id: Project ID
        
    Returns:
        Workflow summary for the project
    """
    workflow_service = get_workflow_service()
    workflows = workflow_service.get_active_workflows(project_id)
    
    # Calculate summary statistics
    total_workflows = len(workflows)
    
    state_counts = {}
    for workflow in workflows:
        state = workflow['state']
        state_counts[state] = state_counts.get(state, 0) + 1
    
    # Find most recent activity
    most_recent_activity = None
    if workflows:
        most_recent = max(workflows, key=lambda w: w['updated_at'])
        most_recent_activity = {
            'workflow_id': most_recent['workflow_id'],
            'state': most_recent['state'],
            'updated_at': most_recent['updated_at']
        }
    
    return {
        'project_id': project_id,
        'total_workflows': total_workflows,
        'workflows_by_state': state_counts,
        'active_workflows': [w for w in workflows if w['state'] not in ['completed', 'failed', 'cancelled']],
        'most_recent_activity': most_recent_activity,
        'summary_generated_at': datetime.utcnow().isoformat()
    }


def monitor_workflow_health() -> Dict[str, Any]:
    """
    Monitor overall workflow system health.
    
    Returns:
        System health metrics and status
    """
    workflow_service = get_workflow_service()
    metrics = workflow_service.get_workflow_metrics()
    
    # Analyze health indicators
    health_score = 1.0
    issues = []
    warnings = []
    
    # Check for stuck workflows
    stuck_workflows = 0
    for workflow_id, execution in workflow_service.active_workflows.items():
        if execution.current_state not in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
            # Check if workflow has been running too long
            hours_running = (datetime.utcnow() - execution.created_at).total_seconds() / 3600
            if hours_running > execution.definition.total_timeout_hours:
                stuck_workflows += 1
    
    if stuck_workflows > 0:
        issues.append(f"{stuck_workflows} workflows appear to be stuck")
        health_score -= 0.2
    
    # Check agent availability
    required_agents = {AgentRole.COORDINATOR, AgentRole.STYLE_ANALYZER, AgentRole.CONTENT_PLANNER, 
                      AgentRole.CONTENT_GENERATOR, AgentRole.EDITOR_QA}
    missing_agents = required_agents - set(workflow_service.agent_registry.keys())
    
    if missing_agents:
        missing_agent_names = [agent.value for agent in missing_agents]
        issues.append(f"Missing agents: {', '.join(missing_agent_names)}")
        health_score -= 0.3
    
    # Check system load
    active_workflows = metrics['workflows_by_state'].get('pending', 0) + \
                      metrics['workflows_by_state'].get('initializing', 0) + \
                      metrics['workflows_by_state'].get('style_analysis', 0) + \
                      metrics['workflows_by_state'].get('content_planning', 0) + \
                      metrics['workflows_by_state'].get('content_generation', 0) + \
                      metrics['workflows_by_state'].get('editing_qa', 0)
    
    if active_workflows > workflow_service.config['max_concurrent_workflows'] * 0.8:
        warnings.append("High system load - approaching maximum concurrent workflows")
        health_score -= 0.1
    
    # Determine overall health status
    if health_score >= 0.9:
        status = 'excellent'
    elif health_score >= 0.7:
        status = 'good'
    elif health_score >= 0.5:
        status = 'fair'
    else:
        status = 'poor'
    
    return {
        'health_score': round(health_score, 2),
        'status': status,
        'issues': issues,
        'warnings': warnings,
        'metrics': metrics,
        'stuck_workflows': stuck_workflows,
        'missing_agents': len(missing_agents),
        'system_load_percentage': round((active_workflows / workflow_service.config['max_concurrent_workflows']) * 100, 1),
        'checked_at': datetime.utcnow().isoformat()
    }


# Export main classes and functions
__all__ = [
    'WorkflowService',
    'WorkflowState',
    'WorkflowPriority', 
    'AgentRole',
    'WorkflowStep',
    'WorkflowDefinition',
    'WorkflowExecution',
    'WorkflowRequest',
    'get_workflow_service',
    'start_content_creation_workflow',
    'get_project_workflow_summary',
    'monitor_workflow_health'
]