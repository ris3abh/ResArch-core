// frontend/src/components/workflow/ChatWorkflowInterface.tsx
// PRODUCTION-READY VERSION with all fixes applied
// FIXED: Agent content generation before checkpoints
// FIXED: WebSocket message handling with correct field mapping
// FIXED: Checkpoint modal state management using refs
// FIXED: Message filtering for clean display

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send,
  Bot,
  User,
  Clock,
  CheckCircle,
  AlertCircle,
  Zap,
  MessageCircle,
  Download,
  Brain,
  Copy,
  AlertTriangle,
  WifiOff,
  Wifi,
  RefreshCw,
  Loader2,
  FileText,
  CheckSquare
} from 'lucide-react';
import { apiService, WorkflowResponse, CheckpointResponse } from '../../services/api';
import AgentProgressDisplay from './AgentProgressDisplay';

// Message types based on backend WebSocket message types
interface WorkflowMessage {
  id: string;
  type: 'agent' | 'user' | 'system' | 'checkpoint' | 'human_input';
  sender: string;
  content: string;
  timestamp: string;
  metadata?: {
    agent_type?: string;
    stage?: string;
    workflow_id?: string;
    checkpoint_id?: string;
    request_id?: string;
    question_type?: string;
    options?: string[];
    requires_approval?: boolean;
    message_type?: string;
  };
}

interface HumanInputRequest {
  request_id: string;
  question: string;
  question_type: 'text' | 'yes_no' | 'multiple_choice' | 'approval';
  options?: string[];
  timeout?: number;
}

interface CheckpointData {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'approved' | 'rejected';
  data: any;
  content_preview?: string;
  full_content?: string;
  checkpoint_type?: string;
  priority?: string;
  timeout_seconds?: number;
}

interface ChatWorkflowInterfaceProps {
  workflowId: string;
  projectId: string;
  onWorkflowComplete?: (result: any) => void;
}

