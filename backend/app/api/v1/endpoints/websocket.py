"""
Enhanced WebSocket endpoints for real-time workflow communication
FIXED: Properly handles authentication, agent messages, checkpoints, and human interactions
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

# Track pending checkpoints per workflow
pending_checkpoints: Dict[str, str] = {}

# Import with error handling
try:
    from app.core.websocket_manager import websocket_manager
    # FIX 1: Import from the correct auth module
    from app.dependencies.auth import get_websocket_user
    from app.core.database import get_db
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
    get_websocket_user = None
    get_db = None


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
    FIXED: Properly unblocks workflow execution and handles open-ended feedback.
    """
    try:
        logger.info(f"Processing checkpoint {decision} for {checkpoint_id}")
        
        # Store pending checkpoint for this workflow
        if decision not in ['approve', 'reject']:
            # If not a clear decision, treat as revision request
            decision = "revise"
        
        # Clear from pending if it exists
        if workflow_id in pending_checkpoints:
            if pending_checkpoints[workflow_id] == checkpoint_id:
                del pending_checkpoints[workflow_id]
        
        # Process the checkpoint response
        if checkpoint_manager:
            # Record the response in checkpoint manager
            approved = decision == 'approve'
            checkpoint_manager.submit_response(
                checkpoint_id=checkpoint_id,
                reviewer_id="user",  # Could be from token if available
                decision=decision,
                feedback=feedback  # Full open-ended feedback
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
            
            logger.info(f"✅ Checkpoint {checkpoint_id} {decision}d with feedback: {feedback[:100]}...")
            
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


async def safe_send_json(websocket: WebSocket, data: dict) -> bool:
    """Safely send JSON data to websocket, checking connection state first."""
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(data)
            return True
        else:
            logger.debug(f"WebSocket not connected, skipping message: {data.get('type', 'unknown')}")
            return False
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected during send")
        return False
    except Exception as e:
        logger.error(f"Error sending to WebSocket: {e}")
        return False


async def handle_websocket_message(
    workflow_id: str,
    data: Dict[Any, Any],
    websocket: WebSocket,
    connection_id: str
):
    """
    Handle incoming WebSocket messages for workflows.
    FIXED: Properly handles all message types including open-ended user feedback.
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
            feedback = data.get("feedback", "")
            
            # Parse decision from feedback if not explicitly provided
            decision = data.get("decision")
            if not decision and feedback:
                # Infer decision from feedback content
                feedback_lower = feedback.lower()
                if any(word in feedback_lower for word in ["approve", "looks good", "accept", "yes", "ok", "lgtm"]):
                    decision = "approve"
                elif any(word in feedback_lower for word in ["reject", "no", "cancel", "stop"]):
                    decision = "reject"
                else:
                    decision = "revise"  # Default for open-ended feedback
            
            if checkpoint_id:
                await handle_checkpoint_response(
                    workflow_id=workflow_id,
                    checkpoint_id=checkpoint_id,
                    decision=decision or "revise",
                    feedback=feedback,
                    websocket=websocket
                )
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid checkpoint response: missing checkpoint_id",
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
            
        elif message_type == "user_message":
            # Handle user messages that might be checkpoint feedback
            user_content = data.get("content", "").strip()
            
            # Check if there's a pending checkpoint for this workflow
            if workflow_id in pending_checkpoints:
                checkpoint_id = pending_checkpoints[workflow_id]
                
                # Parse user intent from message - more sophisticated parsing
                decision = "revise"  # Default to revision request
                content_lower = user_content.lower()
                
                # Check for approval patterns
                if any(word in content_lower for word in ["approve", "looks good", "accept", "yes", "ok", "lgtm", "perfect", "great"]):
                    decision = "approve"
                # Check for rejection patterns
                elif any(word in content_lower for word in ["reject", "no", "cancel", "stop", "wrong"]):
                    decision = "reject"
                # Everything else is treated as revision feedback
                else:
                    decision = "revise"
                
                # Submit to checkpoint manager with full feedback
                if checkpoint_manager:
                    checkpoint_manager.submit_response(
                        checkpoint_id=checkpoint_id,
                        reviewer_id=connection_id,  # Use connection_id as reviewer
                        decision=decision,
                        feedback=user_content  # Full user message as feedback
                    )
                    
                    # Clear pending checkpoint
                    del pending_checkpoints[workflow_id]
                    
                    # Broadcast resolution to all connections
                    await broadcast_to_workflow(workflow_id, {
                        "type": "checkpoint_resolved",
                        "checkpoint_id": checkpoint_id,
                        "decision": decision,
                        "feedback": user_content,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
                    # Send confirmation to sender
                    await websocket.send_json({
                        "type": "checkpoint_response_received",
                        "checkpoint_id": checkpoint_id,
                        "decision": decision,
                        "feedback": user_content,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
                    logger.info(f"✅ User message processed as checkpoint feedback for {checkpoint_id}: {decision}")
                else:
                    logger.warning("Checkpoint manager not available for user message")
            else:
                # Regular user message - forward to workflow if needed
                logger.info(f"Regular user message (no pending checkpoint): {user_content[:50]}...")
                
        elif message_type == "checkpoint_acknowledged":
            # Frontend acknowledging checkpoint receipt
            checkpoint_id = data.get("checkpoint_id")
            if checkpoint_id and workflow_id:
                pending_checkpoints[workflow_id] = checkpoint_id
                logger.info(f"✅ Checkpoint {checkpoint_id} acknowledged for workflow {workflow_id}")
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": f"Error processing message: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


# FIX 2: Remove the /api/v1 prefix - it's added by the router
@router.websocket("/workflows/{workflow_id}")
async def workflow_websocket(
    websocket: WebSocket,
    workflow_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time workflow updates.
    FIXED: Checks connection state before sending to prevent errors.
    """
    
    connection_id = None
    heartbeat_task = None
    
    try:
        # Accept WebSocket connection
        await websocket.accept()
        logger.info(f"✅ WebSocket accepted for workflow {workflow_id}")
        
        # Generate connection ID immediately
        connection_id = f"workflow_{workflow_id}_{uuid.uuid4().hex[:8]}"
        
        # Store connection info
        active_connections[connection_id] = {
            'websocket': websocket,
            'type': 'workflow',
            'workflow_id': workflow_id,
            'user': None,
            'connected_at': datetime.now(timezone.utc)
        }
        
        # Track workflow connections
        workflow_connections[workflow_id].add(connection_id)
        
        # Verify authentication if token provided
        user = None
        if token:
            try:
                if get_db and get_websocket_user:
                    async for db in get_db():
                        user = await get_websocket_user(token, db)
                        break
                    
                    if not user:
                        await safe_send_json(websocket, {
                            "type": "error",
                            "message": "Invalid or expired token",
                            "code": 4001
                        })
                        await websocket.close(code=4001, reason="Invalid token")
                        return
                    
                    # Update connection with user info
                    active_connections[connection_id]['user'] = user
                    logger.info(f"✅ Authenticated user: {user.email if hasattr(user, 'email') else user}")
                else:
                    logger.warning("Auth dependencies not available, continuing without auth")
                    
            except Exception as e:
                logger.warning(f"Token verification failed: {e}")
        
        logger.info(f"📡 Connection registered: {connection_id}")
        
        # Setup heartbeat to keep connection alive
        async def send_heartbeat():
            """Send periodic heartbeat to keep connection alive"""
            while connection_id in active_connections:
                try:
                    await asyncio.sleep(30)  # Every 30 seconds
                    
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await safe_send_json(websocket, {
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
        
        # Send connection confirmation with features
        await safe_send_json(websocket, {
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
        
        # Check for any pending checkpoints for this workflow
        if checkpoint_manager:
            pending = checkpoint_manager.get_pending_checkpoints()
            for checkpoint in pending:
                if checkpoint.metadata and checkpoint.metadata.get('workflow_id') == workflow_id:
                    pending_checkpoints[workflow_id] = checkpoint.checkpoint_id
                    logger.info(f"Found existing pending checkpoint: {checkpoint.checkpoint_id}")
                    
                    # Notify frontend about pending checkpoint
                    await safe_send_json(websocket, {
                        "type": "checkpoint_required",
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "title": checkpoint.title,
                        "description": checkpoint.description,
                        "content_preview": checkpoint.content[:500] if checkpoint.content else "",
                        "full_content": checkpoint.content,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    break
        
        # Register with CAMEL bridge for agent messages
        if camel_bridge:
            # This allows the bridge to send agent messages to this connection
            async def agent_message_handler(message: Dict[str, Any]):
                """Handler for agent messages from CAMEL bridge"""
                await safe_send_json(websocket, message)
            
            # Register handler with bridge (implementation depends on bridge)
            if hasattr(camel_bridge, 'register_workflow_handler'):
                camel_bridge.register_workflow_handler(workflow_id, agent_message_handler)
        
        # Register with websocket_manager if available
        if websocket_manager:
            try:
                if hasattr(websocket_manager, 'connect_accepted'):
                    # Don't call accept again
                    await websocket_manager.connect_accepted(
                        websocket=websocket,
                        connection_type="workflow",
                        resource_id=workflow_id,
                        user_id=str(user.id) if user and hasattr(user, 'id') else "anonymous"
                    )
                logger.info(f"✅ Registered with WebSocket manager")
            except Exception as e:
                logger.warning(f"Could not register with WebSocket manager: {e}")
        
        # Send initial workflow status
        if workflow_service:
            try:
                status = await workflow_service.get_workflow_status(workflow_id)
                if status:
                    await safe_send_json(websocket, {
                        "type": "workflow_status",
                        "status": status,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            except Exception as e:
                logger.warning(f"Could not get initial status: {e}")
        
        # Notify that connection is ready for messages
        await safe_send_json(websocket, {
            "type": "workflow_connection_confirmed",
            "status": "connected",
            "message": "Workflow service connected successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"🎯 Entering message loop for workflow {workflow_id}")
        
        # Main message handling loop
        while True:
            try:
                # Check if still connected before receiving
                if websocket.client_state != WebSocketState.CONNECTED:
                    logger.info(f"WebSocket no longer connected for {workflow_id}")
                    break
                
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
                        await safe_send_json(websocket, {
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
                await safe_send_json(websocket, {
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Continue loop unless critical error
                if "closed" in str(e).lower():
                    break
    
    except Exception as e:
        logger.error(f"WebSocket setup error: {e}", exc_info=True)
        
    finally:
        # Cleanup
        logger.info(f"🧹 Cleaning up connection for workflow {workflow_id}")
        
        # Clear any pending checkpoints for this workflow
        if workflow_id in pending_checkpoints:
            logger.info(f"Clearing pending checkpoint for workflow {workflow_id}")
            del pending_checkpoints[workflow_id]
        
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
        
        # Unregister from websocket_manager
        if websocket_manager and hasattr(websocket_manager, 'disconnect'):
            try:
                await websocket_manager.disconnect(websocket)
            except Exception as e:
                logger.debug(f"Error during manager disconnect: {e}")
        
        logger.info(f"✅ WebSocket fully closed for workflow {workflow_id}")

# FIX 5: Remove /api/v1 prefix from chat endpoint
@router.websocket("/chats/{chat_id}")
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
        # Accept connection first
        await websocket.accept()
        await asyncio.sleep(0.5)
        
        # Verify auth if token provided (same pattern as workflow)
        user = None
        if token:
            try:
                if get_db and get_websocket_user:
                    async for db in get_db():
                        user = await get_websocket_user(token, db)
                        break
                    
                    if not user:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid or expired token",
                            "code": 4001
                        })
                        await websocket.close(code=4001, reason="Invalid token")
                        return
            except Exception as e:
                logger.warning(f"Chat token verification failed: {e}")
        
        # Generate connection ID
        connection_id = f"chat_{chat_id}_{uuid.uuid4().hex[:8]}"
        
        # Track connection
        active_connections[connection_id] = {
            'websocket': websocket,
            'type': 'chat',
            'chat_id': chat_id,
            'user': user,
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


# FIX 6: Remove /api/v1 prefix from stats endpoint
@router.get("/stats")
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
            "checkpoint_manager": "connected" if checkpoint_manager else "disconnected",
            "get_websocket_user": "available" if get_websocket_user else "unavailable"
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