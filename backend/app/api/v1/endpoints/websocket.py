"""
Enhanced WebSocket endpoints for real-time workflow communication
FIXED: Properly handles agent messages, checkpoints, and human interactions
"""
import json
import logging
import asyncio
import traceback
import uuid
from typing import Optional, Dict, Any, Set
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from starlette.websockets import WebSocketState
from collections import defaultdict

logger = logging.getLogger(__name__)
router = APIRouter()

# Global connection tracking
active_connections: Dict[str, Dict[str, Any]] = {}
workflow_connections: Dict[str, Set[str]] = defaultdict(set)
chat_connections: Dict[str, Set[str]] = defaultdict(set)

# Import with error handling
try:
    from app.core.websocket_manager import websocket_manager
    from app.core.auth import verify_token
    from services.workflow.camel_workflow_service import workflow_service
    from services.workflow.camel_websocket_bridge import CAMELWebSocketBridge
    from spinscribe.checkpoints.checkpoint_manager import CheckpointManager
    
    # Create global instances
    camel_bridge = CAMELWebSocketBridge(websocket_manager)
    checkpoint_manager = CheckpointManager()
    
    # Connect services
    if workflow_service:
        workflow_service.set_websocket_manager(websocket_manager)
        if hasattr(workflow_service, 'set_camel_bridge'):
            workflow_service.set_camel_bridge(camel_bridge)
    
    logger.info("✅ WebSocket services initialized successfully")
    
except ImportError as e:
    logger.error(f"Failed to import dependencies: {e}")
    websocket_manager = None
    workflow_service = None
    camel_bridge = None
    checkpoint_manager = None
    verify_token = None


async def broadcast_to_workflow(workflow_id: str, message: Dict[str, Any]):
    """
    Broadcast a message to all connections watching a workflow.
    """
    connections = workflow_connections.get(workflow_id, set())
    dead_connections = set()
    
    for conn_id in connections:
        conn_info = active_connections.get(conn_id)
        if conn_info:
            try:
                websocket = conn_info['websocket']
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    dead_connections.add(conn_id)
            except Exception as e:
                logger.error(f"Failed to send to {conn_id}: {e}")
                dead_connections.add(conn_id)
        else:
            dead_connections.add(conn_id)
    
    # Clean up dead connections
    for conn_id in dead_connections:
        workflow_connections[workflow_id].discard(conn_id)
        active_connections.pop(conn_id, None)


