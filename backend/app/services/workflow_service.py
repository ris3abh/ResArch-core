# backend/app/services/workflow_service.py
"""
Workflow service for SpinScribe multi-agent system integration.
This service handles workflow creation, execution, monitoring, and management.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import subprocess
import sys
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from app.models.workflow import WorkflowExecution, AgentInteraction, KnowledgeOnboarding
from app.models.project import Project
from app.models.user import User
from app.schemas.workflow import (
    WorkflowCreateRequest, WorkflowExecutionResponse, WorkflowStatusResponse,
    AgentInteractionResponse, KnowledgeOnboardingResponse,
    WorkflowStatus, AgentType, InteractionStatus
)

logger = logging.getLogger(__name__)

class WorkflowService:
    """
    Service class for managing SpinScribe workflows.
    Handles workflow lifecycle, execution, and monitoring.
    """
    
    def __init__(self, db_session: AsyncSession, session_factory=None):
        self.db = db_session
        self.session_factory = session_factory  # For creating new sessions in background tasks
        self.spinscribe_path = self._get_spinscribe_path()
        self.active_workflows: Dict[str, asyncio.Task] = {}
    
    def _get_spinscribe_path(self) -> Path:
        """Get the path to the SpinScribe project root."""
        # Assuming backend is in the SpinScribe project root
        backend_path = Path(__file__).parent.parent.parent.parent
        return backend_path
    
    async def create_workflow(
        self, 
        request: WorkflowCreateRequest, 
        user_id: str
    ) -> WorkflowExecution:
        """
        Create a new workflow execution.
        
        Args:
            request: Workflow creation request
            user_id: ID of the user creating the workflow
            
        Returns:
            WorkflowExecution: Created workflow execution
            
        Raises:
            ValueError: If project doesn't exist or user doesn't have access
        """
        logger.info(f"Creating workflow: {request.title} for user {user_id}")
        
        # Validate project exists and user has access
        project = await self._get_project_with_access(request.project_id, user_id)
        if not project:
            raise ValueError(f"Project {request.project_id} not found or access denied")
        
        # Generate unique workflow ID
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        
        # Create workflow execution record
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            project_id=request.project_id,
            user_id=user_id,
            title=request.title,
            content_type=request.content_type.value,
            workflow_type=request.workflow_type.value,
            status=WorkflowStatus.PENDING.value,
            timeout_seconds=request.timeout_seconds,
            enable_human_interaction=request.enable_human_interaction,
            enable_checkpoints=request.enable_checkpoints,
            first_draft=request.first_draft,
            agent_config=request.workflow_config or self._get_default_agent_config(),
            progress_percentage=0
        )
        
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        
        logger.info(f"Created workflow {workflow_id} with ID {workflow.id}")
        return workflow
    
    async def start_workflow(self, workflow_id: str) -> bool:
        """
        Start workflow execution asynchronously.
        
        Args:
            workflow_id: Workflow ID to start
            
        Returns:
            bool: True if workflow started successfully
        """
        logger.info(f"Starting workflow {workflow_id}")
        
        # Get workflow from database
        workflow = await self.get_workflow_by_id(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False
        
        if workflow.status != WorkflowStatus.PENDING.value:
            logger.error(f"Workflow {workflow_id} is not in pending state: {workflow.status}")
            return False
        
        # Mark as started
        workflow.mark_as_started()
        await self.db.commit()
        
        # Start workflow execution as background task
        task = asyncio.create_task(self._execute_workflow(workflow.id))
        self.active_workflows[workflow_id] = task
        
        logger.info(f"Started workflow {workflow_id} execution")
        return True
    
    async def get_workflow_by_id(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """
        Get workflow by workflow ID.
        
        Args:
            workflow_id: Workflow ID to lookup
            
        Returns:
            WorkflowExecution or None if not found
        """
        result = await self.db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.workflow_id == workflow_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatusResponse]:
        """
        Get current workflow status.
        
        Args:
            workflow_id: Workflow ID to check
            
        Returns:
            WorkflowStatusResponse or None if not found
        """
        workflow = await self.get_workflow_by_id(workflow_id)
        if not workflow:
            return None
        
        # Get active agents (simplified for now)
        active_agents = []
        if workflow.is_running:
            active_agents = [workflow.current_stage] if workflow.current_stage else []
        
        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus(workflow.status),
            current_stage=workflow.current_stage,
            progress_percentage=workflow.progress_percentage,
            started_at=workflow.started_at,
            estimated_completion=workflow.estimated_completion,
            agents_active=active_agents,
            next_checkpoint=self._get_next_checkpoint(workflow)
        )
    
    async def cancel_workflow(self, workflow_id: str, reason: str = None) -> bool:
        """
        Cancel a running workflow.
        
        Args:
            workflow_id: Workflow ID to cancel
            reason: Reason for cancellation
            
        Returns:
            bool: True if cancelled successfully
        """
        logger.info(f"Cancelling workflow {workflow_id}")
        
        workflow = await self.get_workflow_by_id(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False
        
        if not workflow.can_be_cancelled:
            logger.error(f"Workflow {workflow_id} cannot be cancelled: {workflow.status}")
            return False
        
        # Cancel the background task if running
        if workflow_id in self.active_workflows:
            task = self.active_workflows[workflow_id]
            task.cancel()
            del self.active_workflows[workflow_id]
        
        # Update workflow status
        workflow.mark_as_cancelled(reason or "User requested cancellation")
        await self.db.commit()
        
        logger.info(f"Cancelled workflow {workflow_id}")
        return True
    
    async def get_workflow_interactions(
        self, 
        workflow_id: str
    ) -> List[AgentInteractionResponse]:
        """
        Get all interactions for a workflow.
        
        Args:
            workflow_id: Workflow ID to get interactions for
            
        Returns:
            List of agent interactions
        """
        workflow = await self.get_workflow_by_id(workflow_id)
        if not workflow:
            return []
        
        result = await self.db.execute(
            select(AgentInteraction)
            .where(AgentInteraction.workflow_execution_id == workflow.id)
            .order_by(AgentInteraction.interaction_sequence)
        )
        interactions = result.scalars().all()
        
        return [
            AgentInteractionResponse.model_validate(interaction.to_dict())
            for interaction in interactions
        ]
    
    async def get_pending_human_interactions(
        self, 
        workflow_id: str
    ) -> List[AgentInteractionResponse]:
        """
        Get pending human interactions for a workflow.
        
        Args:
            workflow_id: Workflow ID to check
            
        Returns:
            List of pending interactions
        """
        workflow = await self.get_workflow_by_id(workflow_id)
        if not workflow:
            return []
        
        result = await self.db.execute(
            select(AgentInteraction)
            .where(
                and_(
                    AgentInteraction.workflow_execution_id == workflow.id,
                    AgentInteraction.requires_human_input == True,
                    AgentInteraction.human_response == None
                )
            )
            .order_by(AgentInteraction.created_at)
        )
        interactions = result.scalars().all()
        
        return [
            AgentInteractionResponse.model_validate(interaction.to_dict())
            for interaction in interactions
        ]
    
    async def respond_to_human_interaction(
        self, 
        interaction_id: str, 
        response: str
    ) -> bool:
        """
        Respond to a human interaction.
        
        Args:
            interaction_id: Interaction ID to respond to
            response: Human response
            
        Returns:
            bool: True if response was recorded successfully
        """
        logger.info(f"Responding to interaction {interaction_id}")
        
        result = await self.db.execute(
            select(AgentInteraction).where(AgentInteraction.id == interaction_id)
        )
        interaction = result.scalar_one_or_none()
        
        if not interaction:
            logger.error(f"Interaction {interaction_id} not found")
            return False
        
        if not interaction.requires_human_input:
            logger.error(f"Interaction {interaction_id} does not require human input")
            return False
        
        if interaction.human_response is not None:
            logger.error(f"Interaction {interaction_id} already has a response")
            return False
        
        # Set human response
        interaction.set_human_response(response)
        await self.db.commit()
        
        logger.info(f"Recorded response for interaction {interaction_id}")
        return True
    
    async def get_workflows_for_user(
        self, 
        user_id: str, 
        project_id: Optional[str] = None,
        limit: int = 50, 
        offset: int = 0
    ) -> List[WorkflowExecutionResponse]:
        """
        Get workflows for a user.
        
        Args:
            user_id: User ID to get workflows for
            project_id: Optional project ID filter
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of workflow executions
        """
        query = select(WorkflowExecution).where(WorkflowExecution.user_id == user_id)
        
        if project_id:
            query = query.where(WorkflowExecution.project_id == project_id)
        
        query = query.order_by(WorkflowExecution.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        workflows = result.scalars().all()
        
        return [
            WorkflowExecutionResponse.model_validate(workflow.to_dict())
            for workflow in workflows
        ]
    
    async def _execute_workflow(self, workflow_id: str) -> None:
        """
        Execute workflow using SpinScribe system.
        This is the core method that interfaces with the enhanced_run_workflow.py.
        Uses a separate database session to avoid concurrency issues.
        
        Args:
            workflow_id: Database ID of the workflow execution to run
        """
        # Create a new session for this background task
        if self.session_factory:
            async with self.session_factory() as session:
                await self._execute_workflow_with_session(session, workflow_id)
        else:
            # Fallback to using the main session (for testing)
            await self._execute_workflow_with_session(self.db, workflow_id)
    
    async def _execute_workflow_with_session(self, session: AsyncSession, workflow_id: str) -> None:
        """
        Execute workflow with a specific database session.
        
        Args:
            session: Database session to use
            workflow_id: Database ID of the workflow execution to run
        """
        # Get workflow from database
        result = await session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            logger.error(f"Workflow with ID {workflow_id} not found")
            return
        
        logger.info(f"Executing workflow {workflow.workflow_id}")
        
        try:
            # Update progress
            await self._update_workflow_progress_with_session(session, workflow, "workflow_building", 10)
            
            # Build command to run SpinScribe workflow
            cmd = self._build_spinscribe_command(workflow)
            
            # Execute SpinScribe workflow
            await self._update_workflow_progress_with_session(session, workflow, "agent_processing", 20)
            
            # For now, simulate workflow execution
            # In production, this would actually call the SpinScribe system
            result = await self._simulate_workflow_execution_with_session(session, workflow)
            
            # Process results
            if result.get('success'):
                await self._update_workflow_progress_with_session(session, workflow, "result_collection", 90)
                
                # Mark as completed
                workflow.mark_as_completed(
                    final_content=result.get('final_content', 'Generated content...'),
                    word_count=result.get('word_count', 1000),
                    quality_score=result.get('quality_score', 0.8)
                )
                
                await self._update_workflow_progress_with_session(session, workflow, "completed", 100)
            else:
                # Mark as failed
                workflow.mark_as_failed(result.get('error_details', {'error': 'Unknown error'}))
            
            await session.commit()
            
        except asyncio.CancelledError:
            logger.info(f"Workflow {workflow.workflow_id} was cancelled")
            workflow.mark_as_cancelled("Execution cancelled")
            await session.commit()
            raise
        except Exception as e:
            logger.error(f"Workflow {workflow.workflow_id} failed: {e}")
            workflow.mark_as_failed({'error': str(e), 'type': type(e).__name__})
            await session.commit()
        finally:
            # Clean up from active workflows
            if workflow.workflow_id in self.active_workflows:
                del self.active_workflows[workflow.workflow_id]
    
    async def _simulate_workflow_execution_with_session(self, session: AsyncSession, workflow: WorkflowExecution) -> Dict[str, Any]:
        """
        Simulate workflow execution for testing with a specific session.
        In production, this would call the actual SpinScribe system.
        
        Args:
            session: Database session to use
            workflow: Workflow to simulate
            
        Returns:
            Dict with execution results
        """
        # Simulate different stages of workflow
        stages = [
            ("style_analysis", 30),
            ("content_planning", 50),
            ("content_generation", 70),
            ("qa", 85),
            ("finalization", 95)
        ]
        
        for stage, progress in stages:
            await self._update_workflow_progress_with_session(session, workflow, stage, progress)
            await asyncio.sleep(0.5)  # Reduced sleep time for faster testing
            
            # Simulate human interaction requirement
            if stage == "style_analysis" and workflow.enable_human_interaction:
                await self._create_human_interaction_with_session(
                    session,
                    workflow, 
                    stage, 
                    "What tone should this content have?",
                    timeout_minutes=30
                )
        
        # Return success result
        return {
            'success': True,
            'final_content': f"Generated {workflow.content_type} content for: {workflow.title}",
            'word_count': 1200,
            'quality_score': 0.85,
            'agents_used': ['coordinator', 'style_analysis', 'content_planning', 'content_generation', 'qa']
        }
    
    async def _create_human_interaction_with_session(
        self, 
        session: AsyncSession,
        workflow: WorkflowExecution, 
        agent_type: str, 
        question: str,
        timeout_minutes: int = 30
    ) -> AgentInteraction:
        """
        Create a human interaction for the workflow with a specific session.
        
        Args:
            session: Database session to use
            workflow: Workflow execution
            agent_type: Type of agent requesting interaction
            question: Question to ask human
            timeout_minutes: Timeout for response
            
        Returns:
            Created agent interaction
        """
        # Get next sequence number
        result = await session.execute(
            select(AgentInteraction.interaction_sequence)
            .where(AgentInteraction.workflow_execution_id == workflow.id)
            .order_by(AgentInteraction.interaction_sequence.desc())
            .limit(1)
        )
        last_sequence = result.scalar_one_or_none()
        next_sequence = (last_sequence or 0) + 1
        
        # Create interaction
        interaction = AgentInteraction(
            workflow_execution_id=workflow.id,
            agent_type=agent_type,
            interaction_sequence=next_sequence,
            interaction_status=InteractionStatus.PENDING.value
        )
        
        interaction.set_human_question(question, timeout_minutes)
        
        session.add(interaction)
        await session.commit()
        await session.refresh(interaction)
        
        logger.info(f"Created human interaction {interaction.id} for workflow {workflow.workflow_id}")
        return interaction
    
    async def _update_workflow_progress_with_session(
        self, 
        session: AsyncSession,
        workflow: WorkflowExecution, 
        stage: str, 
        percentage: int
    ) -> None:
        """
        Update workflow progress with a specific session.
        
        Args:
            session: Database session to use
            workflow: Workflow to update
            stage: Current stage
            percentage: Progress percentage
        """
        workflow.update_progress(stage, percentage)
        await session.commit()
        logger.info(f"Workflow {workflow.workflow_id} progress: {percentage}% ({stage})")
    
    def _build_spinscribe_command(self, workflow: WorkflowExecution) -> List[str]:
        """
        Build command to execute SpinScribe workflow.
        
        Args:
            workflow: Workflow to build command for
            
        Returns:
            List of command arguments
        """
        cmd = [
            sys.executable,
            str(self.spinscribe_path / "scripts" / "enhanced_run_workflow.py"),
            "--title", workflow.title,
            "--type", workflow.content_type,
            "--project-id", workflow.project_id,
            "--timeout", str(workflow.timeout_seconds)
        ]
        
        if workflow.first_draft:
            # Write first draft to temp file
            draft_file = self.spinscribe_path / "temp" / f"{workflow.workflow_id}_draft.txt"
            draft_file.parent.mkdir(exist_ok=True)
            draft_file.write_text(workflow.first_draft)
            cmd.extend(["--first-draft", str(draft_file)])
        
        if workflow.enable_human_interaction:
            cmd.append("--enable-human-interaction")
        else:
            cmd.append("--disable-human-interaction")
        
        return cmd
    
    def _get_default_agent_config(self) -> Dict[str, Any]:
        """Get default agent configuration."""
        return {
            "agents": ["coordinator", "style_analysis", "content_planning", "content_generation", "qa"],
            "rag_enabled": True,
            "quality_threshold": 0.8,
            "max_iterations": 3,
            "checkpoint_stages": ["strategy_approval", "content_review", "final_approval"]
        }
    
    def _get_next_checkpoint(self, workflow: WorkflowExecution) -> Optional[Dict[str, Any]]:
        """Get next checkpoint for workflow."""
        if not workflow.enable_checkpoints or workflow.status != WorkflowStatus.RUNNING.value:
            return None
        
        # Simplified checkpoint logic
        stage_checkpoints = {
            "style_analysis": {"type": "strategy_approval", "description": "Review brand voice analysis"},
            "content_planning": {"type": "content_review", "description": "Review content outline"},
            "qa": {"type": "final_approval", "description": "Final content approval"}
        }
        
        return stage_checkpoints.get(workflow.current_stage)
    
    async def _get_project_with_access(self, project_id: str, user_id: str) -> Optional[Project]:
        """
        Get project if user has access.
        
        Args:
            project_id: Project ID
            user_id: User ID
            
        Returns:
            Project if user has access, None otherwise
        """
        # This is a simplified check - in production you'd check project membership
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return None
        
        # Check if user is creator or member (simplified)
        if project.created_by == user_id:
            return project
        
        # TODO: Add proper project membership checking
        return project