// frontend/src/components/workflow/ChatWorkflowInterface.tsx
// ENHANCED VERSION WITH OPEN-ENDED FEEDBACK SUPPORT

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

// Global WebSocket store to prevent duplicates in StrictMode
const globalWebSockets = new Map<string, WebSocket>();

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
  const mountedRef = useRef(true);
  const cleanupTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Connection state tracking
  const maxReconnectAttempts = 5;
  
  // Sync checkpoint ref with state
  useEffect(() => {
    pendingCheckpointRef.current = pendingCheckpoint;
  }, [pendingCheckpoint]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Message helpers
  const addSystemMessage = useCallback((content: string) => {
    const messageId = `sys-${Date.now()}-${Math.random()}`;
    
    // Skip duplicate messages
    if (processedMessageIds.current.has(content)) {
      console.log('🔄 Skipping duplicate system message:', content.substring(0, 50));
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
    
    console.log('➕ Adding system message:', content);
    setMessages(prev => [...prev, message]);
  }, []);

  const addAgentMessage = useCallback((content: string, agentType?: string, stage?: string) => {
    console.log('🤖 addAgentMessage called:', {
      contentLength: content?.length,
      contentPreview: content?.substring(0, 100),
      agentType,
      stage
    });
    
    // Log why messages might be filtered
    if (!content) {
      console.log('❌ Rejected: No content');
      return;
    }
    
    if (content.trim().length < 10) {
      console.log('❌ Rejected: Content too short (<10 chars):', content);
      return;
    }
    
    // Check for filtered patterns
    const filterPatterns = [
      'INFO:', 'DEBUG:', 'WARNING:', 'Token calculation failed',
      'Multi-agent content creation workflow'
    ];
    
    for (const pattern of filterPatterns) {
      if (content.includes(pattern)) {
        console.log(`❌ Rejected: Contains filtered pattern "${pattern}"`);
        return;
      }
    }
    
    if (content.startsWith('[')) {
      console.log('❌ Rejected: Starts with bracket (debug info)');
      return;
    }
    
    // Create unique ID for deduplication
    const contentKey = `${agentType}-${content.substring(0, 50)}`;
    if (processedMessageIds.current.has(contentKey)) {
      console.log('❌ Rejected: Duplicate message');
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
        workflow_id: workflowId
      }
    };
    
    console.log('✅ ADDING AGENT MESSAGE:', {
      sender: message.sender,
      contentLength: content.length,
      stage
    });
    
    setMessages(prev => [...prev, message]);
  }, [workflowId]);

  // Enhanced WebSocket message handler with extensive logging
  const handleWebSocketMessage = useCallback((data: any) => {
    if (!mountedRef.current) return;
    
    console.log('📨 FULL WebSocket Message:', {
      type: data.type,
      hasMessageContent: !!data.message_content,
      messageContentLength: data.message_content?.length,
      hasContent: !!data.content,
      hasData: !!data.data,
      agentType: data.agent_type || data.agent_role,
      stage: data.stage,
      fullData: JSON.stringify(data, null, 2)
    });

    switch (data.type) {
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
        console.log('📊 Workflow status update:', data);
        const status = data.status;
        if (status) {
          setWorkflowStatus(status.status === 'in_progress' ? 'running' : status.status);
          if (status.current_stage) {
            setCurrentStage(status.current_stage);
          }
        }
        break;

      case 'workflow_started':
        console.log('🚀 Workflow started');
        setWorkflowStatus('running');
        addSystemMessage('🚀 Workflow started - Agents are generating content...');
        break;

      case 'workflow_stage_update':
        const stage = data.data?.stage || data.stage;
        console.log('🔄 Stage update:', stage);
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
        console.log('🤖 AGENT MESSAGE RECEIVED:', {
          hasMessageContent: !!data.message_content,
          messageContentLength: data.message_content?.length,
          agentRole: data.agent_role,
          agentType: data.agent_type,
          stage: data.stage,
          messagePreview: data.message_content?.substring(0, 200)
        });
        
        // Fixed field mapping - backend sends 'message_content' as primary
        const agentContent = data.message_content || data.data?.message_content || data.content || data.message || '';
        const agentType = data.agent_role || data.agent_type || 'Agent';
        const messageStage = data.stage || currentStage;
        
        console.log('📝 Processing agent message:', {
          contentLength: agentContent.length,
          agentType,
          messageStage
        });
        
        if (agentContent && typeof agentContent === 'string' && agentContent.trim().length > 0) {
          console.log('✅ Agent message passes checks, adding to UI');
          addAgentMessage(agentContent, agentType, messageStage);
          
          // Track active agents
          if (agentType && agentType !== 'Agent' && agentType !== 'System' && !activeAgents.includes(agentType)) {
            console.log('➕ Adding active agent:', agentType);
            setActiveAgents(prev => [...prev, agentType]);
          }
        } else {
          console.log('❌ Agent message rejected - empty or invalid');
        }
        break;

      case 'agent_communication':
      case 'agent_output':
        console.log('📡 Agent communication/output received:', data.type);
        // Handle other agent message formats
        const altContent = 
          data.data?.message_content ||  
          data.data?.content || 
          data.content || 
          data.message ||
          data.data?.message ||
          data.text ||
          '';
          
        const altAgentType = 
          data.data?.agent_type || 
          data.data?.role ||
          data.role ||
          data.sender ||
          data.data?.sender ||
          'Agent';
          
        const altStage = data.data?.stage || data.stage || currentStage;
        
        console.log('📝 Alt format processing:', {
          contentLength: altContent.length,
          agentType: altAgentType,
          stage: altStage
        });
        
        if (altContent && typeof altContent === 'string' && altContent.trim().length > 5) {
          console.log('✅ Alt format message accepted');
          addAgentMessage(altContent, altAgentType, altStage);
          
          if (altAgentType && altAgentType !== 'Agent' && !activeAgents.includes(altAgentType)) {
            setActiveAgents(prev => [...prev, altAgentType]);
          }
        }
        break;

      case 'human_input_required':
        console.log('❓ Human input required:', data);
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
        console.log('🔍 CHECKPOINT RECEIVED:', {
          type: data.type,
          hasCheckpointId: !!data.checkpoint_id,
          hasDataCheckpointId: !!data.data?.checkpoint_id,
          hasId: !!data.id,
          hasFullContent: !!data.full_content,
          hasContentPreview: !!data.content_preview,
          hasDataContent: !!data.data?.content,
          hasDataContentPreview: !!data.data?.content_preview,
          title: data.title || data.data?.title,
          description: data.description || data.data?.description
        });
        
        const checkpointId = data.checkpoint_id || data.data?.checkpoint_id || data.id;
        
        if (!checkpointId) {
          console.warn('❌ Checkpoint without ID:', data);
          break;
        }
        
        if (processedCheckpointIds.current.has(checkpointId)) {
          console.log('🔄 Skipping duplicate checkpoint:', checkpointId);
          break;
        }
        
        if (pendingCheckpointRef.current) {
          console.log('⏳ Already have pending checkpoint, queueing:', checkpointId);
          break;
        }
        
        processedCheckpointIds.current.add(checkpointId);
        
        // Try all possible content fields
        const checkpointContent = 
          data.full_content || 
          data.content_preview ||
          data.content || 
          data.data?.content ||
          data.data?.content_preview ||
          data.data?.full_content ||
          data.checkpoint_data?.content || 
          data.checkpoint_data?.full_content ||
          '';
        
        console.log('📋 Checkpoint content extracted:', {
          contentLength: checkpointContent.length,
          contentPreview: checkpointContent.substring(0, 100)
        });
        
        if (checkpointContent && checkpointContent.length > 10) {
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
          
          console.log('✅ CHECKPOINT CREATED:', {
            id: checkpoint.id,
            title: checkpoint.title,
            hasContent: !!checkpoint.full_content
          });
          
          pendingCheckpointRef.current = checkpoint;
          setPendingCheckpoint(checkpoint);
          setWorkflowStatus('paused');
          
          // Enhanced message about feedback
          addSystemMessage(
            `🔍 Checkpoint: ${checkpoint.title}\n` +
            `Please review the content and provide your feedback.\n` +
            `You can approve it, request specific changes, or give detailed instructions.`
          );
          
          // Notify backend that we're tracking this checkpoint
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              type: 'checkpoint_acknowledged',
              checkpoint_id: checkpointId,
              workflow_id: workflowId
            }));
          }
        } else {
          console.warn('❌ Checkpoint has no content or content too short');
        }
        break;

      case 'checkpoint_resolved':
      case 'checkpoint_response_received':
        console.log('✅ Checkpoint resolved:', data);
        if (pendingCheckpointRef.current && 
            (data.checkpoint_id === pendingCheckpointRef.current.id || 
             data.data?.checkpoint_id === pendingCheckpointRef.current.id)) {
          
          pendingCheckpointRef.current = null;
          setPendingCheckpoint(null);
          setWorkflowStatus('running');
          
          // Show the actual feedback provided
          const feedback = data.feedback || data.data?.feedback || 'No feedback provided';
          addSystemMessage(`✅ Checkpoint feedback processed:\n"${feedback}"\n\nWorkflow continuing with your instructions...`);
        }
        break;

      case 'workflow_completed':
        console.log('🎉 Workflow completed:', data);
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
        console.log('❌ Workflow error:', data);
        setWorkflowStatus('error');
        const errorMsg = data.data?.error || data.error || data.message || 'Unknown error occurred';
        addSystemMessage(`❌ Error: ${errorMsg}`);
        break;

      case 'heartbeat':
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'pong' }));
        }
        break;

      case 'pong':
        console.log('💓 Heartbeat OK');
        break;

      case 'workflow_output':
        console.log('📤 Workflow output (skipping):', data.type);
        break;

      default:
        console.log('❓ Unknown message type:', data.type);
        // Fallback for any other message types with content
        if (data.message_content || data.message || data.content || data.text) {
          const content = data.message_content || data.message || data.content || data.text;
          
          if ((data.agent_type || data.role || data.sender_type === 'agent') && content.length > 5) {
            console.log('✅ Fallback: Adding message from unknown type');
            addAgentMessage(content, data.agent_type || data.role || 'Agent', data.stage || currentStage);
          }
        }
    }
  }, [addSystemMessage, addAgentMessage, onWorkflowComplete, currentStage, activeAgents]);

  // WebSocket connection with singleton pattern
  const connectWebSocket = useCallback(() => {
    // Check if we already have a global WebSocket for this workflow
    const existingWs = globalWebSockets.get(workflowId);
    if (existingWs && (existingWs.readyState === WebSocket.OPEN || existingWs.readyState === WebSocket.CONNECTING)) {
      console.log('Using existing global WebSocket for workflow:', workflowId);
      wsRef.current = existingWs;
      
      // Reattach event handlers
      existingWs.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      if (existingWs.readyState === WebSocket.OPEN) {
        setIsConnected(true);
        setIsReconnecting(false);
      }
      return;
    }

    // Clean up old connection if exists
    if (wsRef.current) {
      wsRef.current.close(1000, 'Creating new connection');
      wsRef.current = null;
    }
    
    // Clear existing intervals
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    try {
      setIsReconnecting(true);
      
      const ws = apiService.createWorkflowWebSocket(workflowId);
      wsRef.current = ws;
      globalWebSockets.set(workflowId, ws);

      ws.onopen = () => {
        if (!mountedRef.current) return;
        
        setIsConnected(true);
        setIsReconnecting(false);
        setReconnectAttempts(0);
        console.log('🔌 Connected to workflow WebSocket');
        
        // Setup heartbeat ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        globalWebSockets.delete(workflowId);
        
        if (!mountedRef.current) return;
        
        setIsConnected(false);
        console.log('❌ WebSocket disconnected:', event.code, event.reason);
        
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
            if (mountedRef.current) {
              connectWebSocket();
            }
          }, delay);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          setIsReconnecting(false);
          addSystemMessage('❌ Connection lost. Please refresh the page.');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (mountedRef.current) {
          setIsConnected(false);
          setIsReconnecting(false);
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      if (mountedRef.current) {
        setIsReconnecting(false);
        addSystemMessage('❌ Failed to connect to workflow');
      }
    }
  }, [workflowId, handleWebSocketMessage, addSystemMessage, reconnectAttempts]);

  // Initialize WebSocket connection
  useEffect(() => {
    mountedRef.current = true;
    
    // Clear any pending cleanup timeout
    if (cleanupTimeoutRef.current) {
      clearTimeout(cleanupTimeoutRef.current);
      cleanupTimeoutRef.current = null;
    }
    
    // Connect to WebSocket
    connectWebSocket();
    
    // Load workflow status via API as backup
    apiService.getWorkflowStatus(workflowId)
      .then(workflow => {
        if (mountedRef.current) {
          setWorkflowData(workflow);
          if (workflow.current_stage) {
            setCurrentStage(workflow.current_stage);
          }
        }
      })
      .catch(err => console.warn('Failed to load workflow status:', err));

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;
      
      // Add delay before cleanup to handle StrictMode double-mount
      cleanupTimeoutRef.current = setTimeout(() => {
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        // Only close if this component instance created the WebSocket
        const globalWs = globalWebSockets.get(workflowId);
        if (globalWs === wsRef.current) {
          globalWebSockets.delete(workflowId);
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.close(1000, 'Component unmounting');
          }
        }
        wsRef.current = null;
      }, 100);
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

  // Handle manual reconnection
  const handleReconnect = () => {
    setReconnectAttempts(0);
    connectWebSocket();
  };

  // Copy content to clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    addSystemMessage('📋 Content copied to clipboard!');
  };

  // Send user message - ENHANCED FOR CHECKPOINT FEEDBACK
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
    
    // Store the message before clearing
    const messageContent = inputMessage;
    setInputMessage('');

    // Check if this is feedback for a pending checkpoint
    if (pendingCheckpointRef.current) {
      // Send as checkpoint response with full user feedback
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'checkpoint_response',  // Changed from user_message
          checkpoint_id: pendingCheckpointRef.current.id,
          feedback: messageContent,  // Full open-ended feedback
          workflow_id: workflowId,
          timestamp: new Date().toISOString()
        }));
        
        addSystemMessage(`📝 Checkpoint feedback sent: "${messageContent}"`);
        
        // Clear the checkpoint after sending feedback
        pendingCheckpointRef.current = null;
        setPendingCheckpoint(null);
        setWorkflowStatus('running');
      }
    } else {
      // Regular user message when no checkpoint is pending
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'user_message',
          content: messageContent,
          workflow_id: workflowId
        }));
      }
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

  // The rest of the component remains the same (JSX return statement)
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

        {/* Enhanced Checkpoint Modal - Modified to show guidance only */}
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
                </div>
                
                {/* Modal footer - Modified to show instructions only */}
                <div className="border-t border-gray-700 bg-gray-900/50 px-6 py-4">
                  <p className="text-center text-gray-300">
                    Please review the content above and provide your feedback in the chat below.
                  </p>
                  <p className="text-center text-gray-400 text-sm mt-2">
                    You can approve, request specific changes, or provide detailed instructions.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Regular Input Area - ENHANCED WITH CHECKPOINT CONTEXT */}
        {workflowStatus === 'running' && !pendingHumanInput && (
          <div className="border-t border-gray-700 p-4">
            {/* Show checkpoint feedback prompt when checkpoint is pending */}
            {pendingCheckpoint && (
              <div className="mb-3 bg-yellow-900/30 border border-yellow-600/30 rounded-lg p-3">
                <p className="text-yellow-400 text-sm font-medium flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  Checkpoint Review Active: {pendingCheckpoint.title}
                </p>
                <p className="text-gray-300 text-sm mt-1">
                  Type your feedback below - you can approve, request changes, or provide detailed instructions.
                </p>
              </div>
            )}
            <div className="flex gap-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={pendingCheckpoint 
                  ? "Enter your feedback for this checkpoint..." 
                  : "Send a message to the workflow..."}
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