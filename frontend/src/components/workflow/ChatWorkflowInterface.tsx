// frontend/src/components/workflow/ChatWorkflowInterface.tsx
// Create this new file in your project

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
  ExternalLink
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
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000); // Normal closure
      }
    };
  }, [workflowId, workflowStatus]);

  const addSystemMessage = (content: string) => {
    const message: WorkflowMessage = {
      id: `system-${Date.now()}-${Math.random()}`,
      type: 'system',
      sender: 'System',
      content,
      timestamp: new Date().toISOString(),
      metadata: { workflow_id: workflowId }
    };
    setMessages(prev => [...prev, message]);
  };

  const handleWebSocketMessage = (data: any) => {
    console.log('📨 Received WebSocket message:', data);

    switch (data.type) {
      case 'agent_communication':
      case 'agent_message':
        addAgentMessage(data.data || data);
        break;
      case 'workflow_update':
        handleWorkflowUpdate(data.data || data);
        break;
      case 'checkpoint_required':
      case 'human_checkpoint':
        handleCheckpointRequired(data.data || data);
        break;
      case 'workflow_completed':
      case 'workflow_complete':
        handleWorkflowCompleted(data.data || data);
        break;
      case 'agent_status':
        updateAgentStatus(data.data || data);
        break;
      case 'stage_update':
        handleStageUpdate(data.data || data);
        break;
    }
  };

  const addAgentMessage = (agentData: any) => {
    const message: WorkflowMessage = {
      id: `agent-${Date.now()}-${Math.random()}`,
      type: 'agent',
      sender: agentData.agent_type || agentData.sender || 'AI Agent',
      content: agentData.content || agentData.message_content || agentData.message || '',
      timestamp: new Date().toISOString(),
      metadata: {
        agent_type: agentData.agent_type,
        stage: agentData.stage,
        workflow_id: workflowId,
        message_type: agentData.message_type
      }
    };
    setMessages(prev => [...prev, message]);
  };

  const handleWorkflowUpdate = (updateData: any) => {
    if (updateData.stage) {
      setCurrentStage(updateData.stage);
    }
    if (updateData.status) {
      setWorkflowStatus(updateData.status);
    }
    
    if (updateData.message) {
      addSystemMessage(`📊 ${updateData.message}`);
    }
  };

  const handleStageUpdate = (stageData: any) => {
    const stageName = stageData.stage || stageData.name || 'Unknown Stage';
    setCurrentStage(stageName);
    addSystemMessage(`🔄 Moving to stage: ${stageName}`);
  };

  const handleCheckpointRequired = (checkpointData: any) => {
    const checkpoint = {
      id: checkpointData.checkpoint_id || checkpointData.id || `checkpoint-${Date.now()}`,
      title: checkpointData.title || 'Human Approval Required',
      description: checkpointData.description || 'Please review and approve the current progress.',
      status: 'pending' as const,
      data: checkpointData
    };
    
    setPendingCheckpoint(checkpoint);

    const message: WorkflowMessage = {
      id: `checkpoint-${Date.now()}-${Math.random()}`,
      type: 'checkpoint',
      sender: 'Human Checkpoint',
      content: `🚦 ${checkpoint.title}`,
      timestamp: new Date().toISOString(),
      metadata: {
        checkpoint_id: checkpoint.id,
        requires_approval: true,
        workflow_id: workflowId
      }
    };
    setMessages(prev => [...prev, message]);
    setWorkflowStatus('paused');
  };

  const handleWorkflowCompleted = (completionData: any) => {
    setWorkflowStatus('completed');
    setActiveAgents([]);
    setPendingCheckpoint(null);
    
    if (completionData.final_content || completionData.content) {
      setFinalContent(completionData.final_content || completionData.content);
    }
    
    addSystemMessage('🎉 Workflow completed successfully! Your content is ready.');

    if (onWorkflowComplete) {
      onWorkflowComplete(completionData);
    }
  };

  const updateAgentStatus = (statusData: any) => {
    if (statusData.active_agents) {
      setActiveAgents(statusData.active_agents);
    } else if (statusData.agents) {
      setActiveAgents(statusData.agents);
    }
  };

  const sendHumanMessage = async () => {
    if (!inputMessage.trim()) return;

    const message: WorkflowMessage = {
      id: `human-${Date.now()}-${Math.random()}`,
      type: 'human',
      sender: 'You',
      content: inputMessage,
      timestamp: new Date().toISOString(),
      metadata: { workflow_id: workflowId }
    };
    
    setMessages(prev => [...prev, message]);

    // Send to WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'human_message',
        content: inputMessage,
        workflow_id: workflowId
      }));
    }

    setInputMessage('');
  };

  const handleCheckpointApproval = async (approved: boolean, feedback?: string) => {
    if (!pendingCheckpoint) return;

    try {
      // Call API to approve/reject checkpoint
      if (approved) {
        await apiService.approveCheckpoint(pendingCheckpoint.id, { feedback: feedback || '' });
      } else {
        await apiService.rejectCheckpoint(pendingCheckpoint.id, { feedback: feedback || '' });
      }

      // Send approval via WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'checkpoint_approval',
          data: {
            checkpoint_id: pendingCheckpoint.id,
            approved,
            feedback: feedback || ''
          },
          workflow_id: workflowId
        }));
      }

      // Add response message
      const message: WorkflowMessage = {
        id: `approval-${Date.now()}-${Math.random()}`,
        type: 'human',
        sender: 'You',
        content: `${approved ? '✅ Approved' : '❌ Rejected'}: ${pendingCheckpoint.title}${feedback ? ` - ${feedback}` : ''}`,
        timestamp: new Date().toISOString(),
        metadata: {
          checkpoint_id: pendingCheckpoint.id,
          workflow_id: workflowId
        }
      };
      setMessages(prev => [...prev, message]);

      setPendingCheckpoint(null);
      setWorkflowStatus('running');

    } catch (error: any) {
      console.error('Failed to handle checkpoint:', error);
      addSystemMessage(`❌ Failed to ${approved ? 'approve' : 'reject'} checkpoint: ${error.message}`);
    }
  };

  const getMessageIcon = (message: WorkflowMessage) => {
    switch (message.type) {
      case 'agent':
        return <Bot className="w-4 h-4 text-orange-500" />;
      case 'human':
        return <User className="w-4 h-4 text-blue-500" />;
      case 'system':
        return <Settings className="w-4 h-4 text-purple-500" />;
      case 'checkpoint':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      default:
        return <MessageCircle className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusIcon = () => {
    switch (workflowStatus) {
      case 'running':
        return <Play className="w-4 h-4 text-green-500 animate-pulse" />;
      case 'paused':
        return <Pause className="w-4 h-4 text-yellow-500" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <StopCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      addSystemMessage('📋 Copied to clipboard!');
    });
  };

  return (
    <div className="h-full bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {getStatusIcon()}
              <h2 className="text-lg font-semibold text-white">AI Workflow Chat</h2>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <span>•</span>
              <span>{currentStage}</span>
              {isConnected ? (
                <span className="text-green-400">• Connected</span>
              ) : (
                <span className="text-red-400">• Disconnected</span>
              )}
            </div>
          </div>

          {/* Active Agents */}
          {activeAgents.length > 0 && (
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-gray-400" />
              <div className="flex gap-1 flex-wrap">
                {activeAgents.map((agent, index) => (
                  <div
                    key={index}
                    className="px-2 py-1 bg-orange-500/20 text-orange-300 rounded text-xs"
                  >
                    {agent}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${message.type === 'human' ? 'justify-end' : 'justify-start'}`}
          >
            {message.type !== 'human' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                {getMessageIcon(message)}
              </div>
            )}
            
            <div className={`max-w-[70%] ${message.type === 'human' ? 'order-first' : ''}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-white">{message.sender}</span>
                <span className="text-xs text-gray-400">{formatTime(message.timestamp)}</span>
                {message.metadata?.agent_type && (
                  <span className="text-xs bg-orange-500/20 text-orange-300 px-2 py-0.5 rounded">
                    {message.metadata.agent_type}
                  </span>
                )}
                {message.metadata?.stage && (
                  <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded">
                    {message.metadata.stage}
                  </span>
                )}
              </div>
              
              <div className={`rounded-lg p-3 ${
                message.type === 'human' 
                  ? 'bg-blue-600 text-white' 
                  : message.type === 'agent'
                  ? 'bg-gray-700 text-gray-100 border-l-2 border-orange-500'
                  : message.type === 'system'
                  ? 'bg-purple-900/30 text-purple-200 border border-purple-500/30'
                  : message.type === 'checkpoint'
                  ? 'bg-yellow-900/30 text-yellow-200 border border-yellow-500/30'
                  : 'bg-gray-800 text-gray-200'
              }`}>
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>

            {message.type === 'human' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
            )}
          </div>
        ))}

        {/* Checkpoint Approval */}
        {pendingCheckpoint && (
          <div className="bg-yellow-900/30 border border-yellow-500/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="w-5 h-5 text-yellow-500" />
              <h3 className="font-medium text-yellow-200">Human Checkpoint Required</h3>
            </div>
            
            <div className="mb-4">
              <h4 className="font-medium text-white mb-2">{pendingCheckpoint.title}</h4>
              <p className="text-gray-300 text-sm">{pendingCheckpoint.description}</p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => handleCheckpointApproval(true)}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <CheckCircle className="w-4 h-4" />
                Approve & Continue
              </button>
              <button
                onClick={() => handleCheckpointApproval(false, 'Please revise and try again')}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <StopCircle className="w-4 h-4" />
                Request Changes
              </button>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      {workflowStatus !== 'completed' && (
        <div className="border-t border-gray-700 p-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendHumanMessage()}
              placeholder={
                pendingCheckpoint 
                  ? "Awaiting your approval above..." 
                  : "Send guidance to the AI agents..."
              }
              className="flex-1 px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
              disabled={!isConnected || !!pendingCheckpoint}
            />
            <button
              onClick={sendHumanMessage}
              disabled={!inputMessage.trim() || !isConnected || !!pendingCheckpoint}
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
  );
};

export default ChatWorkflowInterface;