const ChatWorkflowInterface: React.FC<ChatWorkflowInterfaceProps> = ({
  workflowId,
  projectId,
  onWorkflowComplete
}) => {
  // State management
  const [messages, setMessages] = useState<WorkflowMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [workflowStatus, setWorkflowStatus] = useState<'running' | 'paused' | 'completed' | 'error'>('running');
  const [currentStage, setCurrentStage] = useState<string>('Initializing');
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [pendingCheckpoint, setPendingCheckpoint] = useState<CheckpointData | null>(null);
  const [pendingHumanInput, setPendingHumanInput] = useState<HumanInputRequest | null>(null);
  const [humanInputResponse, setHumanInputResponse] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [finalContent, setFinalContent] = useState<string>('');
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [workflowData, setWorkflowData] = useState<WorkflowResponse | null>(null);
  const [checkpointFeedback, setCheckpointFeedback] = useState<string>('');
  
  // Refs for stable references
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pendingCheckpointRef = useRef<CheckpointData | null>(null);
  const processedCheckpointIds = useRef<Set<string>>(new Set());
  const processedMessageIds = useRef<Set<string>>(new Set());
  
  // Connection state tracking
  const isConnectingRef = useRef(false);
  const hasInitializedRef = useRef(false);
  const workflowIdRef = useRef(workflowId);
  const maxReconnectAttempts = 5;
  
  // Sync checkpoint ref with state
  useEffect(() => {
    pendingCheckpointRef.current = pendingCheckpoint;
  }, [pendingCheckpoint]);
  
  // Update workflowId ref when prop changes
  useEffect(() => {
    workflowIdRef.current = workflowId;
  }, [workflowId]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Message helpers
  const addSystemMessage = useCallback((content: string) => {
    const messageId = `sys-${Date.now()}-${Math.random()}`;
    
    // Skip duplicate messages
    if (processedMessageIds.current.has(content)) {
      return;
    }
    processedMessageIds.current.add(content);
    
    const message: WorkflowMessage = {
      id: messageId,
      type: 'system',
      content,
      timestamp: new Date().toISOString(),
      sender: 'System'
    };
    setMessages(prev => [...prev, message]);
  }, []);

  const addAgentMessage = useCallback((content: string, agentType?: string, stage?: string) => {
    // Filter out empty, debug, or template messages
    if (!content || content.trim().length < 10) return;
    
    // Skip log messages
    if (content.includes('INFO:') || 
        content.includes('DEBUG:') || 
        content.includes('WARNING:') ||
        content.includes('Token calculation failed') ||
        content.includes('2025-') ||  // Skip timestamps
        content.startsWith('[') ||     // Skip bracketed debug info
        content === 'Multi-agent content creation workflow') {  // Skip template text
      return;
    }
    
    // Create unique ID for deduplication
    const contentKey = `${agentType}-${content.substring(0, 50)}`;
    if (processedMessageIds.current.has(contentKey)) {
      return;
    }
    processedMessageIds.current.add(contentKey);
    
    const message: WorkflowMessage = {
      id: `agent-${Date.now()}-${Math.random()}`,
      type: 'agent',
      content,
      timestamp: new Date().toISOString(),
      sender: agentType || 'AI Agent',
      metadata: {
        agent_type: agentType,
        stage: stage,
        workflow_id: workflowIdRef.current
      }
    };
    setMessages(prev => [...prev, message]);
  }, []);

  // Enhanced WebSocket message handler
  const handleWebSocketMessage = useCallback((data: any) => {
    console.log('📨 WS Message:', { type: data.type, hasContent: !!data.message_content || !!data.content });

    switch (data.type) {
      case 'workflow_output':
        const outputContent = data.content || data.message || '';
        
        // Only show meaningful workflow outputs
        if (outputContent && 
            !outputContent.includes('INFO') && 
            !outputContent.includes('DEBUG') &&
            !outputContent.includes('Token calculation') &&
            outputContent.trim().length > 20) {
          
          if (outputContent.includes('ERROR') || data.stream === 'stderr') {
            addSystemMessage(`⚠️ ${outputContent}`);
          }
        }
        break;

      case 'connection_established':
        setIsConnected(true);
        setReconnectAttempts(0);
        addSystemMessage(`✅ Connected to workflow`);
        // Request initial status
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'get_status' }));
        }
        break;

      case 'workflow_status':
        const status = data.status;
        if (status) {
          setWorkflowStatus(status.status === 'in_progress' ? 'running' : status.status);
          if (status.current_stage) {
            setCurrentStage(status.current_stage);
          }
        }
        break;

      case 'workflow_started':
        setWorkflowStatus('running');
        addSystemMessage('🚀 Workflow started - Agents are generating content...');
        break;

      case 'workflow_stage_update':
        const stage = data.data?.stage || data.stage;
        if (stage) {
          setCurrentStage(stage);
          if (stage === 'agent_processing') {
            addSystemMessage('🤖 Agents are working on your content...');
          } else if (stage === 'checkpoint_approval') {
            addSystemMessage('📋 Content ready for review');
          }
        }
        break;

      case 'agent_message':
      case 'agent_communication':
      case 'agent_output':
        // FIXED: Prioritize message_content field as per backend structure
        const agentContent = 
          data.message_content ||        // Primary field from backend
          data.data?.message_content ||  
          data.data?.content || 
          data.content || 
          data.message ||
          data.data?.message ||
          data.text ||
          '';
          
        const agentType = 
          data.agent_type ||
          data.data?.agent_type || 
          data.data?.role ||
          data.role ||
          data.agent_role ||
          data.sender ||
          data.data?.sender ||
          'Agent';
          
        const messageStage = data.data?.stage || data.stage || currentStage;
        
        // Only add meaningful agent content
        if (agentContent && typeof agentContent === 'string' && agentContent.trim().length > 20) {
          // Skip template/placeholder content
          if (!agentContent.includes('Multi-agent content creation workflow') &&
              !agentContent.includes('INTEGRATION FEATURES:') &&
              !agentContent.includes('======')) {
            
            console.log('✅ Adding agent message:', { agent: agentType, contentLength: agentContent.length });
            addAgentMessage(agentContent, agentType, messageStage);
            
            // Track active agents
            if (agentType && agentType !== 'Agent' && !activeAgents.includes(agentType)) {
              setActiveAgents(prev => [...prev, agentType]);
            }
          }
        }
        break;

      case 'human_input_required':
        const inputRequest: HumanInputRequest = {
          request_id: data.request_id,
          question: data.question,
          question_type: data.question_type || 'text',
          options: data.options,
          timeout: data.timeout
        };
        setPendingHumanInput(inputRequest);
        setWorkflowStatus('paused');
        addSystemMessage(`❓ Input needed: ${data.question}`);
        break;

      case 'checkpoint_approval_required':
      case 'checkpoint_required':
      case 'checkpoint':
        // FIXED: Use unique checkpoint ID tracking to prevent duplicates
        const checkpointId = data.checkpoint_id || data.data?.checkpoint_id || data.id;
        
        if (!checkpointId) {
          console.warn('Checkpoint without ID:', data);
          break;
        }
        
        // Skip if we've already processed this checkpoint
        if (processedCheckpointIds.current.has(checkpointId)) {
          console.log('Skipping duplicate checkpoint:', checkpointId);
          break;
        }
        
        // Skip if we already have a pending checkpoint
        if (pendingCheckpointRef.current) {
          console.log('Already have pending checkpoint, queueing:', checkpointId);
          break;
        }
        
        // Mark as processed
        processedCheckpointIds.current.add(checkpointId);
        
        // Extract actual content from the checkpoint
        const checkpointContent = 
          data.full_content || 
          data.content || 
          data.data?.content ||
          data.content_preview || 
          data.data?.content_preview ||
          '';
        
        // Only create checkpoint if there's actual content (not template)
        if (checkpointContent && checkpointContent.length > 50) {
          const checkpoint: CheckpointData = {
            id: checkpointId,
            title: data.title || data.data?.title || 'Content Review Required',
            description: data.description || data.data?.description || 'Please review the generated content',
            status: 'pending',
            data: data.data || data,
            content_preview: checkpointContent.substring(0, 1000),
            full_content: checkpointContent,
            checkpoint_type: data.checkpoint_type || data.data?.checkpoint_type,
            priority: data.priority || data.data?.priority || 'medium',
            timeout_seconds: data.timeout_seconds || data.data?.timeout_seconds || 7200
          };
          
          // Update both ref and state
          pendingCheckpointRef.current = checkpoint;
          setPendingCheckpoint(checkpoint);
          setWorkflowStatus('paused');
          addSystemMessage(`🔍 Checkpoint: ${checkpoint.title} - Content ready for review`);
        } else {
          console.log('Checkpoint has no meaningful content, skipping');
        }
        break;

      case 'checkpoint_resolved':
        if (pendingCheckpointRef.current && data.checkpoint_id === pendingCheckpointRef.current.id) {
          pendingCheckpointRef.current = null;
          setPendingCheckpoint(null);
          setWorkflowStatus('running');
          const statusText = data.approved ? '✅ Approved' : '❌ Changes requested';
          addSystemMessage(`Checkpoint ${statusText}: ${data.feedback || 'Continuing workflow'}`);
        }
        break;

      case 'checkpoint_reminder':
        if (data.time_remaining_seconds) {
          addSystemMessage(`⏰ Checkpoint will auto-approve in ${Math.round(data.time_remaining_seconds / 60)} minutes`);
        }
        break;

      case 'workflow_completed':
        setWorkflowStatus('completed');
        const content = data.data?.final_content || data.final_content || '';
        if (content) {
          setFinalContent(content);
          addSystemMessage('🎉 Content generation completed successfully!');
        } else {
          addSystemMessage('✅ Workflow completed');
        }
        if (onWorkflowComplete) {
          onWorkflowComplete(data.data || { final_content: content });
        }
        break;

      case 'workflow_error':
        setWorkflowStatus('error');
        const errorMsg = data.data?.error || data.error || data.message || 'Unknown error occurred';
        addSystemMessage(`❌ Error: ${errorMsg}`);
        break;

      case 'workflow_warning':
        addSystemMessage(`⚠️ ${data.message || 'Workflow warning'}`);
        break;

      case 'heartbeat':
        // Respond with pong
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'pong' }));
        }
        break;

      case 'pong':
        // Heartbeat response received
        console.log('💓 Heartbeat OK');
        break;

      case 'workflow_update':
        if (data.status) {
          setWorkflowStatus(data.status === 'in_progress' ? 'running' : data.status);
        }
        if (data.stage) {
          setCurrentStage(data.stage);
        }
        break;

      default:
        // Try to extract content from unknown message types
        if (data.message_content || data.message || data.content || data.text) {
          const content = data.message_content || data.message || data.content || data.text;
          
          // Check if it's agent content
          if ((data.agent_type || data.role || data.sender_type === 'agent') && content.length > 20) {
            addAgentMessage(content, data.agent_type || data.role || 'Agent', data.stage || currentStage);
          }
        }
    }
  }, [addSystemMessage, addAgentMessage, onWorkflowComplete, currentStage, activeAgents]);

  // WebSocket connection with retry logic
  const connectWebSocket = useCallback(() => {
    // Prevent multiple concurrent connections
    if (wsRef.current && (
      wsRef.current.readyState === WebSocket.OPEN || 
      wsRef.current.readyState === WebSocket.CONNECTING
    )) {
      console.log('WebSocket already connected or connecting');
      return;
    }

    if (isConnectingRef.current) {
      console.log('Connection already in progress');
      return;
    }

    isConnectingRef.current = true;

    try {
      setIsReconnecting(true);
      
      // Clean up existing connection
      if (wsRef.current) {
        wsRef.current.close(1000, 'Creating new connection');
        wsRef.current = null;
      }
      
      // Clear existing intervals
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      
      const ws = apiService.createWorkflowWebSocket(workflowIdRef.current);
      wsRef.current = ws;

      ws.onopen = () => {
        isConnectingRef.current = false;
        setIsConnected(true);
        setIsReconnecting(false);
        setReconnectAttempts(0);
        console.log('🔌 Connected to workflow WebSocket');
        
        // Setup heartbeat ping interval
        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000); // Ping every 30 seconds
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        isConnectingRef.current = false;
        setIsConnected(false);
        console.log('❌ WebSocket disconnected:', event.code, event.reason);
        
        // Clear intervals
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        // Implement exponential backoff reconnection
        if (event.code !== 1000 && event.code !== 1001 && reconnectAttempts < maxReconnectAttempts) {
          const nextAttempt = reconnectAttempts + 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
          
          console.log(`Reconnect attempt ${nextAttempt}/${maxReconnectAttempts} in ${delay}ms`);
          addSystemMessage(`⚠️ Connection lost. Reconnecting in ${Math.round(delay / 1000)}s...`);
          
          setReconnectAttempts(nextAttempt);
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, delay);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          setIsReconnecting(false);
          addSystemMessage('❌ Connection lost. Please refresh the page.');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        isConnectingRef.current = false;
        setIsConnected(false);
        setIsReconnecting(false);
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      isConnectingRef.current = false;
      setIsReconnecting(false);
      addSystemMessage('❌ Failed to connect to workflow');
    }
  }, [handleWebSocketMessage, addSystemMessage, reconnectAttempts]);

  // Initialize WebSocket connection
  useEffect(() => {
    const workflowChanged = workflowIdRef.current !== workflowId;
    
    if (workflowChanged) {
      // Clean up existing connection
      if (wsRef.current) {
        wsRef.current.close(1000, 'Workflow changed');
        wsRef.current = null;
      }
      hasInitializedRef.current = false;
      workflowIdRef.current = workflowId;
      // Clear processed IDs for new workflow
      processedCheckpointIds.current.clear();
      processedMessageIds.current.clear();
    }
    
    if (!hasInitializedRef.current) {
      hasInitializedRef.current = true;
      connectWebSocket();
      
      // Load workflow status via API as backup
      apiService.getWorkflowStatus(workflowId)
        .then(workflow => {
          setWorkflowData(workflow);
          if (workflow.current_stage) {
            setCurrentStage(workflow.current_stage);
          }
        })
        .catch(err => console.warn('Failed to load workflow status:', err));
    }

    // Cleanup on unmount
    return () => {
      hasInitializedRef.current = false;
      isConnectingRef.current = false;
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
        wsRef.current = null;
      }
    };
  }, [workflowId, connectWebSocket]);

  // Handle human input response
  const sendHumanResponse = async () => {
    if (!pendingHumanInput || !humanInputResponse.trim()) return;

    try {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'human_response',
          request_id: pendingHumanInput.request_id,
          response: humanInputResponse,
          workflow_id: workflowId
        }));
        
        addSystemMessage(`✅ Response sent: ${humanInputResponse}`);
        setPendingHumanInput(null);
        setHumanInputResponse('');
        setWorkflowStatus('running');
      } else {
        throw new Error('WebSocket not connected');
      }
    } catch (error) {
      console.error('Failed to send human response:', error);
      addSystemMessage('❌ Failed to send response. Please check connection.');
    }
  };

  // Handle multiple choice selection
  const handleMultipleChoiceResponse = (choice: string) => {
    setHumanInputResponse(choice);
    if (wsRef.current?.readyState === WebSocket.OPEN && pendingHumanInput) {
      wsRef.current.send(JSON.stringify({
        type: 'human_response',
        request_id: pendingHumanInput.request_id,
        response: choice,
        workflow_id: workflowId
      }));
      
      addSystemMessage(`✅ Selected: ${choice}`);
      setPendingHumanInput(null);
      setHumanInputResponse('');
      setWorkflowStatus('running');
    }
  };

  // FIXED: Enhanced checkpoint approval with proper WebSocket and API communication
  const handleCheckpointApproval = async (approved: boolean) => {
    if (!pendingCheckpoint) return;

    try {
      const feedback = checkpointFeedback || (approved ? 'Content approved' : 'Changes requested');
      
      // Send via WebSocket for immediate response
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'checkpoint_response',
          checkpoint_id: pendingCheckpoint.id,
          decision: approved ? 'approve' : 'reject',
          feedback: feedback,
          workflow_id: workflowId,
          timestamp: new Date().toISOString()
        }));
      }
      
      // Also send via API for persistence
      if (approved) {
        await apiService.approveCheckpoint(pendingCheckpoint.id, { feedback });
        addSystemMessage(`✅ Checkpoint approved: ${feedback}`);
      } else {
        await apiService.rejectCheckpoint(pendingCheckpoint.id, { feedback });
        addSystemMessage(`❌ Changes requested: ${feedback}`);
      }
      
      // Clear checkpoint state
      pendingCheckpointRef.current = null;
      setPendingCheckpoint(null);
      setCheckpointFeedback('');
      setWorkflowStatus('running');
      
      // Notify workflow to continue
      addSystemMessage('↻ Workflow resuming with your feedback...');
      
    } catch (error) {
      console.error('Failed to respond to checkpoint:', error);
      addSystemMessage('❌ Failed to submit checkpoint response. Retrying...');
      
      // Retry once after delay
      setTimeout(() => handleCheckpointApproval(approved), 2000);
    }
  };

  // Handle manual reconnection
  const handleReconnect = () => {
    setReconnectAttempts(0);
    isConnectingRef.current = false;
    connectWebSocket();
  };

  // Copy content to clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    addSystemMessage('📋 Content copied to clipboard!');
  };

  // Send user message
  const sendUserMessage = async () => {
    if (!inputMessage.trim() || !isConnected) return;

    const userMessage: WorkflowMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      sender: 'You',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'user_message',
        content: userMessage.content,
        workflow_id: workflowId
      }));
    }
  };

  // Agent colors for visual distinction
  const agentColors: { [key: string]: string } = {
    'coordinator': 'from-blue-500 to-blue-600',
    'style_analysis': 'from-purple-500 to-purple-600',
    'content_planning': 'from-indigo-500 to-indigo-600',
    'content_generation': 'from-green-500 to-green-600',
    'editing_qa': 'from-yellow-500 to-yellow-600',
    'Enhanced Style Analysis Agent': 'from-purple-500 to-purple-600',
    'Enhanced Content Planning Agent': 'from-indigo-500 to-indigo-600',
    'Enhanced Content Generation Agent': 'from-green-500 to-green-600',
    'Quality Assurance Agent': 'from-orange-500 to-orange-600',
    'default': 'from-gray-500 to-gray-600'
  };

  return (
    <div className="flex h-[calc(100vh-200px)] gap-6">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-gray-800 rounded-xl">
        {/* Chat Header */}
        <div className="bg-gray-700 rounded-t-xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              {isConnected ? (
                <Wifi className="w-5 h-5 text-green-500" />
              ) : isReconnecting ? (
                <RefreshCw className="w-5 h-5 text-yellow-500 animate-spin" />
              ) : (
                <WifiOff className="w-5 h-5 text-red-500" />
              )}
              <span className="text-sm text-gray-300">
                {isConnected ? 'Connected' : isReconnecting ? 'Reconnecting...' : 'Disconnected'}
              </span>
            </div>
            <div className="h-4 w-px bg-gray-600" />
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${
                workflowStatus === 'running' ? 'bg-green-500 animate-pulse' :
                workflowStatus === 'paused' ? 'bg-yellow-500' :
                workflowStatus === 'completed' ? 'bg-blue-500' :
                'bg-red-500'
              }`} />
              <span className="text-sm text-gray-300 capitalize">{workflowStatus}</span>
            </div>
            <div className="h-4 w-px bg-gray-600" />
            <span className="text-sm text-gray-400">{currentStage}</span>
          </div>
          
          {!isConnected && !isReconnecting && reconnectAttempts >= maxReconnectAttempts && (
            <button
              onClick={handleReconnect}
              className="px-3 py-1 bg-orange-600 text-white text-sm rounded-lg hover:bg-orange-700 transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Reconnect
            </button>
          )}
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <Brain className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">Workflow is initializing...</p>
              <p className="text-sm text-gray-500 mt-2">Agent messages will appear here</p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} mb-3`}
              >
                <div className={`max-w-[70%] ${
                  message.type === 'user' 
                    ? 'bg-gradient-to-r from-orange-500 to-violet-600 text-white' 
                    : message.type === 'system'
                    ? 'bg-gray-700 text-gray-300'
                    : message.type === 'checkpoint'
                    ? 'bg-yellow-900/30 border border-yellow-600/30 text-yellow-300'
                    : message.type === 'agent'
                    ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white'
                    : 'bg-gray-700 text-white'
                } rounded-lg p-4 shadow-lg`}>
                  <div className="flex items-start gap-3">
                    {message.type === 'agent' && (
                      <Bot className="w-5 h-5 mt-1 flex-shrink-0 text-white" />
                    )}
                    {message.type === 'user' && (
                      <User className="w-5 h-5 mt-1 flex-shrink-0" />
                    )}
                    {message.type === 'system' && (
                      <Zap className="w-5 h-5 mt-1 flex-shrink-0" />
                    )}
                    
                    <div className="flex-1">
                      {message.sender && message.sender !== 'System' && (
                        <p className="text-xs font-bold mb-1 text-white/90">
                          {message.sender}
                        </p>
                      )}
                      <p className="whitespace-pre-wrap break-words">{message.content}</p>
                      {message.metadata?.stage && (
                        <p className="text-xs mt-2 opacity-60">
                          Stage: {message.metadata.stage}
                        </p>
                      )}
                      <p className="text-xs mt-2 opacity-60">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Human Input Request UI */}
        {pendingHumanInput && (
          <div className="border-t border-gray-700 p-4 bg-yellow-900/20">
            <div className="mb-3">
              <p className="text-yellow-300 font-medium mb-2 flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                Response Required
              </p>
              <p className="text-gray-300">{pendingHumanInput.question}</p>
            </div>
            
            {pendingHumanInput.question_type === 'yes_no' ? (
              <div className="flex gap-3">
                <button
                  onClick={() => handleMultipleChoiceResponse('yes')}
                  className="flex-1 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Yes
                </button>
                <button
                  onClick={() => handleMultipleChoiceResponse('no')}
                  className="flex-1 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  No
                </button>
              </div>
            ) : pendingHumanInput.question_type === 'multiple_choice' && pendingHumanInput.options ? (
              <div className="space-y-2">
                {pendingHumanInput.options.map((option, index) => (
                  <button
                    key={index}
                    onClick={() => handleMultipleChoiceResponse(option)}
                    className="w-full py-2 px-4 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors text-left"
                  >
                    {option}
                  </button>
                ))}
              </div>
            ) : (
              <div className="flex gap-3">
                <input
                  type="text"
                  value={humanInputResponse}
                  onChange={(e) => setHumanInputResponse(e.target.value)}
                  placeholder="Type your response..."
                  className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
                  onKeyPress={(e) => e.key === 'Enter' && sendHumanResponse()}
                  autoFocus
                />
                <button
                  onClick={sendHumanResponse}
                  disabled={!humanInputResponse.trim()}
                  className="px-6 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Send
                </button>
              </div>
            )}
          </div>
        )}

        {/* Enhanced Checkpoint Modal - FIXED with proper state management */}
        {pendingCheckpoint && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={(e) => e.stopPropagation()} />
            
            <div className="relative min-h-screen flex items-center justify-center p-4">
              <div className="relative bg-gray-800 border border-gray-700 rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden">
                {/* Modal header with gradient */}
                <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <CheckSquare className="w-6 h-6 text-white" />
                      <h2 className="text-xl font-bold text-white">Content Review Checkpoint</h2>
                    </div>
                    {pendingCheckpoint.priority && (
                      <span className={`text-xs px-3 py-1 rounded-full font-semibold ${
                        pendingCheckpoint.priority === 'high' ? 'bg-red-500 text-white' :
                        pendingCheckpoint.priority === 'medium' ? 'bg-yellow-500 text-black' :
                        'bg-green-500 text-white'
                      }`}>
                        {pendingCheckpoint.priority.toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
                
                {/* Modal body with content */}
                <div className="p-6 overflow-y-auto max-h-[55vh]">
                  <div className="mb-6">
                    <h3 className="text-white font-semibold text-lg mb-2">
                      {pendingCheckpoint.title}
                    </h3>
                    <p className="text-gray-300">
                      {pendingCheckpoint.description}
                    </p>
                    
                    <div className="flex flex-wrap gap-3 mt-3">
                      {pendingCheckpoint.checkpoint_type && (
                        <div className="text-sm bg-gray-700 rounded px-3 py-1">
                          <span className="text-gray-400">Type: </span>
                          <span className="text-white">{pendingCheckpoint.checkpoint_type}</span>
                        </div>
                      )}
                      {pendingCheckpoint.timeout_seconds && (
                        <div className="text-sm bg-yellow-900/30 border border-yellow-600/30 rounded px-3 py-1">
                          <span className="text-yellow-400">
                            ⏱️ Auto-approves in {Math.round(pendingCheckpoint.timeout_seconds / 60)} minutes
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Generated content preview */}
                  <div className="mb-6">
                    <h4 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Generated Content:
                    </h4>
                    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 max-h-80 overflow-y-auto">
                      <pre className="text-sm text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                        {pendingCheckpoint.full_content || pendingCheckpoint.content_preview || 'No content available'}
                      </pre>
                    </div>
                  </div>
                  
                  {/* Feedback input */}
                  <div>
                    <label className="text-sm font-semibold text-gray-400 mb-2 block">
                      Feedback (optional):
                    </label>
                    <textarea
                      value={checkpointFeedback}
                      onChange={(e) => setCheckpointFeedback(e.target.value)}
                      placeholder="Add any feedback or requested changes..."
                      className="w-full px-4 py-3 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      rows={3}
                    />
                  </div>
                </div>
                
                {/* Modal footer with action buttons */}
                <div className="border-t border-gray-700 bg-gray-900/50 px-6 py-4">
                  <div className="flex gap-3">
                    <button
                      onClick={() => handleCheckpointApproval(true)}
                      className="flex-1 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 transition-all duration-200 flex items-center justify-center gap-2 font-semibold shadow-lg"
                    >
                      <CheckCircle className="w-5 h-5" />
                      Approve & Continue
                    </button>
                    <button
                      onClick={() => handleCheckpointApproval(false)}
                      className="flex-1 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:from-orange-600 hover:to-red-600 transition-all duration-200 flex items-center justify-center gap-2 font-semibold shadow-lg"
                    >
                      <AlertCircle className="w-5 h-5" />
                      Request Changes
                    </button>
                  </div>
                  
                  {checkpointFeedback && (
                    <p className="text-xs text-gray-400 mt-3 text-center">
                      Your feedback will be sent to the agents for revision
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Regular Input Area */}
        {workflowStatus === 'running' && !pendingHumanInput && !pendingCheckpoint && (
          <div className="border-t border-gray-700 p-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Send a message to the workflow..."
                className="flex-1 px-4 py-3 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
                disabled={!isConnected}
                onKeyPress={(e) => e.key === 'Enter' && sendUserMessage()}
              />
              <button
                onClick={sendUserMessage}
                disabled={!isConnected || !inputMessage.trim()}
                className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Send className="w-5 h-5" />
                Send
              </button>
            </div>
          </div>
        )}

        {/* Completion UI */}
        {workflowStatus === 'completed' && finalContent && (
          <div className="border-t border-gray-700 p-4 bg-green-900/20">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Workflow Completed Successfully!</span>
              </div>
              <button 
                onClick={() => copyToClipboard(finalContent)}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors flex items-center gap-2"
              >
                <Copy className="w-4 h-4" />
                Copy Content
              </button>
            </div>
            
            <div className="bg-gray-800 rounded-lg p-4">
              <h4 className="font-medium text-white mb-2">Final Generated Content:</h4>
              <div className="bg-gray-900 p-3 rounded max-h-60 overflow-y-auto">
                <pre className="text-sm text-gray-300 whitespace-pre-wrap">{finalContent}</pre>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Side Panel */}
      <div className="w-80 space-y-4">
        {/* Agent Progress Display */}
        <AgentProgressDisplay
          currentStage={currentStage}
          activeAgents={activeAgents}
          workflowStatus={workflowStatus}
        />

        {/* Active Agents List */}
        {activeAgents.length > 0 && (
          <div className="bg-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">Active Agents</h3>
            <div className="space-y-2">
              {activeAgents.map(agent => (
                <div key={agent} className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${
                    agentColors[agent] || agentColors.default
                  }`} />
                  <span className="text-sm text-gray-300">{agent}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Workflow Info */}
        {workflowData && (
          <div className="bg-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">Workflow Info</h3>
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-gray-400">Title:</span>
                <p className="text-gray-300">{workflowData.title}</p>
              </div>
              <div>
                <span className="text-gray-400">Type:</span>
                <p className="text-gray-300">{workflowData.content_type}</p>
              </div>
              <div>
                <span className="text-gray-400">Project:</span>
                <p className="text-gray-300">{projectId}</p>
              </div>
              {workflowData.progress !== undefined && (
                <div>
                  <span className="text-gray-400">Progress:</span>
                  <div className="mt-1 bg-gray-700 rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-orange-500 to-violet-600 h-2 rounded-full transition-all"
                      style={{ width: `${workflowData.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Checkpoint Status */}
        {(pendingCheckpoint || processedCheckpointIds.current.size > 0) && (
          <div className="bg-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">Checkpoints</h3>
            <div className="space-y-2 text-sm">
              {pendingCheckpoint && (
                <div className="flex items-center gap-2 text-yellow-400">
                  <AlertCircle className="w-4 h-4" />
                  <span>Review pending</span>
                </div>
              )}
              <div className="text-gray-400">
                Processed: {processedCheckpointIds.current.size}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatWorkflowInterface;