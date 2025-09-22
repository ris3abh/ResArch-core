"""
WebSocket Message Interceptor for CAMEL Agents - ENHANCED VERSION
==================================================================

This module provides the critical bridge between CAMEL's agent communication system
and the SpinScribe WebSocket infrastructure, enabling real-time frontend updates.

ENHANCED: Properly handles checkpoint responses and workflow service integration.

Author: SpinScribe Team
Created: 2025
License: MIT
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING, Callable
from datetime import datetime, timezone
import uuid
from enum import Enum
import functools
import inspect
import threading

# CAMEL imports - Based on CAMEL Message Cookbook documentation
try:
    from camel.messages import BaseMessage
    from camel.types import RoleType
    from camel.agents import ChatAgent
    CAMEL_AVAILABLE = True
except ImportError:
    # Fallback for testing without CAMEL installed
    BaseMessage = None
    RoleType = None
    ChatAgent = None
    CAMEL_AVAILABLE = False
    logging.warning("CAMEL not installed - using mock mode for testing")

# Type checking imports
if TYPE_CHECKING:
    from camel.messages import BaseMessage as BaseMessageType
else:
    BaseMessageType = Any

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can be intercepted and broadcast"""
    AGENT_COMMUNICATION = "agent_communication"
    HUMAN_INTERACTION = "human_interaction"
    CHECKPOINT_REQUEST = "checkpoint_request"
    TASK_UPDATE = "task_update"
    ERROR = "error"
    COMPLETION = "completion"
    THINKING = "thinking"
    SOLUTION = "solution"
    CHECKPOINT_FEEDBACK = "checkpoint_feedback"


class AgentRole(Enum):
    """Known agent roles in the SpinScribe system"""
    CONTENT_CREATOR = "Content Creator"
    CONTENT_STRATEGIST = "Content Strategist"
    STYLE_ANALYST = "Style Analysis Agent"
    CONTENT_PLANNER = "Content Planning Agent"
    CONTENT_GENERATOR = "Content Generation Agent"
    QA_AGENT = "Quality Assurance Agent"
    EDITOR = "Editor"
    TASK_PLANNER = "Task Planner"
    COORDINATOR = "Coordinator Agent"
    CHECKPOINT_MANAGER = "Checkpoint Manager"
    UNKNOWN = "Unknown Agent"


