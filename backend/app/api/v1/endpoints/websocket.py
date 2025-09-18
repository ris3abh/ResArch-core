"""
Enhanced WebSocket endpoints with detailed debugging and stability fixes
"""
import json
import logging
import asyncio
import traceback
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)
router = APIRouter()

# Import with error handling
try:
    from app.core.websocket_manager import websocket_manager
    from services.workflow.camel_workflow_service import workflow_service
    from services.workflow.camel_websocket_bridge import CAMELWebSocketBridge
    
    # Create a global bridge instance
    camel_bridge = CAMELWebSocketBridge(websocket_manager)
    
    # Connect the workflow service to websocket manager and bridge
    if workflow_service:
        workflow_service.set_websocket_manager(websocket_manager)
        if hasattr(workflow_service, 'set_camel_bridge'):
            workflow_service.set_camel_bridge(camel_bridge)
    
    logger.info("WebSocket manager, workflow service, and CAMEL bridge connected successfully")
    
except ImportError as e:
    logger.error(f"Failed to import websocket dependencies: {e}")
    websocket_manager = None
    workflow_service = None
    camel_bridge = None


async def handle_websocket_message(workflow_id: str, data: Dict[Any, Any], websocket: WebSocket):
    """Handle incoming WebSocket messages for workflows"""
    message_type = data.get("type")
    
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
        
        logger.info(f"Received human response for workflow {workflow_id}, request {request_id}: {response}")
        
        # Send response to CAMEL bridge
        if camel_bridge:
            camel_bridge.handle_human_response(workflow_id, request_id, response)
            
            # Acknowledge receipt
            await websocket.send_json({
                "type": "response_acknowledged",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "CAMEL bridge not available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    elif message_type == "checkpoint_response":
        # Handle checkpoint approval/rejection
        checkpoint_id = data.get("checkpoint_id")
        decision = data.get("decision")  # "approve" or "reject"
        feedback = data.get("feedback", "")
        
        if checkpoint_id and decision:
            logger.info(f"Received checkpoint {decision} for {checkpoint_id}")
            
            if camel_bridge:
                # Forward to bridge for processing
                await camel_bridge.handle_checkpoint_response(
                    workflow_id=workflow_id,
                    checkpoint_id=checkpoint_id,
                    decision=decision,
                    feedback=feedback
                )
                
                await websocket.send_json({
                    "type": "checkpoint_response_acknowledged",
                    "checkpoint_id": checkpoint_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
    
    elif message_type == "get_status":
        # Get current workflow status
        if workflow_service:
            try:
                status = await workflow_service.get_workflow_status(workflow_id)
                await websocket.send_json({
                    "type": "workflow_status",
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Failed to get workflow status: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
    
    elif message_type == "ping":
        # Heartbeat/keepalive
        await websocket.send_json({
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    else:
        logger.warning(f"Unknown message type: {message_type}")
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


@router.websocket("/workflows/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str, token: Optional[str] = Query(None)):
    """
    WebSocket endpoint for real-time workflow updates and human interaction.
    Fixed version with proper connection handling and heartbeat mechanism.
    """
    
    logger.info(f"[1] WebSocket connection attempt for workflow {workflow_id}")
    
    # Initialize connection tracking
    connection_id = None
    heartbeat_task = None
    
    try:
        # Step 1: Accept the WebSocket connection
        await websocket.accept()
        logger.info(f"[2] WebSocket accepted for workflow {workflow_id}")
        
        # Step 2: Critical - Add delay to ensure client is ready
        # This prevents the immediate disconnection issue
        await asyncio.sleep(0.5)  # Increased from 0.1 to 0.5 for stability
        
        # Step 3: Verify WebSocket manager is available
        if not websocket_manager:
            logger.error("[3] WebSocket manager not available")
            await websocket.send_json({
                "type": "error",
                "message": "Server configuration error: WebSocket manager not available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await websocket.close(code=1011, reason="WebSocket manager not available")
            return
        
        # Step 4: Generate connection ID and register with manager
        connection_id = f"workflow_{workflow_id}_{uuid.uuid4().hex[:8]}"
        logger.info(f"[4] Registering connection with ID: {connection_id}")
        
        # Use a different registration method that doesn't conflict
        try:
            # Store connection in manager without calling accept again
            if hasattr(websocket_manager, 'register_connection'):
                await websocket_manager.register_connection(
                    websocket=websocket,
                    connection_id=connection_id,
                    connection_type="workflow",
                    resource_id=workflow_id
                )
            else:
                # Fallback to direct storage if register_connection doesn't exist
                if not hasattr(websocket_manager, '_connections'):
                    websocket_manager._connections = {}
                websocket_manager._connections[connection_id] = {
                    'websocket': websocket,
                    'type': 'workflow',
                    'resource_id': workflow_id,
                    'connected_at': datetime.now(timezone.utc)
                }
        except AttributeError:
            logger.warning("[4] Using fallback connection storage")
        
        logger.info(f"[5] Connection registered: {connection_id}")
        
        # Step 5: Define heartbeat coroutine
        async def send_heartbeat():
            """Send periodic heartbeat to keep connection alive"""
            while True:
                try:
                    await asyncio.sleep(25)  # Send heartbeat every 25 seconds
                    
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json({
                            "type": "heartbeat",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        logger.debug(f"[HB] Heartbeat sent for {workflow_id}")
                    else:
                        logger.warning(f"[HB] WebSocket not connected, stopping heartbeat")
                        break
                        
                except WebSocketDisconnect:
                    logger.info(f"[HB] WebSocket disconnected, stopping heartbeat")
                    break
                except Exception as e:
                    logger.error(f"[HB-ERROR] Heartbeat error: {e}")
                    break
        
        # Step 6: Start heartbeat task
        heartbeat_task = asyncio.create_task(send_heartbeat())
        logger.info(f"[6] Heartbeat task started for {workflow_id}")
        
        # Step 7: Send connection confirmation
        try:
            confirmation_msg = {
                "type": "connection_established",
                "workflow_id": workflow_id,
                "connection_id": connection_id,
                "features": {
                    "human_interaction": True,
                    "checkpoints": True,
                    "agent_messages": True,
                    "heartbeat": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send_json(confirmation_msg)
            logger.info(f"[7] Sent connection confirmation for {workflow_id}")
            
        except Exception as e:
            logger.error(f"[7-ERROR] Failed to send confirmation: {e}")
            raise
        
        # Step 8: Send initial workflow status if available
        if workflow_service:
            try:
                await asyncio.sleep(0.1)  # Small delay before status check
                workflow_status = await workflow_service.get_workflow_status(workflow_id)
                
                if workflow_status:
                    await websocket.send_json({
                        "type": "workflow_status",
                        "status": workflow_status,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    logger.info(f"[8] Sent initial workflow status for {workflow_id}")
                    
            except Exception as e:
                logger.warning(f"[8-WARNING] Could not get initial status: {e}")
                # Don't fail connection if status is unavailable
        
        # Step 9: Link workflow to CAMEL bridge if available
        if camel_bridge and hasattr(camel_bridge, 'link_workflow_websocket'):
            try:
                camel_bridge.link_workflow_websocket(workflow_id, websocket)
                logger.info(f"[9] Linked workflow {workflow_id} to CAMEL bridge")
            except Exception as e:
                logger.warning(f"[9-WARNING] Could not link to CAMEL bridge: {e}")
        
        logger.info(f"[10] Entering main message loop for {workflow_id}")
        
        # Step 10: Main message handling loop
        while True:
            try:
                # Use receive_text with no timeout to avoid unnecessary timeouts
                # The heartbeat task handles keeping the connection alive
                message = await websocket.receive_text()
                
                if message:
                    logger.debug(f"[11] Received message from client: {message[:200]}")
                    
                    try:
                        data = json.loads(message)
                        await handle_websocket_message(workflow_id, data, websocket)
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"[11-WARNING] Invalid JSON: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid JSON format",
                            "details": str(e),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        
            except WebSocketDisconnect as e:
                logger.info(f"[12] WebSocket disconnected for workflow {workflow_id}: code={e.code}, reason={e.reason}")
                break
                
            except asyncio.CancelledError:
                logger.info(f"[13] WebSocket task cancelled for {workflow_id}")
                break
                
            except Exception as e:
                logger.error(f"[14-ERROR] Unexpected error in message loop: {e}")
                logger.error(f"[14-ERROR] Traceback: {traceback.format_exc()}")
                
                # Try to send error to client
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Internal server error",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except:
                    pass
                    
                break
    
    except Exception as e:
        logger.error(f"[15-ERROR] WebSocket setup error for workflow {workflow_id}: {e}")
        logger.error(f"[15-ERROR] Type: {type(e).__name__}")
        logger.error(f"[15-ERROR] Traceback: {traceback.format_exc()}")
        
    finally:
        # Step 11: Cleanup
        logger.info(f"[16] Starting cleanup for workflow {workflow_id}")
        
        # Cancel heartbeat task
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info(f"[17] Heartbeat task cancelled for {workflow_id}")
        
        # Disconnect from manager
        if connection_id and websocket_manager:
            try:
                if hasattr(websocket_manager, 'unregister_connection'):
                    await websocket_manager.unregister_connection(connection_id)
                elif hasattr(websocket_manager, '_connections'):
                    websocket_manager._connections.pop(connection_id, None)
                else:
                    await websocket_manager.disconnect(websocket)
                    
            except Exception as e:
                logger.error(f"[18-ERROR] Error during cleanup: {e}")
        
        # Ensure WebSocket is closed
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1000, reason="Connection closed")
        except:
            pass
            
        logger.info(f"[19] WebSocket connection fully closed for workflow {workflow_id}")


@router.websocket("/chats/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: str, token: Optional[str] = Query(None)):
    """
    WebSocket endpoint for real-time chat updates.
    Fixed version with proper connection handling.
    """
    
    connection_id = None
    heartbeat_task = None
    
    try:
        # Accept connection first
        await websocket.accept()
        await asyncio.sleep(0.5)  # Ensure client is ready
        
        if not websocket_manager:
            await websocket.send_json({
                "type": "error", 
                "message": "WebSocket manager not available"
            })
            await websocket.close(code=1011, reason="WebSocket manager not available")
            return
        
        # Generate connection ID
        connection_id = f"chat_{chat_id}_{uuid.uuid4().hex[:8]}"
        
        # Register connection
        if hasattr(websocket_manager, 'register_connection'):
            await websocket_manager.register_connection(
                websocket=websocket,
                connection_id=connection_id,
                connection_type="chat",
                resource_id=chat_id
            )
        
        logger.info(f"WebSocket connected for chat {chat_id}")
        
        # Heartbeat coroutine
        async def send_heartbeat():
            while True:
                try:
                    await asyncio.sleep(25)
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json({
                            "type": "heartbeat",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                except:
                    break
        
        # Start heartbeat
        heartbeat_task = asyncio.create_task(send_heartbeat())
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "chat_id": chat_id,
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Main message loop
        while True:
            try:
                message = await websocket.receive_text()
                
                try:
                    data = json.loads(message)
                    
                    if data.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    else:
                        # Handle other chat messages
                        pass
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from chat client: {message[:100]}")
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for chat {chat_id}")
                break
                
            except Exception as e:
                logger.error(f"Error in chat WebSocket: {e}")
                break
    
    except Exception as e:
        logger.error(f"Chat WebSocket connection error for {chat_id}: {e}")
        
    finally:
        # Cleanup
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if connection_id and websocket_manager:
            try:
                if hasattr(websocket_manager, 'unregister_connection'):
                    await websocket_manager.unregister_connection(connection_id)
                else:
                    await websocket_manager.disconnect(websocket)
            except:
                pass
                
        logger.info(f"Chat WebSocket connection closed for chat {chat_id}")


@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    if not websocket_manager:
        return {
            "status": "unavailable",
            "message": "WebSocket manager not initialized"
        }
    
    try:
        if hasattr(websocket_manager, 'get_connection_stats'):
            stats = await websocket_manager.get_connection_stats()
        else:
            # Fallback stats if method doesn't exist
            stats = {
                "total": len(getattr(websocket_manager, '_connections', {})),
                "workflows": sum(1 for c in getattr(websocket_manager, '_connections', {}).values() 
                               if c.get('type') == 'workflow'),
                "chats": sum(1 for c in getattr(websocket_manager, '_connections', {}).values() 
                            if c.get('type') == 'chat')
            }
        
        return {
            "status": "operational",
            "connections": stats,
            "camel_bridge": "connected" if camel_bridge else "not_connected",
            "workflow_service": "connected" if workflow_service else "not_connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }