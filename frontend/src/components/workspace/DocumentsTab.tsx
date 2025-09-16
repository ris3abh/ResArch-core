// frontend/src/components/workspace/DocumentsTab.tsx
// Enhanced version with real API integration and document management

import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  FileText,
  Download,
  Trash2,
  Search,
  Filter,
  Folder,
  File,
  Image,
  FileCode,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle,
  X,
  Loader2,
  Eye,
  MoreVertical,
  Grid,
  List,
  Calendar,
  HardDrive
} from 'lucide-react';
import { apiService, Document, DocumentStats } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

interface DocumentsTabProps {
  projectId: string;
  onDocumentSelect?: (document: Document) => void;
}

const DocumentsTab: React.FC<DocumentsTabProps> = ({ projectId, onDocumentSelect }) => {
  const { user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // State management
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentStats, setDocumentStats] = useState<DocumentStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [dragActive, setDragActive] = useState(false);

  // File type icons and colors
  const fileTypeInfo: { [key: string]: { icon: React.ComponentType<any>; color: string } } = {
    'pdf': { icon: FileText, color: 'text-red-500' },
    'doc': { icon: FileText, color: 'text-blue-500' },
    'docx': { icon: FileText, color: 'text-blue-500' },
    'txt': { icon: FileText, color: 'text-gray-500' },
    'md': { icon: FileText, color: 'text-purple-500' },
    'jpg': { icon: Image, color: 'text-green-500' },
    'jpeg': { icon: Image, color: 'text-green-500' },
    'png': { icon: Image, color: 'text-green-500' },
    'gif': { icon: Image, color: 'text-green-500' },
    'svg': { icon: Image, color: 'text-yellow-500' },
    'xls': { icon: FileSpreadsheet, color: 'text-green-600' },
    'xlsx': { icon: FileSpreadsheet, color: 'text-green-600' },
    'csv': { icon: FileSpreadsheet, color: 'text-green-600' },
    'json': { icon: FileCode, color: 'text-orange-500' },
    'xml': { icon: FileCode, color: 'text-orange-500' },
    'html': { icon: FileCode, color: 'text-red-500' },
    'css': { icon: FileCode, color: 'text-blue-500' },
    'js': { icon: FileCode, color: 'text-yellow-500' },
    'ts': { icon: FileCode, color: 'text-blue-600' },
    'default': { icon: File, color: 'text-gray-400' }
  };

  // Load documents and stats
  useEffect(() => {
    loadDocuments();
    loadDocumentStats();
  }, [projectId]);

  // Clear messages after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(''), 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(''), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const loadDocuments = async () => {
    try {
      setIsLoading(true);
      const docs = await apiService.getProjectDocuments(projectId);
      setDocuments(docs);
    } catch (err: any) {
      console.error('Failed to load documents:', err);
      setError('Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocumentStats = async () => {
    try {
      const stats = await apiService.getDocumentStats();
      setDocumentStats(stats);
    } catch (err: any) {
      console.error('Failed to load document stats:', err);
      // Non-critical error, don't show to user
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      setSelectedFiles(Array.from(files));
    }
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setSelectedFiles(files);
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadProgress(0);
    setError('');

    try {
      let completed = 0;
      const total = selectedFiles.length;

      for (const file of selectedFiles) {
        try {
          // Upload with progress tracking
          await apiService.uploadWithProgress(
            `/documents/upload/${projectId}`,
            file,
            (progress) => {
              const overallProgress = ((completed + progress / 100) / total) * 100;
              setUploadProgress(Math.round(overallProgress));
            }
          );
          completed++;
        } catch (err: any) {
          console.error(`Failed to upload ${file.name}:`, err);
          setError(`Failed to upload ${file.name}`);
        }
      }

      setSuccessMessage(`Successfully uploaded ${completed} file(s)`);
      setSelectedFiles([]);
      await loadDocuments();
      await loadDocumentStats();
    } catch (err: any) {
      console.error('Upload failed:', err);
      setError('Failed to upload files');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDownload = async (doc: Document) => {
    try {
      const blob = await apiService.downloadDocument(doc.id);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = doc.original_filename || doc.filename;
      a.click();
      window.URL.revokeObjectURL(url);
      setSuccessMessage(`Downloaded ${doc.filename}`);
    } catch (err: any) {
      console.error('Download failed:', err);
      setError('Failed to download file');
    }
  };

  const handleDelete = async (document: Document) => {
    if (!window.confirm(`Are you sure you want to delete ${document.filename}?`)) {
      return;
    }

    try {
      await apiService.deleteDocument(document.id);
      setDocuments(prev => prev.filter(doc => doc.id !== document.id));
      setSuccessMessage(`Deleted ${document.filename}`);
      await loadDocumentStats();
    } catch (err: any) {
      console.error('Delete failed:', err);
      setError('Failed to delete file');
    }
  };

  // Get file icon and color
  const getFileInfo = (filename: string) => {
    const extension = filename.split('.').pop()?.toLowerCase() || '';
    return fileTypeInfo[extension] || fileTypeInfo.default;
  };

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  // Filter documents
  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         doc.original_filename?.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (filterType === 'all') return matchesSearch;
    
    const extension = doc.filename.split('.').pop()?.toLowerCase() || '';
    
    switch (filterType) {
      case 'documents':
        return matchesSearch && ['pdf', 'doc', 'docx', 'txt', 'md'].includes(extension);
      case 'images':
        return matchesSearch && ['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(extension);
      case 'spreadsheets':
        return matchesSearch && ['xls', 'xlsx', 'csv'].includes(extension);
      case 'code':
        return matchesSearch && ['json', 'xml', 'html', 'css', 'js', 'ts'].includes(extension);
      default:
        return matchesSearch;
    }
  });

  // Calculate total size
  const totalSize = documents.reduce((acc, doc) => acc + doc.file_size, 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-orange-500 mx-auto mb-4" />
          <p className="text-gray-300">Loading documents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-gray-800 rounded-t-xl p-6 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Documents</h2>
            <p className="text-sm text-gray-400 mt-1">
              {documents.length} files • {formatFileSize(totalSize)}
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            {/* View Mode Toggle */}
            <div className="flex bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded ${viewMode === 'grid' ? 'bg-gray-600 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                <Grid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded ${viewMode === 'list' ? 'bg-gray-600 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>

            {/* Upload Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 transition-all duration-300 flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Upload Files
            </button>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search documents..."
              className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
            />
          </div>
          
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-orange-500"
          >
            <option value="all">All Files</option>
            <option value="documents">Documents</option>
            <option value="images">Images</option>
            <option value="spreadsheets">Spreadsheets</option>
            <option value="code">Code Files</option>
          </select>
        </div>
      </div>

      {/* Messages */}
      {successMessage && (
        <div className="mx-6 mt-4 p-3 bg-green-900/20 border border-green-600/30 rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-green-300 text-sm">{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage('')} className="text-green-400 hover:text-green-300">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {error && (
        <div className="mx-6 mt-4 p-3 bg-red-900/20 border border-red-600/30 rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <span className="text-red-300 text-sm">{error}</span>
          </div>
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-300">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Upload Progress */}
      {isUploading && (
        <div className="mx-6 mt-4 p-4 bg-gray-800 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-300">Uploading files...</span>
            <span className="text-sm text-gray-400">{uploadProgress}%</span>
          </div>
          <div className="bg-gray-700 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-orange-500 to-violet-600 h-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Selected Files Preview */}
      {selectedFiles.length > 0 && (
        <div className="mx-6 mt-4 p-4 bg-gray-800 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-white">Ready to Upload</h3>
            <button
              onClick={() => setSelectedFiles([])}
              className="text-gray-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-2 mb-3">
            {selectedFiles.map((file, index) => (
              <div key={index} className="flex items-center justify-between py-2 px-3 bg-gray-700 rounded">
                <div className="flex items-center gap-3">
                  {(() => {
                    const fileInfo = getFileInfo(file.name);
                    const Icon = fileInfo.icon;
                    return <Icon className={`w-4 h-4 ${fileInfo.color}`} />;
                  })()}
                  <span className="text-sm text-gray-300">{file.name}</span>
                </div>
                <span className="text-xs text-gray-500">{formatFileSize(file.size)}</span>
              </div>
            ))}
          </div>
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="w-full py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
          >
            Upload {selectedFiles.length} File{selectedFiles.length > 1 ? 's' : ''}
          </button>
        </div>
      )}

      {/* Documents List/Grid */}
      <div className="flex-1 overflow-y-auto p-6">
        {filteredDocuments.length === 0 ? (
          <div
            className={`h-full flex items-center justify-center border-2 border-dashed rounded-xl transition-colors ${
              dragActive ? 'border-orange-500 bg-orange-500/10' : 'border-gray-700'
            }`}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <div className="text-center">
              <Upload className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 mb-2">
                {searchTerm || filterType !== 'all' 
                  ? 'No documents found' 
                  : 'No documents uploaded yet'}
              </p>
              <p className="text-sm text-gray-500">
                Drag and drop files here or click the upload button
              </p>
            </div>
          </div>
        ) : viewMode === 'grid' ? (
          // Grid View
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredDocuments.map((doc) => {
              const fileInfo = getFileInfo(doc.filename);
              const Icon = fileInfo.icon;
              
              return (
                <div
                  key={doc.id}
                  className="bg-gray-800 rounded-lg p-4 hover:bg-gray-700 transition-colors cursor-pointer group"
                >
                  <div className="flex flex-col items-center">
                    <Icon className={`w-12 h-12 ${fileInfo.color} mb-3`} />
                    <p className="text-sm text-white text-center truncate w-full" title={doc.filename}>
                      {doc.filename}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">{formatFileSize(doc.file_size)}</p>
                    <p className="text-xs text-gray-600 mt-1">{formatDate(doc.created_at)}</p>
                    
                    <div className="flex gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDownload(doc);
                        }}
                        className="p-2 bg-gray-700 rounded hover:bg-gray-600 transition-colors"
                        title="Download"
                      >
                        <Download className="w-3 h-3 text-gray-300" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(doc);
                        }}
                        className="p-2 bg-gray-700 rounded hover:bg-red-600 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3 text-gray-300" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          // List View
          <div className="space-y-2">
            {filteredDocuments.map((doc) => {
              const fileInfo = getFileInfo(doc.filename);
              const Icon = fileInfo.icon;
              
              return (
                <div
                  key={doc.id}
                  className="bg-gray-800 rounded-lg p-4 hover:bg-gray-700 transition-colors cursor-pointer flex items-center justify-between group"
                >
                  <div className="flex items-center gap-4">
                    <Icon className={`w-8 h-8 ${fileInfo.color}`} />
                    <div>
                      <p className="text-white font-medium">{doc.filename}</p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                        <span>{formatFileSize(doc.file_size)}</span>
                        <span>•</span>
                        <span>{formatDate(doc.created_at)}</span>
                        <span>•</span>
                        <span>Uploaded by {doc.uploaded_by_id === user?.id ? 'You' : 'Team member'}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDocumentSelect?.(doc);
                      }}
                      className="p-2 bg-gray-700 rounded hover:bg-gray-600 transition-colors"
                      title="View"
                    >
                      <Eye className="w-4 h-4 text-gray-300" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDownload(doc);
                      }}
                      className="p-2 bg-gray-700 rounded hover:bg-gray-600 transition-colors"
                      title="Download"
                    >
                      <Download className="w-4 h-4 text-gray-300" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(doc);
                      }}
                      className="p-2 bg-gray-700 rounded hover:bg-red-600 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4 text-gray-300" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Stats Footer */}
      {documentStats && (
        <div className="bg-gray-800 border-t border-gray-700 px-6 py-4">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Folder className="w-4 h-4 text-gray-400" />
                <span className="text-gray-300">{documentStats.total_projects} Projects</span>
              </div>
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-gray-400" />
                <span className="text-gray-300">{documentStats.total_documents} Total Documents</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-gray-400" />
              <span className="text-gray-300">{formatFileSize(totalSize)} Used</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentsTab;