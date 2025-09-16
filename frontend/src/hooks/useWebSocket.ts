/**
 * WebSocket Hook for real-time communication
 * Manages WebSocket connections and message handling
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

  const connect = useCallback(() => {
    // Get the auth token
    const token = localStorage.getItem('spinscribe_token');
    
    // Build the WebSocket URL with token as query parameter
    const baseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    const wsUrl = `${baseUrl}${endpoint}${token ? `?token=${token}` : ''}`;
    
    console.log(`🔌 Attempting WebSocket connection to: ${endpoint}`);
    
    try {
      ws.current = new WebSocket(wsUrl);
      setConnectionStatus('connecting');

      ws.current.onopen = () => {
        console.log(`✅ WebSocket connected to ${endpoint}`);
        setConnectionStatus('connected');
        reconnectAttempts.current = 0; // Reset reconnect counter
        
        // Don't send ping immediately - let the server send connection confirmation first
        // The server will send us a connection_established message
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
              break;
            case 'checkpoint_required':
              console.log('🔔 Checkpoint approval required:', data);
              break;
            case 'agent_communication':
              console.log('🤖 Agent message:', data);
              break;
            case 'workflow_update':
              console.log('📊 Workflow update:', data);
              break;
            case 'heartbeat':
              // Respond to heartbeat with pong
              sendMessage({ type: 'pong' });
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
        setConnectionStatus('disconnected');
      };

      ws.current.onclose = (event) => {
        console.log(`🔌 WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason}`);
        setConnectionStatus('disconnected');
        
        // Only reconnect if we haven't exceeded max attempts and it wasn't a normal closure
        if (reconnectAttempts.current < maxReconnectAttempts && event.code !== 1000) {
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
      setConnectionStatus('disconnected');
    }
  }, [endpoint]);

  const sendMessage = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log('📤 Sending WebSocket message:', message);
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('⚠️ WebSocket is not connected. Current state:', ws.current?.readyState);
    }
  }, []);

  const disconnect = useCallback(() => {
    console.log('🔌 Manually disconnecting WebSocket');
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    if (ws.current) {
      ws.current.close(1000, 'User disconnected');
    }
    reconnectAttempts.current = 0;
  }, []);

  // Keep connection alive with periodic pings
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        sendMessage({ type: 'ping' });
      }
    }, 25000); // Ping every 25 seconds (before the 30s timeout)

    return () => clearInterval(pingInterval);
  }, [sendMessage]);

  useEffect(() => {
    connect();
    
    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    messages,
    sendMessage,
    connectionStatus,
    reconnect: () => {
      reconnectAttempts.current = 0;
      connect();
    },
    disconnect,
    isConnected: connectionStatus === 'connected'
  };
};