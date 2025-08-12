// src/components/ProjectWorkspace.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Zap, 
  Upload, 
  FileText, 
  MessageCircle, 
  Activity, 
  Settings,
  Trash2,
  Download,
  Calendar,
  Loader2,
  Plus,
  Search,
  Filter
} from 'lucide-react';
import { apiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

// Simple toast function
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

interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  file_path: string;
  project_id: string;
  uploaded_by_id: string;
  created_at: string;
  updated_at: string;
}

export default function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'workflows' | 'settings'>('overview');
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [error, setError] = useState<string>('');

  // Document upload states
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (projectId) {
      loadProject();
      loadDocuments();
    }
  }, [projectId]);

  const loadProject = async () => {
    if (!projectId) return;
    
    try {
      const projectData = await apiService.getProject(projectId);
      setProject(projectData);
    } catch (error: any) {
      console.error('Failed to load project:', error);
      setError('Failed to load project');
      showToast('Failed to load project', 'error');
    }
  };

  const loadDocuments = async () => {
    if (!projectId) return;
    
    try {
      setIsLoadingDocuments(true);
      const documentsData = await apiService.getProjectDocuments(projectId);
      setDocuments(documentsData);
    } catch (error: any) {
      console.error('Failed to load documents:', error);
      // Don't show error for documents as it's not critical
    } finally {
      setIsLoadingDocuments(false);
      setIsLoading(false);
    }
  };

  const handleStartWorkflow = () => {
    navigate(`/workflow/${projectId}`);
  };

  const handleBackToDashboard = () => {
    navigate('/dashboard');
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDragEvents = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragEnter = (e: React.DragEvent) => {
    handleDragEvents(e);
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    handleDragEvents(e);
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    handleDragEvents(e);
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      setSelectedFile(files[0]);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile || !projectId) return;

    try {
      setIsUploading(true);
      await apiService.uploadDocument(projectId, selectedFile);
      await loadDocuments();
      setShowUploadModal(false);
      setSelectedFile(null);
      showToast('Document uploaded successfully!', 'success');
    } catch (error: any) {
      console.error('Failed to upload document:', error);
      showToast('Failed to upload document: ' + error.message, 'error');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDocument = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await apiService.deleteDocument(documentId);
      setDocuments(documents.filter(doc => doc.id !== documentId));
      showToast('Document deleted successfully!', 'success');
    } catch (error: any) {
      console.error('Failed to delete document:', error);
      showToast('Failed to delete document', 'error');
    }
  };

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
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-orange-500 to-violet-600 rounded-full mb-4 animate-pulse">
            <FileText className="w-8 h-8 text-white" />
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
            onClick={handleBackToDashboard}
            className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'workflows', label: 'AI Workflows', icon: Zap },
    { id: 'settings', label: 'Settings', icon: Settings },
  ] as const;

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={handleBackToDashboard}
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              Dashboard
            </button>
            <div className="w-px h-6 bg-gray-600" />
            <div>
              <h1 className="text-xl font-semibold">{project.name}</h1>
              <p className="text-sm text-gray-400">
                {project.description || 'No description'}
                {project.client_name && ` • Client: ${project.client_name}`}
              </p>
            </div>
          </div>
          
          <button
            onClick={handleStartWorkflow}
            className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2"
          >
            <Zap className="w-4 h-4" />
            Start AI Workflow
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="px-6">
          <nav className="flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-1 py-4 border-b-2 font-medium text-sm transition-colors ${
                    isActive
                      ? 'border-orange-500 text-orange-500'
                      : 'border-transparent text-gray-400 hover:text-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1">
        {activeTab === 'overview' && (
          <div className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Quick Stats */}
              <div className="lg:col-span-2">
                <h2 className="text-lg font-semibold mb-4">Project Overview</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-400">Documents</p>
                        <p className="text-2xl font-bold">{documents.length}</p>
                      </div>
                      <FileText className="w-8 h-8 text-blue-500" />
                    </div>
                  </div>
                  
                  <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-400">AI Workflows</p>
                        <p className="text-2xl font-bold">0</p>
                      </div>
                      <Zap className="w-8 h-8 text-orange-500" />
                    </div>
                  </div>
                  
                  <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-400">Created</p>
                        <p className="text-lg font-bold">{formatDate(project.created_at).split(',')[0]}</p>
                      </div>
                      <Calendar className="w-8 h-8 text-green-500" />
                    </div>
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
                  <h3 className="font-semibold mb-4">Quick Actions</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <button
                      onClick={handleStartWorkflow}
                      className="p-4 bg-gradient-to-r from-orange-500 to-violet-600 rounded-lg text-left hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
                    >
                      <Zap className="w-6 h-6 mb-2" />
                      <h4 className="font-medium mb-1">Start AI Workflow</h4>
                      <p className="text-sm text-orange-100">Let our agents create content for you</p>
                    </button>
                    
                    <button
                      onClick={() => setActiveTab('documents')}
                      className="p-4 bg-gray-700 border border-gray-600 rounded-lg text-left hover:bg-gray-650 transition-all duration-300"
                    >
                      <Upload className="w-6 h-6 mb-2 text-blue-400" />
                      <h4 className="font-medium mb-1">Upload Documents</h4>
                      <p className="text-sm text-gray-400">Add brand guidelines and resources</p>
                    </button>
                  </div>
                </div>
              </div>

              {/* Recent Documents */}
              <div>
                <h2 className="text-lg font-semibold mb-4">Recent Documents</h2>
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                  {documents.length === 0 ? (
                    <div className="text-center py-8">
                      <FileText className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                      <p className="text-gray-500 text-sm">No documents yet</p>
                      <p className="text-gray-600 text-xs mt-1">Upload brand guidelines to get started</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {documents.slice(0, 5).map((doc) => (
                        <div key={doc.id} className="flex items-center gap-3 p-2 bg-gray-700 rounded-lg">
                          <FileText className="w-4 h-4 text-blue-400" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-white truncate">{doc.original_filename}</p>
                            <p className="text-xs text-gray-400">{formatFileSize(doc.file_size)}</p>
                          </div>
                        </div>
                      ))}
                      {documents.length > 5 && (
                        <button
                          onClick={() => setActiveTab('documents')}
                          className="w-full text-sm text-orange-500 hover:text-orange-400 transition-colors"
                        >
                          View all {documents.length} documents
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-semibold mb-1">Project Documents</h2>
                <p className="text-gray-400">Manage your brand guidelines, style guides, and reference materials</p>
              </div>
              <button
                onClick={() => setShowUploadModal(true)}
                className="px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Upload Document
              </button>
            </div>

            {isLoadingDocuments ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-12">
                <Upload className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">No documents uploaded</h3>
                <p className="text-gray-500 mb-6">
                  Upload brand guidelines, style guides, or sample content to help AI agents understand your requirements better.
                </p>
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2 mx-auto"
                >
                  <Upload className="w-4 h-4" />
                  Upload Your First Document
                </button>
              </div>
            ) : (
              <div className="grid gap-4">
                {documents.map((document) => (
                  <div key={document.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <FileText className="w-8 h-8 text-blue-500" />
                        <div>
                          <h3 className="font-medium text-white">{document.original_filename}</h3>
                          <div className="flex items-center gap-4 text-sm text-gray-400">
                            <span>{formatFileSize(document.file_size)}</span>
                            <span>{document.file_type}</span>
                            <span>{formatDate(document.created_at)}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => apiService.downloadDocument(document.id)}
                          className="p-2 text-gray-400 hover:text-blue-400 transition-colors"
                          title="Download"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteDocument(document.id)}
                          className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'workflows' && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-semibold mb-1">AI Workflows</h2>
                <p className="text-gray-400">Multi-agent content creation workflows</p>
              </div>
              <button
                onClick={handleStartWorkflow}
                className="px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2"
              >
                <Zap className="w-4 h-4" />
                Start New Workflow
              </button>
            </div>

            <div className="text-center py-12">
              <Zap className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-300 mb-2">No workflows yet</h3>
              <p className="text-gray-500 mb-6">
                Start your first SpinScribe AI workflow to create content with our multi-agent system.
              </p>
              <button
                onClick={handleStartWorkflow}
                className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2 mx-auto"
              >
                <Zap className="w-4 h-4" />
                Start AI Workflow
              </button>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="p-6">
            <h2 className="text-lg font-semibold mb-4">Project Settings</h2>
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Project Name
                  </label>
                  <input
                    type="text"
                    value={project.name}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-orange-500"
                    readOnly
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Description
                  </label>
                  <textarea
                    value={project.description || ''}
                    rows={3}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-orange-500"
                    readOnly
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Client Name
                  </label>
                  <input
                    type="text"
                    value={project.client_name || ''}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-orange-500"
                    readOnly
                  />
                </div>
                
                <div className="pt-4 border-t border-gray-700">
                  <p className="text-sm text-gray-500 mb-4">Created by: {user?.first_name} {user?.last_name}</p>
                  <p className="text-sm text-gray-500">Project ID: {project.id}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Upload Document Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-4">Upload Document</h3>
            
            <div 
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                isDragging ? 'border-orange-500 bg-orange-500/10' : 'border-gray-600 hover:border-gray-500'
              }`}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragEvents}
              onDrop={handleDrop}
            >
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              
              {selectedFile ? (
                <div className="space-y-2">
                  <p className="text-green-400 font-medium">{selectedFile.name}</p>
                  <p className="text-sm text-gray-400">{formatFileSize(selectedFile.size)}</p>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="text-sm text-red-400 hover:text-red-300"
                  >
                    Remove file
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-gray-600 mb-2">Drag and drop your file here</p>
                  <p className="text-sm text-gray-500 mb-4">or click to browse</p>
                  <label className="inline-block">
                    <input
                      type="file"
                      className="hidden"
                      onChange={handleFileSelect}
                      accept=".txt,.md,.doc,.docx,.pdf"
                    />
                    <span className="px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300 cursor-pointer">
                      Choose File
                    </span>
                  </label>
                </div>
              )}
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                }}
                className="flex-1 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                disabled={isUploading}
              >
                Cancel
              </button>
              <button
                onClick={handleFileUpload}
                disabled={!selectedFile || isUploading}
                className="flex-1 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  'Upload Document'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}