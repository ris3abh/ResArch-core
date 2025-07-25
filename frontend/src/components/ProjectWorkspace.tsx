// src/components/ProjectWorkspace.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Upload, FileText, MessageCircle, Plus, Calendar, Loader2, Trash2 } from 'lucide-react';
import { apiService, Project, Document } from '../services/api';
import Sidebar from './Sidebar';

interface Chat {
  id: string;
  name: string;
  createdAt: string;
  lastMessage?: string;
  lastActivity: string;
}

// Mock chats for now - will be replaced with real API
const mockChats: Chat[] = [
  {
    id: '1',
    name: 'Initial Content Strategy',
    createdAt: '2024-01-15T10:30:00Z',
    lastMessage: 'Content outline looks great! Ready to proceed with generation.',
    lastActivity: '2 hours ago'
  },
  {
    id: '2', 
    name: 'Blog Post Series Planning',
    createdAt: '2024-01-14T15:20:00Z',
    lastMessage: 'Let me analyze your brand voice and create the blog series outline.',
    lastActivity: '1 day ago'
  },
  {
    id: '3',
    name: 'Social Media Guidelines',
    createdAt: '2024-01-12T09:15:00Z',
    lastMessage: 'Guidelines document is ready for review.',
    lastActivity: '3 days ago'
  }
];

