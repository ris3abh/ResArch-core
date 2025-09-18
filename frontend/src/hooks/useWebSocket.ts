/**
 * WebSocket Hook for real-time communication
 * Manages WebSocket connections and message handling with improved error handling
 */

import { useEffect, useState, useRef, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export const useWebSocket = (endpoint: string) => {
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const pingInterval = useRef<NodeJS.Timeout | null>(null);
  
  // Connection state tracking to prevent race conditions
  const isConnecting = useRef(false);
  const connectionEstablished = useRef(false);
  const intentionalDisconnect = useRef(false);

  const connect = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (isConnecting.current) {
      console.log('⏳ Connection already in progress, skipping...');
      return;
    }
    
    // Check if already connected
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log('✅ Already connected, skipping connection attempt');
      return;
    }
    
    // Clean up existing connection if any
    if (ws.current && (ws.current.readyState === WebSocket.CONNECTING || ws.current.readyState === WebSocket.OPEN)) {
      ws.current.close(1000, 'Creating new connection');
      ws.current = null;
    }
    
    isConnecting.current = true;
    connectionEstablished.current = false;
    
    // Get the auth token
    const token = localStorage.getItem('spinscribe_token');
    
    // Build the WebSocket URL with token as query parameter
    const baseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    const wsUrl = `${baseUrl}${endpoint}${token ? `?token=${token}` : ''}`;
    
    console.log(`🔌 Attempting WebSocket connection to: ${endpoint}`);
    
    try {
      ws.current = new WebSocket(wsUrl);
      setConnectionStatus('connecting');
      
      // Set connection timeout (10 seconds)
      const connectionTimeout = setTimeout(() => {
        if (!connectionEstablished.current) {
          console.error('⏱️ Connection timeout - closing WebSocket');
          if (ws.current) {
            ws.current.close(1006, 'Connection timeout');
          }
        }
      }, 10000);

      ws.current.onopen = async () => {
        console.log(`✅ WebSocket connected to ${endpoint}`);
        
        // Clear connection timeout
        clearTimeout(connectionTimeout);
        
        // CRITICAL: Add delay after connection to ensure client is ready
        // This prevents the immediate disconnection issue (1006 error)
        await new Promise(resolve => setTimeout(resolve, 500));
        
        isConnecting.current = false;
        connectionEstablished.current = true;
        setConnectionStatus('connected');
        reconnectAttempts.current = 0; // Reset reconnect counter
        
        // Send initial ready message after delay
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          try {
            ws.current.send(JSON.stringify({ 
              type: 'client_ready',
              timestamp: Date.now() 
            }));
            console.log('📤 Sent client_ready message');
          } catch (error) {
            console.error('Failed to send initial message:', error);
          }
        }
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 WebSocket message received:', data.type);
          setMessages(prev => [...prev, data]);
          
          // Handle specific message types
          switch (data.type) {
            case 'connection_established':
              console.log('✅ Connection established with server:', data);
              connectionEstablished.current = true;
              break;
            case 'checkpoint_required':
            case 'checkpoint_approval_required':
              console.log('🔔 Checkpoint approval required:', data);
              break;
            case 'agent_communication':
            case 'agent_message':
              console.log('🤖 Agent message:', data);
              break;
            case 'workflow_update':
              console.log('📊 Workflow update:', data);
              break;
            case 'heartbeat':
              // Respond to heartbeat with pong
              if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                ws.current.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
              }
              break;
            case 'pong':
              console.log('🏓 Pong received');
              break;
            default:
              console.log('📨 Other message:', data);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        isConnecting.current = false;
        connectionEstablished.current = false;
        setConnectionStatus('disconnected');
        clearTimeout(connectionTimeout);
      };

      ws.current.onclose = (event) => {
        console.log(`🔌 WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason}`);
        
        isConnecting.current = false;
        connectionEstablished.current = false;
        setConnectionStatus('disconnected');
        clearTimeout(connectionTimeout);
        
        // Handle specific close codes
        if (event.code === 1006) {
          console.error('❌ Abnormal closure (1006) - possible network or server issue');
          
          // Special handling for 1006 errors
          if (!intentionalDisconnect.current) {
            // Immediate reconnect attempt for 1006 errors
            if (reconnectAttempts.current < maxReconnectAttempts) {
              reconnectAttempts.current++;
              const delay = Math.min(500 * Math.pow(2, reconnectAttempts.current - 1), 5000); // Faster backoff for 1006
              
              console.log(`🔄 Handling 1006 error - Reconnecting (${reconnectAttempts.current}/${maxReconnectAttempts}) in ${delay}ms...`);
              reconnectTimeout.current = setTimeout(() => {
                connect();
              }, delay);
            }
          }
        } else if (event.code === 1000 || event.code === 1001) {
          // Normal closure
          console.log('👋 Normal WebSocket closure');
        } else if (!intentionalDisconnect.current && reconnectAttempts.current < maxReconnectAttempts) {
          // Other abnormal closures
          reconnectAttempts.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000); // Exponential backoff
          
          console.log(`🔄 Attempting reconnect ${reconnectAttempts.current}/${maxReconnectAttempts} in ${delay}ms...`);
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          console.error('❌ Max reconnection attempts reached. Please refresh the page.');
        }
      };
    } catch (error) {
      console.error('❌ Failed to create WebSocket connection:', error);
      isConnecting.current = false;
      connectionEstablished.current = false;
      setConnectionStatus('disconnected');
    }
  }, [endpoint]);

  const sendMessage = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN && connectionEstablished.current) {
      console.log('📤 Sending WebSocket message:', message);
      try {
        ws.current.send(JSON.stringify(message));
      } catch (error) {
        console.error('❌ Failed to send message:', error);
        // Trigger reconnection if send fails
        if (ws.current) {
          ws.current.close(1006, 'Send failed');
        }
      }
    } else {
      console.warn('⚠️ WebSocket is not ready. State:', {
        hasWebSocket: !!ws.current,
        readyState: ws.current?.readyState,
        connectionEstablished: connectionEstablished.current
      });
      
      // Queue the message or trigger reconnection
      if (!ws.current || ws.current.readyState === WebSocket.CLOSED) {
        console.log('🔄 Triggering reconnection to send message');
        connect();
      }
    }
  }, [connect]);

  const disconnect = useCallback(() => {
    console.log('🔌 Manually disconnecting WebSocket');
    intentionalDisconnect.current = true;
    isConnecting.current = false;
    connectionEstablished.current = false;
    
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    
    if (pingInterval.current) {
      clearInterval(pingInterval.current);
      pingInterval.current = null;
    }
    
    if (ws.current) {
      ws.current.close(1000, 'User disconnected');
      ws.current = null;
    }
    
    reconnectAttempts.current = 0;
    setConnectionStatus('disconnected');
  }, []);

  const reconnect = useCallback(() => {
    console.log('🔄 Manual reconnection triggered');
    intentionalDisconnect.current = false;
    reconnectAttempts.current = 0;
    isConnecting.current = false;
    connectionEstablished.current = false;
    
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    
    disconnect();
    setTimeout(() => {
      connect();
    }, 100);
  }, [connect, disconnect]);

  // Keep connection alive with periodic pings
  useEffect(() => {
    // Clear existing interval if any
    if (pingInterval.current) {
      clearInterval(pingInterval.current);
    }
    
    pingInterval.current = setInterval(() => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN && connectionEstablished.current) {
        try {
          ws.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
          console.log('💓 Heartbeat ping sent');
        } catch (error) {
          console.error('Failed to send ping:', error);
        }
      }
    }, 25000); // Ping every 25 seconds (before the 30s timeout)

    return () => {
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
        pingInterval.current = null;
      }
    };
  }, [connectionStatus]); // Re-setup when connection status changes

  useEffect(() => {
    intentionalDisconnect.current = false;
    connect();
    
    // Cleanup on unmount
    return () => {
      intentionalDisconnect.current = true;
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    messages,
    sendMessage,
    connectionStatus,
    reconnect,
    disconnect,
    isConnected: connectionStatus === 'connected' && connectionEstablished.current,
    connectionState: {
      isConnecting: isConnecting.current,
      isEstablished: connectionEstablished.current,
      reconnectAttempts: reconnectAttempts.current,
      maxReconnectAttempts
    }
  };
};