class WebSocketMessageInterceptor:
    """
    Intercepts CAMEL agent messages and broadcasts them to WebSocket clients.
    ENHANCED: Properly handles checkpoint responses and workflow integration.
    """
    
    def __init__(
        self, 
        websocket_bridge=None,
        workflow_id: str = None,
        chat_id: Optional[str] = None,
        enable_detailed_logging: bool = True
    ):
        """
        Initialize the WebSocket Message Interceptor.
        
        Args:
            websocket_bridge: CAMELWebSocketBridge instance for broadcasting
            workflow_id: Unique identifier for the workflow
            chat_id: Optional chat instance ID for chat-based interactions
            enable_detailed_logging: Whether to log detailed message content
        """
        self.bridge = websocket_bridge
        self.workflow_id = workflow_id or f"workflow_{uuid.uuid4().hex[:8]}"
        self.chat_id = chat_id
        self.enable_detailed_logging = enable_detailed_logging
        
        # Message tracking
        self.message_count = 0
        self.agent_message_history = []
        self.pending_human_inputs = {}
        self.pending_checkpoints = {}  # Track pending checkpoints
        
        # Agent tracking for wrapping
        self.wrapped_agents = set()
        
        # Workflow service reference
        self.workflow_service = None
        
        # Checkpoint events for synchronization
        self.checkpoint_events: Dict[str, threading.Event] = {}
        
        # Performance tracking
        self.start_time = datetime.now(timezone.utc)
        self.last_message_time = self.start_time
        
        logger.info(f"📡 WebSocket Interceptor initialized for workflow {self.workflow_id}")
        if chat_id:
            logger.info(f"   Connected to chat: {chat_id}")
    
    def set_workflow_service(self, workflow_service):
        """
        Set reference to the workflow service for checkpoint tracking.
        
        Args:
            workflow_service: The CAMELWorkflowService instance
        """
        self.workflow_service = workflow_service
        logger.info(f"✅ Workflow service connected to interceptor")
    
    def wrap_agent(self, agent: Any, agent_name: str = None) -> Any:
        """
        Wrap a CAMEL agent to intercept its messages.
        ENHANCED: Better handling of agent output and checkpoint integration.
        
        Args:
            agent: The CAMEL agent to wrap
            agent_name: Name of the agent for identification
            
        Returns:
            The wrapped agent with intercepted methods
        """
        if not agent or id(agent) in self.wrapped_agents:
            return agent
        
        agent_name = agent_name or getattr(agent, 'name', 'Unknown Agent')
        interceptor = self
        
        # Mark as wrapped
        self.wrapped_agents.add(id(agent))
        
        # Store original methods
        original_step = getattr(agent, 'step', None)
        original_step_async = getattr(agent, 'step_async', None)
        original_run = getattr(agent, 'run', None)
        original_run_async = getattr(agent, 'run_async', None)
        
        # Wrap the step method (most commonly used in CAMEL agents)
        if original_step:
            def wrapped_step(input_message):
                """Wrapped step method that intercepts messages"""
                try:
                    # Log input
                    input_content = interceptor._extract_content_from_message(input_message)
                    
                    if input_content and len(input_content.strip()) > 10:
                        # Send input notification asynchronously
                        asyncio.create_task(interceptor.intercept_agent_message(
                            agent_name=agent_name,
                            message=f"📥 Received task: {input_content[:200]}...",
                            role=interceptor._get_agent_role_name(agent_name),
                            stage="processing_start"
                        ))
                    
                    # Call original method
                    result = original_step(input_message)
                    
                    # Extract output from result
                    output_content = interceptor._extract_content_from_result(result)
                    
                    # Check if this is a checkpoint request
                    if output_content and "checkpoint" in output_content.lower():
                        asyncio.create_task(interceptor._handle_potential_checkpoint(
                            output_content, agent_name
                        ))
                    
                    if output_content and len(output_content.strip()) > 10:
                        # Send output notification asynchronously
                        asyncio.create_task(interceptor.intercept_agent_message(
                            agent_name=agent_name,
                            message=output_content,
                            role=interceptor._get_agent_role_name(agent_name),
                            stage="processing_complete"
                        ))
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error in wrapped_step for {agent_name}: {e}")
                    return original_step(input_message)
            
            agent.step = wrapped_step
            logger.info(f"   ✅ Wrapped {agent_name} step method")
        
        # Wrap async step if available
        if original_step_async:
            async def wrapped_step_async(input_message):
                """Wrapped async step method"""
                try:
                    # Log input
                    input_content = interceptor._extract_content_from_message(input_message)
                    if input_content and len(input_content.strip()) > 10:
                        await interceptor.intercept_agent_message(
                            agent_name=agent_name,
                            message=f"📥 Processing: {input_content[:200]}...",
                            role=interceptor._get_agent_role_name(agent_name),
                            stage="processing_start"
                        )
                    
                    # Call original
                    result = await original_step_async(input_message)
                    
                    # Log output
                    output_content = interceptor._extract_content_from_result(result)
                    
                    # Check for checkpoint
                    if output_content and "checkpoint" in output_content.lower():
                        await interceptor._handle_potential_checkpoint(output_content, agent_name)
                    
                    if output_content and len(output_content.strip()) > 10:
                        await interceptor.intercept_agent_message(
                            agent_name=agent_name,
                            message=output_content,
                            role=interceptor._get_agent_role_name(agent_name),
                            stage="processing_complete"
                        )
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error in wrapped_step_async for {agent_name}: {e}")
                    return await original_step_async(input_message)
            
            agent.step_async = wrapped_step_async
            logger.info(f"   ✅ Wrapped {agent_name} step_async method")
        
        # Wrap run method if available
        if original_run:
            def wrapped_run(*args, **kwargs):
                """Wrapped run method"""
                try:
                    # Log start
                    task = args[0] if args else kwargs.get('task', '')
                    if task:
                        asyncio.create_task(interceptor.intercept_agent_message(
                            agent_name=agent_name,
                            message=f"🚀 Starting: {str(task)[:200]}...",
                            role=interceptor._get_agent_role_name(agent_name),
                            stage="task_start"
                        ))
                    
                    # Call original
                    result = original_run(*args, **kwargs)
                    
                    # Log completion
                    if result:
                        asyncio.create_task(interceptor.intercept_agent_message(
                            agent_name=agent_name,
                            message=f"✅ Completed: {str(result)[:500]}...",
                            role=interceptor._get_agent_role_name(agent_name),
                            stage="task_complete"
                        ))
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error in wrapped_run for {agent_name}: {e}")
                    return original_run(*args, **kwargs)
            
            agent.run = wrapped_run
            logger.info(f"   ✅ Wrapped {agent_name} run method")
        
        logger.info(f"   📡 WebSocket wrapping complete for {agent_name}")
        return agent
    
    async def _handle_potential_checkpoint(self, content: str, agent_name: str):
        """
        Check if content contains a checkpoint request and handle it.
        
        Args:
            content: The content to check
            agent_name: Name of the agent generating the content
        """
        # Check for checkpoint markers
        if any(marker in content.lower() for marker in ["checkpoint:", "review required:", "approval needed:"]):
            # Extract checkpoint data
            checkpoint_id = f"checkpoint_{uuid.uuid4().hex[:8]}"
            
            # Parse content for title and description
            lines = content.split('\n')
            title = "Content Review Required"
            for line in lines:
                if "checkpoint:" in line.lower():
                    title = line.split(":", 1)[1].strip() if ":" in line else title
                    break
            
            checkpoint_data = {
                "checkpoint_id": checkpoint_id,
                "title": title,
                "description": f"Review requested by {agent_name}",
                "content": content,
                "agent": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Send checkpoint and wait for response
            await self.send_checkpoint_and_wait(checkpoint_id, checkpoint_data)
    
    def _extract_content_from_message(self, message: Any) -> str:
        """
        Extract content from various message types.
        
        Args:
            message: The message to extract content from
            
        Returns:
            Extracted content string
        """
        if not message:
            return ""
        
        # Handle CAMEL BaseMessage
        if hasattr(message, 'content'):
            return str(message.content)
        
        # Handle dict
        if isinstance(message, dict):
            return message.get('content', '') or message.get('message', '') or str(message)
        
        # Handle string
        return str(message)
    
    def _extract_content_from_result(self, result: Any) -> str:
        """
        Extract content from agent step result.
        CRITICAL: This extracts from CAMEL's response structure.
        
        Args:
            result: The result from agent.step()
            
        Returns:
            Extracted content string
        """
        if not result:
            return ""
        
        # Handle CAMEL ChatAgentResponse (has msgs attribute)
        if hasattr(result, 'msgs') and result.msgs:
            # msgs is a list of messages
            if isinstance(result.msgs, list) and len(result.msgs) > 0:
                # Get the first message (usually the agent's response)
                first_msg = result.msgs[0]
                if hasattr(first_msg, 'content'):
                    return str(first_msg.content)
                else:
                    return str(first_msg)
            return str(result.msgs)
        
        # Handle direct message
        if hasattr(result, 'content'):
            return str(result.content)
        
        # Handle dict result
        if isinstance(result, dict):
            return result.get('content', '') or result.get('result', '') or str(result)
        
        # Fallback
        return str(result) if result else ""
    
    def _get_agent_role_name(self, agent_name: str) -> str:
        """
        Get human-readable role name for agent.
        
        Args:
            agent_name: Raw agent name
            
        Returns:
            Human-readable role name
        """
        role_map = {
            'enhanced_style_analysis': 'Style Analysis Agent',
            'enhanced_content_planning': 'Content Planning Agent',
            'enhanced_content_generation': 'Content Generation Agent',
            'enhanced_qa': 'Quality Assurance Agent',
            'enhanced_coordinator': 'Coordinator Agent',
            'style_analyst': 'Style Analysis Agent',
            'content_planner': 'Content Planning Agent',
            'content_generator': 'Content Generation Agent',
            'qa_agent': 'Quality Assurance Agent',
            'coordinator': 'Coordinator Agent'
        }
        
        # Try exact match first
        if agent_name in role_map:
            return role_map[agent_name]
        
        # Try to identify by keywords
        agent_lower = agent_name.lower()
        if 'style' in agent_lower:
            return 'Style Analysis Agent'
        elif 'planning' in agent_lower or 'planner' in agent_lower:
            return 'Content Planning Agent'
        elif 'generation' in agent_lower or 'generator' in agent_lower:
            return 'Content Generation Agent'
        elif 'qa' in agent_lower or 'quality' in agent_lower:
            return 'Quality Assurance Agent'
        elif 'coordinator' in agent_lower:
            return 'Coordinator Agent'
        
        return agent_name.replace('_', ' ').title()
    
    async def intercept_agent_message(
        self,
        agent_name: str,
        message: str,
        role: str = None,
        stage: str = "processing",
        **kwargs
    ) -> None:
        """
        Intercept and broadcast an agent message.
        
        Args:
            agent_name: Name of the agent
            message: Message content
            role: Agent role
            stage: Current stage
            **kwargs: Additional metadata
        """
        try:
            self.message_count += 1
            
            # Ensure we have actual content
            if not message or (isinstance(message, str) and not message.strip()):
                logger.debug(f"Skipping empty message from {agent_name}")
                return
            
            # Filter out debug/system messages
            if any(pattern in str(message) for pattern in ["DEBUG:", "INFO:", "WARNING:", "[2025-"]):
                logger.debug(f"Skipping system message from {agent_name}")
                return
            
            role = role or self._get_agent_role_name(agent_name)
            
            # Build message data with the correct field name
            message_data = {
                "type": "agent_message",
                "agent_type": agent_name,
                "agent_role": role,
                "message_content": str(message),  # CRITICAL: Use message_content field
                "stage": stage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_number": self.message_count,
                **kwargs
            }
            
            # Store in history
            self.agent_message_history.append(message_data)
            
            # Broadcast via bridge if available
            if self.bridge:
                try:
                    if hasattr(self.bridge, 'broadcast_agent_message'):
                        await self.bridge.broadcast_agent_message(
                            workflow_id=self.workflow_id,
                            agent_message=message_data
                        )
                        logger.info(f"✅ Broadcast agent message #{self.message_count} from {role}")
                        
                    elif hasattr(self.bridge, 'broadcast_to_workflow'):
                        await self.bridge.broadcast_to_workflow(
                            self.workflow_id,
                            message_data
                        )
                        logger.info(f"✅ Broadcast message #{self.message_count} via fallback")
                    else:
                        logger.error(f"❌ Bridge has no broadcast methods!")
                        
                except Exception as e:
                    logger.error(f"❌ Broadcast failed: {e}", exc_info=True)
            else:
                logger.warning(f"No bridge available for broadcasting")
            
            # Log if enabled
            if self.enable_detailed_logging:
                logger.debug(f"📨 Intercepted {role} message #{self.message_count}")
                if len(message) < 200:
                    logger.debug(f"   Content: {message}")
                else:
                    logger.debug(f"   Content: {message[:200]}...")
            
        except Exception as e:
            logger.error(f"Error in intercept_agent_message: {e}", exc_info=True)
    
    async def send_checkpoint_and_wait(self, checkpoint_id: str, checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send checkpoint requirement through WebSocket and wait for response.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            checkpoint_data: Checkpoint details
            
        Returns:
            The checkpoint response with decision and feedback
        """
        logger.info(f"🛑 Checkpoint created: {checkpoint_id}")
        
        # Track the checkpoint
        self.pending_checkpoints[checkpoint_id] = checkpoint_data
        
        # Register with workflow service if available
        if self.workflow_service and hasattr(self.workflow_service, 'register_checkpoint'):
            await self.workflow_service.register_checkpoint(self.workflow_id, checkpoint_id)
        
        # Create event for waiting
        event = threading.Event()
        self.checkpoint_events[checkpoint_id] = event
        
        checkpoint_msg = {
            "type": "checkpoint_required",
            "checkpoint_id": checkpoint_id,
            "title": checkpoint_data.get('title', 'Content Review Required'),
            "description": checkpoint_data.get('description', 'Please review the generated content'),
            "content_preview": str(checkpoint_data.get('content', ''))[:1000],
            "full_content": checkpoint_data.get('content', ''),
            "stage": checkpoint_data.get('stage', 'checkpoint'),
            "priority": checkpoint_data.get('priority', 'normal'),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Broadcast if bridge available
        if self.bridge:
            try:
                if hasattr(self.bridge, 'broadcast_checkpoint_notification'):
                    await self.bridge.broadcast_checkpoint_notification(
                        workflow_id=self.workflow_id,
                        checkpoint_data=checkpoint_msg
                    )
                else:
                    await self.bridge.broadcast_to_workflow(
                        self.workflow_id,
                        checkpoint_msg
                    )
                logger.info(f"📤 Checkpoint {checkpoint_id} sent, waiting for response...")
                
                # Wait for response with timeout
                timeout = checkpoint_data.get('timeout', 7200)  # 2 hours default
                
                # Use bridge's get_checkpoint_response if available
                if hasattr(self.bridge, 'get_checkpoint_response'):
                    response = self.bridge.get_checkpoint_response(checkpoint_id, timeout=timeout)
                    if response:
                        logger.info(f"✅ Got checkpoint response: {response.get('decision')}")
                        return response
                
                # Fallback: wait for event
                if event.wait(timeout):
                    # Response received
                    response = self.pending_checkpoints.get(checkpoint_id, {})
                    logger.info(f"✅ Checkpoint {checkpoint_id} resolved")
                    return response
                else:
                    # Timeout - auto-approve
                    logger.warning(f"⏰ Checkpoint {checkpoint_id} timed out, auto-approving")
                    return {
                        "decision": "approve",
                        "feedback": "Auto-approved due to timeout",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
            except Exception as e:
                logger.error(f"Failed to send checkpoint: {e}")
                return {
                    "decision": "approve",
                    "feedback": "Auto-approved due to error",
                    "error": str(e)
                }
        
        # No bridge - auto-approve
        return {
            "decision": "approve",
            "feedback": "Auto-approved (no bridge)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def handle_checkpoint_response(self, checkpoint_id: str, decision: str, feedback: str):
        """
        Handle checkpoint response from user.
        
        Args:
            checkpoint_id: The checkpoint ID
            decision: The user's decision
            feedback: User's feedback
        """
        if checkpoint_id in self.pending_checkpoints:
            # Update checkpoint data
            self.pending_checkpoints[checkpoint_id].update({
                "decision": decision,
                "feedback": feedback,
                "resolved_at": datetime.now(timezone.utc).isoformat()
            })
            
            # Set event to unblock waiting
            if checkpoint_id in self.checkpoint_events:
                self.checkpoint_events[checkpoint_id].set()
            
            logger.info(f"✅ Checkpoint {checkpoint_id} resolved with {decision}")
    
    async def send_checkpoint(self, checkpoint_id: str, checkpoint_data: Dict[str, Any]) -> None:
        """
        Legacy method for compatibility - redirects to send_checkpoint_and_wait.
        """
        await self.send_checkpoint_and_wait(checkpoint_id, checkpoint_data)
    
    async def intercept_completion(
        self,
        final_content: str,
        agent_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Intercept and broadcast workflow completion.
        """
        completion_data = {
            "type": "workflow_completed",
            "agent_type": agent_type,
            "final_content": final_content,
            "total_messages": self.message_count,
            "duration": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": self.workflow_id,
            "metadata": metadata or {}
        }
        
        if self.bridge:
            try:
                await self.bridge.broadcast_to_workflow(self.workflow_id, completion_data)
            except Exception as e:
                logger.error(f"Failed to broadcast completion: {e}")
        
        logger.info(f"✅ Workflow completed after {self.message_count} messages")
    
    async def cleanup(self):
        """
        Clean up resources when interceptor is done.
        """
        # Clear pending checkpoints
        self.pending_checkpoints.clear()
        self.checkpoint_events.clear()
        
        # Clear message history if it's too large
        if len(self.agent_message_history) > 1000:
            self.agent_message_history = self.agent_message_history[-100:]  # Keep last 100
        
        logger.info(f"🧹 Cleaned up interceptor for workflow {self.workflow_id}")
    
    def _identify_agent_role(self, agent_type: str) -> AgentRole:
        """
        Identify the specific agent role from the agent type string.
        """
        agent_type_lower = agent_type.lower()
        
        if "checkpoint" in agent_type_lower:
            return AgentRole.CHECKPOINT_MANAGER
        elif "style" in agent_type_lower:
            return AgentRole.STYLE_ANALYST
        elif "planning" in agent_type_lower or "planner" in agent_type_lower:
            return AgentRole.CONTENT_PLANNER
        elif "generation" in agent_type_lower or "generator" in agent_type_lower:
            return AgentRole.CONTENT_GENERATOR
        elif "qa" in agent_type_lower or "quality" in agent_type_lower:
            return AgentRole.QA_AGENT
        elif "coordinator" in agent_type_lower:
            return AgentRole.COORDINATOR
        else:
            return AgentRole.UNKNOWN


# Helper function for easy integration
def create_interceptor(
    websocket_bridge=None,
    workflow_id: str = None,
    chat_id: Optional[str] = None
) -> WebSocketMessageInterceptor:
    """
    Factory function to create a WebSocket interceptor.
    
    Args:
        websocket_bridge: CAMELWebSocketBridge instance
        workflow_id: Workflow identifier
        chat_id: Optional chat identifier
        
    Returns:
        Configured WebSocketMessageInterceptor instance
    """
    interceptor = WebSocketMessageInterceptor(
        websocket_bridge=websocket_bridge,
        workflow_id=workflow_id,
        chat_id=chat_id
    )
    
    return interceptor