// frontend/src/components/workflow/ChatWorkflowInterface.tsx
// FIXED VERSION - Properly handles chat interface and agent interactions

import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Bot,
  User,
  Clock,
  CheckCircle,
  AlertCircle,
  Zap,
  MessageCircle,
  Settings,
  Download,
  Pause,
  Play,
  StopCircle,
  Users,
  Brain,
  Copy,
  ExternalLink,
  AlertTriangle
} from 'lucide-react';
import { apiService } from '../../services/api';

interface WorkflowMessage {
  id: string;
  type: 'agent' | 'human' | 'system' | 'checkpoint';
  sender: string;
  content: string;
  timestamp: string;
  metadata?: {
    agent_type?: string;
    stage?: string;
    workflow_id?: string;
    checkpoint_id?: string;
    requires_approval?: boolean;
    message_type?: string;
  };
}

interface CheckpointData {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'approved' | 'rejected';
  data: any;
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
  const [messages, setMessages] = useState<WorkflowMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [workflowStatus, setWorkflowStatus] = useState<'running' | 'paused' | 'completed' | 'error'>('running');
  const [currentStage, setCurrentStage] = useState<string>('Initializing');
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [pendingCheckpoint, setPendingCheckpoint] = useState<CheckpointData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [finalContent, setFinalContent] = useState<string>('');
  const [selectedStage, setSelectedStage] = useState<string>('all');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const ws = apiService.createWorkflowWebSocket(workflowId);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          console.log('🔌 Connected to workflow WebSocket');
          addSystemMessage('🚀 Connected to AI workflow. Agents are starting up...');
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
          console.log('❌ Workflow WebSocket disconnected:', event.code);
          
