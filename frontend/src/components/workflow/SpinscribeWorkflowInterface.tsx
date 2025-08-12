// src/components/workflow/SpinscribeWorkflowInterface.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Zap, ArrowLeft, Download, Copy, Play, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import { apiService } from '../../services/api';

// Simple toast function (no external dependency)
const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
  const toast = document.createElement('div');
  const bgColor = type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#3B82F6';
  
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: ${bgColor};
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 9999;
    transform: translateX(100%);
    transition: transform 0.3s ease;
    max-width: 400px;
  `;
  
  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
  toast.textContent = `${icon} ${message}`;
  document.body.appendChild(toast);
  
  setTimeout(() => toast.style.transform = 'translateX(0)', 10);
  setTimeout(() => {
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => document.body.removeChild(toast), 300);
  }, 4000);
};

interface WorkflowConfig {
  title: string;
  contentType: string;
  hasInitialDraft: boolean;
  initialDraft?: string;
  useProjectDocuments: boolean;
  enableCheckpoints: boolean;
}

export default function SpinscribeWorkflowInterface() {
  const { projectId, chatId } = useParams<{ projectId: string; chatId?: string }>();
  const navigate = useNavigate();
  
  const [step, setStep] = useState<'configure' | 'running' | 'completed' | 'error'>('configure');
  const [workflowId, setWorkflowId] = useState<string>('');
  const [workflowStatus, setWorkflowStatus] = useState<any>(null);
  const [error, setError] = useState<string>('');
  const [config, setConfig] = useState<WorkflowConfig>({
    title: '',
    contentType: 'article',
    hasInitialDraft: false,
    useProjectDocuments: true,
    enableCheckpoints: true
  });

  const startWorkflow = async () => {
    if (!config.title.trim()) {
      showToast('Please enter a title for your content', 'error');
      return;
    }

    try {
      showToast('🚀 Starting Spinscribe agents...', 'info');
      
      const response = await apiService.startWorkflow({
        project_id: projectId!,
        chat_id: chatId,
        title: config.title,
        content_type: config.contentType,
        initial_draft: config.hasInitialDraft ? config.initialDraft : undefined,
        use_project_documents: config.useProjectDocuments
      });

      setWorkflowId(response.workflow_id);
      setStep('running');
      showToast('🎉 Workflow started! Agents are working...', 'success');
      
      // Start polling for status
      startStatusPolling(response.workflow_id);

    } catch (error: any) {
      console.error('Failed to start workflow:', error);
      setError(error.message || 'Failed to start workflow');
      showToast('Failed to start workflow: ' + error.message, 'error');
    }
  };

  const startStatusPolling = (workflowId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await apiService.getWorkflowStatus(workflowId);
        setWorkflowStatus(status);

        if (status.status === 'completed') {
          setStep('completed');
          clearInterval(pollInterval);
          showToast('🎉 Content creation completed!', 'success');
        } else if (status.status === 'failed') {
          setStep('error');
          clearInterval(pollInterval);
          setError('Workflow failed during execution');
          showToast('❌ Workflow failed', 'error');
        }
      } catch (error) {
        console.error('Failed to fetch status:', error);
      }
    }, 2000);

    setTimeout(() => clearInterval(pollInterval), 30 * 60 * 1000);
  };

  const copyToClipboard = async () => {
    if (workflowStatus?.final_content) {
      await navigator.clipboard.writeText(workflowStatus.final_content);
      showToast('📋 Content copied to clipboard!', 'success');
    }
  };

  const downloadContent = () => {
    if (workflowStatus?.final_content) {
      const blob = new Blob([workflowStatus.final_content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${config.title.replace(/\s+/g, '_')}_content.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  if (!projectId) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-2">Project Not Found</h1>
          <p className="text-gray-400">Please select a valid project to continue.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              Back
            </button>
            <div className="w-px h-6 bg-gray-600" />
            <div>
              <h1 className="text-xl font-semibold flex items-center gap-2">
                <Zap className="w-6 h-6 text-orange-500" />
                SpinScribe Multi-Agent Workflow
              </h1>
              <p className="text-sm text-gray-400">Intelligent content creation with AI agents</p>
            </div>
          </div>

          {step !== 'configure' && workflowStatus && (
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${
                step === 'running' ? 'bg-yellow-500 animate-pulse' :
                step === 'completed' ? 'bg-green-500' : 'bg-red-500'
              }`} />
              <span className="text-sm">
                {step === 'running' ? 'Agents Working...' :
                 step === 'completed' ? 'Completed' : 'Error'}
              </span>
              {workflowStatus?.progress && (
                <span className="text-xs text-gray-400">
                  {Math.round(workflowStatus.progress)}%
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {step === 'configure' && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold mb-4">Configure Your Workflow</h2>
              <p className="text-gray-400">Set up your AI-powered content creation</p>
            </div>

            <div className="bg-gray-800 rounded-xl p-6 space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Content Title *
                </label>
                <input
                  type="text"
                  value={config.title}
                  onChange={(e) => setConfig(prev => ({ ...prev, title: e.target.value }))}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                  placeholder="Enter your content title..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Content Type
                </label>
                <select
                  value={config.contentType}
                  onChange={(e) => setConfig(prev => ({ ...prev, contentType: e.target.value }))}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-orange-500"
                >
                  <option value="article">Article</option>
                  <option value="blog_post">Blog Post</option>
                  <option value="landing_page">Landing Page</option>
                  <option value="email">Email</option>
                  <option value="social_media">Social Media</option>
                </select>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                <div>
                  <h4 className="font-medium text-white">Initial Draft</h4>
                  <p className="text-sm text-gray-400">Do you have existing content to enhance?</p>
                </div>
                <button
                  onClick={() => setConfig(prev => ({ ...prev, hasInitialDraft: !prev.hasInitialDraft }))}
                  className={`w-12 h-6 rounded-full transition-all duration-300 ${
                    config.hasInitialDraft ? 'bg-orange-500' : 'bg-gray-500'
                  }`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full transition-transform duration-300 ${
                    config.hasInitialDraft ? 'transform translate-x-6' : 'transform translate-x-0.5'
                  }`} />
                </button>
              </div>

              {config.hasInitialDraft && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Initial Draft Content
                  </label>
                  <textarea
                    value={config.initialDraft || ''}
                    onChange={(e) => setConfig(prev => ({ ...prev, initialDraft: e.target.value }))}
                    rows={6}
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                    placeholder="Paste your initial draft here..."
                  />
                </div>
              )}

              <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                <div>
                  <h4 className="font-medium text-white">Use Project Documents</h4>
                  <p className="text-sm text-gray-400">Use uploaded documents for context</p>
                </div>
                <button
                  onClick={() => setConfig(prev => ({ ...prev, useProjectDocuments: !prev.useProjectDocuments }))}
                  className={`w-12 h-6 rounded-full transition-all duration-300 ${
                    config.useProjectDocuments ? 'bg-orange-500' : 'bg-gray-500'
                  }`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full transition-transform duration-300 ${
                    config.useProjectDocuments ? 'transform translate-x-6' : 'transform translate-x-0.5'
                  }`} />
                </button>
              </div>

              <button
                onClick={startWorkflow}
                disabled={!config.title.trim()}
                className="w-full px-6 py-4 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Play className="w-5 h-5" />
                Start AI Workflow
              </button>
            </div>
          </div>
        )}

        {step === 'running' && (
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">AI Agents Working</h2>
              <p className="text-gray-400">Multi-agent collaboration in progress...</p>
            </div>

            {/* Simple Progress Display */}
            <div className="bg-gray-800 rounded-xl p-6">
              <div className="space-y-4">
                {[
                  { stage: 'Document Processing', progress: workflowStatus?.progress > 10, icon: '📚' },
                  { stage: 'Style Analysis', progress: workflowStatus?.progress > 30, icon: '🎨' },
                  { stage: 'Content Planning', progress: workflowStatus?.progress > 50, icon: '📋' },
                  { stage: 'Content Generation', progress: workflowStatus?.progress > 70, icon: '✍️' },
                  { stage: 'Quality Assurance', progress: workflowStatus?.progress > 90, icon: '🔍' },
                ].map((item, index) => (
                  <div key={index} className="flex items-center gap-4">
                    <span className="text-2xl">{item.icon}</span>
                    <div className="flex-1">
                      <p className="font-medium text-white">{item.stage}</p>
                      <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                        <div className={`h-2 rounded-full transition-all duration-500 ${
                          item.progress ? 'bg-gradient-to-r from-orange-500 to-violet-600' : 'bg-gray-700'
                        }`} style={{ width: item.progress ? '100%' : '0%' }} />
                      </div>
                    </div>
                    {item.progress && <CheckCircle className="w-5 h-5 text-green-500" />}
                  </div>
                ))}
              </div>

              {workflowStatus && (
                <div className="mt-6 p-4 bg-gray-700 rounded-lg">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-400">Overall Progress</span>
                    <span className="text-white font-medium">
                      {Math.round(workflowStatus.progress || 0)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-600 rounded-full h-2 mt-2">
                    <div 
                      className="bg-gradient-to-r from-orange-500 to-violet-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${workflowStatus.progress || 0}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {step === 'completed' && workflowStatus && (
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-3xl font-bold mb-2">Content Created Successfully!</h2>
              <p className="text-gray-400">Your AI agents have completed the workflow</p>
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold">Generated Content</h3>
                <div className="flex gap-2">
                  <button
                    onClick={copyToClipboard}
                    className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors flex items-center gap-2"
                  >
                    <Copy className="w-4 h-4" />
                    Copy
                  </button>
                  <button
                    onClick={downloadContent}
                    className="px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-colors flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                </div>
              </div>
              
              <div className="bg-gray-900 rounded-lg p-6 max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-gray-300 leading-relaxed">
                  {workflowStatus.final_content}
                </pre>
              </div>
            </div>

            <div className="text-center mt-8">
              <button
                onClick={() => {
                  setStep('configure');
                  setWorkflowStatus(null);
                  setConfig({
                    title: '',
                    contentType: 'article',
                    hasInitialDraft: false,
                    useProjectDocuments: true,
                    enableCheckpoints: true
                  });
                }}
                className="px-8 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
              >
                Create Another Content
              </button>
            </div>
          </div>
        )}

        {step === 'error' && (
          <div className="max-w-2xl mx-auto text-center">
            <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Workflow Failed</h2>
            <p className="text-gray-400 mb-6">{error || 'An error occurred during content creation'}</p>
            <button
              onClick={() => {
                setStep('configure');
                setError('');
                setWorkflowStatus(null);
              }}
              className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}