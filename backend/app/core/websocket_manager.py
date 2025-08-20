# backend/app/core/websocket_manager.py
"""
Enhanced WebSocket Manager that supports workflow-specific broadcasting.
UPDATE to existing websocket_manager to support Spinscribe workflows.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Enhanced WebSocket manager that supports workflow-specific channels.
    """
    
    def __init__(self):
        # Connection management
        self.active_connections: List[WebSocket] = []
        self.workflow_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Statistics
        self.total_connections = 0
        self.total_messages_sent = 0
        
        logger.info("🔌 Enhanced WebSocket Manager initialized")
    
    async def connect(self, websocket: WebSocket, workflow_id: Optional[str] = None, user_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        
        await websocket.accept()
        self.active_connections.append(websocket)
        self.total_connections += 1
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "workflow_id": workflow_id,
            "user_id": user_id,
            "connected_at": datetime.now(),
            "messages_received": 0
        }
        
        # Add to workflow-specific connections
        if workflow_id:
            if workflow_id not in self.workflow_connections:
                self.workflow_connections[workflow_id] = set()
            self.workflow_connections[workflow_id].add(websocket)
            
            logger.info(f"🔌 WebSocket connected to workflow {workflow_id} (user: {user_id})")
        else:
            logger.info(f"🔌 General WebSocket connected (user: {user_id})")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
            "message": f"Connected to {'workflow ' + workflow_id if workflow_id else 'Spinscribe backend'}"
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection."""
        
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from workflow connections
        metadata = self.connection_metadata.get(websocket, {})
        workflow_id = metadata.get("workflow_id")
        
        if workflow_id and workflow_id in self.workflow_connections:
            self.workflow_connections[workflow_id].discard(websocket)
            
            # Clean up empty workflow connections
            if not self.workflow_connections[workflow_id]:
                del self.workflow_connections[workflow_id]
        
        # Clean up metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        
        logger.info(f"🔌 WebSocket disconnected from {'workflow ' + workflow_id if workflow_id else 'general'}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        
        try:
            if websocket in self.active_connections:
                await websocket.send_text(json.dumps(message))
                self.total_messages_sent += 1
                
                # Update metadata
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]["messages_received"] += 1
                    
        except Exception as e:
            logger.error(f"Failed to send personal message: {str(e)}")
            # Remove broken connection
            self.disconnect(websocket)
    
    async def broadcast_to_workflow(self, workflow_id: str, message: Dict[str, Any]):
        """Send a message to all connections subscribed to a specific workflow."""
        
        if workflow_id not in self.workflow_connections:
            logger.debug(f"No connections for workflow {workflow_id}")
            return
        
        # Get all connections for this workflow
        connections = list(self.workflow_connections[workflow_id])
        
        if not connections:
            return
        
        logger.debug(f"📡 Broadcasting to {len(connections)} connections for workflow {workflow_id}")
        
        # Add workflow context to message
        enhanced_message = {
            **message,
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all workflow connections
        disconnected_websockets = []
        for websocket in connections:
            try:
                await websocket.send_text(json.dumps(enhanced_message))
                self.total_messages_sent += 1
                
                # Update metadata
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]["messages_received"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to send to workflow connection: {str(e)}")
                disconnected_websockets.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Send a message to all active connections."""
        
        if not self.active_connections:
            return
        
        logger.debug(f"📡 Broadcasting to {len(self.active_connections)} total connections")
        
        enhanced_message = {
            **message,
            "timestamp": datetime.now().isoformat()
        }
        
        disconnected_websockets = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(json.dumps(enhanced_message))
                self.total_messages_sent += 1
                
            except Exception as e:
                logger.error(f"Failed to broadcast message: {str(e)}")
                disconnected_websockets.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket)
    
    async def send_workflow_status(self, workflow_id: str, status_data: Dict[str, Any]):
        """Send workflow status update to subscribers."""
        
        message = {
            "type": "workflow_status",
            "data": status_data
        }
        
        await self.broadcast_to_workflow(workflow_id, message)
    
    async def send_agent_message(self, workflow_id: str, agent_type: str, message_content: str, message_type: str = "text"):
        """Send agent message to workflow subscribers."""
        
        message = {
            "type": "agent_message",
            "data": {
                "agent_type": agent_type,
                "message_content": message_content,
                "message_type": message_type,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await self.broadcast_to_workflow(workflow_id, message)
    
    async def send_checkpoint_notification(self, workflow_id: str, checkpoint_data: Dict[str, Any]):
        """Send checkpoint notification to workflow subscribers."""
        
        message = {
            "type": "checkpoint_required",
            "data": checkpoint_data
        }
        
        await self.broadcast_to_workflow(workflow_id, message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        
        return {
            "active_connections": len(self.active_connections),
            "workflow_connections": {
                workflow_id: len(connections) 
                for workflow_id, connections in self.workflow_connections.items()
            },
            "total_lifetime_connections": self.total_connections,
            "total_messages_sent": self.total_messages_sent,
            "active_workflows": list(self.workflow_connections.keys())
        }
    
    def get_workflow_subscribers(self, workflow_id: str) -> int:
        """Get number of subscribers for a specific workflow."""
        
        return len(self.workflow_connections.get(workflow_id, set()))
    
    async def cleanup_stale_connections(self):
        """Clean up stale connections."""
        
        stale_connections = []
        
        for websocket in self.active_connections:
            try:
                # Send ping to check if connection is alive
                await websocket.ping()
            except Exception:
                stale_connections.append(websocket)
        
        # Remove stale connections
        for websocket in stale_connections:
            self.disconnect(websocket)
        
        if stale_connections:
            logger.info(f"🧹 Cleaned up {len(stale_connections)} stale connections")

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

# Connection handler for workflow-specific WebSockets
async def handle_workflow_websocket(websocket: WebSocket, workflow_id: str, user_id: Optional[str] = None):
    """Handle workflow-specific WebSocket connection."""
    
    await websocket_manager.connect(websocket, workflow_id=workflow_id, user_id=user_id)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                # Handle different message types
                if message_type == "ping":
                    await websocket_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                        websocket
                    )
                
                elif message_type == "subscribe_workflow":
                    requested_workflow_id = message.get("workflow_id")
                    if requested_workflow_id:
                        # Add this connection to the requested workflow
                        if requested_workflow_id not in websocket_manager.workflow_connections:
                            websocket_manager.workflow_connections[requested_workflow_id] = set()
                        websocket_manager.workflow_connections[requested_workflow_id].add(websocket)
                        
                        await websocket_manager.send_personal_message(
                            {
                                "type": "subscription_confirmed",
                                "workflow_id": requested_workflow_id
                            },
                            websocket
                        )
                
                elif message_type == "request_status":
                    # Client requesting workflow status
                    await websocket_manager.send_personal_message(
                        {
                            "type": "status_requested",
                            "workflow_id": workflow_id,
                            "message": "Status update requested"
                        },
                        websocket
                    )
                
                else:
                    logger.debug(f"Unknown message type: {message_type}")
                    
            except json.JSONDecodeError:
                logger.error("Received invalid JSON from WebSocket")
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        websocket_manager.disconnect(websocket)