// frontend/src/components/workflow/ChatWorkflowInterface.tsx
// Enhanced version with proper backend integration and human input handling

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
  Loader2
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
  const [selectedStage, setSelectedStage] = useState<string>('all');
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [workflowData, setWorkflowData] = useState<WorkflowResponse | null>(null);
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Add system message helper
  const addSystemMessage = useCallback((content: string) => {
    const message: WorkflowMessage = {
      id: `sys-${Date.now()}-${Math.random()}`,
      type: 'system',
      content,
      timestamp: new Date().toISOString(),
      sender: 'System'
    };
    setMessages(prev => [...prev, message]);
  }, []);

  // Add agent message helper
  const addAgentMessage = useCallback((content: string, agentType?: string, stage?: string) => {
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
    setMessages(prev => [...prev, message]);
  }, [workflowId]);

  // Handle WebSocket messages based on backend message types
  const handleWebSocketMessage = useCallback((data: any) => {
    console.log('📨 WebSocket message received:', data.type, data);

    switch (data.type) {
      case 'connection_established':
        setIsConnected(true);
        setReconnectAttempts(0);
        addSystemMessage(`✅ Connected to workflow (ID: ${data.workflow_id})`);
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
        addSystemMessage('🚀 Workflow started successfully');
        break;

      case 'workflow_stage_update':
        const stage = data.data?.stage || data.stage;
        if (stage) {
          setCurrentStage(stage);
          if (data.data?.message) {
            addSystemMessage(`📍 ${stage}: ${data.data.message}`);
          }
        }
        break;

      case 'agent_message':
        const agentContent = data.data?.message_content || data.data?.content || data.content || '';
        const agentType = data.data?.agent_type || data.agent_type || data.role;
        const messageStage = data.data?.stage || data.stage;
        
        if (agentContent) {
          addAgentMessage(agentContent, agentType, messageStage);
          
          // Track active agents
          if (agentType && !activeAgents.includes(agentType)) {
            setActiveAgents(prev => [...prev, agentType]);
          }
        }
        break;

      case 'agent_output':
        // Handle console output from agents
        if (data.content && data.content.trim()) {
          const agentRole = data.agent_role || data.role || 'Agent';
          addAgentMessage(data.content, agentRole, data.stage);
        }
        break;

      case 'human_input_required':
        // Handle human input request from CAMEL agents
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

      case 'checkpoint_required':
        // Handle checkpoint that needs approval
        const checkpoint: CheckpointData = {
          id: data.data?.checkpoint_id || data.checkpoint_id,
          title: data.data?.title || data.title || 'Review Required',
          description: data.data?.description || data.description || 'Please review and approve to continue',
          status: 'pending',
          data: data.data?.checkpoint_data || data.data || {},
          content_preview: data.data?.content_preview
        };
        setPendingCheckpoint(checkpoint);
        setWorkflowStatus('paused');
        addSystemMessage(`🔍 Checkpoint: ${checkpoint.title}`);
        break;

      case 'workflow_completed':
        setWorkflowStatus('completed');
        const content = data.data?.final_content || data.final_content || '';
        if (content) {
          setFinalContent(content);
        }
        addSystemMessage('🎉 Workflow completed successfully!');
        if (onWorkflowComplete) {
          onWorkflowComplete(data.data || { final_content: content });
        }
        break;

      case 'workflow_error':
        setWorkflowStatus('error');
        const errorMsg = data.data?.error || data.error || data.message || 'Unknown error occurred';
        addSystemMessage(`❌ Error: ${errorMsg}`);
        break;

      case 'response_acknowledged':
        // Human response was received by backend
        console.log('Response acknowledged:', data.request_id);
        break;

      case 'pong':
        // Heartbeat response
        console.log('💓 Pong received');
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }, [addSystemMessage, addAgentMessage, activeAgents, workflowId, onWorkflowComplete]);

  // WebSocket connection management
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    try {
      setIsReconnecting(true);
      const ws = apiService.createWorkflowWebSocket(workflowId);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsReconnecting(false);
        setReconnectAttempts(0);
        console.log('🔌 Connected to workflow WebSocket');
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
        setIsConnected(false);
        console.log('❌ WebSocket disconnected:', event.code, event.reason);
        
        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        
        // Attempt to reconnect if not a normal closure and workflow is still running
        if (event.code !== 1000 && workflowStatus === 'running' && reconnectAttempts < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
          addSystemMessage(`⚠️ Connection lost. Reconnecting in ${delay / 1000}s...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connectWebSocket();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
        setIsReconnecting(false);
      };

      // Setup ping interval to keep connection alive
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000); // Ping every 30 seconds

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setIsReconnecting(false);
      addSystemMessage('❌ Failed to connect to workflow');
    }
  }, [workflowId, workflowStatus, reconnectAttempts, handleWebSocketMessage, addSystemMessage]);

  // Initialize WebSocket connection
  useEffect(() => {
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

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [connectWebSocket, workflowId]);

  // Handle human input response for CAMEL agents
  const sendHumanResponse = async () => {
    if (!pendingHumanInput || !humanInputResponse.trim()) return;

    try {
      // Send via WebSocket (primary method for CAMEL bridge)
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
    // Auto-send for multiple choice
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

  // Handle checkpoint approval
  const handleCheckpointApproval = async (approved: boolean, feedback?: string) => {
    if (!pendingCheckpoint) return;

    try {
      // Use the proper API endpoint
      if (approved) {
        await apiService.approveCheckpoint(pendingCheckpoint.id, {
          feedback: feedback || ''
        });
        addSystemMessage(`✅ Checkpoint approved${feedback ? `: ${feedback}` : ''}`);
      } else {
        await apiService.rejectCheckpoint(pendingCheckpoint.id, {
          feedback: feedback || ''
        });
        addSystemMessage(`❌ Checkpoint rejected${feedback ? `: ${feedback}` : ''}`);
      }
      
      setPendingCheckpoint(null);
      setWorkflowStatus('running');
    } catch (error) {
      console.error('Failed to respond to checkpoint:', error);
      addSystemMessage('❌ Failed to respond to checkpoint. Please try again.');
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

  // Send user message (for general workflow communication)
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

    // Send via WebSocket
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'user_message',
        content: inputMessage,
        workflow_id: workflowId
      }));
    }
  };

  // Filter messages by stage
  const filteredMessages = selectedStage === 'all' 
    ? messages 
    : messages.filter(msg => 
        msg.metadata?.stage === selectedStage || 
        msg.type === 'system' || 
        msg.type === 'user'
      );

  // Agent colors for visual distinction
  const agentColors: { [key: string]: string } = {
    'coordinator': 'from-blue-500 to-blue-600',
    'style_analysis': 'from-purple-500 to-purple-600',
    'content_planning': 'from-indigo-500 to-indigo-600',
    'content_generation': 'from-green-500 to-green-600',
    'editing_qa': 'from-yellow-500 to-yellow-600',
    'Content Creator': 'from-green-500 to-green-600',
    'Content Strategist': 'from-purple-500 to-purple-600',
    'default': 'from-gray-500 to-gray-600'
  };

  // Available stages for filtering
  const stages = Array.from(new Set(messages
    .map(m => m.metadata?.stage)
    .filter(Boolean)
  ));

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
          
          {!isConnected && !isReconnecting && (
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
          {filteredMessages.length === 0 ? (
            <div className="text-center py-12">
              <Brain className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">Workflow is initializing...</p>
              <p className="text-sm text-gray-500 mt-2">Agent messages will appear here</p>
            </div>
          ) : (
            filteredMessages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[70%] ${
                  message.type === 'user' 
                    ? 'bg-gradient-to-r from-orange-500 to-violet-600 text-white' 
                    : message.type === 'system'
                    ? 'bg-gray-700 text-gray-300'
                    : message.type === 'checkpoint'
                    ? 'bg-yellow-900/30 border border-yellow-600/30 text-yellow-300'
                    : 'bg-gray-700 text-white'
                } rounded-lg p-4`}>
                  <div className="flex items-start gap-3">
                    {message.type === 'agent' && <Bot className="w-5 h-5 mt-1 flex-shrink-0" />}
                    {message.type === 'user' && <User className="w-5 h-5 mt-1 flex-shrink-0" />}
                    {message.type === 'system' && <Zap className="w-5 h-5 mt-1 flex-shrink-0" />}
                    
                    <div className="flex-1">
                      {message.sender && (
                        <p className="text-xs font-medium mb-1 opacity-80">{message.sender}</p>
                      )}
                      <p className="whitespace-pre-wrap">{message.content}</p>
                      {message.metadata?.stage && (
                        <p className="text-xs mt-2 opacity-60">Stage: {message.metadata.stage}</p>
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
            
            {/* Yes/No Questions */}
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
              // Multiple Choice Questions
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
              // Text Input Questions
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

        {/* Checkpoint Approval UI */}
        {pendingCheckpoint && (
          <div className="border-t border-gray-700 p-4 bg-blue-900/20">
            <div className="mb-3">
              <p className="text-blue-300 font-medium mb-2 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Checkpoint Review
              </p>
              <p className="text-white font-semibold">{pendingCheckpoint.title}</p>
              <p className="text-gray-300 mt-1">{pendingCheckpoint.description}</p>
            </div>
            
            {pendingCheckpoint.content_preview && (
              <div className="bg-gray-900 rounded-lg p-3 mb-4 max-h-32 overflow-y-auto">
                <pre className="text-xs text-gray-400 whitespace-pre-wrap">
                  {pendingCheckpoint.content_preview}
                </pre>
              </div>
            )}
            
            <div className="flex gap-3">
              <button
                onClick={() => handleCheckpointApproval(true)}
                className="flex-1 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
              >
                <CheckCircle className="w-5 h-5" />
                Approve
              </button>
              <button
                onClick={() => handleCheckpointApproval(false)}
                className="flex-1 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
              >
                <AlertCircle className="w-5 h-5" />
                Request Changes
              </button>
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
        {workflowStatus === 'completed' && (
          <div className="border-t border-gray-700 p-4 bg-green-900/20">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Workflow Completed Successfully!</span>
              </div>
              {finalContent && (
                <button 
                  onClick={() => copyToClipboard(finalContent)}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors flex items-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  Copy Content
                </button>
              )}
            </div>
            
            {finalContent && (
              <div className="bg-gray-800 rounded-lg p-4">
                <h4 className="font-medium text-white mb-2">Generated Content:</h4>
                <div className="bg-gray-900 p-3 rounded max-h-60 overflow-y-auto">
                  <pre className="text-sm text-gray-300 whitespace-pre-wrap">{finalContent}</pre>
                </div>
              </div>
            )}
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

        {/* Stage Filter */}
        {stages.length > 0 && (
          <div className="bg-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">Filter by Stage</h3>
            <select
              value={selectedStage}
              onChange={(e) => setSelectedStage(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="all">All Stages</option>
              {stages.map(stage => (
                <option key={stage} value={stage}>{stage}</option>
              ))}
            </select>
          </div>
        )}

        {/* Active Agents List */}
        {activeAgents.length > 0 && (
          <div className="bg-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">Active Agents</h3>
            <div className="space-y-2">
              {activeAgents.map(agent => (
                <div key={agent} className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${agentColors[agent] || agentColors.default}`} />
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
      </div>
    </div>
  );
};

export default ChatWorkflowInterface;