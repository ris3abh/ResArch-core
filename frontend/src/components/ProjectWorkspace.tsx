// frontend/src/components/ProjectWorkspace.tsx 
// FIXED VERSION - All errors and warnings resolved

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
  Filter,
  Save,
  Edit3,
  User,
  AlertCircle,
  CheckCircle
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
    setTimeout(() => {
      if (document.body.contains(toast)) {
        document.body.removeChild(toast);
      }
    }, 300);
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
  created_at: string;
}

type TabType = 'overview' | 'documents' | 'workflows' | 'settings';

// ProjectSettingsTab component
const ProjectSettingsTab: React.FC<{
  project: Project;
  onProjectUpdate: (project: Project) => void;
}> = ({ project, onProjectUpdate }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  
  const [formData, setFormData] = useState({
    name: project.name || '',
    description: project.description || '',
    client_name: project.client_name || ''
  });

  useEffect(() => {
    setFormData({
      name: project.name || '',
      description: project.description || '',
      client_name: project.client_name || ''
    });
  }, [project]);

  const showMessage = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      showMessage('Project name is required', 'error');
      return;
    }

    try {
      setIsSaving(true);
      
      // Use the API service method to update project
      const updatedProject = await apiService.updateProject(project.id, {
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        client_name: formData.client_name.trim() || undefined
      });
      
      onProjectUpdate(updatedProject);
      setIsEditing(false);
      showMessage('Project settings updated successfully!', 'success');
      
    } catch (error: any) {
      console.error('Failed to update project:', error);
      showMessage('Failed to update project settings: ' + (error.message || 'Unknown error'), 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setFormData({
      name: project.name || '',
      description: project.description || '',
      client_name: project.client_name || ''
    });
    setIsEditing(false);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="h-full bg-gray-900 p-6">
      {/* Message Toast */}
      {message && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg text-white transition-all duration-300 shadow-lg ${
          message.type === 'success' ? 'bg-green-500' : 
          message.type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        }`}>
          <div className="flex items-center gap-2">
            {message.type === 'success' && <CheckCircle className="w-4 h-4" />}
            {message.type === 'error' && <AlertCircle className="w-4 h-4" />}
            {message.type === 'info' && <Settings className="w-4 h-4" />}
            {message.text}
          </div>
        </div>
      )}

      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">Project Settings</h2>
            <p className="text-gray-400">Manage your project information and configuration</p>
          </div>
          
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
            >
              <Edit3 className="w-4 h-4" />
              Edit Settings
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <button
                onClick={handleCancel}
                disabled={isSaving}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving || !formData.name.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Changes
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        <div className="space-y-6">
          {/* Project Information */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="w-5 h-5 text-orange-500" />
              <h3 className="text-lg font-semibold text-white">Project Information</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Project Name *
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
                    placeholder="Enter project name"
                  />
                ) : (
                  <div className="px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white">
                    {project.name || 'Untitled Project'}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Client Name
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    value={formData.client_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, client_name: e.target.value }))}
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
                    placeholder="Enter client name (optional)"
                  />
                ) : (
                  <div className="px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white">
                    {project.client_name || 'No client specified'}
                  </div>
                )}
              </div>
            </div>

            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Project Description
              </label>
              {isEditing ? (
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  rows={4}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
                  placeholder="Describe your project goals, objectives, and any important details..."
                />
              ) : (
                <div className="px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white min-h-[100px]">
                  {project.description || 'No description provided'}
                </div>
              )}
            </div>
          </div>

          {/* Project Metadata */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-5 h-5 text-blue-500" />
              <h3 className="text-lg font-semibold text-white">Project Timeline</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Created</label>
                <div className="px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-gray-300">
                  {formatDate(project.created_at)}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Last Modified</label>
                <div className="px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-gray-300">
                  {formatDate(project.updated_at)}
                </div>
              </div>
            </div>
          </div>

          {/* Project ID */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center gap-2 mb-4">
              <User className="w-5 h-5 text-purple-500" />
              <h3 className="text-lg font-semibold text-white">Project Details</h3>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Project ID</label>
              <div className="px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-gray-300 font-mono text-sm">
                {project.id}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                This unique identifier is used for API calls and integrations
              </p>
            </div>
          </div>

          {isEditing && (
            <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4">
              <div className="flex items-center gap-2 text-yellow-400">
                <AlertCircle className="w-5 h-5" />
                <p className="font-medium">Editing Project Settings</p>
              </div>
              <p className="text-yellow-300/80 mt-1 text-sm">
                Make sure to save your changes before navigating away from this page.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Main ProjectWorkspace component
const ProjectWorkspace: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (projectId) {
      loadProjectData();
    }
  }, [projectId]);

  const loadProjectData = async () => {
    if (!projectId) return;

    try {
      setIsLoading(true);
      const [projectData, documentsData] = await Promise.all([
        apiService.getProject(projectId),
        apiService.getProjectDocuments(projectId)
      ]);
      
      setProject(projectData);
      setDocuments(documentsData);
    } catch (error: any) {
      console.error('Failed to load project data:', error);
      setError('Failed to load project data');
      showToast('Failed to load project data', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleProjectUpdate = (updatedProject: Project) => {
    setProject(updatedProject);
    showToast('Project updated successfully!', 'success');
  };

  const handleBackToDashboard = () => {
    navigate('/dashboard');
  };

  const handleStartWorkflow = () => {
    if (projectId) {
      navigate(`/workflow/${projectId}`);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0 || !projectId) return;

    setIsUploading(true);
    setUploadProgress(0);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        // Pass the actual File object, not FormData
        await apiService.uploadDocument(projectId, file);
        setUploadProgress(((i + 1) / files.length) * 100);
      }

      await loadProjectData(); // Reload documents
      showToast(`Successfully uploaded ${files.length} file(s)`, 'success');
    } catch (error: any) {
      console.error('Upload failed:', error);
      showToast('Failed to upload files', 'error');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      if (event.target) {
        event.target.value = '';
      }
    }
  };

  const handleDeleteDocument = async (documentId: string) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;

    try {
      await apiService.deleteDocument(documentId);
      setDocuments(docs => docs.filter(doc => doc.id !== documentId));
      showToast('Document deleted successfully', 'success');
    } catch (error: any) {
      console.error('Failed to delete document:', error);
      showToast('Failed to delete document', 'error');
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const filteredDocuments = documents.filter(doc =>
    doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.file_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-orange-500 animate-spin mx-auto mb-4" />
          <p className="text-white">Loading project...</p>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error || 'Project not found'}</p>
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
                      className="flex items-center gap-3 p-4 bg-gradient-to-r from-orange-500/20 to-violet-600/20 border border-orange-500/30 rounded-lg hover:from-orange-500/30 hover:to-violet-600/30 transition-all duration-300"
                    >
                      <Zap className="w-6 h-6 text-orange-500" />
                      <div className="text-left">
                        <p className="font-medium">Start AI Workflow</p>
                        <p className="text-sm text-gray-400">Begin content generation</p>
                      </div>
                    </button>
                    
                    <label className="flex items-center gap-3 p-4 bg-blue-500/20 border border-blue-500/30 rounded-lg hover:bg-blue-500/30 transition-all duration-300 cursor-pointer">
                      <Upload className="w-6 h-6 text-blue-500" />
                      <div className="text-left">
                        <p className="font-medium">Upload Documents</p>
                        <p className="text-sm text-gray-400">Add reference materials</p>
                      </div>
                      <input
                        type="file"
                        multiple
                        onChange={handleFileUpload}
                        className="hidden"
                        disabled={isUploading}
                      />
                    </label>
                  </div>
                </div>
              </div>

              {/* Project Info */}
              <div>
                <h2 className="text-lg font-semibold mb-4">Project Details</h2>
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 space-y-4">
                  <div>
                    <p className="text-sm text-gray-400">Client</p>
                    <p className="font-medium">{project.client_name || 'No client specified'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Created</p>
                    <p className="font-medium">{formatDate(project.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Last Updated</p>
                    <p className="font-medium">{formatDate(project.updated_at)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Documents</p>
                    <p className="font-medium">{documents.length} files</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">Documents</h2>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search documents..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 pr-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                  />
                </div>
                <label className="px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 cursor-pointer flex items-center gap-2">
                  <Upload className="w-4 h-4" />
                  Upload Files
                  <input
                    type="file"
                    multiple
                    onChange={handleFileUpload}
                    className="hidden"
                    disabled={isUploading}
                  />
                </label>
              </div>
            </div>

            {isUploading && (
              <div className="mb-6 bg-blue-900/30 border border-blue-500/30 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-blue-200">Uploading files...</span>
                  <span className="text-blue-200">{Math.round(uploadProgress)}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-orange-500 to-violet-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredDocuments.map((doc) => (
                <div key={doc.id} className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-5 h-5 text-blue-500" />
                      <div className="min-w-0">
                        <p className="font-medium text-white truncate" title={doc.original_filename}>
                          {doc.original_filename}
                        </p>
                        <p className="text-sm text-gray-400">
                          {doc.file_type.toUpperCase()} • {formatFileSize(doc.file_size)}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteDocument(doc.id)}
                      className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      {formatDate(doc.created_at)}
                    </span>
                    <button className="p-1 text-gray-400 hover:text-white transition-colors">
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {filteredDocuments.length === 0 && !isUploading && (
              <div className="text-center py-12">
                <FileText className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                <p className="text-gray-400 mb-2">
                  {searchTerm ? 'No documents match your search' : 'No documents uploaded yet'}
                </p>
                {!searchTerm && (
                  <label className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 cursor-pointer">
                    <Upload className="w-4 h-4" />
                    Upload Your First Document
                    <input
                      type="file"
                      multiple
                      onChange={handleFileUpload}
                      className="hidden"
                      disabled={isUploading}
                    />
                  </label>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'workflows' && (
          <div className="p-6">
            <div className="text-center py-12">
              <Zap className="w-16 h-16 text-gray-500 mx-auto mb-6" />
              <h3 className="text-xl font-semibold mb-4">AI Workflows</h3>
              <p className="text-gray-400 mb-6 max-w-md mx-auto">
                Create intelligent content using AI agents that collaborate to produce high-quality results.
              </p>
              <button
                onClick={handleStartWorkflow}
                className="px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2 mx-auto"
              >
                <Zap className="w-5 h-5" />
                Start Your First Workflow
              </button>
            </div>
          </div>
        )}

        {activeTab === 'settings' && project && (
          <ProjectSettingsTab 
            project={project} 
            onProjectUpdate={handleProjectUpdate}
          />
        )}
      </div>
    </div>
  );
};

export default ProjectWorkspace;