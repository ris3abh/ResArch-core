// File: frontend/src/components/Dashboard.tsx
import React, { useState } from 'react';
import { Plus, Search, Users, Activity, FileText, MessageSquare, Zap, Play, CheckCircle, AlertCircle, Clock, Upload } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Sidebar from './Sidebar';
import { 
  useProjects, 
  useDocuments, 
  useChats, 
  useWorkflows,
  type Project,
  type Document,
  type Chat,
  type Workflow
} from '../hooks/useAPI';

export default function Dashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'chats' | 'workflows'>('overview');
  const { user } = useAuth();

  // Use custom hooks for data management
  const { 
    projects, 
    loading: projectsLoading, 
    error: projectsError, 
    createProject 
  } = useProjects();

  const { 
    documents, 
    loading: documentsLoading, 
    uploadDocument 
  } = useDocuments(selectedProject?.id || null);

  const { 
    chats, 
    loading: chatsLoading, 
    createChat 
  } = useChats(selectedProject?.id || null);

  const { 
    workflows, 
    loading: workflowsLoading, 
    createWorkflow 
  } = useWorkflows(selectedProject?.id || null);

  // Modal states
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showCreateWorkflow, setShowCreateWorkflow] = useState(false);
  const [showUploadDocument, setShowUploadDocument] = useState(false);
  const [showCreateChat, setShowCreateChat] = useState(false);

  // Form states
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    client_name: ''
  });
  const [newWorkflow, setNewWorkflow] = useState({
    title: '',
    content_type: 'article',
    enable_checkpoints: true,
    enable_human_interaction: true,
    timeout_seconds: 600
  });
  const [newChat, setNewChat] = useState({
    name: '',
    description: '',
    chat_type: 'standard'
  });

  // Error state management
  const [error, setError] = useState<string | null>(null);

  // Set selected project when projects load
  React.useEffect(() => {
    if (projects.length > 0 && !selectedProject) {
      setSelectedProject(projects[0]);
    }
  }, [projects, selectedProject]);

  // Handle errors from different sources
  React.useEffect(() => {
    if (projectsError) {
      setError(projectsError);
    }
  }, [projectsError]);

  const handleCreateProject = async () => {
    if (!newProject.name.trim()) return;

    try {
      const project = await createProject(newProject);
      setSelectedProject(project);
      setShowCreateProject(false);
      setNewProject({ name: '', description: '', client_name: '' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    }
  };

  const handleCreateWorkflow = async () => {
    if (!selectedProject || !newWorkflow.title.trim()) return;

    try {
      await createWorkflow({
        ...newWorkflow,
        project_id: selectedProject.id
      });
      setShowCreateWorkflow(false);
      setNewWorkflow({
        title: '',
        content_type: 'article',
        enable_checkpoints: true,
        enable_human_interaction: true,
        timeout_seconds: 600
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create workflow');
    }
  };

  const handleCreateChat = async () => {
    if (!selectedProject || !newChat.name.trim()) return;

    try {
      await createChat(newChat);
      setShowCreateChat(false);
      setNewChat({ name: '', description: '', chat_type: 'standard' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create chat');
    }
  };

  const handleUploadDocument = async (file: File, documentType: string) => {
    if (!selectedProject) return;

    try {
      await uploadDocument(file, documentType);
      setShowUploadDocument(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload document');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-400';
      case 'running': return 'text-blue-400';
      case 'failed': return 'text-red-400';
      case 'pending': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4" />;
      case 'running': return <Play className="w-4 h-4" />;
      case 'failed': return <AlertCircle className="w-4 h-4" />;
      case 'pending': return <Clock className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (project.client_name && project.client_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (projectsLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading Spinscribe Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex">
      <Sidebar />
      
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-gray-800 border-b border-gray-700 p-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-white">Projects Dashboard</h1>
              <p className="text-gray-400 mt-1">Manage your Spinscribe content projects</p>
            </div>
            <button
              onClick={() => setShowCreateProject(true)}
              className="bg-gradient-to-r from-orange-500 to-violet-600 hover:from-orange-600 hover:to-violet-700 text-white px-6 py-3 rounded-xl flex items-center gap-2 transition-all duration-300"
            >
              <Plus className="w-5 h-5" />
              New Project
            </button>
          </div>
        </header>

        <div className="flex-1 flex">
          {/* Projects Sidebar */}
          <div className="w-80 bg-gray-800 border-r border-gray-700 p-6">
            <div className="mb-6">
              <div className="relative">
                <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white placeholder-gray-400"
                />
              </div>
            </div>

            <div className="space-y-3">
              {filteredProjects.map((project) => (
                <div
                  key={project.id}
                  onClick={() => setSelectedProject(project)}
                  className={`p-4 rounded-xl cursor-pointer transition-all duration-300 ${
                    selectedProject?.id === project.id
                      ? 'bg-gradient-to-r from-orange-500/20 to-violet-600/20 border border-orange-500/30'
                      : 'bg-gray-700 hover:bg-gray-600 border border-gray-600'
                  }`}
                >
                  <h3 className="font-semibold text-white truncate">{project.name}</h3>
                  {project.client_name && (
                    <p className="text-sm text-gray-400 truncate">{project.client_name}</p>
                  )}
                  <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      {documents.length || 0}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="w-3 h-3" />
                      {chats.length || 0}
                    </span>
                    <span className="flex items-center gap-1">
                      <Zap className="w-3 h-3" />
                      {workflows.length || 0}
                    </span>
                  </div>
                </div>
              ))}
              
              {filteredProjects.length === 0 && (
                <div className="text-center py-8">
                  <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400">No projects found</p>
                </div>
              )}
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 p-6">
            {selectedProject ? (
              <>
                {/* Project Header */}
                <div className="bg-gray-800 rounded-xl p-6 mb-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="text-xl font-bold text-white">{selectedProject.name}</h2>
                      {selectedProject.client_name && (
                        <p className="text-gray-400 mt-1">Client: {selectedProject.client_name}</p>
                      )}
                      {selectedProject.description && (
                        <p className="text-gray-300 mt-2">{selectedProject.description}</p>
                      )}
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={() => setShowCreateWorkflow(true)}
                        className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                      >
                        <Zap className="w-4 h-4" />
                        New Workflow
                      </button>
                      <button
                        onClick={() => setShowUploadDocument(true)}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                      >
                        <Upload className="w-4 h-4" />
                        Upload
                      </button>
                      <button
                        onClick={() => setShowCreateChat(true)}
                        className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                      >
                        <MessageSquare className="w-4 h-4" />
                        New Chat
                      </button>
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="bg-gray-800 rounded-xl overflow-hidden">
                  <div className="border-b border-gray-700">
                    <nav className="flex space-x-8 px-6">
                      {[
                        { key: 'overview', label: 'Overview', icon: Activity },
                        { key: 'documents', label: 'Documents', icon: FileText },
                        { key: 'chats', label: 'Chats', icon: MessageSquare },
                        { key: 'workflows', label: 'Workflows', icon: Zap }
                      ].map(({ key, label, icon: Icon }) => (
                        <button
                          key={key}
                          onClick={() => setActiveTab(key as any)}
                          className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                            activeTab === key
                              ? 'border-orange-500 text-orange-400'
                              : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <Icon className="w-4 h-4" />
                            {label}
                          </div>
                        </button>
                      ))}
                    </nav>
                  </div>

                  <div className="p-6">
                    {/* Overview Tab */}
                    {activeTab === 'overview' && (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg p-6">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-blue-200">Documents</p>
                              <p className="text-2xl font-bold text-white">{documents.length}</p>
                            </div>
                            <FileText className="w-8 h-8 text-blue-300" />
                          </div>
                        </div>
                        <div className="bg-gradient-to-r from-purple-600 to-purple-700 rounded-lg p-6">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-purple-200">Active Chats</p>
                              <p className="text-2xl font-bold text-white">{chats.filter(c => c.is_active).length}</p>
                            </div>
                            <MessageSquare className="w-8 h-8 text-purple-300" />
                          </div>
                        </div>
                        <div className="bg-gradient-to-r from-green-600 to-green-700 rounded-lg p-6">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-green-200">Workflows</p>
                              <p className="text-2xl font-bold text-white">{workflows.length}</p>
                            </div>
                            <Zap className="w-8 h-8 text-green-300" />
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Documents Tab */}
                    {activeTab === 'documents' && (
                      <div className="space-y-4">
                        {documents.length === 0 ? (
                          <div className="text-center py-12">
                            <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                            <h3 className="text-lg font-medium text-white mb-2">No documents uploaded</h3>
                            <p className="text-gray-400 mb-4">Upload brand guidelines, style guides, or sample content to get started.</p>
                            <button
                              onClick={() => setShowUploadDocument(true)}
                              className="bg-gradient-to-r from-orange-500 to-violet-600 hover:from-orange-600 hover:to-violet-700 text-white px-6 py-3 rounded-xl transition-all"
                            >
                              Upload Your First Document
                            </button>
                          </div>
                        ) : (
                          documents.map((document) => (
                            <div key={document.id} className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                              <div className="flex items-center gap-3">
                                <FileText className="w-5 h-5 text-gray-400" />
                                <div>
                                  <h4 className="font-medium text-white">{document.filename}</h4>
                                  <p className="text-sm text-gray-400">
                                    {document.document_type} • {(document.file_size / 1024).toFixed(1)} KB
                                  </p>
                                </div>
                              </div>
                              <div className={`flex items-center gap-2 ${getStatusColor(document.processing_status)}`}>
                                {getStatusIcon(document.processing_status)}
                                <span className="text-sm font-medium capitalize">{document.processing_status}</span>
                              </div>
                            </div>
                          ))
                        )}
                        {documentsLoading && (
                          <div className="text-center py-4">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-orange-500 mx-auto"></div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Chats Tab */}
                    {activeTab === 'chats' && (
                      <div className="space-y-4">
                        {chats.length === 0 ? (
                          <div className="text-center py-12">
                            <MessageSquare className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                            <h3 className="text-lg font-medium text-white mb-2">No chat instances</h3>
                            <p className="text-gray-400 mb-4">Create a chat to start collaborating with AI agents.</p>
                            <button
                              onClick={() => setShowCreateChat(true)}
                              className="bg-gradient-to-r from-orange-500 to-violet-600 hover:from-orange-600 hover:to-violet-700 text-white px-6 py-3 rounded-xl transition-all"
                            >
                              Create Your First Chat
                            </button>
                          </div>
                        ) : (
                          chats.map((chat) => (
                            <div key={chat.id} className="flex items-center justify-between p-4 bg-gray-700 rounded-lg hover:bg-gray-600 cursor-pointer transition-colors">
                              <div className="flex items-center gap-3">
                                <MessageSquare className="w-5 h-5 text-gray-400" />
                                <div>
                                  <h4 className="font-medium text-white">{chat.name}</h4>
                                  <p className="text-sm text-gray-400">
                                    {chat.chat_type} • Created {new Date(chat.created_at).toLocaleDateString()}
                                  </p>
                                </div>
                              </div>
                              <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                                chat.is_active 
                                  ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                                  : 'bg-gray-600/20 text-gray-400 border border-gray-600/30'
                              }`}>
                                {chat.is_active ? 'Active' : 'Inactive'}
                              </div>
                            </div>
                          ))
                        )}
                        {chatsLoading && (
                          <div className="text-center py-4">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-orange-500 mx-auto"></div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Workflows Tab */}
                    {activeTab === 'workflows' && (
                      <div className="space-y-4">
                        {workflows.length === 0 ? (
                          <div className="text-center py-12">
                            <Zap className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                            <h3 className="text-lg font-medium text-white mb-2">No workflows created</h3>
                            <p className="text-gray-400 mb-4">Create an AI workflow to generate content with multi-agent collaboration.</p>
                            <button
                              onClick={() => setShowCreateWorkflow(true)}
                              className="bg-gradient-to-r from-orange-500 to-violet-600 hover:from-orange-600 hover:to-violet-700 text-white px-6 py-3 rounded-xl transition-all"
                            >
                              Create Your First Workflow
                            </button>
                          </div>
                        ) : (
                          workflows.map((workflow) => (
                            <div key={workflow.workflow_id} className="p-4 bg-gray-700 rounded-lg">
                              <div className="flex items-center justify-between mb-3">
                                <h4 className="font-medium text-white">{workflow.title}</h4>
                                <div className={`flex items-center gap-2 ${getStatusColor(workflow.status)}`}>
                                  {getStatusIcon(workflow.status)}
                                  <span className="text-sm font-medium capitalize">{workflow.status}</span>
                                </div>
                              </div>
                              
                              {workflow.current_stage && (
                                <p className="text-sm text-gray-400 mb-2">
                                  Current Stage: {workflow.current_stage}
                                </p>
                              )}
                              
                              <div className="w-full bg-gray-600 rounded-full h-2 mb-2">
                                <div 
                                  className="bg-gradient-to-r from-orange-500 to-violet-600 h-2 rounded-full transition-all duration-300"
                                  style={{ width: `${workflow.progress_percentage}%` }}
                                ></div>
                              </div>
                              
                              <div className="flex justify-between items-center text-sm text-gray-400">
                                <span>{workflow.progress_percentage.toFixed(1)}% complete</span>
                                <span>Created {new Date(workflow.created_at).toLocaleDateString()}</span>
                              </div>
                            </div>
                          ))
                        )}
                        {workflowsLoading && (
                          <div className="text-center py-4">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-orange-500 mx-auto"></div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-20">
                <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-xl font-medium text-white mb-2">Welcome to Spinscribe</h3>
                <p className="text-gray-400 mb-6">Create your first project to start using AI-powered content creation.</p>
                <button
                  onClick={() => setShowCreateProject(true)}
                  className="bg-gradient-to-r from-orange-500 to-violet-600 hover:from-orange-600 hover:to-violet-700 text-white px-8 py-4 rounded-xl text-lg transition-all"
                >
                  Create Your First Project
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      {showCreateProject && (
        <Modal onClose={() => setShowCreateProject(false)}>
          <h2 className="text-xl font-bold text-white mb-6">Create New Project</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Project Name *
              </label>
              <input
                type="text"
                value={newProject.name}
                onChange={(e) => setNewProject({...newProject, name: e.target.value})}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white placeholder-gray-400"
                placeholder="My Content Project"
                autoFocus
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Client Name
              </label>
              <input
                type="text"
                value={newProject.client_name}
                onChange={(e) => setNewProject({...newProject, client_name: e.target.value})}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white placeholder-gray-400"
                placeholder="Acme Corporation"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Description
              </label>
              <textarea
                value={newProject.description}
                onChange={(e) => setNewProject({...newProject, description: e.target.value})}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white placeholder-gray-400"
                rows={3}
                placeholder="Project description and goals..."
              />
            </div>
          </div>
          
          <div className="flex gap-3 mt-6">
            <button
              onClick={() => setShowCreateProject(false)}
              className="flex-1 px-4 py-3 bg-gray-700 text-white rounded-xl hover:bg-gray-600 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCreateProject}
              disabled={!newProject.name.trim()}
              className="flex-1 px-4 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-xl hover:from-orange-600 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Create Project
            </button>
          </div>
        </Modal>
      )}

      {showCreateWorkflow && (
        <Modal onClose={() => setShowCreateWorkflow(false)}>
          <h2 className="text-xl font-bold text-white mb-6">Create New Workflow</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Title *
              </label>
              <input
                type="text"
                value={newWorkflow.title}
                onChange={(e) => setNewWorkflow({...newWorkflow, title: e.target.value})}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white placeholder-gray-400"
                placeholder="AI Guide for Business Transformation"
                autoFocus
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Content Type
              </label>
              <select
                value={newWorkflow.content_type}
                onChange={(e) => setNewWorkflow({...newWorkflow, content_type: e.target.value})}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white"
              >
                <option value="article">Article</option>
                <option value="blog_post">Blog Post</option>
                <option value="landing_page">Landing Page</option>
                <option value="email">Email</option>
                <option value="social_media">Social Media</option>
              </select>
            </div>
            
            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={newWorkflow.enable_checkpoints}
                  onChange={(e) => setNewWorkflow({...newWorkflow, enable_checkpoints: e.target.checked})}
                  className="mr-3 w-4 h-4 text-orange-500 bg-gray-700 border-gray-600 rounded focus:ring-orange-500"
                />
                <span className="text-sm text-gray-300">Enable human checkpoints</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={newWorkflow.enable_human_interaction}
                  onChange={(e) => setNewWorkflow({...newWorkflow, enable_human_interaction: e.target.checked})}
                  className="mr-3 w-4 h-4 text-orange-500 bg-gray-700 border-gray-600 rounded focus:ring-orange-500"
                />
                <span className="text-sm text-gray-300">Enable human interaction</span>
              </label>
            </div>
          </div>
          
          <div className="flex gap-3 mt-6">
            <button
              onClick={() => setShowCreateWorkflow(false)}
              className="flex-1 px-4 py-3 bg-gray-700 text-white rounded-xl hover:bg-gray-600 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCreateWorkflow}
              disabled={!newWorkflow.title.trim()}
              className="flex-1 px-4 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Start Workflow
            </button>
          </div>
        </Modal>
      )}

      {showUploadDocument && (
        <DocumentUploadModal
          onUpload={handleUploadDocument}
          onClose={() => setShowUploadDocument(false)}
        />
      )}

      {showCreateChat && (
        <Modal onClose={() => setShowCreateChat(false)}>
          <h2 className="text-xl font-bold text-white mb-6">Create New Chat</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Chat Name *
              </label>
              <input
                type="text"
                value={newChat.name}
                onChange={(e) => setNewChat({...newChat, name: e.target.value})}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white placeholder-gray-400"
                placeholder="Blog Post Discussion"
                autoFocus
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Chat Type
              </label>
              <select
                value={newChat.chat_type}
                onChange={(e) => setNewChat({...newChat, chat_type: e.target.value})}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white"
              >
                <option value="standard">Standard Chat</option>
                <option value="workflow">Workflow Chat</option>
                <option value="brainstorm">Brainstorming</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Description
              </label>
              <textarea
                value={newChat.description}
                onChange={(e) => setNewChat({...newChat, description: e.target.value})}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white placeholder-gray-400"
                rows={2}
                placeholder="What will you discuss in this chat?"
              />
            </div>
          </div>
          
          <div className="flex gap-3 mt-6">
            <button
              onClick={() => setShowCreateChat(false)}
              className="flex-1 px-4 py-3 bg-gray-700 text-white rounded-xl hover:bg-gray-600 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCreateChat}
              disabled={!newChat.name.trim()}
              className="flex-1 px-4 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Create Chat
            </button>
          </div>
        </Modal>
      )}

      {error && (
        <div className="fixed bottom-4 right-4 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg">
          <p>{error}</p>
          <button 
            onClick={() => setError(null)}
            className="ml-2 text-red-200 hover:text-white"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}

// Modal Component
function Modal({ children, onClose }: { children: React.ReactNode, onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-gray-800 rounded-xl max-w-md w-full p-6 border border-gray-700">
        {children}
      </div>
    </div>
  );
}

// Document Upload Modal Component
function DocumentUploadModal({ onUpload, onClose }: { 
  onUpload: (file: File, type: string) => void, 
  onClose: () => void 
}) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('general');
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = () => {
    if (selectedFile) {
      onUpload(selectedFile, documentType);
    }
  };

  return (
    <Modal onClose={onClose}>
      <h2 className="text-xl font-bold text-white mb-6">Upload Document</h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Document Type
          </label>
          <select
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all text-white"
          >
            <option value="general">General Document</option>
            <option value="brand_guidelines">Brand Guidelines</option>
            <option value="style_guide">Style Guide</option>
            <option value="sample_content">Sample Content</option>
            <option value="reference">Reference Material</option>
          </select>
        </div>
        
        <div
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
            dragActive ? 'border-orange-500 bg-orange-500/10' : 'border-gray-600 hover:border-gray-500'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          {selectedFile ? (
            <div>
              <FileText className="w-12 h-12 text-orange-500 mx-auto mb-3" />
              <p className="text-sm font-medium text-white">{selectedFile.name}</p>
              <p className="text-xs text-gray-400">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div>
              <Upload className="w-12 h-12 text-gray-500 mx-auto mb-3" />
              <p className="text-gray-300 mb-2">
                Drag and drop your file here, or
              </p>
              <label className="text-orange-500 hover:text-orange-400 cursor-pointer font-medium">
                browse files
                <input
                  type="file"
                  className="hidden"
                  onChange={handleFileSelect}
                  accept=".pdf,.doc,.docx,.txt,.md"
                />
              </label>
            </div>
          )}
        </div>
      </div>
      
      <div className="flex gap-3 mt-6">
        <button
          onClick={onClose}
          className="flex-1 px-4 py-3 bg-gray-700 text-white rounded-xl hover:bg-gray-600 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleUpload}
          disabled={!selectedFile}
          className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Upload Document
        </button>
      </div>
    </Modal>
  );
}