// src/components/workspace/DocumentsTab.tsx
import React, { useState } from 'react';
import { Upload, FileText, Trash2, Download, Calendar, Loader2 } from 'lucide-react';
import { apiService, Project, Document } from '../../services/api';

interface DocumentsTabProps {
  project: Project;
  documents: Document[];
  onDocumentsChange: () => void;
}

export default function DocumentsTab({ project, documents, onDocumentsChange }: DocumentsTabProps) {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  const handleFileUpload = async () => {
    if (!selectedFile) return;

    try {
      setIsUploading(true);
      setUploadError('');
      await apiService.uploadDocument(project.id, selectedFile);
      await onDocumentsChange();
      setShowUploadModal(false);
      setSelectedFile(null);
    } catch (error) {
      console.error('Failed to upload document:', error);
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDocument = async (documentId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;

    try {
      await apiService.deleteDocument(documentId);
      await onDocumentsChange();
    } catch (error) {
      console.error('Failed to delete document:', error);
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

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setSelectedFile(files[0]);
      setShowUploadModal(true);
    }
  };

  return (
    <div className="h-full p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Documents</h2>
          <p className="text-gray-300">
            Upload and manage project documents for AI analysis
          </p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
        >
          <Upload className="w-5 h-5" />
          Upload Document
        </button>
      </div>

      {/* Drag & Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 mb-6 transition-all duration-300 ${
          isDragging
            ? 'border-orange-500 bg-orange-500/10'
            : 'border-gray-600 hover:border-gray-500'
        }`}
      >
        <div className="text-center">
          <Upload className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-300 mb-2">
            Drag and drop files here, or{' '}
            <button
              onClick={() => setShowUploadModal(true)}
              className="text-orange-500 hover:text-orange-600 font-medium"
            >
              browse
            </button>
          </p>
          <p className="text-gray-500 text-sm">
            Supports PDF, DOCX, TXT, MD files up to 50MB
          </p>
        </div>
      </div>

      {/* Documents List */}
      {documents.length > 0 ? (
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
                      <FileText className="w-6 h-6 text-orange-400" />
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
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDeleteDocument(document.id, document.original_filename)}
                      className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                      title="Delete document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-12">
          <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-400 mb-2">
            No documents uploaded yet
          </h3>
          <p className="text-gray-500 mb-6">
            Upload documents to help AI agents understand your project context and requirements
          </p>
          <button
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
          >
            <Upload className="w-5 h-5" />
            Upload First Document
          </button>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-2xl border border-gray-700 p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">Upload Document</h3>
            
            {uploadError && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                <p className="text-red-400 text-sm">{uploadError}</p>
              </div>
            )}
            
            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center">
                <Upload className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                <input
                  type="file"
                  onChange={(e) => {
                    setSelectedFile(e.target.files?.[0] || null);
                    setUploadError('');
                  }}
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
                    setUploadError('');
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