# backend/services/chat/websocket_service.py
import json
import asyncio
from typing import Dict, Set, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid

from app.schemas.chat import WebSocketMessage, ChatMessageWebSocket, WorkflowUpdateWebSocket, CheckpointWebSocket

class ConnectionManager:
    """Manages WebSocket connections for real-time chat and workflow updates."""
    
    def __init__(self):
        # Active connections by user_id
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        
        # Chat room connections by chat_instance_id
        self.chat_connections: Dict[str, Set[WebSocket]] = {}
        
        # Workflow connections by workflow_id
        self.workflow_connections: Dict[str, Set[WebSocket]] = {}
        
        # User to chat/workflow mapping
        self.user_chat_mapping: Dict[str, Set[str]] = {}
        self.user_workflow_mapping: Dict[str, Set[str]] = {}
    
    async def connect_user(self, websocket: WebSocket, user_id: str):
        """Connect a user to the WebSocket system."""
        await websocket.accept()
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        
        self.user_connections[user_id].add(websocket)
        
        # Send connection confirmation
        await self.send_to_user(user_id, {
            "type": "connection_established",
            "data": {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def disconnect_user(self, websocket: WebSocket, user_id: str):
        """Disconnect a user from the WebSocket system."""
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                
                # Clean up chat and workflow connections
                if user_id in self.user_chat_mapping:
                    for chat_id in self.user_chat_mapping[user_id]:
                        if chat_id in self.chat_connections:
                            self.chat_connections[chat_id].discard(websocket)
                            if not self.chat_connections[chat_id]:
                                del self.chat_connections[chat_id]
                    del self.user_chat_mapping[user_id]
                
                if user_id in self.user_workflow_mapping:
                    for workflow_id in self.user_workflow_mapping[user_id]:
                        if workflow_id in self.workflow_connections:
                            self.workflow_connections[workflow_id].discard(websocket)
                            if not self.workflow_connections[workflow_id]:
                                del self.workflow_connections[workflow_id]
                    del self.user_workflow_mapping[user_id]
    
    async def join_chat(self, websocket: WebSocket, user_id: str, chat_id: str):
        """Join a user to a specific chat room."""
        if chat_id not in self.chat_connections:
            self.chat_connections[chat_id] = set()
        
        self.chat_connections[chat_id].add(websocket)
        
        # Track user's chat memberships
        if user_id not in self.user_chat_mapping:
            self.user_chat_mapping[user_id] = set()
        self.user_chat_mapping[user_id].add(chat_id)
        
        await self.send_to_chat(chat_id, {
            "type": "user_joined_chat",
            "data": {"user_id": user_id, "chat_id": chat_id},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def leave_chat(self, websocket: WebSocket, user_id: str, chat_id: str):
        """Remove a user from a specific chat room."""
        if chat_id in self.chat_connections:
            self.chat_connections[chat_id].discard(websocket)
            
            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]
        
        if user_id in self.user_chat_mapping:
            self.user_chat_mapping[user_id].discard(chat_id)
    
    async def join_workflow(self, websocket: WebSocket, user_id: str, workflow_id: str):
        """Join a user to workflow updates."""
        if workflow_id not in self.workflow_connections:
            self.workflow_connections[workflow_id] = set()
        
        self.workflow_connections[workflow_id].add(websocket)
        
        # Track user's workflow subscriptions
        if user_id not in self.user_workflow_mapping:
            self.user_workflow_mapping[user_id] = set()
        self.user_workflow_mapping[user_id].add(workflow_id)
    
    async def leave_workflow(self, websocket: WebSocket, user_id: str, workflow_id: str):
        """Remove a user from workflow updates."""
        if workflow_id in self.workflow_connections:
            self.workflow_connections[workflow_id].discard(websocket)
            
            if not self.workflow_connections[workflow_id]:
                del self.workflow_connections[workflow_id]
        
        if user_id in self.user_workflow_mapping:
            self.user_workflow_mapping[user_id].discard(workflow_id)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a specific user."""
        if user_id in self.user_connections:
            dead_connections = set()
            
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                self.user_connections[user_id].discard(dead_conn)
    
    async def send_to_chat(self, chat_id: str, message: dict):
        """Send message to all users in a chat room."""
        if chat_id in self.chat_connections:
            dead_connections = set()
            
            for connection in self.chat_connections[chat_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                self.chat_connections[chat_id].discard(dead_conn)
    
    async def send_to_workflow(self, workflow_id: str, message: dict):
        """Send workflow update to all subscribers."""
        if workflow_id in self.workflow_connections:
            dead_connections = set()
            
            for connection in self.workflow_connections[workflow_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                self.workflow_connections[workflow_id].discard(dead_conn)
    
    async def broadcast_chat_message(self, chat_id: str, message_data: dict):
        """Broadcast a new chat message to all chat participants."""
        websocket_message = ChatMessageWebSocket(
            data=message_data,
            timestamp=datetime.utcnow()
        )
        await self.send_to_chat(chat_id, websocket_message.dict())
    
    async def broadcast_workflow_update(self, workflow_id: str, update_data: dict):
        """Broadcast workflow progress update."""
        websocket_message = WorkflowUpdateWebSocket(
            data=update_data,
            timestamp=datetime.utcnow()
        )
        await self.send_to_workflow(workflow_id, websocket_message.dict())
    
    async def broadcast_checkpoint_required(self, workflow_id: str, checkpoint_data: dict):
        """Broadcast that a checkpoint requires human approval."""
        websocket_message = CheckpointWebSocket(
            data=checkpoint_data,
            timestamp=datetime.utcnow()
        )
        await self.send_to_workflow(workflow_id, websocket_message.dict())

# Global connection manager instance
connection_manager = ConnectionManager()

# backend/services/camel_integration/camel_bridge.py
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from services.chat.websocket_service import connection_manager

class CAMELEventBridge:
    """
    Bridge between CAMEL agents and the web interface.
    This preserves all CAMEL agent-to-agent communication while
    providing web updates.
    """
    
    def __init__(self):
        self.active_workflows: Dict[str, Any] = {}
    
    async def start_workflow_monitoring(self, workflow_id: str, chat_id: Optional[str] = None):
        """Start monitoring a CAMEL workflow for web updates."""
        
        self.active_workflows[workflow_id] = {
            'chat_id': chat_id,
            'start_time': datetime.utcnow(),
            'last_update': datetime.utcnow()
        }
        
        # Notify web clients that workflow has started
        await connection_manager.broadcast_workflow_update(workflow_id, {
            'workflow_id': workflow_id,
            'status': 'started',
            'stage': 'initialization',
            'progress': 0.0,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def emit_agent_started(self, workflow_id: str, agent_type: str, stage: str):
        """Emit event when an agent starts working."""
        
        await connection_manager.broadcast_workflow_update(workflow_id, {
            'workflow_id': workflow_id,
            'event_type': 'agent_started',
            'agent_type': agent_type,
            'stage': stage,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # If there's an associated chat, send agent message
        if workflow_id in self.active_workflows and self.active_workflows[workflow_id]['chat_id']:
            chat_id = self.active_workflows[workflow_id]['chat_id']
            
            await connection_manager.broadcast_chat_message(chat_id, {
                'sender_type': 'agent',
                'agent_type': agent_type,
                'message_content': f"🤖 {agent_type.replace('_', ' ').title()} agent is now working on {stage}...",
                'message_type': 'system',
                'metadata': {
                    'workflow_id': workflow_id,
                    'stage': stage,
                    'event_type': 'agent_started'
                }
            })
    
    async def emit_agent_completed(self, workflow_id: str, agent_type: str, result: str):
        """Emit event when an agent completes its work."""
        
        await connection_manager.broadcast_workflow_update(workflow_id, {
            'workflow_id': workflow_id,
            'event_type': 'agent_completed',
            'agent_type': agent_type,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send completion message to chat
        if workflow_id in self.active_workflows and self.active_workflows[workflow_id]['chat_id']:
            chat_id = self.active_workflows[workflow_id]['chat_id']
            
            await connection_manager.broadcast_chat_message(chat_id, {
                'sender_type': 'agent',
                'agent_type': agent_type,
                'message_content': f"✅ {agent_type.replace('_', ' ').title()} agent completed its task.",
                'message_type': 'text',
                'metadata': {
                    'workflow_id': workflow_id,
                    'result': result,
                    'event_type': 'agent_completed'
                }
            })
    
    async def emit_checkpoint_required(self, workflow_id: str, checkpoint_data: Dict[str, Any]):
        """Emit event when human checkpoint is required."""
        
        await connection_manager.broadcast_checkpoint_required(workflow_id, {
            'workflow_id': workflow_id,
            'checkpoint_type': checkpoint_data.get('type', 'review'),
            'title': checkpoint_data.get('title', 'Review Required'),
            'description': checkpoint_data.get('description', ''),
            'content': checkpoint_data.get('content', ''),
            'requires_approval': True,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send checkpoint message to chat
        if workflow_id in self.active_workflows and self.active_workflows[workflow_id]['chat_id']:
            chat_id = self.active_workflows[workflow_id]['chat_id']
            
            await connection_manager.broadcast_chat_message(chat_id, {
                'sender_type': 'system',
                'message_content': f"⏸️ **Checkpoint Required**: {checkpoint_data.get('title', 'Review Required')}",
                'message_type': 'checkpoint',
                'metadata': {
                    'workflow_id': workflow_id,
                    'checkpoint_data': checkpoint_data,
                    'event_type': 'checkpoint_required'
                }
            })
    
    async def emit_workflow_progress(self, workflow_id: str, stage: str, progress: float):
        """Emit workflow progress update."""
        
        await connection_manager.broadcast_workflow_update(workflow_id, {
            'workflow_id': workflow_id,
            'event_type': 'progress_update',
            'stage': stage,
            'progress': progress,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def emit_workflow_completed(self, workflow_id: str, final_content: str):
        """Emit event when workflow is completed."""
        
        await connection_manager.broadcast_workflow_update(workflow_id, {
            'workflow_id': workflow_id,
            'event_type': 'workflow_completed',
            'status': 'completed',
            'final_content': final_content,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send completion message to chat
        if workflow_id in self.active_workflows and self.active_workflows[workflow_id]['chat_id']:
            chat_id = self.active_workflows[workflow_id]['chat_id']
            
            await connection_manager.broadcast_chat_message(chat_id, {
                'sender_type': 'system',
                'message_content': f"🎉 **Workflow Completed!** Your content is ready for review.",
                'message_type': 'text',
                'metadata': {
                    'workflow_id': workflow_id,
                    'final_content': final_content,
                    'event_type': 'workflow_completed'
                }
            })
        
        # Clean up
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]

# Global bridge instance
camel_bridge = CAMELEventBridge()