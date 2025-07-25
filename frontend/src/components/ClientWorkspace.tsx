// src/components/ClientWorkspace.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { FolderOpen, Brain, MessageCircle, ArrowLeft, Loader2 } from 'lucide-react';
import { apiService, Project } from '../services/api';
import Sidebar from './Sidebar';
import ProjectsTab from './workspace/ProjectsTab';
import KnowledgeTab from './workspace/KnowledgeTab';
import ChatTab from './workspace/ChatTab';

type TabType = 'projects' | 'knowledge' | 'chat';

export default function ClientWorkspace() {
  const { clientId, projectId } = useParams<{ clientId?: string; projectId?: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>(projectId ? 'chat' : 'projects');
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Load project data if we have a projectId
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
    } catch (error) {
      console.error('Failed to load project:', error);
      setError('Failed to load project');
    } finally {
      setIsLoading(false);
    }
  };

  const tabs = [
    { id: 'projects', label: 'Projects', icon: FolderOpen },
    { id: 'knowledge', label: 'Knowledge', icon: Brain },
    { id: 'chat', label: 'Chat', icon: MessageCircle },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'projects':
        return <ProjectsTab clientId={clientId || 'default'} />;
      case 'knowledge':
        return <KnowledgeTab clientId={clientId || 'default'} />;
      case 'chat':
        return <ChatTab clientId={clientId || 'default'} projectId={projectId} />;
      default:
        return null;
    }
  };

  const getPageTitle = () => {
    if (projectId && project) {
      return project.name;
    }
    if (projectId && !project && !isLoading) {
      return 'Project Not Found';
    }
    if (clientId === '1') {
      return 'Acme Corporation';
    }
    return 'Workspace';
  };

  const getPageDescription = () => {
    if (projectId) {
      return 'Chat with AI agents for your project';
    }
    return 'Manage projects, knowledge base, and chat interactions';
  };

  if (projectId && isLoading) {
    return (
      <div className="flex h-screen bg-gray-900">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-orange-500 mx-auto mb-4" />
            <p className="text-gray-300">Loading project...</p>
          </div>
        </div>
      </div>
    );
  }

  if (projectId && error && !project) {
    return (
      <div className="flex h-screen bg-gray-900">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-red-400 mb-4">
              <MessageCircle className="w-16 h-16 mx-auto mb-4" />
              <p className="text-xl font-semibold mb-2">Project Not Found</p>
              <p className="text-gray-300">{error}</p>
            </div>
            <button
              onClick={() => navigate('/dashboard')}
              className="mt-4 px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-900">
      <Sidebar />
      
      <main className="flex-1 flex flex-col">
        <div className="border-b border-gray-700 bg-gray-800 backdrop-blur-xl">
          <div className="px-8 py-6">
            {/* Back button for project view */}
            {projectId && (
              <div className="flex items-center gap-3 mb-4">
                <button
                  onClick={() => navigate('/dashboard')}
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-5 h-5" />
                </button>
                <div>
                  <h1 className="text-2xl font-bold text-white">
                    {project?.name || 'Loading...'}
                  </h1>
                  {project?.client_name && (
                    <p className="text-orange-400 font-medium">
                      {project.client_name}
                    </p>
                  )}
                  {project?.description && (
                    <p className="text-gray-300 mt-1">
                      {project.description}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Regular header for workspace view */}
            {!projectId && (
              <>
                <h1 className="text-2xl font-bold text-white mb-2">
                  {getPageTitle()}
                </h1>
                <p className="text-gray-300">
                  {getPageDescription()}
                </p>
              </>
            )}
          </div>
          
          <div className="px-8">
            <div className="flex space-x-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                // Hide projects and knowledge tabs when in project chat mode
                if (projectId && (tab.id === 'projects' || tab.id === 'knowledge')) {
                  return null;
                }
                
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as TabType)}
                    className={`flex items-center gap-2 px-6 py-3 rounded-t-xl transition-all duration-300 ${
                      activeTab === tab.id
                        ? 'bg-gradient-to-r from-orange-500/20 to-violet-600/20 text-orange-500 border-t border-l border-r border-orange-500/30'
                        : 'text-gray-300 hover:text-white hover:bg-gray-700'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
        
        <div className="flex-1 overflow-hidden">
          {renderTabContent()}
        </div>
      </main>
    </div>
  );
}