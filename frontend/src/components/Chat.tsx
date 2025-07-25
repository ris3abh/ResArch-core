// src/components/Chat.tsx
import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Send, Paperclip, Bot, User, Settings } from 'lucide-react';
import Sidebar from './Sidebar';

export default function Chat() {
  const { projectId, chatId } = useParams<{ projectId: string; chatId: string }>();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');

  // Mock chat data - will be replaced with real API
  const chatName = "Initial Content Strategy"; // This would come from API
  const projectName = "Acme Corporation Project"; // This would come from API

  const handleSend = () => {
    if (message.trim()) {
      console.log('Sending message:', message);
      setMessage('');
      // TODO: Implement real chat functionality
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen bg-gray-900">
      <Sidebar />
      
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-700 bg-gray-800/50 backdrop-blur-xl">
          <div className="px-6 py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(`/project/${projectId}`)}
                className="p-2 text-gray-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="flex-1">
                <h1 className="text-xl font-bold text-white">
                  {chatName}
                </h1>
                <p className="text-gray-400 text-sm">
                  {projectName}
                </p>
              </div>
              <button className="p-2 text-gray-400 hover:text-white transition-colors">
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto">
            {/* Welcome Message */}
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-orange-500 to-violet-600 rounded-full mb-4">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">
                Chat with AI Agents
              </h2>
              <p className="text-gray-300 mb-6">
                This chat is currently non-functional. Coming soon!
              </p>
              <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4 max-w-md mx-auto">
                <p className="text-orange-400 text-sm">
                  💡 <strong>Coming Soon:</strong> Multi-agent conversations with style analysis, content planning, generation, and QA agents.
                </p>
              </div>
            </div>

            {/* Placeholder for future messages */}
            <div className="space-y-4">
              {/* Example message structure for future implementation */}
              <div className="flex items-start gap-3 opacity-50">
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 bg-gray-800/50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium text-blue-400">Style Analysis Agent</span>
                    <span className="text-xs text-gray-500">10:30 AM</span>
                  </div>
                  <p className="text-gray-300">
                    I'll analyze your brand guidelines and previous content to understand your voice and tone preferences...
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 opacity-50">
                <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 bg-gray-700/50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium text-green-400">You</span>
                    <span className="text-xs text-gray-500">10:32 AM</span>
                  </div>
                  <p className="text-gray-300">
                    That sounds perfect. I need help creating a blog post about sustainable technology...
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-700 p-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <button 
                disabled
                className="p-3 text-gray-500 cursor-not-allowed"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <div className="flex-1 relative">
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Chat functionality coming soon..."
                  disabled
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400 resize-none cursor-not-allowed"
                  rows={3}
                />
              </div>
              <button
                onClick={handleSend}
                disabled
                className="p-3 bg-gray-700 text-gray-500 rounded-lg cursor-not-allowed"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
            <div className="mt-3 text-center">
              <p className="text-gray-500 text-sm">
                🚧 Chat functionality is under development and will be available soon
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}