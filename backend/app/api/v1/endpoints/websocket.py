"""
Enhanced WebSocket endpoints with detailed debugging
"""
import json
import logging
import asyncio
import traceback
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
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
    """WebSocket endpoint for real-time workflow updates and human interaction."""
    
    logger.info(f"[1] WebSocket connection attempt for workflow {workflow_id}")
    logger.info(f"[1a] WebSocket state before accept: {websocket.client_state if hasattr(websocket, 'client_state') else 'unknown'}")
    logger.info(f"[1b] Client info: {websocket.client if hasattr(websocket, 'client') else 'unknown'}")
    
    # Accept the connection FIRST, before any other operations
    try:
        await websocket.accept()
        logger.info(f"[2] WebSocket accepted for workflow {workflow_id}")
        logger.info(f"[2a] WebSocket state after accept: {websocket.client_state if hasattr(websocket, 'client_state') else 'unknown'}")
    except Exception as e:
        logger.error(f"[2-ERROR] Failed to accept WebSocket: {e}")
        logger.error(f"[2-ERROR] Traceback: {traceback.format_exc()}")
        return
    
    # Add small delay to ensure client is ready
    await asyncio.sleep(0.1)
    
    if not websocket_manager:
        logger.error("[3] WebSocket manager not available")
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return
    
    connection_id = None
    try:
        # Now register with manager (WITHOUT calling accept again)
        logger.info(f"[4] Registering connection with manager")
        connection_id = await websocket_manager.connect_accepted(
            websocket=websocket,
            connection_type="workflow",
            resource_id=workflow_id,
            user_id="anonymous"
        )
        
        logger.info(f"[5] Connection registered with ID: {connection_id}")
        
        # Check WebSocket state before sending
        if hasattr(websocket, 'client_state'):
            logger.info(f"[5a] WebSocket state before send: {websocket.client_state}")
        if hasattr(websocket, 'application_state'):
            logger.info(f"[5b] WebSocket app state: {websocket.application_state}")
        
        # Send connection confirmation with detailed error handling
        try:
            # Check if WebSocket is still open
            if hasattr(websocket, 'client_state') and websocket.client_state != WebSocketState.CONNECTED:
                logger.error(f"[5-ERROR] WebSocket not in CONNECTED state: {websocket.client_state}")
                raise Exception(f"WebSocket not connected: {websocket.client_state}")
            
            confirmation_msg = {
                "type": "connection_established",
                "workflow_id": workflow_id,
                "connection_id": connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"[5c] Attempting to send: {confirmation_msg}")
            await websocket.send_json(confirmation_msg)
            logger.info(f"[6] Sent connection confirmation for {workflow_id}")
            
        except WebSocketDisconnect as e:
            logger.error(f"[5-ERROR] WebSocket disconnected during send: code={e.code}, reason={e.reason}")
            raise
        except ConnectionError as e:
            logger.error(f"[5-ERROR] Connection error during send: {e}")
            logger.error(f"[5-ERROR] Connection type: {type(e)}")
            raise
        except Exception as e:
            logger.error(f"[5-ERROR] Failed to send connection confirmation: {e}")
            logger.error(f"[5-ERROR] Exception type: {type(e).__name__}")
            logger.error(f"[5-ERROR] Exception details: {str(e)}")
            logger.error(f"[5-ERROR] Traceback: {traceback.format_exc()}")
            raise
        
        # Get initial workflow status if available
        if workflow_service:
            try:
                logger.info(f"[7] Getting workflow status for {workflow_id}")
                workflow_status = await workflow_service.get_workflow_status(workflow_id)
                if workflow_status:
                    await websocket.send_json({
                        "type": "workflow_status",
                        "status": workflow_status,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    logger.info(f"[8] Sent workflow status for {workflow_id}")
            except Exception as e:
                logger.warning(f"[7-WARNING] Failed to get initial workflow status: {e}")
        
        logger.info(f"[9] Entering main loop for {workflow_id}")
        
        # Main message loop
        while True:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout
                )
                logger.debug(f"[10] Received message from client: {message[:100] if message else 'empty'}")
                
                # Parse and handle message
                try:
                    data = json.loads(message)
                    await handle_websocket_message(workflow_id, data, websocket)
                except json.JSONDecodeError as e:
                    logger.warning(f"[10-WARNING] Invalid JSON: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                    
            except asyncio.TimeoutError:
                # Send heartbeat on timeout to keep connection alive
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    logger.debug(f"[11] Sent heartbeat for {workflow_id}")
                except Exception as e:
                    logger.error(f"[11-ERROR] Failed to send heartbeat: {e}")
                    break  # Connection is dead
                    
            except WebSocketDisconnect as e:
                logger.info(f"[12] WebSocket disconnected for workflow {workflow_id}: code={e.code}, reason={e.reason}")
                break
                
            except Exception as e:
                logger.error(f"[13-ERROR] Unexpected error in WebSocket loop: {e}")
                logger.error(f"[13-ERROR] Traceback: {traceback.format_exc()}")
                break
    
    except Exception as e:
        logger.error(f"[14-ERROR] WebSocket connection error for workflow {workflow_id}: {e}")
        logger.error(f"[14-ERROR] Exception type: {type(e).__name__}")
        logger.error(f"[14-ERROR] Traceback: {traceback.format_exc()}")
    
    finally:
        # Clean disconnect
        if connection_id and websocket_manager:
            logger.info(f"[15] Cleaning up connection {connection_id}")
            try:
                await websocket_manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"[15-ERROR] Error during cleanup: {e}")
        logger.info(f"[16] WebSocket connection closed for workflow {workflow_id}")


@router.websocket("/chats/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: str):
    """WebSocket endpoint for real-time chat updates."""
    
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return
    
    connection_id = None
    try:
        # Connect and register with manager
        connection_id = await websocket_manager.connect(
            websocket=websocket,
            connection_type="chat",
            resource_id=chat_id,
            user_id="anonymous"
        )
        
        logger.info(f"WebSocket connected for chat {chat_id}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "chat_id": chat_id,
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep connection alive
        while True:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Parse and handle message
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
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except:
                    break
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for chat {chat_id}")
                break
                
            except Exception as e:
                logger.error(f"Error in chat WebSocket: {e}")
                break
    
    except Exception as e:
        logger.error(f"Chat WebSocket connection error for {chat_id}: {e}")
        
    finally:
        if connection_id and websocket_manager:
            await websocket_manager.disconnect(websocket)
        logger.info(f"Chat WebSocket connection closed for chat {chat_id}")


@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    if not websocket_manager:
        return {
            "status": "unavailable",
            "message": "WebSocket manager not initialized"
        }
    
    stats = await websocket_manager.get_connection_stats()
    return {
        "status": "operational",
        "connections": stats,
        "camel_bridge": "connected" if camel_bridge else "not_connected",
        "workflow_service": "connected" if workflow_service else "not_connected",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }