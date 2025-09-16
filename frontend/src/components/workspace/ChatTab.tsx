// frontend/src/components/workspace/ChatTab.tsx
// Enhanced version with real API integration and workflow support

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Send,
  Paperclip,
  Bot,
  User,
  Clock,
  CheckCircle,
  AlertCircle,
  Zap,
  ArrowLeft,
  MessageCircle,
  PlayCircle,
  RefreshCw,
  Loader2,
  Edit3,
  Trash2,
  MoreVertical,
  Download
} from 'lucide-react';
import { apiService, ChatMessage, ChatInstance } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

interface ChatTabProps {
  projectId?: string;
  chatId?: string;
  onStartWorkflow?: () => void;
}

const ChatTab: React.FC<ChatTabProps> = ({ projectId, chatId, onStartWorkflow }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State management
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [currentChat, setCurrentChat] = useState<ChatInstance | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [activeWorkflow, setActiveWorkflow] = useState<string | null>(null);
  const [error, setError] = useState<string>('');
  const [selectedStage, setSelectedStage] = useState<string>('all');
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);

  // Agent types and colors
  const agentInfo: { [key: string]: { color: string; label: string } } = {
    'style_analysis': { color: 'from-purple-500 to-purple-600', label: 'Style Analysis' },
    'content_planning': { color: 'from-blue-500 to-blue-600', label: 'Content Planning' },
    'content_generation': { color: 'from-green-500 to-green-600', label: 'Content Generation' },
    'editing_qa': { color: 'from-yellow-500 to-yellow-600', label: 'Quality Assurance' },
    'coordinator': { color: 'from-indigo-500 to-indigo-600', label: 'Coordinator' },
    'default': { color: 'from-gray-500 to-gray-600', label: 'AI Agent' }
  };

  // Stage filters
  const stages = [
    { id: 'all', label: 'All Messages', color: 'from-gray-500 to-gray-600' },
    { id: 'style_analysis', label: 'Style Analysis', color: 'from-purple-500 to-purple-600' },
    { id: 'content_planning', label: 'Content Planning', color: 'from-blue-500 to-blue-600' },
    { id: 'content_generation', label: 'Content Generation', color: 'from-green-500 to-green-600' },
    { id: 'editing_qa', label: 'Quality Assurance', color: 'from-yellow-500 to-yellow-600' },
  ];

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load chat data and messages
  useEffect(() => {
    if (chatId) {
      loadChatData();
    } else if (projectId) {
      createOrLoadProjectChat();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [chatId, projectId]);

  // Load existing chat
  const loadChatData = async () => {
    if (!chatId) return;

    try {
      setIsLoading(true);
      setError('');

      // Load chat instance
      const chat = await apiService.getChatInstance(chatId);
      setCurrentChat(chat);

      // Load chat messages with workflow context
      const chatMessages = await apiService.getChatMessages(chatId, {
        include_workflow_context: true,
        limit: 100
      });
      setMessages(chatMessages);

      // Check for active workflows
      if (chat.active_workflows && chat.active_workflows.length > 0) {
        setActiveWorkflow(chat.active_workflows[0]);
      }

      // Setup WebSocket connection
      setupWebSocket(chatId);
    } catch (error: any) {
      console.error('Failed to load chat:', error);
      setError('Failed to load chat conversation');
    } finally {
      setIsLoading(false);
    }
  };

  // Create or load project chat
  const createOrLoadProjectChat = async () => {
    if (!projectId) return;

    try {
      setIsLoading(true);
      setError('');

      // Get or create a default chat for the project
      const chats = await apiService.getProjectChats(projectId);
      
      let chat: ChatInstance;
      if (chats.length > 0) {
        // Use the first chat
        chat = chats[0];
      } else {
        // Create a new chat
        chat = await apiService.createChat(projectId, {
          name: 'Project Discussion',
          description: 'Main project chat for team collaboration',
          chat_type: 'project'
        });
      }

      setCurrentChat(chat);

      // Load messages
      const chatMessages = await apiService.getChatMessages(chat.id, {
        include_workflow_context: true,
        limit: 100
      });
      setMessages(chatMessages);

      // Check for active workflows
      if (chat.workflow_id) {
        setActiveWorkflow(chat.workflow_id);
      }

      // Setup WebSocket
      setupWebSocket(chat.id);
    } catch (error: any) {
      console.error('Failed to load project chat:', error);
      setError('Failed to load chat');
    } finally {
      setIsLoading(false);
    }
  };

  // Setup WebSocket connection
  const setupWebSocket = (chatId: string) => {
    try {
      const ws = apiService.createChatWebSocket(chatId);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log('✅ Connected to chat WebSocket');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('❌ Chat WebSocket disconnected');
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
    } catch (error) {
      console.error('Failed to setup WebSocket:', error);
    }
  };

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'new_message':
        // New message from another user or agent
        const newMessage: ChatMessage = {
          id: data.data.id || `msg-${Date.now()}`,
          chat_instance_id: currentChat?.id || '',
          sender_id: data.data.sender_id,
          sender_type: data.data.sender_type,
          agent_type: data.data.agent_type,
          message_content: data.data.message_content,
          message_type: data.data.message_type || 'text',
          message_metadata: data.data.metadata,
          created_at: data.data.created_at || new Date().toISOString(),
          is_edited: false,
          workflow_id: data.data.workflow_id,
          stage: data.data.stage
        };
        
        // Only add if not from current user (to avoid duplicates)
        if (data.data.sender_id !== user?.id) {
          setMessages(prev => [...prev, newMessage]);
        }
        break;

      case 'agent_message':
        // Agent message from workflow
        const agentMessage: ChatMessage = {
          id: data.data?.id || `agent-${Date.now()}`,
          chat_instance_id: currentChat?.id || '',
          sender_type: 'agent',
          agent_type: data.data?.agent_type,
          message_content: data.data?.message_content,
          message_type: 'agent',
          message_metadata: data.data?.metadata,
          created_at: data.timestamp || new Date().toISOString(),
          is_edited: false,
          workflow_id: data.data?.workflow_id,
          stage: data.data?.stage
        };
        setMessages(prev => [...prev, agentMessage]);
        break;

      case 'message_updated':
        // Message was edited
        setMessages(prev => prev.map(msg => 
          msg.id === data.data.id 
            ? { ...msg, message_content: data.data.message_content, is_edited: true }
            : msg
        ));
        break;

      case 'message_deleted':
        // Message was deleted
        setMessages(prev => prev.filter(msg => msg.id !== data.data.id));
        break;

      case 'typing_indicator':
        // Someone is typing
        setIsTyping(true);
        setTimeout(() => setIsTyping(false), 3000);
        break;

      case 'workflow_update':
        // Workflow status update
        if (data.status === 'completed') {
          setActiveWorkflow(null);
        } else if (data.workflow_id) {
          setActiveWorkflow(data.workflow_id);
        }
        break;

      default:
        console.log('Unknown WebSocket message type:', data.type);
    }
  };

  // Send message
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !currentChat || isSending) return;

    const tempId = `temp-${Date.now()}`;
    const tempMessage: ChatMessage = {
      id: tempId,
      chat_instance_id: currentChat.id,
      sender_id: user?.id,
      sender_type: 'user',
      message_content: inputMessage,
      message_type: 'text',
      created_at: new Date().toISOString(),
      is_edited: false
    };

    try {
      setIsSending(true);
      setMessages(prev => [...prev, tempMessage]);
      const messageToSend = inputMessage;
      setInputMessage('');

      // Send via API
      const sentMessage = await apiService.sendChatMessage(currentChat.id, messageToSend);
      
      // Replace temp message with real one
      setMessages(prev => prev.map(msg => 
        msg.id === tempId ? sentMessage : msg
      ));

      // Send typing indicator via WebSocket
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'typing_indicator',
          chat_id: currentChat.id
        }));
      }
    } catch (error: any) {
      console.error('Failed to send message:', error);
      // Remove temp message on error
      setMessages(prev => prev.filter(msg => msg.id !== tempId));
      setError('Failed to send message');
      setInputMessage(inputMessage); // Restore message
    } finally {
      setIsSending(false);
    }
  };

  // Edit message
  const handleEditMessage = async (messageId: string, newContent: string) => {
    if (!currentChat || !newContent.trim()) return;

    try {
      const updatedMessage = await apiService.updateChatMessage(
        currentChat.id,
        messageId,
        newContent
      );
      
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? updatedMessage : msg
      ));
      
      setEditingMessageId(null);
      setEditContent('');
    } catch (error: any) {
      console.error('Failed to edit message:', error);
      setError('Failed to edit message');
    }
  };

  // Delete message
  const handleDeleteMessage = async (messageId: string) => {
    if (!currentChat) return;
    
    if (!window.confirm('Are you sure you want to delete this message?')) return;

    try {
      await apiService.deleteChatMessage(currentChat.id, messageId);
      setMessages(prev => prev.filter(msg => msg.id !== messageId));
    } catch (error: any) {
      console.error('Failed to delete message:', error);
      setError('Failed to delete message');
    }
  };

  // Start workflow from chat
  const handleStartWorkflow = async () => {
    if (!currentChat || !projectId) return;

    try {
      const result = await apiService.startSpinscribeWorkflow(
        currentChat.id,
        'Create content from chat discussion'
      );
      setActiveWorkflow(result.workflow_id);
      
      // Navigate to workflow page
      if (onStartWorkflow) {
        onStartWorkflow();
      } else {
        navigate(`/workflow/${projectId}/${result.workflow_id}`);
      }
    } catch (error: any) {
      console.error('Failed to start workflow:', error);
      setError('Failed to start workflow');
    }
  };

  // Handle file attachment
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      setAttachments(Array.from(files));
    }
  };

  // Refresh messages
  const handleRefresh = async () => {
    if (!currentChat) return;
    
    try {
      setIsLoading(true);
      const chatMessages = await apiService.getChatMessages(currentChat.id, {
        include_workflow_context: true,
        limit: 100
      });
      setMessages(chatMessages);
    } catch (error) {
      console.error('Failed to refresh messages:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter messages by stage
  const filteredMessages = selectedStage === 'all' 
    ? messages 
    : messages.filter(msg => 
        msg.stage === selectedStage || 
        msg.agent_type === selectedStage ||
        msg.sender_type === 'user' // Always show user messages
      );

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-orange-500 mx-auto mb-4" />
          <p className="text-gray-300">Loading chat...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 border-r border-gray-700 p-4 flex flex-col">
        {projectId && (
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="flex items-center gap-2 mb-4 px-3 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-all duration-300"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Back to Project</span>
          </button>
        )}
        
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white mb-2">
            {currentChat?.name || 'Chat'}
          </h3>
          {currentChat?.description && (
            <p className="text-sm text-gray-400">{currentChat.description}</p>
          )}
        </div>

        {/* Connection Status */}
        <div className="flex items-center gap-2 mb-4 px-3 py-2 bg-gray-700 rounded-lg">
          <div className={`w-2 h-2 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-gray-500'
          }`} />
          <span className="text-xs text-gray-400">
            {isConnected ? 'Connected' : 'Offline'}
          </span>
          <button
            onClick={handleRefresh}
            className="ml-auto p-1 hover:bg-gray-600 rounded transition-colors"
            title="Refresh messages"
          >
            <RefreshCw className="w-3 h-3 text-gray-400" />
          </button>
        </div>
        
        {/* Stage Filter */}
        <div className="space-y-2 mb-6">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Filter by Stage</h4>
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
        
        {/* Workflow Actions */}
        <div className="border-t border-gray-700 pt-4 mt-auto">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Workflow Actions</h4>
          <div className="space-y-2">
            {activeWorkflow ? (
              <button
                onClick={() => navigate(`/workflow/${projectId}/${activeWorkflow}`)}
                className="w-full py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-all duration-300 flex items-center justify-center gap-2"
              >
                <PlayCircle className="w-4 h-4" />
                View Active Workflow
              </button>
            ) : (
              <button
                onClick={handleStartWorkflow}
                className="w-full py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white text-sm font-medium rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
              >
                Run Content Workflow
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {filteredMessages.length === 0 ? (
            <div className="text-center py-12">
              <MessageCircle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No messages yet</p>
              <p className="text-sm text-gray-500 mt-2">Start a conversation or launch a workflow</p>
            </div>
          ) : (
            <>
              {filteredMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.sender_type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.sender_type !== 'user' && (
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      msg.sender_type === 'agent' 
                        ? `bg-gradient-to-r ${agentInfo[msg.agent_type || 'default'].color}` 
                        : 'bg-gray-500'
                    }`}>
                      {msg.sender_type === 'agent' ? (
                        <Bot className="w-4 h-4 text-white" />
                      ) : (
                        <Clock className="w-4 h-4 text-white" />
                      )}
                    </div>
                  )}
                  
                  <div className={`max-w-2xl ${
                    msg.sender_type === 'user' 
                      ? 'bg-gradient-to-r from-orange-500 to-violet-600' 
                      : 'bg-gray-700'
                  } rounded-2xl p-4 group relative`}>
                    {msg.sender_type === 'agent' && msg.agent_type && (
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-medium text-orange-500">
                          {agentInfo[msg.agent_type || 'default'].label}
                        </span>
                        {msg.stage && (
                          <span className="text-xs px-2 py-1 bg-gray-600 rounded-full text-gray-200">
                            {msg.stage}
                          </span>
                        )}
                      </div>
                    )}
                    
                    {editingMessageId === msg.id ? (
                      <div className="space-y-2">
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white resize-none"
                          rows={3}
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleEditMessage(msg.id, editContent)}
                            className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => {
                              setEditingMessageId(null);
                              setEditContent('');
                            }}
                            className="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <p className="text-white leading-relaxed">{msg.message_content}</p>
                        
                        <div className="flex items-center justify-between mt-3">
                          <span className="text-xs text-gray-400">
                            {formatTimestamp(msg.created_at)}
                            {msg.is_edited && ' (edited)'}
                          </span>
                          
                          {msg.sender_type === 'user' && msg.sender_id === user?.id && (
                            <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                              <button
                                onClick={() => {
                                  setEditingMessageId(msg.id);
                                  setEditContent(msg.message_content);
                                }}
                                className="p-1 hover:bg-gray-600 rounded"
                              >
                                <Edit3 className="w-3 h-3 text-gray-400" />
                              </button>
                              <button
                                onClick={() => handleDeleteMessage(msg.id)}
                                className="p-1 hover:bg-gray-600 rounded"
                              >
                                <Trash2 className="w-3 h-3 text-gray-400" />
                              </button>
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                  
                  {msg.sender_type === 'user' && (
                    <div className="w-8 h-8 bg-gradient-to-r from-orange-500 to-violet-600 rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              ))}
              
              {isTyping && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 bg-gradient-to-r from-orange-500 to-violet-600 rounded-full flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-700 rounded-2xl p-4">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                        <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                      </div>
                      <span className="text-sm text-gray-300">Agent is typing...</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Error Display */}
        {error && (
          <div className="px-6 py-2 bg-red-900/20 border-t border-red-600/30">
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{error}</span>
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-gray-700 p-6">
          {attachments.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {attachments.map((file, index) => (
                <div key={index} className="flex items-center gap-2 px-3 py-1 bg-gray-700 rounded-lg">
                  <Paperclip className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-300">{file.name}</span>
                  <button
                    onClick={() => setAttachments(prev => prev.filter((_, i) => i !== index))}
                    className="text-red-400 hover:text-red-300"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
          
          <div className="flex gap-3">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              multiple
              className="hidden"
            />
            <button 
              onClick={() => fileInputRef.current?.click()}
              className="p-3 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-all duration-300"
            >
              <Paperclip className="w-5 h-5" />
            </button>
            
            <div className="flex-1 relative">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Type your message... (Shift+Enter for new line)"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400 resize-none"
                rows={3}
                disabled={isSending}
              />
            </div>
            
            <button
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || isSending}
              className="p-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatTab;