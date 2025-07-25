// src/components/Dashboard.tsx
import React, { useState, useEffect } from 'react';
import { Plus, Search, Calendar, Activity, FileText, Loader2, Trash2, MoreVertical } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiService, Project } from '../services/api';
import Sidebar from './Sidebar';

export default function Dashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [newClientName, setNewClientName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setIsLoading(true);
      const projectsData = await apiService.getProjects();
      setProjects(projectsData);
    } catch (error) {
      console.error('Failed to load projects:', error);
      // Don't show error if it's a session expiration (user will be redirected)
      if (error instanceof Error && !error.message.includes('Session expired')) {
        setError('Failed to load projects');
      }
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
        client_name: newClientName || undefined,
      });

      setProjects([newProject, ...projects]);
      setShowCreateModal(false);
      setNewProjectName('');
      setNewProjectDescription('');
      setNewClientName('');
    } catch (error) {
      console.error('Failed to create project:', error);
      setError('Failed to create project');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!projectToDelete) return;

    try {
      setIsDeleting(true);
      await apiService.deleteProject(projectToDelete.id);
      setProjects(projects.filter(p => p.id !== projectToDelete.id));
      setShowDeleteModal(false);
      setProjectToDelete(null);
    } catch (error) {
      console.error('Failed to delete project:', error);
      setError('Failed to delete project');
    } finally {
      setIsDeleting(false);
    }
  };

  const openDeleteModal = (project: Project, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent navigation to project
    setProjectToDelete(project);
    setShowDeleteModal(true);
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

  const getProjectStats = () => {
    const totalProjects = projects.length;
    const totalDocuments = projects.reduce((sum, project) => sum + (project.document_count || 0), 0);
    const recentProjects = projects.filter(project => {
      const projectDate = new Date(project.created_at);
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return projectDate > weekAgo;
    }).length;

    return { totalProjects, totalDocuments, recentProjects };
  };

  const stats = getProjectStats();

  if (isLoading) {
    return (
      <div className="flex h-screen bg-gray-900">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-orange-500 mx-auto mb-4" />
            <p className="text-gray-300">Loading projects...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-900">
      <Sidebar />
      
      <main className="flex-1 overflow-hidden">
        <div className="h-full p-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">
              Welcome back, {user?.first_name}! 👋
            </h1>
            <p className="text-gray-300">
              Manage your content creation projects and collaborate with AI agents
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
              <p className="text-red-400">{error}</p>
              <button 
                onClick={() => setError('')}
                className="text-red-300 hover:text-red-200 text-sm mt-1"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/10 backdrop-blur-xl border border-orange-500/20 rounded-2xl p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-orange-500/20 rounded-xl">
                  <FileText className="w-6 h-6 text-orange-400" />
                </div>
                <div>
                  <p className="text-orange-400 font-medium">Total Projects</p>
                  <p className="text-2xl font-bold text-white">{stats.totalProjects}</p>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-violet-500/10 to-violet-600/10 backdrop-blur-xl border border-violet-500/20 rounded-2xl p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-violet-500/20 rounded-xl">
                  <FileText className="w-6 h-6 text-violet-400" />
                </div>
                <div>
                  <p className="text-violet-400 font-medium">Total Documents</p>
                  <p className="text-2xl font-bold text-white">{stats.totalDocuments}</p>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/10 backdrop-blur-xl border border-emerald-500/20 rounded-2xl p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-500/20 rounded-xl">
                  <Activity className="w-6 h-6 text-emerald-400" />
                </div>
                <div>
                  <p className="text-emerald-400 font-medium">This Week</p>
                  <p className="text-2xl font-bold text-white">{stats.recentProjects}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Search and Create */}
          <div className="flex flex-col sm:flex-row gap-4 mb-8">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search projects or clients..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400"
              />
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
            >
              <Plus className="w-5 h-5" />
              New Project
            </button>
          </div>

          {/* Projects Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredProjects.map((project) => (
              <div
                key={project.id}
                className="bg-gray-800/50 backdrop-blur-xl border border-gray-700 rounded-2xl p-6 hover:border-orange-500/30 transition-all duration-300 cursor-pointer group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div 
                    className="flex-1"
                    onClick={() => navigate(`/project/${project.id}`)}
                  >
                    <h3 className="text-xl font-semibold text-white mb-1">
                      {project.name}
                    </h3>
                    {project.client_name && (
                      <p className="text-orange-400 text-sm font-medium">
                        {project.client_name}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-2 text-gray-400">
                      <FileText className="w-4 h-4" />
                      <span className="text-sm">{project.document_count || 0}</span>
                    </div>
                    <button
                      onClick={(e) => openDeleteModal(project, e)}
                      className="p-2 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all duration-300"
                      title="Delete project"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div 
                  onClick={() => navigate(`/project/${project.id}`)}
                  className="flex-1"
                >
                  {project.description && (
                    <p className="text-gray-300 text-sm mb-4 line-clamp-2">
                      {project.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-sm text-gray-400">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      <span>Created {formatDate(project.created_at)}</span>
                    </div>
                    <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded-lg text-xs">
                      Active
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredProjects.length === 0 && !isLoading && (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-400 mb-2">
                {searchTerm ? 'No projects found' : 'No projects yet'}
              </h3>
              <p className="text-gray-500 mb-6">
                {searchTerm 
                  ? 'Try adjusting your search terms'
                  : 'Create your first project to get started with AI-powered content creation'
                }
              </p>
              {!searchTerm && (
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
                >
                  <Plus className="w-5 h-5" />
                  Create Project
                </button>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-2xl border border-gray-700 p-8 w-full max-w-md">
            <h3 className="text-2xl font-bold text-white mb-6">Create New Project</h3>
            
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Project name"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400"
                autoFocus
              />
              
              <input
                type="text"
                placeholder="Client name (optional)"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400"
              />
              
              <textarea
                placeholder="Project description (optional)"
                value={newProjectDescription}
                onChange={(e) => setNewProjectDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400 resize-none"
              />
              
              <div className="flex gap-3 pt-4">
                <button
                  onClick={handleCreateProject}
                  disabled={!newProjectName.trim() || isCreating}
                  className="flex-1 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
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
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewProjectName('');
                    setNewProjectDescription('');
                    setNewClientName('');
                  }}
                  className="flex-1 py-3 bg-gray-700 text-white font-semibold rounded-xl hover:bg-gray-600 transition-all duration-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Project Modal */}
      {showDeleteModal && projectToDelete && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-2xl border border-gray-700 p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">Delete Project</h3>
            
            <div className="mb-6">
              <div className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-4">
                <Trash2 className="w-5 h-5 text-red-400" />
                <div>
                  <p className="text-red-400 font-medium">This action cannot be undone</p>
                  <p className="text-red-300 text-sm">All documents and chats will be permanently deleted</p>
                </div>
              </div>
              
              <p className="text-gray-300">
                Are you sure you want to delete <strong className="text-white">"{projectToDelete.name}"</strong>?
              </p>
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={handleDeleteProject}
                disabled={isDeleting}
                className="flex-1 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete Project
                  </>
                )}
              </button>
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setProjectToDelete(null);
                }}
                className="flex-1 py-3 bg-gray-700 text-white font-semibold rounded-lg hover:bg-gray-600 transition-all duration-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}