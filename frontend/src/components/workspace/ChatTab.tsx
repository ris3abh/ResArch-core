import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Bot, User, Clock, CheckCircle, AlertCircle, Zap, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Message {
  id: string;
  type: 'user' | 'agent' | 'system';
  content: string;
  timestamp: string;
  agent?: 'style' | 'planning' | 'generation' | 'qa';
  stage?: 'style' | 'outline' | 'draft' | 'qa';
  attachments?: string[];
}

const mockMessages: Message[] = [
  {
    id: '1',
    type: 'system',
    content: 'Content workflow initiated. Style Analysis Agent is now analyzing your brand requirements.',
    timestamp: '10:30 AM',
    stage: 'style'
  },
  {
    id: '2',
    type: 'agent',
    content: 'I\'ve analyzed your brand guidelines and previous content. I recommend a professional yet approachable tone that aligns with your brand identity. The content should emphasize expertise while remaining accessible to your target audience.',
    timestamp: '10:32 AM',
    agent: 'style'
  },
  {
    id: '3',
    type: 'user',
    content: 'That sounds perfect. Let\'s proceed with the content planning phase.',
    timestamp: '10:35 AM'
  },
  {
    id: '4',
    type: 'agent',
    content: 'Excellent! I\'ve created a comprehensive content outline based on your style preferences. The structure includes an engaging introduction, three main sections highlighting key benefits, and a compelling call-to-action.',
    timestamp: '10:37 AM',
    agent: 'planning',
    stage: 'outline'
  },
];

const agentColors = {
  style: 'from-purple-500 to-purple-600',
  planning: 'from-blue-500 to-blue-600',
  generation: 'from-green-500 to-green-600',
  qa: 'from-red-500 to-red-600',
};

const stageIcons = {
  style: AlertCircle,
  outline: CheckCircle,
  draft: Zap,
  qa: CheckCircle,
};

interface ChatTabProps {
  clientId: string;
  projectId?: string;
}

export default function ChatTab({ clientId, projectId }: ChatTabProps) {
  const [message, setMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [selectedStage, setSelectedStage] = useState<string>('all');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const stages = [
    { id: 'all', label: 'All Messages', color: 'from-gray-500 to-gray-600' },
    { id: 'style', label: 'Style Analysis', color: 'from-purple-500 to-purple-600' },
    { id: 'outline', label: 'Content Planning', color: 'from-blue-500 to-blue-600' },
    { id: 'draft', label: 'Content Generation', color: 'from-green-500 to-green-600' },
    { id: 'qa', label: 'Quality Assurance', color: 'from-red-500 to-red-600' },
  ];

  const filteredMessages = mockMessages.filter(msg => 
    selectedStage === 'all' || msg.stage === selectedStage || msg.agent === selectedStage
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [filteredMessages]);

  const handleSend = () => {
    if (message.trim()) {
      console.log('Sending message:', message);
      setMessage('');
      setIsTyping(true);
      
      // Simulate agent response
      setTimeout(() => {
        setIsTyping(false);
      }, 2000);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleBackToProjects = () => {
    navigate(`/client/${clientId}`);
  };
  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 backdrop-blur-xl border-r border-gray-700 p-4">
        {projectId && (
          <button
            onClick={handleBackToProjects}
            className="flex items-center gap-2 mb-4 px-3 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-all duration-300"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Back to Projects</span>
          </button>
        )}
        
        <h3 className="text-lg font-semibold text-white mb-4">
          {projectId ? 'Project Chat' : 'Chat Sessions'}
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
        
        <div className="border-t border-gray-700 pt-4">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Workflow Actions</h4>
          <div className="space-y-2">
            <button className="w-full py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white text-sm font-medium rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300">
              Run Content Workflow
            </button>
            <button className="w-full py-2 bg-gray-700 text-white text-sm font-medium rounded-lg hover:bg-gray-600 transition-all duration-300">
              Submit Feedback
            </button>
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
              className={`flex gap-3 ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.type !== 'user' && (
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  msg.type === 'agent' ? `bg-gradient-to-r ${agentColors[msg.agent!]}` : 'bg-gray-500'
                }`}>
                  {msg.type === 'agent' ? (
                    <Bot className="w-4 h-4 text-white" />
                  ) : (
                    <Clock className="w-4 h-4 text-white" />
                  )}
                </div>
              )}
              
              <div className={`max-w-2xl ${msg.type === 'user' ? 'bg-gradient-to-r from-orange-500 to-violet-600' : 'bg-gray-700'} rounded-2xl p-4`}>
                {msg.type === 'agent' && (
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-orange-500 capitalize">
                      {msg.agent} Agent
                    </span>
                    {msg.stage && (
                      <span className="text-xs px-2 py-1 bg-gray-600 rounded-full text-gray-200">
                        {msg.stage}
                      </span>
                    )}
                  </div>
                )}
                
                <p className="text-white leading-relaxed">{msg.content}</p>
                
                <div className="flex items-center justify-between mt-3">
                  <span className="text-xs text-gray-400">{msg.timestamp}</span>
                  {msg.stage && (
                    <div className="flex items-center gap-1">
                      {React.createElement(stageIcons[msg.stage], {
                        className: "w-4 h-4 text-green-400"
                      })}
                    </div>
                  )}
                </div>
              </div>
              
              {msg.type === 'user' && (
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
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-700 p-6">
          <div className="flex gap-3">
            <button className="p-3 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-all duration-300">
              <Paperclip className="w-5 h-5" />
            </button>
            <div className="flex-1 relative">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message... (Shift+Enter for new line)"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400 resize-none"
                rows={3}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!message.trim()}
              className="p-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}