          // Only attempt to reconnect if it wasn't a normal closure
          if (event.code !== 1000 && workflowStatus !== 'completed') {
            addSystemMessage('⚠️ Connection lost. Attempting to reconnect...');
            setTimeout(connectWebSocket, 3000);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnected(false);
          addSystemMessage('❌ Connection error. Please check your network.');
        };

      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        setIsConnected(false);
        addSystemMessage('❌ Failed to connect to workflow. Please refresh the page.');
      }
    };

    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [workflowId, workflowStatus]);

  const addSystemMessage = (content: string) => {
    const message: WorkflowMessage = {
      id: `sys-${Date.now()}`,
      type: 'system',
      sender: 'System',
      content,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, message]);
  };

  const handleWebSocketMessage = (data: any) => {
    console.log('📨 Received WebSocket message:', data);

    switch (data.type) {
      case 'agent_message':
        const agentMessage: WorkflowMessage = {
          id: data.data.id || `agent-${Date.now()}`,
          type: 'agent',
          sender: data.data.agent_type || 'AI Agent',
          content: data.data.message_content || data.data.content || '',
          timestamp: data.timestamp || new Date().toISOString(),
          metadata: {
            agent_type: data.data.agent_type,
            stage: data.data.stage,
            workflow_id: data.data.workflow_id,
            message_type: data.data.message_type
          }
        };
        setMessages(prev => [...prev, agentMessage]);
        
        // Update active agents
        if (data.data.agent_type && !activeAgents.includes(data.data.agent_type)) {
          setActiveAgents(prev => [...prev, data.data.agent_type]);
        }
        break;

      case 'workflow_stage_update':
        setCurrentStage(data.data.stage || 'Unknown Stage');
        addSystemMessage(`🔄 Stage Update: ${data.data.stage}`);
        break;

      case 'checkpoint_required':
        const checkpoint: CheckpointData = {
          id: data.data.checkpoint_id,
          title: data.data.title || 'Review Required',
          description: data.data.description || 'Please review the following content.',
          status: 'pending',
          data: data.data.data || {}
        };
        setPendingCheckpoint(checkpoint);
        addSystemMessage(`⏸️ Checkpoint reached: ${checkpoint.title}`);
        break;

      case 'workflow_completed':
        setWorkflowStatus('completed');
        setFinalContent(data.data.final_content || '');
        addSystemMessage('✅ Workflow completed successfully!');
        
        if (onWorkflowComplete) {
          onWorkflowComplete(data.data);
        }
        break;

      case 'workflow_error':
        setWorkflowStatus('error');
        addSystemMessage(`❌ Workflow error: ${data.data.error || 'Unknown error occurred'}`);
        break;

      case 'system_message':
        addSystemMessage(data.data.message_content || data.data.content || '');
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || !isConnected) return;

    const userMessage: WorkflowMessage = {
      id: `user-${Date.now()}`,
      type: 'human',
      sender: 'You',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);

    try {
      // Send message to backend
      await apiService.sendWorkflowMessage(workflowId, {
        content: inputMessage,
        type: 'human_feedback'
      });

      setInputMessage('');
    } catch (error) {
      console.error('Failed to send message:', error);
      addSystemMessage('❌ Failed to send message. Please try again.');
    }
  };

  const handleCheckpointApproval = async (approved: boolean, feedback?: string) => {
    if (!pendingCheckpoint) return;

    try {
      await apiService.respondToCheckpoint(workflowId, pendingCheckpoint.id, {
        approved,
        feedback
      });

      setPendingCheckpoint(null);
      addSystemMessage(
        approved 
          ? '✅ Checkpoint approved. Workflow continuing...' 
          : '🔄 Checkpoint rejected. Agents will revise and try again...'
      );
    } catch (error) {
      console.error('Failed to respond to checkpoint:', error);
      addSystemMessage('❌ Failed to respond to checkpoint. Please try again.');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    addSystemMessage('📋 Content copied to clipboard!');
  };

  // Agent types and their colors
  const agentColors: { [key: string]: string } = {
    'coordinator': 'from-blue-500 to-blue-600',
    'style_analysis': 'from-purple-500 to-purple-600',
    'content_planning': 'from-indigo-500 to-indigo-600',
    'content_generation': 'from-green-500 to-green-600',
    'editing_qa': 'from-yellow-500 to-yellow-600',
    'default': 'from-gray-500 to-gray-600'
  };

  // Filter messages by stage
  const filteredMessages = selectedStage === 'all' 
    ? messages 
    : messages.filter(msg => 
        msg.metadata?.stage === selectedStage || 
        msg.type === 'system' || 
        msg.type === 'human'
      );

  // Available stages for filtering
  const stages = [
    { id: 'all', label: 'All Messages', color: 'from-gray-500 to-gray-600' },
    { id: 'document_processing', label: 'Document Processing', color: 'from-blue-500 to-blue-600' },
    { id: 'style_analysis', label: 'Style Analysis', color: 'from-purple-500 to-purple-600' },
    { id: 'content_planning', label: 'Content Planning', color: 'from-indigo-500 to-indigo-600' },
    { id: 'content_generation', label: 'Content Generation', color: 'from-green-500 to-green-600' },
    { id: 'editing_qa', label: 'Editing & QA', color: 'from-yellow-500 to-yellow-600' },
  ];

  return (
    <div className="flex h-full bg-gray-900">
      {/* Sidebar */}
      <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
        {/* Sidebar Header */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-violet-600 rounded-lg flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">AI Workflow</h3>
              <p className="text-xs text-gray-400">Multi-Agent Chat</p>
            </div>
          </div>
          
          {/* Status Indicator */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              workflowStatus === 'running' ? 'bg-green-400 animate-pulse' :
              workflowStatus === 'completed' ? 'bg-blue-400' :
              workflowStatus === 'error' ? 'bg-red-400' : 'bg-gray-400'
            }`} />
            <span className="text-sm text-gray-300">
              {workflowStatus === 'running' ? `Running: ${currentStage}` :
               workflowStatus === 'completed' ? 'Completed' :
               workflowStatus === 'error' ? 'Error' : 'Initializing'}
            </span>
          </div>
        </div>

        {/* Stage Filter */}
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-sm font-medium text-gray-300 mb-3">
            {selectedStage === 'all' ? 'Project Chat' : 'Chat Sessions'}
          </h3>
          
          <div className="space-y-2 mb-6">
            {stages.map((stage) => (
              <button
                key={stage.id}
                onClick={() => setSelectedStage(stage.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-300 ${
                  selectedStage === stage.id
                    ? 'bg-gradient-to-r from-orange-500/20 to-violet-600/20 text-orange-500 border border-orange-500/30'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }`}
              >
                <div className={`w-3 h-3 rounded-full bg-gradient-to-r ${stage.color}`} />
                <span className="text-sm">{stage.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Active Agents */}
        <div className="p-4 border-b border-gray-700">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Active Agents</h4>
          <div className="space-y-2">
            {activeAgents.length > 0 ? (
              activeAgents.map((agent) => (
                <div key={agent} className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${agentColors[agent] || agentColors.default}`} />
                  <span className="text-sm text-gray-400 capitalize">{agent.replace('_', ' ')}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-500">No active agents</p>
            )}
          </div>
        </div>

        {/* Connection Status */}
        <div className="mt-auto p-4 border-t border-gray-700">
          <div className="flex items-center gap-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
            <span className="text-gray-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {filteredMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.type === 'human' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.type !== 'human' && (
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  msg.type === 'agent' ? `bg-gradient-to-r ${agentColors[msg.metadata?.agent_type || 'default']}` : 'bg-gray-500'
                }`}>
                  {msg.type === 'agent' ? (
                    <Bot className="w-4 h-4 text-white" />
                  ) : (
                    <Clock className="w-4 h-4 text-white" />
                  )}
                </div>
              )}
              
              <div className={`max-w-2xl ${msg.type === 'human' ? 'bg-gradient-to-r from-orange-500 to-violet-600' : 'bg-gray-800'} rounded-lg p-4`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-medium text-white">{msg.sender}</span>
                  {msg.metadata?.stage && (
                    <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">
                      {msg.metadata.stage.replace('_', ' ')}
                    </span>
                  )}
                  <span className="text-xs text-gray-400 ml-auto">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="text-gray-100 whitespace-pre-wrap">{msg.content}</div>
              </div>

              {msg.type === 'human' && (
                <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Checkpoint Approval */}
        {pendingCheckpoint && (
          <div className="border-t border-gray-700 p-4 bg-yellow-900/20">
            <div className="max-w-2xl mx-auto">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                <h4 className="font-medium text-white">{pendingCheckpoint.title}</h4>
              </div>
              <p className="text-gray-300 text-sm mb-4">{pendingCheckpoint.description}</p>
              
              {pendingCheckpoint.data && (
                <div className="bg-gray-900 rounded-lg p-3 mb-4 max-h-32 overflow-y-auto">
                  <pre className="text-xs text-gray-400 whitespace-pre-wrap">
                    {JSON.stringify(pendingCheckpoint.data, null, 2)}
                  </pre>
                </div>
              )}
              
              <div className="flex gap-3">
                <button
                  onClick={() => handleCheckpointApproval(true)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                >
                  <CheckCircle className="w-4 h-4" />
                  Approve
                </button>
                <button
                  onClick={() => handleCheckpointApproval(false)}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                >
                  <AlertTriangle className="w-4 h-4" />
                  Request Changes
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Input Area */}
        {workflowStatus === 'running' && !pendingCheckpoint && (
          <div className="border-t border-gray-700 p-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder={isConnected ? "Send feedback to agents..." : "Connecting..."}
                disabled={!isConnected}
                className="flex-1 px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500 disabled:opacity-50"
              />
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || !isConnected}
                className="px-4 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            
            {!isConnected && (
              <p className="text-xs text-red-400 mt-2">
                Connection lost. Attempting to reconnect...
              </p>
            )}
          </div>
        )}

        {/* Completion Actions */}
        {workflowStatus === 'completed' && (
          <div className="border-t border-gray-700 p-4 bg-green-900/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Workflow Completed Successfully!</span>
              </div>
              <div className="flex gap-3">
                {finalContent && (
                  <button 
                    onClick={() => copyToClipboard(finalContent)}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                  >
                    <Copy className="w-4 h-4" />
                    Copy Content
                  </button>
                )}
                <button className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300">
                  <Zap className="w-4 h-4" />
                  Start New Workflow
                </button>
              </div>
            </div>
            
            {finalContent && (
              <div className="mt-4 p-4 bg-gray-800 rounded-lg">
                <h4 className="font-medium text-white mb-2">Generated Content:</h4>
                <div className="text-sm text-gray-300 bg-gray-900 p-3 rounded max-h-40 overflow-y-auto">
                  <pre className="whitespace-pre-wrap">{finalContent}</pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatWorkflowInterface;