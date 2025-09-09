// frontend/src/components/WorkflowPage.tsx
// FIXED VERSION - Properly integrates ChatWorkflowInterface

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Zap, 
  FileText, 
  MessageCircle, 
  Settings,
  Loader2,
  AlertCircle,
  CheckCircle,
  Play,
  Users
} from 'lucide-react';
import { apiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import ChatWorkflowInterface from './workflow/ChatWorkflowInterface';

interface Project {
  id: string;
  name: string;
  description?: string;
  client_name?: string;
}

interface WorkflowExecution {
  workflow_id: string;
  project_id: string;
  title: string;
  content_type: string;
  status: string;
  current_stage?: string;
  progress?: number;
  final_content?: string;
  created_at: string;
  completed_at?: string;
}

type WorkflowState = 'setup' | 'running' | 'completed' | 'error';

const WorkflowPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [project, setProject] = useState<Project | null>(null);
  const [workflowState, setWorkflowState] = useState<WorkflowState>('setup');
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowExecution | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Setup form state
  const [workflowConfig, setWorkflowConfig] = useState({
    title: '',
    contentType: 'article',
    initialDraft: '',
    useProjectDocuments: true
  });

  useEffect(() => {
    if (projectId) {
      loadProjectData();
    }
  }, [projectId]);

  const loadProjectData = async () => {
    if (!projectId) return;

    try {
      setIsLoading(true);
      const projectData = await apiService.getProject(projectId);
      setProject(projectData);
      
      // Check for active workflows
      await checkActiveWorkflow();
    } catch (error: any) {
      console.error('Failed to load project data:', error);
      setError('Failed to load project data');
    } finally {
      setIsLoading(false);
    }
  };

  const checkActiveWorkflow = async () => {
    if (!projectId) return;

    try {
      const activeWorkflows = await apiService.getActiveWorkflows(projectId);
      
      if (activeWorkflows && activeWorkflows.length > 0) {
        const workflow = activeWorkflows[0];
        setCurrentWorkflow(workflow);
        
        switch (workflow.status) {
          case 'running':
          case 'paused':
            setWorkflowState('running');
            break;
          case 'completed':
            setWorkflowState('completed');
            break;
          case 'error':
          case 'failed':
            setWorkflowState('error');
            break;
          default:
            setWorkflowState('setup');
        }
      } else {
        setWorkflowState('setup');
      }
    } catch (error) {
      console.warn('Failed to check active workflows:', error);
      setWorkflowState('setup');
    }
  };

  const handleStartWorkflow = async () => {
    if (!projectId || !workflowConfig.title.trim()) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      setIsLoading(true);
      setError('');

      // Create workflow execution
      const workflowExecution = await apiService.createWorkflowExecution({
        project_id: projectId,
        title: workflowConfig.title,
        content_type: workflowConfig.contentType,
        initial_draft: workflowConfig.initialDraft || undefined,
        use_project_documents: workflowConfig.useProjectDocuments
      });

      setCurrentWorkflow(workflowExecution);
      setWorkflowState('running');
    } catch (error: any) {
      console.error('Failed to start workflow:', error);
      setError(error.message || 'Failed to start workflow');
    } finally {
      setIsLoading(false);
    }
  };

  const handleWorkflowComplete = (result: any) => {
    setCurrentWorkflow(prev => prev ? {
      ...prev,
      status: 'completed',
      final_content: result.final_content,
      completed_at: new Date().toISOString()
    } : null);
    
    setWorkflowState('completed');
  };

  const handleBackToProject = () => {
    if (projectId) {
      navigate(`/project/${projectId}`);
    } else {
      navigate('/dashboard');
    }
  };

  const handleStartNewWorkflow = () => {
    setCurrentWorkflow(null);
    setWorkflowState('setup');
    setError('');
    setWorkflowConfig({
      title: '',
      contentType: 'article',
      initialDraft: '',
      useProjectDocuments: true
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-orange-500 animate-spin mx-auto mb-4" />
          <p className="text-white">Loading workflow...</p>
        </div>
      </div>
    );
  }

  if (error && workflowState !== 'error') {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-400 mb-4">{error}</p>
          <div className="space-x-3">
            <button
              onClick={handleBackToProject}
              className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
            >
              Back to Project
            </button>
            <button
              onClick={() => setError('')}
              className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  const contentTypes = [
    { value: 'article', label: 'Article' },
    { value: 'blog_post', label: 'Blog Post' },
    { value: 'email', label: 'Email' },
    { value: 'social_media', label: 'Social Media' },
    { value: 'marketing_copy', label: 'Marketing Copy' },
    { value: 'technical_docs', label: 'Technical Documentation' },
  ];

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={handleBackToProject}
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              Back to Project
            </button>
            <div className="w-px h-6 bg-gray-600" />
            <div>
              <h1 className="text-xl font-semibold text-white">
                {workflowState === 'setup' ? 'Setup Content Workflow' : 
                 workflowState === 'running' ? 'AI Workflow in Progress' :
                 workflowState === 'completed' ? 'Workflow Completed' : 'Workflow Error'}
              </h1>
              {project && (
                <p className="text-sm text-gray-400">
                  {project.name} {project.client_name && `• ${project.client_name}`}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {workflowState === 'running' && (
              <div className="flex items-center gap-2 text-green-400">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                <span className="text-sm">Live</span>
              </div>
            )}
            <div className="flex items-center gap-2 text-gray-400">
              <Users className="w-4 h-4" />
              <span className="text-sm">{user?.first_name || user?.email}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6">
        {/* Setup State */}
        {workflowState === 'setup' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-violet-600 rounded-lg flex items-center justify-center">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">Create AI Content</h2>
                  <p className="text-sm text-gray-400">Configure your multi-agent workflow</p>
                </div>
              </div>

              <form onSubmit={(e) => { e.preventDefault(); handleStartWorkflow(); }} className="space-y-6">
                {/* Title */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Content Title *
                  </label>
                  <input
                    type="text"
                    value={workflowConfig.title}
                    onChange={(e) => setWorkflowConfig(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                    placeholder="e.g., 'AI Revolution in Healthcare'"
                    required
                  />
                </div>

                {/* Content Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Content Type
                  </label>
                  <select
                    value={workflowConfig.contentType}
                    onChange={(e) => setWorkflowConfig(prev => ({ ...prev, contentType: e.target.value }))}
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-orange-500"
                  >
                    {contentTypes.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Initial Draft */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Initial Draft (Optional)
                  </label>
                  <textarea
                    value={workflowConfig.initialDraft}
                    onChange={(e) => setWorkflowConfig(prev => ({ ...prev, initialDraft: e.target.value }))}
                    rows={4}
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                    placeholder="Provide any initial content, outline, or requirements..."
                  />
                </div>

                {/* Options */}
                <div className="space-y-3">
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={workflowConfig.useProjectDocuments}
                      onChange={(e) => setWorkflowConfig(prev => ({ ...prev, useProjectDocuments: e.target.checked }))}
                      className="w-5 h-5 text-orange-500 bg-gray-700 border-gray-600 rounded focus:ring-orange-500"
                    />
                    <span className="text-sm text-gray-300">Use project documents and knowledge base</span>
                  </label>
                </div>

                {error && (
                  <div className="p-4 bg-red-900/20 border border-red-700 rounded-lg">
                    <p className="text-red-400 text-sm">{error}</p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={handleBackToProject}
                    className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isLoading || !workflowConfig.title.trim()}
                    className="flex-1 px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Starting Workflow...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4" />
                        Start AI Workflow
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Running State - Use ChatWorkflowInterface */}
        {workflowState === 'running' && currentWorkflow && (
          <ChatWorkflowInterface
            workflowId={currentWorkflow.workflow_id}
            projectId={projectId!}
            onWorkflowComplete={handleWorkflowComplete}
          />
        )}

        {/* Completed State */}
        {workflowState === 'completed' && currentWorkflow && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-green-500 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">Workflow Completed Successfully!</h2>
                  <p className="text-sm text-gray-400">Your content has been generated and is ready for review</p>
                </div>
              </div>

              {currentWorkflow.final_content && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-white mb-3">Generated Content:</h3>
                  <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto">
                    <pre className="text-gray-300 whitespace-pre-wrap">{currentWorkflow.final_content}</pre>
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={handleBackToProject}
                  className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Back to Project
                </button>
                <button
                  onClick={handleStartNewWorkflow}
                  className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
                >
                  Create Another Content
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {workflowState === 'error' && (
          <div className="max-w-2xl mx-auto text-center">
            <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Workflow Failed</h2>
            <p className="text-gray-400 mb-6">{error || 'An error occurred during content creation'}</p>
            <div className="flex gap-4 justify-center">
              <button
                onClick={handleBackToProject}
                className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                Back to Project
              </button>
              <button
                onClick={handleStartNewWorkflow}
                className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkflowPage;