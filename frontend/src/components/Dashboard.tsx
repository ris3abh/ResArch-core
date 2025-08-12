// src/components/Dashboard.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Plus, 
  Search, 
  Zap, 
  FileText, 
  Activity,
  Loader2
} from 'lucide-react';
import { apiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface Project {
  id: string;
  name: string;
  description?: string;
  client_name?: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  document_count?: number;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);
  
  useEffect(() => {
    loadProjects();
  }, []);

  // Auto-hide messages after 4 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  const showMessage = (text: string, type: 'success' | 'error' = 'success') => {
    setMessage({ type, text });
  };

  const loadProjects = async () => {
    try {
      setIsLoading(true);
      const projectsData = await apiService.getProjects();
      setProjects(projectsData);
    } catch (error: any) {
      console.error('Failed to load projects:', error);
      showMessage('Failed to load projects', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;

    try {
      setIsCreating(true);
      const newProject = await apiService.createProject({
        name: newProjectName,
        description: newProjectDescription || undefined,
      });

      setProjects([newProject, ...projects]);
      setShowCreateModal(false);
      setNewProjectName('');
      setNewProjectDescription('');
      showMessage('Project created successfully!');
    } catch (error: any) {
      console.error('Failed to create project:', error);
      showMessage('Failed to create project: ' + error.message, 'error');
    } finally {
      setIsCreating(false);
    }
  };

  const handleStartWorkflow = (projectId: string) => {
    navigate(`/workflow/${projectId}`);
  };

  const handleOpenProject = (projectId: string) => {
    navigate(`/project/${projectId}`);
  };

  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (project.client_name && project.client_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Message Toast */}
      {message && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-lg text-white transition-all duration-300 ${
          message.type === 'success' ? 'bg-green-500' : 'bg-red-500'
        }`}>
          {message.type === 'success' ? '✅' : '❌'} {message.text}
        </div>
      )}

      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-violet-600 rounded-lg flex items-center justify-center">
                <span className="text-lg font-bold text-white">S</span>
              </div>
              <div>
                <h1 className="text-xl font-semibold">SpinScribe Dashboard</h1>
                <p className="text-sm text-gray-400">Multi-Agent Content Creation System</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-300">
              Welcome back, {user?.first_name}
            </div>
            <button
              onClick={logout}
              className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <button
              onClick={() => setShowCreateModal(true)}
              className="p-6 bg-gradient-to-r from-orange-500 to-violet-600 rounded-xl text-left hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
            >
              <Plus className="w-8 h-8 mb-3" />
              <h3 className="font-semibold mb-1">Create New Project</h3>
              <p className="text-sm text-orange-100">Start a new content creation project</p>
            </button>
            
            <div className="p-6 bg-gray-800 border border-gray-700 rounded-xl text-left">
              <Zap className="w-8 h-8 mb-3 text-yellow-500" />
              <h3 className="font-semibold mb-1">AI Workflows</h3>
              <p className="text-sm text-gray-400">Multi-agent content creation</p>
            </div>
            
            <div className="p-6 bg-gray-800 border border-gray-700 rounded-xl text-left">
              <Activity className="w-8 h-8 mb-3 text-green-500" />
              <h3 className="font-semibold mb-1">Analytics</h3>
              <p className="text-sm text-gray-400">Track content performance</p>
            </div>
          </div>
        </div>

        {/* Projects Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold">Your Projects</h2>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                />
              </div>
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-300 mb-2">No projects yet</h3>
              <p className="text-gray-500 mb-4">Create your first project to get started with SpinScribe</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
              >
                Create Project
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredProjects.map((project) => (
                <div
                  key={project.id}
                  className="bg-gray-800 border border-gray-700 rounded-xl p-6 hover:bg-gray-750 transition-all duration-300"
                >
                  <div className="mb-4">
                    <h3 className="text-lg font-semibold mb-2">{project.name}</h3>
                    {project.description && (
                      <p className="text-gray-400 text-sm mb-2">{project.description}</p>
                    )}
                    {project.client_name && (
                      <p className="text-orange-400 text-sm">Client: {project.client_name}</p>
                    )}
                  </div>
                  
                  <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                    <span>📄 {project.document_count || 0} docs</span>
                    <span>📅 {formatDate(project.created_at)}</span>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleStartWorkflow(project.id)}
                      className="flex-1 px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center justify-center gap-2"
                    >
                      <Zap className="w-4 h-4" />
                      Start AI
                    </button>
                    <button
                      onClick={() => handleOpenProject(project.id)}
                      className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                    >
                      Manage
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Create New Project</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Project Name *
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                  placeholder="Enter project name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                  placeholder="Describe your project (optional)"
                />
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                disabled={isCreating}
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!newProjectName.trim() || isCreating}
                className="flex-1 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Project'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}