import React, { useState } from 'react';
import { Upload, Search, FileText, Tag, Calendar, Trash2, Edit, Download } from 'lucide-react';

interface KnowledgeItem {
  id: string;
  name: string;
  type: 'pdf' | 'docx' | 'txt' | 'md';
  uploadDate: string;
  size: string;
  tags: string[];
  content: string;
  chunks: number;
}

const mockKnowledge: KnowledgeItem[] = [
  {
    id: '1',
    name: 'Brand Guidelines.pdf',
    type: 'pdf',
    uploadDate: '2024-01-15',
    size: '2.4 MB',
    tags: ['branding', 'guidelines', 'style'],
    content: 'Brand guidelines and style guide for consistent brand implementation...',
    chunks: 24
  },
  {
    id: '2',
    name: 'Product Specifications.docx',
    type: 'docx',
    uploadDate: '2024-01-14',
    size: '1.8 MB',
    tags: ['product', 'specifications', 'technical'],
    content: 'Detailed product specifications and technical requirements...',
    chunks: 18
  },
  {
    id: '3',
    name: 'Marketing Strategy.md',
    type: 'md',
    uploadDate: '2024-01-13',
    size: '450 KB',
    tags: ['marketing', 'strategy', 'campaign'],
    content: 'Comprehensive marketing strategy for Q1 2024...',
    chunks: 12
  },
];

const fileTypeColors = {
  pdf: 'from-red-500 to-red-600',
  docx: 'from-blue-500 to-blue-600',
  txt: 'from-gray-500 to-gray-600',
  md: 'from-green-500 to-green-600',
};

interface KnowledgeTabProps {
  clientId: string;
}

export default function KnowledgeTab({ clientId }: KnowledgeTabProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItem, setSelectedItem] = useState<KnowledgeItem | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const filteredKnowledge = mockKnowledge.filter(item =>
    item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      console.log('Dropped file:', files[0]);
      // Handle file upload
    }
  };

  return (
    <div className="flex h-full">
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-900">Knowledge Base</h2>
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
          >
            <Upload className="w-4 h-4" />
            Upload Files
          </button>
        </div>

        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-4 h-4" />
            <input
              type="text"
              placeholder="Search knowledge base..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-gray-900 placeholder-gray-500"
            />
          </div>
        </div>

        <div className="grid gap-4">
          {filteredKnowledge.map((item) => (
            <div
              key={item.id}
              onClick={() => setSelectedItem(item)}
              className="group p-6 bg-gradient-to-br from-gray-50 to-gray-100 backdrop-blur-xl rounded-xl border border-gray-200 hover:border-orange-500/30 transition-all duration-300 cursor-pointer"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 bg-gradient-to-r ${fileTypeColors[item.type]} rounded-lg flex items-center justify-center`}>
                    <FileText className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 group-hover:text-orange-500 transition-colors mb-1">
                      {item.name}
                    </h3>
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span>{item.size}</span>
                      <span>{item.chunks} chunks</span>
                      <div className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        <span>{item.uploadDate}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-300">
                    <Edit className="w-4 h-4" />
                  </button>
                  <button className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-300">
                    <Download className="w-4 h-4" />
                  </button>
                  <button className="p-2 text-gray-600 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-300">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div className="flex flex-wrap gap-2 mb-3">
                {item.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 bg-gradient-to-r from-orange-500/20 to-violet-600/20 text-orange-500 text-sm rounded-full border border-orange-500/30"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
              
              <p className="text-gray-600 text-sm line-clamp-2">{item.content}</p>
            </div>
          ))}
        </div>

        {filteredKnowledge.length === 0 && (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-600">No knowledge items found</p>
          </div>
        )}
      </div>

      {selectedItem && (
        <div className="w-80 bg-gray-50 backdrop-blur-xl border-l border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Knowledge Details</h3>
            <button
              onClick={() => setSelectedItem(null)}
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              ×
            </button>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 bg-gradient-to-r ${fileTypeColors[selectedItem.type]} rounded-lg flex items-center justify-center`}>
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div>
                <h4 className="font-medium text-white">{selectedItem.name}</h4>
                <p className="text-sm text-gray-600">{selectedItem.size}</p>
              </div>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Upload Date:</span>
                <span className="text-gray-900">{selectedItem.uploadDate}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Chunks:</span>
                <span className="text-gray-900">{selectedItem.chunks}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Type:</span>
                <span className="text-gray-900 uppercase">{selectedItem.type}</span>
              </div>
            </div>
            
            <div>
              <h5 className="text-sm font-medium text-gray-600 mb-2">Tags</h5>
              <div className="flex flex-wrap gap-1">
                {selectedItem.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 bg-gradient-to-r from-orange-500/20 to-violet-600/20 text-orange-500 text-xs rounded-full border border-orange-500/30"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
            
            <div>
              <h5 className="text-sm font-medium text-gray-600 mb-2">Content Preview</h5>
              <p className="text-sm text-gray-700 bg-gray-100 p-3 rounded-lg">
                {selectedItem.content}
              </p>
            </div>
          </div>
        </div>
      )}

      {showUploadModal && (
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white backdrop-blur-xl p-8 rounded-2xl border border-gray-200 w-full max-w-md shadow-2xl">
            <h3 className="text-xl font-bold text-gray-900 mb-6">Upload Knowledge</h3>
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
                dragActive ? 'border-orange-500 bg-orange-500/10' : 'border-gray-600 hover:border-gray-500'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 mb-2">Drag and drop files here</p>
              <p className="text-sm text-gray-500 mb-4">or click to browse</p>
              <button className="px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300">
                Choose Files
              </button>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowUploadModal(false)}
                className="flex-1 py-3 bg-gray-100 text-gray-900 font-semibold rounded-xl hover:bg-gray-200 transition-all duration-300"
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