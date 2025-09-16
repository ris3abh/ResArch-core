// frontend/src/components/WorkflowPage.tsx
// Enhanced version with proper API integration based on backend schemas

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
  Clock,
  Play,
  Pause,
  StopCircle,
  Users
} from 'lucide-react';
import { 
  apiService, 
  Project, 
  WorkflowResponse, 
  WorkflowCreateRequest 
} from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import ChatWorkflowInterface from './workflow/ChatWorkflowInterface';

// Local interface for workflow configuration form
interface WorkflowConfig {
  title: string;
  contentType: string;
  initialDraft: string;
  useProjectDocuments: boolean;
}

type WorkflowState = 'setup' | 'starting' | 'running' | 'paused' | 'completed' | 'error';

const WorkflowPage: React.FC = () => {
  const { projectId, workflowId: urlWorkflowId } = useParams<{ projectId: string; workflowId?: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  // State management
  const [workflowState, setWorkflowState] = useState<WorkflowState>('setup');
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowResponse | null>(null);
  const [workflowConfig, setWorkflowConfig] = useState<WorkflowConfig>({
    title: '',
    contentType: 'article',
    initialDraft: '',
    useProjectDocuments: true
  });
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [activeWorkflows, setActiveWorkflows] = useState<WorkflowResponse[]>([]);

  // Content type options
  const contentTypes = [
    { value: 'article', label: 'Article' },
    { value: 'blog_post', label: 'Blog Post' },
    { value: 'email', label: 'Email' },
    { value: 'social_media', label: 'Social Media Post' },
    { value: 'marketing_copy', label: 'Marketing Copy' },
    { value: 'technical_docs', label: 'Technical Documentation' },
    { value: 'report', label: 'Report' },
    { value: 'proposal', label: 'Business Proposal' }
  ];

  // Load project and check for active workflows
  useEffect(() => {
    if (projectId) {
      loadProjectData();
    }
  }, [projectId]);

  // Handle URL workflow ID - load existing workflow
  useEffect(() => {
    if (urlWorkflowId && projectId) {
      loadExistingWorkflow(urlWorkflowId);
    }
  }, [urlWorkflowId, projectId]);

  const loadProjectData = async () => {
    if (!projectId) return;

    try {
      setIsLoading(true);
      setError('');

      // Load project data
      const projectData = await apiService.getProject(projectId);
      setProject(projectData);

      // Only check for active workflows if no specific workflow ID in URL
      if (!urlWorkflowId) {
        await checkActiveWorkflows();
      }
    } catch (err: any) {
      console.error('Failed to load project data:', err);
      setError('Failed to load project data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const checkActiveWorkflows = async () => {
    if (!projectId) return;

    try {
      // Use the listWorkflows API with proper parameters
      const workflows = await apiService.listWorkflows({
        project_id: projectId,
        status: 'running'
      });
      
      setActiveWorkflows(workflows);
      
      // If there are active workflows, show them first
      if (workflows.length > 0) {
        // User can choose to resume or start new
        setWorkflowState('setup');
      } else {
        setWorkflowState('setup');
      }
    } catch (error) {
      console.warn('Failed to check active workflows:', error);
      // If the endpoint fails, just proceed to setup
      setWorkflowState('setup');
    }
  };

  const loadExistingWorkflow = async (workflowId: string) => {
    try {
      setIsLoading(true);
      // Use getWorkflowStatus to load existing workflow
      const workflow = await apiService.getWorkflowStatus(workflowId);
      setCurrentWorkflow(workflow);
      
      // Determine state based on workflow status
      switch (workflow.status) {
        case 'running':
        case 'in_progress':
          setWorkflowState('running');
          break;
        case 'paused':
          setWorkflowState('paused');
          break;
        case 'completed':
          setWorkflowState('completed');
          break;
        case 'failed':
        case 'error':
          setWorkflowState('error');
          setError(workflow.message || 'Workflow encountered an error');
          break;
        default:
          setWorkflowState('running');
      }
    } catch (err: any) {
      console.error('Failed to load workflow:', err);
      setError('Failed to load workflow. It may have been completed or deleted.');
      setWorkflowState('error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartWorkflow = async () => {
    if (!projectId || !workflowConfig.title.trim()) {
      setError('Please provide a title for your content');
      return;
    }

    try {
      setWorkflowState('starting');
      setError('');

      // Create the workflow using the proper API endpoint
      const workflowRequest: WorkflowCreateRequest = {
        project_id: projectId,
        title: workflowConfig.title,
        content_type: workflowConfig.contentType,
        initial_draft: workflowConfig.initialDraft || undefined,
        use_project_documents: workflowConfig.useProjectDocuments,
        chat_id: undefined // Will be created automatically if needed
      };

      const workflow = await apiService.startWorkflow(workflowRequest);

      // Store the workflow data
      setCurrentWorkflow(workflow);
      setWorkflowState('running');

      // Update URL to include workflow ID
      navigate(`/workflow/${projectId}/${workflow.workflow_id}`, { replace: true });
    } catch (err: any) {
      console.error('Failed to start workflow:', err);
      setError(err.message || 'Failed to start workflow. Please try again.');
      setWorkflowState('setup');
    }
  };

  const handleResumeWorkflow = (workflow: WorkflowResponse) => {
    setCurrentWorkflow(workflow);
    setWorkflowState('running');
    navigate(`/workflow/${projectId}/${workflow.workflow_id}`);
  };

  const handleWorkflowComplete = (result: any) => {
    setWorkflowState('completed');
    if (currentWorkflow) {
      setCurrentWorkflow({
        ...currentWorkflow,
        status: 'completed',
        final_content: result?.final_content || result?.content
      });
    }
    console.log('Workflow completed:', result);
  };

  const handlePauseWorkflow = async () => {
    if (!currentWorkflow) return;

    try {
      // Note: pauseWorkflow might not be implemented in backend yet
      // For now, just update local state
      setWorkflowState('paused');
    } catch (err: any) {
      console.error('Failed to pause workflow:', err);
      setError('Failed to pause workflow');
    }
  };

  const handleCancelWorkflow = async () => {
    if (!currentWorkflow) return;

    if (!window.confirm('Are you sure you want to cancel this workflow? This action cannot be undone.')) {
      return;
    }

    try {
      await apiService.cancelWorkflow(currentWorkflow.workflow_id);
      setWorkflowState('setup');
      navigate(`/project/${projectId}`);
    } catch (err: any) {
      console.error('Failed to cancel workflow:', err);
      setError('Failed to cancel workflow');
    }
  };

  const handleBackToProject = () => {
    navigate(`/project/${projectId}`);
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
    // Clear workflow ID from URL
    navigate(`/workflow/${projectId}`);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-orange-500 mx-auto mb-4" />
          <p className="text-gray-300">Loading workflow...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={handleBackToProject}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              title="Back to Project"
            >
              <ArrowLeft className="w-5 h-5 text-gray-300" />
            </button>
            <div>
              <h1 className="text-xl font-semibold text-white">
                {workflowState === 'setup' ? 'Setup AI Workflow' :
                 workflowState === 'starting' ? 'Starting Workflow...' :
                 workflowState === 'running' ? 'AI Workflow in Progress' :
                 workflowState === 'paused' ? 'Workflow Paused' :
                 workflowState === 'completed' ? 'Workflow Completed' : 
                 'Workflow Error'}
              </h1>
              {project && (
                <p className="text-sm text-gray-400">
                  {project.name} {project.client_name && `• ${project.client_name}`}
                </p>
              )}
            </div>
          </div>

          {/* Status and Controls */}
          <div className="flex items-center gap-4">
            {workflowState === 'running' && currentWorkflow && (
              <>
                <div className="flex items-center gap-2 text-green-400">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  <span className="text-sm">Live</span>
                </div>
                <button
                  onClick={handlePauseWorkflow}
                  className="px-3 py-1.5 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors flex items-center gap-2"
                >
                  <Pause className="w-4 h-4" />
                  Pause
                </button>
                <button
                  onClick={handleCancelWorkflow}
                  className="px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                >
                  <StopCircle className="w-4 h-4" />
                  Cancel
                </button>
              </>
            )}
            
            <div className="flex items-center gap-2 text-gray-400">
              <Users className="w-4 h-4" />
              <span className="text-sm">{user?.first_name || user?.email}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6">
        {/* Show active workflows if any exist */}
        {workflowState === 'setup' && activeWorkflows.length > 0 && (
          <div className="max-w-4xl mx-auto mb-6">
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h2 className="text-lg font-semibold text-white mb-4">Active Workflows</h2>
              <div className="space-y-3">
                {activeWorkflows.map((workflow) => (
                  <div
                    key={workflow.workflow_id}
                    className="bg-gray-700 rounded-lg p-4 flex items-center justify-between"
                  >
                    <div>
                      <h3 className="font-medium text-white">{workflow.title}</h3>
                      <p className="text-sm text-gray-400">
                        Stage: {workflow.current_stage || 'Processing'}
                      </p>
                      {workflow.created_at && (
                        <p className="text-xs text-gray-500 mt-1">
                          Started: {new Date(workflow.created_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => handleResumeWorkflow(workflow)}
                      className="px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2"
                    >
                      <Play className="w-4 h-4" />
                      Resume
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Setup State - Configuration Form */}
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
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
                    placeholder="e.g., 'The Future of AI in Healthcare'"
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
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
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
                    Initial Draft or Requirements (Optional)
                  </label>
                  <textarea
                    value={workflowConfig.initialDraft}
                    onChange={(e) => setWorkflowConfig(prev => ({ ...prev, initialDraft: e.target.value }))}
                    rows={4}
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
                    placeholder="Provide any initial content, outline, or specific requirements..."
                  />
                </div>

                {/* Options */}
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={workflowConfig.useProjectDocuments}
                      onChange={(e) => setWorkflowConfig(prev => ({ ...prev, useProjectDocuments: e.target.checked }))}
                      className="w-5 h-5 text-orange-500 bg-gray-700 border-gray-600 rounded focus:ring-orange-500"
                    />
                    <span className="text-sm text-gray-300">Use project documents and knowledge base</span>
                  </label>
                </div>

                {/* Error Display */}
                {error && (
                  <div className="p-4 bg-red-900/20 border border-red-600/30 rounded-lg flex items-center gap-3">
                    <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                    <p className="text-red-300">{error}</p>
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
                    disabled={!workflowConfig.title.trim()}
                    className="flex-1 px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
                  >
                    <Play className="w-4 h-4" />
                    Start AI Workflow
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Starting state */}
        {workflowState === 'starting' && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Loader2 className="w-12 h-12 animate-spin text-orange-500 mx-auto mb-4" />
              <p className="text-lg text-gray-300">Starting workflow...</p>
              <p className="text-sm text-gray-500 mt-2">Initializing AI agents</p>
            </div>
          </div>
        )}

        {/* Running state - Pass workflow ID to ChatWorkflowInterface */}
        {workflowState === 'running' && currentWorkflow && (
          <ChatWorkflowInterface
            workflowId={currentWorkflow.workflow_id}
            projectId={projectId!}
            onWorkflowComplete={handleWorkflowComplete}
          />
        )}

        {/* Paused state */}
        {workflowState === 'paused' && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Clock className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">Workflow Paused</h2>
              <p className="text-gray-300 mb-6">Your workflow has been paused</p>
              <button
                onClick={() => setWorkflowState('running')}
                className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2 mx-auto"
              >
                <Play className="w-5 h-5" />
                Resume Workflow
              </button>
            </div>
          </div>
        )}

        {/* Completed state */}
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
                    <pre className="text-gray-300 whitespace-pre-wrap font-sans">{currentWorkflow.final_content}</pre>
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
          <div className="max-w-2xl mx-auto">
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 text-center">
              <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">Workflow Error</h2>
              <p className="text-gray-300 mb-6">{error || 'An error occurred during the workflow'}</p>
              <div className="flex gap-3 justify-center">
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