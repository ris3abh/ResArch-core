# services/workflow/console_websocket_bridge.py
"""
Console to WebSocket Bridge for SpinScribe CAMEL agents
Captures existing agent console I/O and redirects to WebSocket streams
"""
import asyncio
import sys
import io
import threading
import queue
import uuid
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConsoleCapture:
    """Captures console input/output for WebSocket streaming"""
    
    def __init__(self, websocket_manager, session_id: str):
        self.websocket_manager = websocket_manager
        self.session_id = session_id
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.original_stdin = sys.stdin
        
        # Queues for async communication
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()
        self.input_responses = {}
        
        # Captured streams
        self.stdout_capture = io.StringIO()
        self.stderr_capture = io.StringIO()
        
        # State tracking
        self.is_capturing = False
        self.pending_input_id = None
    
    def start_capture(self):
        """Start capturing console I/O"""
        if self.is_capturing:
            return
        
        self.is_capturing = True
        
        # Replace stdout/stderr with captured versions
        sys.stdout = StreamCapture(self.stdout_capture, self._on_output, 'stdout')
        sys.stderr = StreamCapture(self.stderr_capture, self._on_output, 'stderr')
        
        logger.info(f"Started console capture for session {self.session_id}")
    
    def stop_capture(self):
        """Stop capturing and restore original streams"""
        if not self.is_capturing:
            return
        
        # Restore original streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        sys.stdin = self.original_stdin
        
        self.is_capturing = False
        logger.info(f"Stopped console capture for session {self.session_id}")
    
    def _on_output(self, text: str, stream_type: str):
        """Handle captured output"""
        if not text.strip():
            return
        
        # Check if this looks like a CAMEL agent message
        agent_info = self._parse_agent_output(text)
        
        # Send to WebSocket
        asyncio.create_task(self._send_output_to_websocket(text, stream_type, agent_info))
    
    def _parse_agent_output(self, text: str) -> Dict[str, Any]:
        """Parse CAMEL agent information from output"""
        agent_info = {
            "is_agent_message": False,
            "agent_role": None,
            "message_type": "output"
        }
        
        # Look for CAMEL agent patterns
        if "Content Creator" in text or "Content Strategist" in text:
            agent_info["is_agent_message"] = True
            
            if "Content Creator" in text:
                agent_info["agent_role"] = "Content Creator"
            elif "Content Strategist" in text:
                agent_info["agent_role"] = "Content Strategist"
        
        # Check for human interaction patterns
        if "Question:" in text or "Your reply:" in text:
            agent_info["message_type"] = "human_interaction"
        elif "Enhanced conversation turn" in text:
            agent_info["message_type"] = "turn_start"
        elif "conversation completed" in text.lower():
            agent_info["message_type"] = "completion"
        
        return agent_info
    
    async def _send_output_to_websocket(self, text: str, stream_type: str, agent_info: Dict):
        """Send captured output to WebSocket"""
        try:
            message_data = {
                "type": "console_output",
                "content": text.strip(),
                "stream": stream_type,
                "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
                "session_id": self.session_id,
                **agent_info
            }
            
            # If this looks like an agent message, format it specially
            if agent_info["is_agent_message"]:
                message_data["type"] = "agent_message"
                message_data["role"] = agent_info["agent_role"]
            
            # If this is human interaction, handle it
            if agent_info["message_type"] == "human_interaction" and "Question:" in text:
                await self._handle_human_interaction(text)
            
            # Broadcast to WebSocket
            await self.websocket_manager.broadcast_to_workflow(self.session_id, message_data)
            
        except Exception as e:
            logger.error(f"Error sending output to WebSocket: {e}")
    
    async def _handle_human_interaction(self, question_text: str):
        """Handle human interaction requests"""
        try:
            # Extract question from CAMEL output
            question = question_text.replace("Question:", "").strip()
            
            # Generate request ID
            request_id = str(uuid.uuid4())
            self.pending_input_id = request_id
            
            # Send human input request to WebSocket
            await self.websocket_manager.broadcast_to_workflow(self.session_id, {
                "type": "human_input_required",
                "request_id": request_id,
                "question": question,
                "timestamp": datetime.now(datetime.timezone.utc).isoformat()
            })
            
            # Wait for response from WebSocket (with timeout)
            try:
                response = await asyncio.wait_for(
                    self._wait_for_input_response(request_id), 
                    timeout=3600  # 1 hour timeout
                )
                
                # Inject response into stdin for CAMEL agents
                self._inject_stdin_response(response)
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for human response to: {question}")
                # Inject default response to prevent hanging
                self._inject_stdin_response("Please continue with your best judgment.")
                
        except Exception as e:
            logger.error(f"Error handling human interaction: {e}")
    
    async def _wait_for_input_response(self, request_id: str) -> str:
        """Wait for human response from WebSocket"""
        while request_id not in self.input_responses:
            await asyncio.sleep(0.1)
        
        response = self.input_responses.pop(request_id)
        return response
    
    def _inject_stdin_response(self, response: str):
        """Inject response into stdin for CAMEL agents"""
        # This is tricky - we need to simulate stdin input
        # We'll use a custom input method that CAMEL can read
        self.input_queue.put(response)
    
    def handle_websocket_response(self, request_id: str, response: str):
        """Handle human response from WebSocket"""
        if request_id == self.pending_input_id:
            self.input_responses[request_id] = response
            self.pending_input_id = None

class StreamCapture:
    """Custom stream that captures output while maintaining normal behavior"""
    
    def __init__(self, capture_stream, callback: Callable, stream_type: str):
        self.capture_stream = capture_stream
        self.callback = callback
        self.stream_type = stream_type
        self.original_stream = sys.stdout if stream_type == 'stdout' else sys.stderr
    
    def write(self, text):
        # Write to original stream (so console still works)
        self.original_stream.write(text)
        
        # Capture for WebSocket
        self.capture_stream.write(text)
        
        # Trigger callback
        if self.callback:
            try:
                self.callback(text, self.stream_type)
            except Exception as e:
                # Don't let callback errors break the stream
                pass
        
        return len(text)
    
    def flush(self):
        self.original_stream.flush()
        self.capture_stream.flush()
    
    def __getattr__(self, name):
        # Delegate other attributes to original stream
        return getattr(self.original_stream, name)

class CAMELWebSocketBridge:
    """Main bridge between existing CAMEL agents and WebSocket"""
    
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self.active_captures: Dict[str, ConsoleCapture] = {}
        self.original_camel_input = None
    
    @contextmanager
    def capture_camel_session(self, session_id: str):
        """Context manager for capturing CAMEL session I/O"""
        
        capture = ConsoleCapture(self.websocket_manager, session_id)
        self.active_captures[session_id] = capture
        
        try:
            # Start capturing
            capture.start_capture()
            
            # Patch CAMEL's input function
            self._patch_camel_input(capture)
            
            yield capture
            
        finally:
            # Stop capturing
            capture.stop_capture()
            
            # Restore CAMEL input
            self._restore_camel_input()
            
            # Cleanup
            self.active_captures.pop(session_id, None)
    
    def _patch_camel_input(self, capture: ConsoleCapture):
        """Patch CAMEL's input function to use our queue"""
        
        # Import CAMEL's human toolkit
        try:
            from camel.toolkits.human_toolkit import HumanToolkit
            
            # Store original input method
            if hasattr(HumanToolkit, '_original_input'):
                self.original_camel_input = HumanToolkit._original_input
            else:
                self.original_camel_input = input
                HumanToolkit._original_input = input
            
            # Replace with our custom input
            def custom_input(prompt=""):
                if prompt:
                    print(f"Question: {prompt}")
                
                # Wait for response from WebSocket
                while capture.input_queue.empty():
                    import time
                    time.sleep(0.1)
                
                response = capture.input_queue.get()
                print(f"Your reply: {response}")
                return response
            
            # Patch the input function
            import builtins
            builtins.input = custom_input
            
            # Also patch CAMEL's toolkit if it exists
            if hasattr(HumanToolkit, 'ask_human'):
                HumanToolkit.ask_human = lambda self, prompt: custom_input(prompt)
                
        except ImportError:
            logger.warning("Could not import CAMEL HumanToolkit for patching")
    
    def _restore_camel_input(self):
        """Restore original CAMEL input function"""
        if self.original_camel_input:
            import builtins
            builtins.input = self.original_camel_input
            
            try:
                from camel.toolkits.human_toolkit import HumanToolkit
                if hasattr(HumanToolkit, '_original_input'):
                    HumanToolkit.ask_human = lambda self, prompt: self._original_input(prompt)
            except ImportError:
                pass
    
    def handle_human_response(self, session_id: str, request_id: str, response: str):
        """Handle human response from WebSocket"""
        if session_id in self.active_captures:
            capture = self.active_captures[session_id]
            capture.handle_websocket_response(request_id, response)
    
    async def run_existing_camel_workflow(self, session_id: str, workflow_func: Callable, *args, **kwargs):
        """Run existing CAMEL workflow with WebSocket bridge"""
        
        with self.capture_camel_session(session_id) as capture:
            try:
                # Notify start
                await self.websocket_manager.broadcast_to_workflow(session_id, {
                    "type": "workflow_started",
                    "session_id": session_id,
                    "timestamp": datetime.now(datetime.timezone.utc).isoformat()
                })
                
                # Run the existing workflow function
                result = await asyncio.to_thread(workflow_func, *args, **kwargs)
                
                # Notify completion
                await self.websocket_manager.broadcast_to_workflow(session_id, {
                    "type": "workflow_completed",
                    "session_id": session_id,
                    "result": str(result) if result else "Workflow completed",
                    "timestamp": datetime.now(datetime.timezone.utc).isoformat()
                })
                
                return result
                
            except Exception as e:
                logger.error(f"Error in CAMEL workflow {session_id}: {e}")
                
                # Notify error
                await self.websocket_manager.broadcast_to_workflow(session_id, {
                    "type": "workflow_error",
                    "session_id": session_id,
                    "error": str(e),
                    "timestamp": datetime.now(datetime.timezone.utc).isoformat()
                })
                
                raise

# Global bridge instance
camel_websocket_bridge = None

def initialize_bridge(websocket_manager):
    """Initialize the global bridge instance"""
    global camel_websocket_bridge
    camel_websocket_bridge = CAMELWebSocketBridge(websocket_manager)
    return camel_websocket_bridge