async def handle_checkpoint_response(
    workflow_id: str,
    checkpoint_id: str,
    decision: str,
    feedback: str,
    websocket: WebSocket
):
    """
    Handle checkpoint approval/rejection from frontend.
    FIXED: Properly unblocks workflow execution.
    """
    try:
        logger.info(f"Processing checkpoint {decision} for {checkpoint_id}")
        
        # Validate decision
        if decision not in ['approve', 'reject']:
            await websocket.send_json({
                "type": "error",
                "message": f"Invalid decision: {decision}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return
        
        # Process the checkpoint response
        if checkpoint_manager:
            # Record the response in checkpoint manager
            approved = decision == 'approve'
            checkpoint_manager.respond_to_checkpoint(
                checkpoint_id=checkpoint_id,
                approved=approved,
                feedback=feedback,
                responded_by="user"  # Could be from token if available
            )
            
            # Notify all workflow connections about the decision
            await broadcast_to_workflow(workflow_id, {
                "type": "checkpoint_resolved",
                "checkpoint_id": checkpoint_id,
                "decision": decision,
                "feedback": feedback,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # If CAMEL bridge available, notify it to resume workflow
            if camel_bridge and hasattr(camel_bridge, 'handle_checkpoint_response'):
                await camel_bridge.handle_checkpoint_response(
                    workflow_id=workflow_id,
                    checkpoint_id=checkpoint_id,
                    decision=decision,
                    feedback=feedback
                )
            
            # Send acknowledgment
            await websocket.send_json({
                "type": "checkpoint_response_processed",
                "checkpoint_id": checkpoint_id,
                "decision": decision,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"✅ Checkpoint {checkpoint_id} {decision}d")
            
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Checkpoint manager not available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error handling checkpoint response: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to process checkpoint: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


async def handle_websocket_message(
    workflow_id: str,
    data: Dict[Any, Any],
    websocket: WebSocket,
    connection_id: str
):
    """
    Handle incoming WebSocket messages for workflows.
    FIXED: Properly handles all message types.
    """
    message_type = data.get("type")
    
    try:
        if message_type == "human_response":
            # Handle human response to agent questions
            request_id = data.get("request_id")
            response = data.get("response")
            
            if not request_id or response is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid human response: missing request_id or response",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                return
            
            logger.info(f"Human response for {request_id}: {response}")
            
            # Forward to CAMEL bridge
            if camel_bridge:
                camel_bridge.handle_human_response(workflow_id, request_id, response)
                
                # Broadcast to all workflow connections
                await broadcast_to_workflow(workflow_id, {
                    "type": "human_response_received",
                    "request_id": request_id,
                    "response": response,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
        elif message_type == "checkpoint_response":
            # Handle checkpoint approval/rejection
            checkpoint_id = data.get("checkpoint_id")
            decision = data.get("decision")
            feedback = data.get("feedback", "")
            
            if checkpoint_id and decision:
                await handle_checkpoint_response(
                    workflow_id=workflow_id,
                    checkpoint_id=checkpoint_id,
                    decision=decision,
                    feedback=feedback,
                    websocket=websocket
                )
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid checkpoint response: missing checkpoint_id or decision",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        
        elif message_type == "get_status":
            # Get current workflow status
            if workflow_service:
                status = await workflow_service.get_workflow_status(workflow_id)
                await websocket.send_json({
                    "type": "workflow_status",
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                await websocket.send_json({
                    "type": "workflow_status",
                    "status": {"state": "unknown"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        
        elif message_type == "ping":
            # Heartbeat response
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        elif message_type == "subscribe_agents":
            # Subscribe to agent messages
            logger.info(f"Connection {connection_id} subscribed to agent messages")
            # Could store this preference if needed
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": f"Error processing message: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


@router.websocket("/api/v1/ws/workflows/{workflow_id}")
async def workflow_websocket(
    websocket: WebSocket,
    workflow_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time workflow updates.
    FIXED: Properly handles agent messages and checkpoints.
    """
    
    connection_id = None
    heartbeat_task = None
    
    try:
        # Step 1: Verify authentication if token provided
        user = None
        if token and verify_token:
            try:
                user = await verify_token(token)
                if not user:
                    await websocket.close(code=4001, reason="Invalid token")
                    return
            except Exception as e:
                logger.warning(f"Token verification failed: {e}")
                # Continue without auth for now
        
        # Step 2: Accept WebSocket connection
        await websocket.accept()
        logger.info(f"✅ WebSocket accepted for workflow {workflow_id}")
        
        # Critical: Allow client time to establish connection
        await asyncio.sleep(0.5)
        
        # Step 3: Generate connection ID and track connection
        connection_id = f"workflow_{workflow_id}_{uuid.uuid4().hex[:8]}"
        
        # Store connection info
        active_connections[connection_id] = {
            'websocket': websocket,
            'type': 'workflow',
            'workflow_id': workflow_id,
            'user': user,
            'connected_at': datetime.now(timezone.utc)
        }
        
        # Track workflow connections
        workflow_connections[workflow_id].add(connection_id)
        
        logger.info(f"📡 Connection registered: {connection_id}")
        
        # Step 4: Setup heartbeat to keep connection alive
        async def send_heartbeat():
            """Send periodic heartbeat to keep connection alive"""
            while connection_id in active_connections:
                try:
                    await asyncio.sleep(30)  # Every 30 seconds
                    
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json({
                            "type": "heartbeat",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    else:
                        logger.info(f"WebSocket disconnected, stopping heartbeat")
                        break
                        
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
                    break
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(send_heartbeat())
        
        # Step 5: Send connection confirmation with features
        await websocket.send_json({
            "type": "connection_established",
            "workflow_id": workflow_id,
            "connection_id": connection_id,
            "features": {
                "checkpoints": True,
                "agent_messages": True,
                "human_interaction": True,
                "heartbeat": True,
                "real_time_updates": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Step 6: Register with CAMEL bridge for agent messages
        if camel_bridge:
            # This allows the bridge to send agent messages to this connection
            def agent_message_handler(message: Dict[str, Any]):
                """Handler for agent messages from CAMEL bridge"""
                asyncio.create_task(websocket.send_json(message))
            
            # Register handler with bridge (implementation depends on bridge)
            if hasattr(camel_bridge, 'register_workflow_handler'):
                camel_bridge.register_workflow_handler(workflow_id, agent_message_handler)
        
        # Step 7: Send initial workflow status
        if workflow_service:
            try:
                status = await workflow_service.get_workflow_status(workflow_id)
                if status:
                    await websocket.send_json({
                        "type": "workflow_status",
                        "status": status,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            except Exception as e:
                logger.warning(f"Could not get initial status: {e}")
        
        # Step 8: Notify that connection is ready for messages
        await websocket.send_json({
            "type": "workflow_connection_confirmed",
            "status": "connected",
            "message": "Workflow service connected successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"🎯 Entering message loop for workflow {workflow_id}")
        
        # Step 9: Main message handling loop
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                
                if message:
                    try:
                        data = json.loads(message)
                        
                        # Handle the message
                        await handle_websocket_message(
                            workflow_id=workflow_id,
                            data=data,
                            websocket=websocket,
                            connection_id=connection_id
                        )
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON received: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid JSON format",
                            "details": str(e),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        
            except WebSocketDisconnect as e:
                logger.info(f"WebSocket disconnected: {workflow_id}, code={e.code}")
                break
                
            except asyncio.CancelledError:
                logger.info(f"WebSocket task cancelled: {workflow_id}")
                break
                
            except Exception as e:
                logger.error(f"Error in message loop: {e}", exc_info=True)
                
                # Try to notify client
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Internal server error",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except:
                    pass
                
                # Continue loop unless critical error
                if "closed" in str(e).lower():
                    break
    
    except Exception as e:
        logger.error(f"WebSocket setup error: {e}", exc_info=True)
        
    finally:
        # Cleanup
        logger.info(f"🧹 Cleaning up connection for workflow {workflow_id}")
        
        # Cancel heartbeat
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Remove from tracking
        if connection_id:
            active_connections.pop(connection_id, None)
            workflow_connections[workflow_id].discard(connection_id)
            
            # Unregister from CAMEL bridge
            if camel_bridge and hasattr(camel_bridge, 'unregister_workflow_handler'):
                camel_bridge.unregister_workflow_handler(workflow_id)
        
        # Close WebSocket if still open
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1000, reason="Connection closed")
        except:
            pass
        
        logger.info(f"✅ WebSocket fully closed for workflow {workflow_id}")


@router.websocket("/api/v1/ws/chats/{chat_id}")
async def chat_websocket(
    websocket: WebSocket,
    chat_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time chat updates.
    """
    connection_id = None
    heartbeat_task = None
    
    try:
        # Accept connection
        await websocket.accept()
        await asyncio.sleep(0.5)
        
        # Generate connection ID
        connection_id = f"chat_{chat_id}_{uuid.uuid4().hex[:8]}"
        
        # Track connection
        active_connections[connection_id] = {
            'websocket': websocket,
            'type': 'chat',
            'chat_id': chat_id,
            'connected_at': datetime.now(timezone.utc)
        }
        
        chat_connections[chat_id].add(connection_id)
        
        # Heartbeat
        async def send_heartbeat():
            while connection_id in active_connections:
                try:
                    await asyncio.sleep(30)
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json({
                            "type": "heartbeat",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    else:
                        break
                except:
                    break
        
        heartbeat_task = asyncio.create_task(send_heartbeat())
        
        # Send confirmation
        await websocket.send_json({
            "type": "connection_established",
            "chat_id": chat_id,
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Message loop
        while True:
            try:
                message = await websocket.receive_text()
                
                if message:
                    data = json.loads(message)
                    
                    if data.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    
                    # Handle other chat messages as needed
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Chat WebSocket error: {e}")
                break
    
    finally:
        # Cleanup
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except:
                pass
        
        if connection_id:
            active_connections.pop(connection_id, None)
            chat_connections[chat_id].discard(connection_id)
        
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except:
            pass


@router.get("/api/v1/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "status": "operational",
        "connections": {
            "total": len(active_connections),
            "workflows": sum(1 for c in active_connections.values() if c.get('type') == 'workflow'),
            "chats": sum(1 for c in active_connections.values() if c.get('type') == 'chat'),
            "by_workflow": {wid: len(conns) for wid, conns in workflow_connections.items() if conns},
            "by_chat": {cid: len(conns) for cid, conns in chat_connections.items() if conns}
        },
        "services": {
            "camel_bridge": "connected" if camel_bridge else "disconnected",
            "workflow_service": "connected" if workflow_service else "disconnected",
            "checkpoint_manager": "connected" if checkpoint_manager else "disconnected"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Helper function to broadcast agent messages
async def broadcast_agent_message(workflow_id: str, agent_message: Dict[str, Any]):
    """
    Broadcast an agent message to all workflow connections.
    This is called by the CAMEL bridge when agents produce output.
    """
    # Ensure message has required fields
    message = {
        "type": "agent_message",
        "workflow_id": workflow_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **agent_message
    }
    
    await broadcast_to_workflow(workflow_id, message)


# Export for use by other modules
__all__ = [
    'router',
    'broadcast_agent_message',
    'broadcast_to_workflow'
]