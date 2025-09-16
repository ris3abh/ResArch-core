# backend/services/workflow/camel_websocket_bridge.py
"""
CAMEL WebSocket Bridge - Connects CAMEL's console I/O to WebSocket for frontend communication
Fixed version with proper builtins handling and required broadcast methods
"""

import sys
import io
import asyncio
import logging
import uuid
import builtins  # Import at module level
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
        self.workflow_chat_mapping: Dict[str, str] = {}  # Maps workflow_id to chat_id
        
    def link_workflow_to_chat(self, workflow_id: str, chat_id: str):
        """Link a workflow to a chat for message routing"""
        self.workflow_chat_mapping[workflow_id] = chat_id
        logger.info(f"Linked workflow {workflow_id} to chat {chat_id}")
        
    async def broadcast_agent_message(self, workflow_id: str, agent_message: dict):
        """
        Broadcast agent message to workflow and optionally to chat.
        REQUIRED by WebSocketMessageInterceptor.
        """
        if not self.websocket_manager:
            return
            
        # Send to workflow WebSocket connections
        await self.websocket_manager.broadcast_to_workflow(workflow_id, {
            "type": "agent_message",
            "data": agent_message,
            "timestamp": agent_message.get("timestamp", datetime.now(timezone.utc).isoformat())
        })
        
        # Also send to chat if linked
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            await self.websocket_manager.send_to_chat(chat_id, {
                "type": "agent_message",
                "data": {
                    "sender_type": "agent",
                    "agent_type": agent_message.get("agent_type"),
                    "message_content": agent_message.get("content"),
                    "stage": agent_message.get("stage"),
                    "workflow_id": workflow_id,
                    "metadata": agent_message.get("metadata", {})
                },
                "timestamp": agent_message.get("timestamp")
            })
    
    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """
        Generic broadcast to workflow WebSocket connections.
        REQUIRED by WebSocketMessageInterceptor for various message types.
        """
        if self.websocket_manager:
            await self.websocket_manager.broadcast_to_workflow(workflow_id, message)
            
    async def broadcast_to_chat(self, chat_id: str, message: dict):
        """
        Broadcast to chat WebSocket connections.
        Used for sending messages directly to chat interface.
        """
        if self.websocket_manager:
            await self.websocket_manager.send_to_chat(chat_id, message)
    
    async def broadcast_checkpoint_notification(self, workflow_id: str, checkpoint_data: dict):
        """
        Broadcast checkpoint notification to workflow and chat.
        Used when human approval is required.
        """
        message = {
            "type": "checkpoint_required",
            "data": checkpoint_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.broadcast_to_workflow(workflow_id, message)
        
        # Also send to chat if linked
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            await self.broadcast_to_chat(chat_id, message)
            
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
        
        # Store the response
        self.input_responses[request_id] = response
        
        # Signal that response is available
        if request_id in self.pending_inputs:
            self.pending_inputs[request_id].set()
    
    async def wait_for_human_response(self, session_id: str, request_id: str, timeout: int = 3600) -> str:
        """Wait for human response from WebSocket (async version)"""
        event = threading.Event()
        self.pending_inputs[request_id] = event
        
        try:
            # Wait for response with timeout
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
        
        # Stream capture
        self.original_stdout = None
        self.original_stderr = None
        self.original_input = None
        self.is_capturing = False
        
        # For async event loop
        self.loop = None
        
    def start_capture(self):
        """Start capturing stdout/stderr and override input()"""
        if self.is_capturing:
            return
        
        logger.info(f"Starting I/O capture for session {self.session_id}")
        
        # Store originals
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.original_input = builtins.input  # Use builtins directly
        
        # Create custom streams
        sys.stdout = StreamCapture(sys.stdout, self._on_output, 'stdout')
        sys.stderr = StreamCapture(sys.stderr, self._on_output, 'stderr')
        
        # Override input function
        builtins.input = self._custom_input
        
        # Also patch CAMEL's HumanToolkit if it's being used
        try:
            from camel.toolkits.human_toolkit import HumanToolkit
            # Store original method
            if hasattr(HumanToolkit, 'ask_human_via_console'):
                self._original_ask_human = HumanToolkit.ask_human_via_console
                # Replace with our custom method
                HumanToolkit.ask_human_via_console = lambda self, prompt: self._custom_input(prompt)
        except ImportError:
            pass
        
        self.is_capturing = True
        
        # Get or create event loop for async operations
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
        
        # Restore originals
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        builtins.input = self.original_input  # Use builtins directly
        
        # Restore CAMEL's HumanToolkit
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
        
        # Parse the prompt to identify question type
        question_data = self._parse_question(prompt)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Send question to WebSocket
        asyncio.run_coroutine_threadsafe(
            self._send_human_input_request(request_id, question_data),
            self.loop
        ).result()
        
        # Wait for response (blocking)
        response = asyncio.run_coroutine_threadsafe(
            self.bridge.wait_for_human_response(self.session_id, request_id),
            self.loop
        ).result()
        
        # Also print to console for logging
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
        
        # Detect question type
        prompt_lower = prompt.lower()
        
        if "[yes/no]" in prompt_lower:
            question_data["type"] = "yes_no"
            question_data["options"] = ["yes", "no"]
        elif "professional/casual/technical" in prompt_lower:
            question_data["type"] = "choice"
            question_data["options"] = ["professional", "casual", "technical"]
        elif "approve" in prompt_lower:
            question_data["type"] = "approval"
            question_data["options"] = ["yes", "no", "needs revision"]
        
        return question_data
    
    async def _send_human_input_request(self, request_id: str, question_data: Dict):
        """Send human input request via WebSocket"""
        try:
            message = {
                "type": "human_input_required",
                "request_id": request_id,
                "session_id": self.session_id,
                "question": question_data["question"],
                "question_type": question_data["type"],
                "options": question_data["options"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to workflow WebSocket connections
            await self.websocket_manager.broadcast_to_workflow(self.session_id, message)
            
            logger.info(f"Sent human input request {request_id} via WebSocket")
            
        except Exception as e:
            logger.error(f"Error sending human input request: {e}")
    
    def _on_output(self, text: str, stream_type: str):
        """Handle captured output from stdout/stderr"""
        if not text.strip():
            return
        
        # Parse for agent information
        agent_info = self._parse_agent_output(text)
        
        # Send to WebSocket asynchronously
        asyncio.run_coroutine_threadsafe(
            self._send_output_to_websocket(text, stream_type, agent_info),
            self.loop
        )
    
    def _parse_agent_output(self, text: str) -> Dict[str, Any]:
        """Parse CAMEL agent information from output"""
        agent_info = {
            "is_agent_message": False,
            "agent_role": None,
            "message_type": "general"
        }
        
        # Detect CAMEL agent patterns
        if "Content Creator" in text:
            agent_info["is_agent_message"] = True
            agent_info["agent_role"] = "Content Creator"
        elif "Content Strategist" in text:
            agent_info["is_agent_message"] = True
            agent_info["agent_role"] = "Content Strategist"
        elif "Style Analysis" in text or "Style Analyst" in text:
            agent_info["is_agent_message"] = True
            agent_info["agent_role"] = "Style Analysis Agent"
        elif "Content Planning" in text or "Content Planner" in text:
            agent_info["is_agent_message"] = True
            agent_info["agent_role"] = "Content Planning Agent"
        elif "Content Generation" in text:
            agent_info["is_agent_message"] = True
            agent_info["agent_role"] = "Content Generation Agent"
        elif "Quality Assurance" in text or "QA Agent" in text:
            agent_info["is_agent_message"] = True
            agent_info["agent_role"] = "Quality Assurance Agent"
        elif "Coordinator" in text:
            agent_info["is_agent_message"] = True
            agent_info["agent_role"] = "Coordinator Agent"
        
        # Detect message types
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
        """Send captured output to WebSocket"""
        try:
            message = {
                "type": "agent_output",
                "content": text.strip(),
                "stream": stream_type,
                "session_id": self.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **agent_info
            }
            
            # Special handling for agent messages
            if agent_info["is_agent_message"]:
                message["type"] = "agent_message"
            
            # Broadcast to workflow WebSocket
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
        # Write to original stream (console)
        self.original_stream.write(text)
        
        # Buffer text for line-based processing
        self.buffer += text
        
        # Process complete lines
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
        
        # Flush any remaining buffer
        if self.buffer.strip() and self.callback:
            try:
                self.callback(self.buffer, self.stream_type)
            except Exception:
                pass
            self.buffer = ""
    
    def __getattr__(self, name):
        # Delegate other attributes to original stream
        return getattr(self.original_stream, name)