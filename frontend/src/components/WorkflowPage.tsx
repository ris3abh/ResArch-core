// frontend/src/components/WorkflowPage.tsx
// UPDATED to use the new chat interface

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
  
  const [project, setProject] = useState<Project | null>(null);
  const [workflowState, setWorkflowState] = useState<WorkflowState>('setup');
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowExecution | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [showSetupForm, setShowSetupForm] = useState(false);

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
      setError('Please provide a workflow title');
      return;
    }

    try {
      setIsLoading(true);
      const response = await apiService.startWorkflow({
        project_id: projectId,
        title: workflowConfig.title,
        content_type: workflowConfig.contentType,
        initial_draft: workflowConfig.initialDraft || undefined,
        use_project_documents: workflowConfig.useProjectDocuments
      });
      
      setCurrentWorkflow({
        workflow_id: response.workflow_id,
        project_id: projectId,
        title: workflowConfig.title,
        content_type: workflowConfig.contentType,
        status: response.status,
        current_stage: response.current_stage,
        progress: response.progress,
        created_at: new Date().toISOString()
      });
      
      setWorkflowState('running');
      setShowSetupForm(false);
    } catch (error: any) {
      console.error('Failed to start workflow:', error);
      setError('Failed to start workflow: ' + (error.message || 'Unknown error'));
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
                {workflowState === 'setup' ? 'Start AI Workflow' : 
                 workflowState === 'running' ? 'AI Workflow Chat' : 
                 workflowState === 'completed' ? 'Workflow Completed' : 
                 'Workflow Error'}
              </h1>
              <p className="text-sm text-gray-400">
                {project?.name} {project?.client_name && `• ${project.client_name}`}
              </p>
            </div>
          </div>

          {/* Status Indicator */}
          <div className="flex items-center gap-2">
            {workflowState === 'running' && currentWorkflow && (
              <>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-green-400 text-sm">
                  {currentWorkflow.current_stage || 'Running'}
                </span>
              </>
            )}
            {workflowState === 'completed' && (
              <>
                <CheckCircle className="w-4 h-4 text-green-500" />
                <span className="text-green-400 text-sm">Completed</span>
              </>
            )}
            {workflowState === 'error' && (
              <>
                <AlertCircle className="w-4 h-4 text-red-500" />
                <span className="text-red-400 text-sm">Error</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="h-[calc(100vh-73px)]">
        {workflowState === 'setup' && (
          <div className="h-full flex items-center justify-center">
            <div className="max-w-2xl w-full mx-auto p-6">
              <div className="text-center mb-8">
                <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-violet-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Zap className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Start AI Workflow</h2>
                <p className="text-gray-400">Configure your content creation workflow</p>
              </div>

              <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Content Title *
                    </label>
                    <input
                      type="text"
                      value={workflowConfig.title}
                      onChange={(e) => setWorkflowConfig(prev => ({ ...prev, title: e.target.value }))}
                      className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                      placeholder="What content do you want to create?"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Content Type
                    </label>
                    <select
                      value={workflowConfig.contentType}
                      onChange={(e) => setWorkflowConfig(prev => ({ ...prev, contentType: e.target.value }))}
                      className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-orange-500"
                    >
                      {contentTypes.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Initial Draft (Optional)
                    </label>
                    <textarea
                      value={workflowConfig.initialDraft}
                      onChange={(e) => setWorkflowConfig(prev => ({ ...prev, initialDraft: e.target.value }))}
                      rows={4}
                      className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                      placeholder="Provide an initial draft or outline (optional)..."
                    />
                  </div>

                  <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                    <div>
                      <h4 className="font-medium text-white">Use Project Documents</h4>
                      <p className="text-sm text-gray-400">Include uploaded documents as context</p>
                    </div>
                    <button
                      onClick={() => setWorkflowConfig(prev => ({ ...prev, useProjectDocuments: !prev.useProjectDocuments }))}
                      className={`w-12 h-6 rounded-full transition-all duration-300 ${
                        workflowConfig.useProjectDocuments ? 'bg-gradient-to-r from-orange-500 to-violet-600' : 'bg-gray-500'
                      }`}
                    >
                      <div className={`w-5 h-5 bg-white rounded-full transition-transform duration-300 ${
                        workflowConfig.useProjectDocuments ? 'transform translate-x-6' : 'transform translate-x-0.5'
                      }`} />
                    </button>
                  </div>
                </div>

                {error && (
                  <div className="mt-4 p-3 bg-red-900/30 border border-red-500/50 rounded-lg">
                    <p className="text-red-400 text-sm">{error}</p>
                  </div>
                )}

                <div className="mt-6 flex gap-3">
                  <button
                    onClick={handleBackToProject}
                    className="flex-1 px-4 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleStartWorkflow}
                    disabled={!workflowConfig.title.trim() || isLoading}
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <Zap className="w-4 h-4" />
                        Start Workflow
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {workflowState === 'running' && currentWorkflow && (
          <ChatWorkflowInterface
            workflowId={currentWorkflow.workflow_id}
            projectId={projectId!}
            onWorkflowComplete={handleWorkflowComplete}
          />
        )}

        {workflowState === 'completed' && currentWorkflow && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-2xl px-6">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-6" />
              <h2 className="text-2xl font-bold text-white mb-4">
                Workflow Completed Successfully!
              </h2>
              <p className="text-gray-300 mb-6">
                Your content "{currentWorkflow.title}" has been generated and is ready for review.
              </p>

              {currentWorkflow.final_content && (
                <div className="bg-gray-800 rounded-lg p-6 mb-6 text-left">
                  <h3 className="text-lg font-semibold text-white mb-4">Generated Content</h3>
                  <div className="bg-gray-900 rounded-lg p-4 text-gray-100 max-h-96 overflow-y-auto">
                    <pre className="whitespace-pre-wrap text-sm">
                      {currentWorkflow.final_content}
                    </pre>
                  </div>
                </div>
              )}

              <div className="flex gap-4 justify-center">
                <button
                  onClick={handleBackToProject}
                  className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Back to Project
                </button>
                <button
                  onClick={handleStartNewWorkflow}
                  className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2"
                >
                  <Zap className="w-4 h-4" />
                  Start New Workflow
                </button>
              </div>
            </div>
          </div>
        )}

        {workflowState === 'error' && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md px-6">
              <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-6" />
              <h2 className="text-2xl font-bold text-white mb-4">
                Workflow Error
              </h2>
              <p className="text-gray-300 mb-6">
                {error || 'An error occurred while processing your workflow.'}
              </p>
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
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkflowPage;