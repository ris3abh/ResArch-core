// src/components/workspace/ProjectsTab.tsx
import React, { useState, useEffect } from 'react';
import { Plus, Calendar, Activity, MessageCircle, Search, Filter, FolderOpen, Upload, FileText, Trash2, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiService, Project, Document } from '../../services/api';

interface ProjectsTabProps {
  clientId: string;
}

export default function ProjectsTab({ clientId }: ProjectsTabProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      loadDocuments(selectedProject.id);
    }
  }, [selectedProject]);

  const loadProjects = async () => {
    try {
      setIsLoading(true);
      const projectsData = await apiService.getProjects();
      setProjects(projectsData);
      if (projectsData.length > 0 && !selectedProject) {
        setSelectedProject(projectsData[0]);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
      setError('Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocuments = async (projectId: string) => {
    try {
      setIsLoadingDocuments(true);
      const documentsData = await apiService.getProjectDocuments(projectId);
      setDocuments(documentsData);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setError('Failed to load documents');
    } finally {
      setIsLoadingDocuments(false);
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
      setSelectedProject(newProject);
      setShowCreateModal(false);
      setNewProjectName('');
      setNewProjectDescription('');
    } catch (error) {
      console.error('Failed to create project:', error);
      setError('Failed to create project');
    } finally {
      setIsCreating(false);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile || !selectedProject) return;

    try {
      setIsUploading(true);
      await apiService.uploadDocument(selectedProject.id, selectedFile);
      await loadDocuments(selectedProject.id);
      setShowUploadModal(false);
      setSelectedFile(null);
    } catch (error) {
      console.error('Failed to upload document:', error);
      setError('Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDocument = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await apiService.deleteDocument(documentId);
      setDocuments(documents.filter(doc => doc.id !== documentId));
    } catch (error) {
      console.error('Failed to delete document:', error);
      setError('Failed to delete document');
    }
  };

  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-orange-500 mx-auto mb-4" />
          <p className="text-gray-300">Loading projects...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Projects Sidebar */}
      <div className="w-1/3 border-r border-gray-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">Projects</h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="p-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm">{error}</p>
            <button 
              onClick={() => setError('')}
              className="text-red-300 hover:text-red-200 text-xs mt-1"
            >
              Dismiss
            </button>
          </div>
        )}

        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400 text-sm"
          />
        </div>

        <div className="space-y-2">
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              className={`p-4 rounded-lg cursor-pointer transition-all duration-300 ${
                selectedProject?.id === project.id
                  ? 'bg-gradient-to-r from-orange-500/20 to-violet-600/20 border border-orange-500/30'
                  : 'bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700'
              }`}
              onClick={() => setSelectedProject(project)}
            >
              <h3 className="font-medium text-white mb-1">{project.name}</h3>
              {project.description && (
                <p className="text-gray-400 text-sm mb-2 line-clamp-2">
                  {project.description}
                </p>
              )}
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <div className="flex items-center gap-1">
                  <FileText className="w-3 h-3" />
                  <span>{project.document_count || 0} docs</span>
                </div>
                <div className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  <span>{formatDate(project.created_at).split(',')[0]}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredProjects.length === 0 && (
          <div className="text-center py-8">
            <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-sm">
              {searchTerm ? 'No projects found' : 'No projects yet'}
            </p>
          </div>
        )}
      </div>

      {/* Project Details */}
      <div className="flex-1 p-6">
        {selectedProject ? (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">
                  {selectedProject.name}
                </h2>
                {selectedProject.description && (
                  <p className="text-gray-300">{selectedProject.description}</p>
                )}
                {selectedProject.client_name && (
                  <p className="text-orange-400 font-medium">
                    Client: {selectedProject.client_name}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
                >
                  <Upload className="w-4 h-4" />
                  Upload Document
                </button>
                <button
                  onClick={() => navigate(`/client/${clientId}/project/${selectedProject.id}`)}
                  className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white font-medium rounded-lg hover:from-emerald-600 hover:to-emerald-700 transition-all duration-300"
                >
                  <MessageCircle className="w-4 h-4" />
                  Open Chat
                </button>
              </div>
            </div>

            <div className="bg-gray-800/50 rounded-lg border border-gray-700">
              <div className="p-4 border-b border-gray-700">
                <h3 className="font-semibold text-white">Documents</h3>
              </div>

              {isLoadingDocuments ? (
                <div className="p-8 text-center">
                  <Loader2 className="w-6 h-6 animate-spin text-orange-500 mx-auto mb-2" />
                  <p className="text-gray-400 text-sm">Loading documents...</p>
                </div>
              ) : documents.length > 0 ? (
                <div className="divide-y divide-gray-700">
                  {documents.map((document) => (
                    <div key={document.id} className="p-4 flex items-center justify-between">
                      <div className="flex-1">
                        <h4 className="font-medium text-white mb-1">
                          {document.original_filename}
                        </h4>
                        <div className="flex items-center gap-4 text-sm text-gray-400">
                          <span>{formatFileSize(document.file_size)}</span>
                          <span>{document.file_type}</span>
                          <span>Uploaded {formatDate(document.created_at)}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleDeleteDocument(document.id)}
                          className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center">
                  <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                  <p className="text-gray-400 mb-4">No documents uploaded yet</p>
                  <button
                    onClick={() => setShowUploadModal(true)}
                    className="text-orange-500 hover:text-orange-600 font-medium"
                  >
                    Upload your first document
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">Select a project to view details</p>
            </div>
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-2xl border border-gray-700 p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">Create New Project</h3>
            
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Project name"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400"
                autoFocus
              />
              
              <textarea
                placeholder="Project description (optional)"
                value={newProjectDescription}
                onChange={(e) => setNewProjectDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400 resize-none"
              />
              
              <div className="flex gap-3">
                <button
                  onClick={handleCreateProject}
                  disabled={!newProjectName.trim() || isCreating}
                  className="flex-1 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-lg hover:from-orange-600 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
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
                  }}
                  className="flex-1 py-3 bg-gray-700 text-white font-semibold rounded-lg hover:bg-gray-600 transition-all duration-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Document Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-2xl border border-gray-700 p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">Upload Document</h3>
            
            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center">
                <Upload className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  accept=".pdf,.docx,.txt,.md"
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer text-orange-500 hover:text-orange-600 font-medium"
                >
                  Choose file to upload
                </label>
                <p className="text-gray-400 text-sm mt-2">
                  Supports PDF, DOCX, TXT, MD files
                </p>
                {selectedFile && (
                  <p className="text-white text-sm mt-2">
                    Selected: {selectedFile.name}
                  </p>
                )}
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={handleFileUpload}
                  disabled={!selectedFile || isUploading}
                  className="flex-1 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-lg hover:from-orange-600 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    'Upload'
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowUploadModal(false);
                    setSelectedFile(null);
                  }}
                  className="flex-1 py-3 bg-gray-700 text-white font-semibold rounded-lg hover:bg-gray-600 transition-all duration-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}