// src/components/WorkflowPage.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Zap, Settings, Play } from 'lucide-react';
import { apiService, Project } from '../services/api';
import SpinscribeWorkflowInterface from './workflow/SpinscribeWorkflowInterface';
import { toast } from '../utils/toast';

export default function WorkflowPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (projectId) {
      loadProject();
    }
  }, [projectId]);

  const loadProject = async () => {
    if (!projectId) return;
    
    try {
      setIsLoading(true);
      const projectData = await apiService.getProject(projectId);
      setProject(projectData);
    } catch (error: any) {
      console.error('Failed to load project:', error);
      setError('Failed to load project');
      toast.error('Failed to load project: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToProject = () => {
    navigate(`/project/${projectId}`);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-orange-500 to-violet-600 rounded-full mb-4 animate-pulse">
            <Zap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-xl font-semibold text-white mb-2">Loading Project...</h1>
          <p className="text-gray-400">Setting up your workspace</p>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">❌</span>
          </div>
          <h1 className="text-xl font-semibold text-white mb-2">Project Not Found</h1>
          <p className="text-gray-400 mb-4">{error || 'The requested project could not be loaded.'}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
          >
            Back to Dashboard
          </button>
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
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              Back to Project
            </button>
            <div className="w-px h-6 bg-gray-600" />
            <div>
              <h1 className="text-xl font-semibold flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-r from-orange-500 to-violet-600 rounded-lg flex items-center justify-center">
                  <Zap className="w-4 h-4 text-white" />
                </div>
                {project.name}
              </h1>
              <p className="text-sm text-gray-400">SpinScribe Multi-Agent Workflow</p>
            </div>
          </div>
          
          <div className="text-sm text-gray-400">
            Project ID: {project.id}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <SpinscribeWorkflowInterface />
    </div>
  );
}