export default function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [chats, setChats] = useState<Chat[]>(mockChats);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [error, setError] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showNewChatModal, setShowNewChatModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [newChatName, setNewChatName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [showDeleteChatModal, setShowDeleteChatModal] = useState(false);
  const [chatToDelete, setChatToDelete] = useState<Chat | null>(null);
  const [isDeletingChat, setIsDeletingChat] = useState(false);

  useEffect(() => {
    if (projectId) {
      loadProject();
      loadDocuments();
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
      // Don't show error if it's a session expiration (user will be redirected)
      if (error instanceof Error && !error.message.includes('Session expired')) {
        setError('Failed to load project');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocuments = async () => {
    if (!projectId) return;

    try {
      setIsLoadingDocuments(true);
      const documentsData = await apiService.getProjectDocuments(projectId);
      setDocuments(documentsData);
    } catch (error) {
      console.error('Failed to load documents:', error);
      // Don't show error if it's a session expiration (user will be redirected)
      if (error instanceof Error && !error.message.includes('Session expired')) {
        setError('Failed to load documents');
      }
    } finally {
      setIsLoadingDocuments(false);
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

  const handleCreateChat = async () => {
    if (!newChatName.trim()) return;

    try {
      setIsCreatingChat(true);
      // TODO: Replace with real API call
      const newChat: Chat = {
        id: Date.now().toString(),
        name: newChatName,
        createdAt: new Date().toISOString(),
        lastActivity: 'Just now'
      };
      
      setChats([newChat, ...chats]);
      setShowNewChatModal(false);
      setNewChatName('');
      
      // Navigate to the new chat
      navigate(`/project/${projectId}/chat/${newChat.id}`);
    } catch (error) {
      console.error('Failed to create chat:', error);
      setError('Failed to create chat');
    } finally {
      setIsCreatingChat(false);
    }
  };

  const handleDeleteChat = async () => {
    if (!chatToDelete) return;

    try {
      setIsDeletingChat(true);
      // TODO: Replace with real API call
      setChats(chats.filter(c => c.id !== chatToDelete.id));
      setShowDeleteChatModal(false);
      setChatToDelete(null);
    } catch (error) {
      console.error('Failed to delete chat:', error);
      setError('Failed to delete chat');
    } finally {
      setIsDeletingChat(false);
    }
  };

  const openDeleteChatModal = (chat: Chat, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent navigation to chat
    setChatToDelete(chat);
    setShowDeleteChatModal(true);
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

  if (error && !project) {
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
      
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-700 bg-gray-800/50 backdrop-blur-xl">
          <div className="px-6 py-4">
            <div className="flex items-center gap-4 mb-4">
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
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* Main Content Area */}
          <div className="flex-1 p-6 overflow-y-auto">
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

            {/* Documents Section */}
            <div className="mb-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-white mb-2">Project Documents</h2>
                  <p className="text-gray-300">
                    Upload documents to help AI agents understand your project context
                  </p>
                </div>
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
                >
                  <Upload className="w-4 h-4" />
                  Upload Document
                </button>
              </div>

              {isLoadingDocuments ? (
                <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-8 text-center">
                  <Loader2 className="w-6 h-6 animate-spin text-orange-500 mx-auto mb-2" />
                  <p className="text-gray-400">Loading documents...</p>
                </div>
              ) : documents.length > 0 ? (
                <div className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden">
                  <div className="p-4 border-b border-gray-700">
                    <h3 className="font-semibold text-white">
                      Uploaded Documents ({documents.length})
                    </h3>
                  </div>
                  <div className="divide-y divide-gray-700">
                    {documents.map((document) => (
                      <div key={document.id} className="p-4 hover:bg-gray-700/30 transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4 flex-1">
                            <div className="p-2 bg-orange-500/20 rounded-lg">
                              <FileText className="w-5 h-5 text-orange-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium text-white mb-1 truncate">
                                {document.original_filename}
                              </h4>
                              <div className="flex items-center gap-4 text-sm text-gray-400">
                                <span>{formatFileSize(document.file_size)}</span>
                                <span className="capitalize">{document.file_type.split('/').pop()}</span>
                                <div className="flex items-center gap-1">
                                  <Calendar className="w-3 h-3" />
                                  <span>{formatDate(document.created_at)}</span>
                                </div>
                              </div>
                            </div>
                          </div>
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
                </div>
              ) : (
                <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-8 text-center">
                  <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-400 mb-2">
                    No documents uploaded yet
                  </h3>
                  <p className="text-gray-500 mb-4">
                    Upload documents to provide context for AI agents
                  </p>
                  <button
                    onClick={() => setShowUploadModal(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
                  >
                    <Upload className="w-4 h-4" />
                    Upload First Document
                  </button>
                </div>
              )}
            </div>

            {/* Start New Chat Section */}
            <div className="text-center">
              <div className="inline-flex items-center gap-3 p-6 bg-gradient-to-r from-orange-500/10 to-violet-600/10 rounded-xl border border-orange-500/20">
                <MessageCircle className="w-8 h-8 text-orange-400" />
                <div className="text-left">
                  <h3 className="text-lg font-semibold text-white">Ready to start creating?</h3>
                  <p className="text-gray-300">Begin a new conversation with AI agents</p>
                </div>
                <button
                  onClick={() => setShowNewChatModal(true)}
                  className="ml-4 px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
                >
                  Start New Chat
                </button>
              </div>
            </div>
          </div>

          {/* Chat History Sidebar */}
          <div className="w-80 border-l border-gray-700 bg-gray-800/30 p-4">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Chat History</h3>
              <button
                onClick={() => setShowNewChatModal(true)}
                className="p-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  className="p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-orange-500/30 transition-all duration-300 group"
                >
                  <div className="flex items-start justify-between">
                    <div 
                      className="flex-1 cursor-pointer"
                      onClick={() => navigate(`/project/${projectId}/chat/${chat.id}`)}
                    >
                      <h4 className="font-medium text-white mb-2 group-hover:text-orange-400 transition-colors">
                        {chat.name}
                      </h4>
                      {chat.lastMessage && (
                        <p className="text-gray-400 text-sm mb-2 line-clamp-2">
                          {chat.lastMessage}
                        </p>
                      )}
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Calendar className="w-3 h-3" />
                        <span>{chat.lastActivity}</span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => openDeleteChatModal(chat, e)}
                      className="p-1 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all duration-300"
                      title="Delete chat"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {chats.length === 0 && (
              <div className="text-center py-8">
                <MessageCircle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 text-sm mb-4">No chats yet</p>
                <button
                  onClick={() => setShowNewChatModal(true)}
                  className="text-orange-500 hover:text-orange-600 font-medium text-sm"
                >
                  Start your first chat
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

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
                  Supports PDF, DOCX, TXT, MD files (max 50MB)
                </p>
                {selectedFile && (
                  <div className="mt-3 p-2 bg-gray-700 rounded text-left">
                    <p className="text-white text-sm font-medium">
                      {selectedFile.name}
                    </p>
                    <p className="text-gray-400 text-xs">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
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

      {/* New Chat Modal */}
      {showNewChatModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-2xl border border-gray-700 p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">Start New Chat</h3>
            
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Give your chat a name..."
                value={newChatName}
                onChange={(e) => setNewChatName(e.target.value)}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400"
                autoFocus
              />
              
              <div className="flex gap-3">
                <button
                  onClick={handleCreateChat}
                  disabled={!newChatName.trim() || isCreatingChat}
                  className="flex-1 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-lg hover:from-orange-600 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
                >
                  {isCreatingChat ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Start Chat'
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowNewChatModal(false);
                    setNewChatName('');
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

      {/* Delete Chat Modal */}
      {showDeleteChatModal && chatToDelete && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-2xl border border-gray-700 p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">Delete Chat</h3>
            
            <div className="mb-6">
              <div className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-4">
                <Trash2 className="w-5 h-5 text-red-400" />
                <div>
                  <p className="text-red-400 font-medium">This action cannot be undone</p>
                  <p className="text-red-300 text-sm">All messages in this chat will be permanently deleted</p>
                </div>
              </div>
              
              <p className="text-gray-300">
                Are you sure you want to delete the chat <strong className="text-white">"{chatToDelete.name}"</strong>?
              </p>
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={handleDeleteChat}
                disabled={isDeletingChat}
                className="flex-1 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
              >
                {isDeletingChat ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete Chat
                  </>
                )}
              </button>
              <button
                onClick={() => {
                  setShowDeleteChatModal(false);
                  setChatToDelete(null);
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