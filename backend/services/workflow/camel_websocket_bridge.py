# backend/services/workflow/camel_websocket_bridge.py
"""
CAMEL WebSocket Bridge - Connects CAMEL's console I/O to WebSocket for frontend communication
Fixed version with flattened message structure for frontend compatibility
"""

import sys
import io
import asyncio
import logging
import uuid
import builtins
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
from contextlib import contextmanager
from queue import Queue
import threading

logger = logging.getLogger(__name__)


class CAMELWebSocketBridge:
    """
    Bridge between CAMEL's console I/O and WebSocket connections.
    Captures stdout/stderr and intercepts input() calls for real-time frontend communication.
    """
    
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self.active_sessions: Dict[str, 'CaptureSession'] = {}
        self.input_responses: Dict[str, str] = {}
        self.pending_inputs: Dict[str, threading.Event] = {}
        self.workflow_chat_mapping: Dict[str, str] = {}
        self._workflow_websockets: Dict[str, Any] = {}  # Direct WebSocket connections
        self._checkpoint_responses: Dict[str, Dict] = {}  # Store checkpoint responses
        
    def link_workflow_to_chat(self, workflow_id: str, chat_id: str):
        """Link a workflow to a chat for message routing"""
        self.workflow_chat_mapping[workflow_id] = chat_id
        logger.info(f"Linked workflow {workflow_id} to chat {chat_id}")
    
    def link_workflow_websocket(self, workflow_id: str, websocket):
        """Link a workflow to a specific WebSocket connection"""
        self._workflow_websockets[workflow_id] = websocket
        logger.info(f"Linked workflow {workflow_id} to WebSocket")
        
    async def broadcast_agent_message(self, workflow_id: str, agent_message: dict):
        """
        Broadcast agent message to workflow and optionally to chat.
        FIXED: Flattened structure without data nesting
        """
        if not self.websocket_manager:
            return
        
        # CRITICAL FIX: Send flattened message structure for workflow
        workflow_msg = {
            "type": "agent_message",
            "message_content": agent_message.get("content", ""),  # Changed from nested data.content
            "agent_type": agent_message.get("agent_type", "unknown"),
            "agent_role": agent_message.get("agent_role", "Agent"),
            "stage": agent_message.get("stage", "processing"),
            "workflow_id": workflow_id,
            "timestamp": agent_message.get("timestamp", datetime.now(timezone.utc).isoformat())
        }
        
        # Send flattened structure to workflow
        await self.websocket_manager.broadcast_to_workflow(workflow_id, workflow_msg)
        
        # Also send to chat if linked (chat can use different structure if needed)
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            chat_msg = {
                "type": "agent_message",
                "sender_type": "agent",
                "agent_type": agent_message.get("agent_type"),
                "message_content": agent_message.get("content", ""),
                "stage": agent_message.get("stage"),
                "workflow_id": workflow_id,
                "metadata": agent_message.get("metadata", {}),
                "timestamp": agent_message.get("timestamp")
            }
            await self.websocket_manager.send_to_chat(chat_id, chat_msg)
    
    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """
        Generic broadcast to workflow WebSocket connections.
        FIXED: Ensure no data nesting for agent messages
        """
        if self.websocket_manager:
            # Fix message structure if it's an agent_message with nested data
            if message.get("type") == "agent_message" and "data" in message:
                # Flatten the structure
                data = message.pop("data")
                message.update({
                    "message_content": data.get("content", data.get("message_content", "")),
                    "agent_type": data.get("agent_type", "unknown"),
                    "agent_role": data.get("agent_role", "Agent"),
                    "stage": data.get("stage", "processing")
                })
            
            await self.websocket_manager.broadcast_to_workflow(workflow_id, message)
            
    async def broadcast_to_chat(self, chat_id: str, message: dict):
        """Broadcast to chat WebSocket connections."""
        if self.websocket_manager:
            await self.websocket_manager.send_to_chat(chat_id, message)
    
    async def broadcast_checkpoint_notification(self, workflow_id: str, checkpoint_data: dict):
        """
        Broadcast checkpoint notification to workflow and chat.
        FIXED: Use correct message type and structure
        """
        # CRITICAL FIX: Use "checkpoint_required" type and flatten structure
        message = {
            "type": "checkpoint_required",  # Frontend expects this exact type
            "checkpoint_id": checkpoint_data.get("checkpoint_id", str(uuid.uuid4())),
            "title": checkpoint_data.get("title", "Approval Required"),
            "description": checkpoint_data.get("description", "Please review and approve"),
            "content_preview": checkpoint_data.get("content", "")[:500] if checkpoint_data.get("content") else "",
            "status": "pending",
            "workflow_id": workflow_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.broadcast_to_workflow(workflow_id, message)
        
        # Also send to chat if linked
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            await self.broadcast_to_chat(chat_id, message)
    
    async def handle_checkpoint_response(self, workflow_id: str, checkpoint_id: str, decision: str, feedback: str = ""):
        """Handle checkpoint approval/rejection from frontend"""
        logger.info(f"Checkpoint {decision} for {checkpoint_id} in workflow {workflow_id}")
        
        self._checkpoint_responses[checkpoint_id] = {
            "decision": decision,
            "feedback": feedback,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Notify workflow of response
        await self.broadcast_to_workflow(workflow_id, {
            "type": "checkpoint_response_received",
            "checkpoint_id": checkpoint_id,
            "decision": decision,
            "feedback": feedback,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def get_checkpoint_response(self, checkpoint_id: str) -> Optional[Dict]:
        """Get stored checkpoint response"""
        return self._checkpoint_responses.get(checkpoint_id)
            
    @contextmanager
    def capture_camel_session(self, session_id: str):
        """Context manager to capture CAMEL agent I/O for a session"""
        capture = CaptureSession(session_id, self.websocket_manager, self)
        self.active_sessions[session_id] = capture
        
        try:
            capture.start_capture()
            yield capture
        finally:
            capture.stop_capture()
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    def handle_human_response(self, session_id: str, request_id: str, response: str):
        """Handle human response from WebSocket"""
        logger.info(f"Received human response for session {session_id}, request {request_id}: {response}")
        
        self.input_responses[request_id] = response
        
        if request_id in self.pending_inputs:
            self.pending_inputs[request_id].set()
    
    async def wait_for_human_response(self, session_id: str, request_id: str, timeout: int = 3600) -> str:
        """Wait for human response from WebSocket (async version)"""
        event = threading.Event()
        self.pending_inputs[request_id] = event
        
        try:
            if event.wait(timeout):
                response = self.input_responses.pop(request_id, "")
                logger.info(f"Got human response for {request_id}: {response}")
                return response
            else:
                logger.warning(f"Timeout waiting for human response to request {request_id}")
                return "Please continue with your best judgment."
        finally:
            if request_id in self.pending_inputs:
                del self.pending_inputs[request_id]


class CaptureSession:
    """Individual capture session for a CAMEL workflow"""
    
    def __init__(self, session_id: str, websocket_manager, bridge):
        self.session_id = session_id
        self.websocket_manager = websocket_manager
        self.bridge = bridge
        
        self.original_stdout = None
        self.original_stderr = None
        self.original_input = None
        self.is_capturing = False
        self.loop = None
        
    def start_capture(self):
        """Start capturing stdout/stderr and override input()"""
        if self.is_capturing:
            return
        
        logger.info(f"Starting I/O capture for session {self.session_id}")
        
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.original_input = builtins.input
        
        sys.stdout = StreamCapture(sys.stdout, self._on_output, 'stdout')
        sys.stderr = StreamCapture(sys.stderr, self._on_output, 'stderr')
        builtins.input = self._custom_input
        
        # Patch CAMEL's HumanToolkit if available
        try:
            from camel.toolkits.human_toolkit import HumanToolkit
            if hasattr(HumanToolkit, 'ask_human_via_console'):
                self._original_ask_human = HumanToolkit.ask_human_via_console
                HumanToolkit.ask_human_via_console = lambda self, prompt: self._custom_input(prompt)
        except ImportError:
            pass
        
        self.is_capturing = True
        
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
    
    def stop_capture(self):
        """Stop capturing and restore original I/O"""
        if not self.is_capturing:
            return
        
        logger.info(f"Stopping I/O capture for session {self.session_id}")
        
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        builtins.input = self.original_input
        
        try:
            from camel.toolkits.human_toolkit import HumanToolkit
            if hasattr(self, '_original_ask_human'):
                HumanToolkit.ask_human_via_console = self._original_ask_human
        except ImportError:
            pass
        
        self.is_capturing = False
    
    def _custom_input(self, prompt: str = "") -> str:
        """Custom input function that uses WebSocket for human interaction"""
        logger.info(f"Intercepted input request: {prompt}")
        
        question_data = self._parse_question(prompt)
        request_id = str(uuid.uuid4())
        
        asyncio.run_coroutine_threadsafe(
            self._send_human_input_request(request_id, question_data),
            self.loop
        ).result()
        
        response = asyncio.run_coroutine_threadsafe(
            self.bridge.wait_for_human_response(self.session_id, request_id),
            self.loop
        ).result()
        
        if self.original_stdout:
            self.original_stdout.write(f"Your reply: {response}\n")
            self.original_stdout.flush()
        
        return response
    
    def _parse_question(self, prompt: str) -> Dict[str, Any]:
        """Parse the question prompt to extract metadata"""
        question_data = {
            "question": prompt.strip(),
            "type": "general",
            "options": None
        }
        
        prompt_lower = prompt.lower()
        
        if "[yes/no]" in prompt_lower:
            question_data["type"] = "yes_no"
            question_data["options"] = ["yes", "no"]
        elif "professional/casual/technical" in prompt_lower:
            question_data["type"] = "choice"
            question_data["options"] = ["professional", "casual", "technical"]
        elif "approve" in prompt_lower:
            question_data["type"] = "approval"
            question_data["options"] = ["approve", "reject", "needs revision"]
        
        return question_data
    
    async def _send_human_input_request(self, request_id: str, question_data: Dict):
        """Send human input request via WebSocket - FIXED structure"""
        try:
            # CRITICAL FIX: Send flattened structure
            message = {
                "type": "human_input_required",
                "request_id": request_id,
                "question": question_data["question"],
                "question_type": question_data["type"],
                "options": question_data["options"],
                "workflow_id": self.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.websocket_manager.broadcast_to_workflow(self.session_id, message)
            logger.info(f"Sent human input request {request_id} via WebSocket")
            
        except Exception as e:
            logger.error(f"Error sending human input request: {e}")
    
    def _on_output(self, text: str, stream_type: str):
        """Handle captured output from stdout/stderr"""
        if not text.strip():
            return
        
        agent_info = self._parse_agent_output(text)
        
        asyncio.run_coroutine_threadsafe(
            self._send_output_to_websocket(text, stream_type, agent_info),
            self.loop
        )
    
    def _parse_agent_output(self, text: str) -> Dict[str, Any]:
        """Parse CAMEL agent information from output"""
        agent_info = {
            "is_agent_message": False,
            "agent_type": None,
            "agent_role": None,
            "message_type": "general"
        }
        
        # Agent detection patterns
        agent_patterns = [
            ("Content Creator", "content_creator", "Content Creator Agent"),
            ("Content Strategist", "content_strategist", "Content Strategy Agent"),
            ("Style Analysis", "style_analyst", "Style Analysis Agent"),
            ("Content Planning", "content_planner", "Content Planning Agent"),
            ("Content Generation", "content_generator", "Content Generation Agent"),
            ("Quality Assurance", "qa_agent", "Quality Assurance Agent"),
            ("Coordinator", "coordinator", "Coordinator Agent")
        ]
        
        for pattern, agent_type, agent_role in agent_patterns:
            if pattern in text:
                agent_info["is_agent_message"] = True
                agent_info["agent_type"] = agent_type
                agent_info["agent_role"] = agent_role
                break
        
        # Message type detection
        if "Solution:" in text:
            agent_info["message_type"] = "solution"
        elif "Instruction:" in text:
            agent_info["message_type"] = "instruction"
        elif "Question:" in text:
            agent_info["message_type"] = "question"
        elif "turn" in text.lower() and "/" in text:
            agent_info["message_type"] = "progress"
        
        return agent_info
    
    async def _send_output_to_websocket(self, text: str, stream_type: str, agent_info: Dict):
        """Send captured output to WebSocket - FIXED structure"""
        try:
            if agent_info["is_agent_message"]:
                # CRITICAL FIX: Send flattened agent message
                message = {
                    "type": "agent_message",
                    "message_content": text.strip(),  # Use message_content
                    "agent_type": agent_info["agent_type"],
                    "agent_role": agent_info["agent_role"],
                    "stage": "processing",
                    "workflow_id": self.session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                # System output (not an agent message)
                message = {
                    "type": "workflow_output",
                    "content": text.strip(),
                    "stream": stream_type,
                    "message_type": agent_info["message_type"],
                    "workflow_id": self.session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            await self.websocket_manager.broadcast_to_workflow(self.session_id, message)
            
        except Exception as e:
            logger.error(f"Error sending output to WebSocket: {e}")


class StreamCapture:
    """Custom stream wrapper that captures output while maintaining console display"""
    
    def __init__(self, original_stream, callback: Callable, stream_type: str):
        self.original_stream = original_stream
        self.callback = callback
        self.stream_type = stream_type
        self.buffer = ""
    
    def write(self, text):
        self.original_stream.write(text)
        self.buffer += text
        
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            if line.strip() and self.callback:
                try:
                    self.callback(line, self.stream_type)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        
        return len(text)
    
    def flush(self):
        self.original_stream.flush()
        
        if self.buffer.strip() and self.callback:
            try:
                self.callback(self.buffer, self.stream_type)
            except Exception:
                pass
            self.buffer = ""
    
    def __getattr__(self, name):
        return getattr(self.original_stream, name)