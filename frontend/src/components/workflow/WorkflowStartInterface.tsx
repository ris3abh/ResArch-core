// frontend/src/components/workflow/WorkflowStartInterface.tsx
// Simplified workflow configuration form component
// This is optional - functionality is already in WorkflowPage.tsx

import React from 'react';
import { Play, FileText, AlertCircle, Loader2 } from 'lucide-react';

interface WorkflowConfig {
  title: string;
  contentType: string;
  initialDraft: string;
  useProjectDocuments: boolean;
}

interface WorkflowStartInterfaceProps {
  config: WorkflowConfig;
  onConfigChange: (config: WorkflowConfig) => void;
  onStart: () => void;
  isStarting?: boolean;
  error?: string;
}

const WorkflowStartInterface: React.FC<WorkflowStartInterfaceProps> = ({
  config,
  onConfigChange,
  onStart,
  isStarting = false,
  error
}) => {
  const contentTypes = [
    { value: 'article', label: 'Article' },
    { value: 'blog_post', label: 'Blog Post' },
    { value: 'email', label: 'Email' },
    { value: 'social_media', label: 'Social Media Post' },
    { value: 'marketing_copy', label: 'Marketing Copy' },
    { value: 'technical_docs', label: 'Technical Documentation' },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (config.title.trim()) {
      onStart();
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center gap-3 mb-6">
          <FileText className="w-6 h-6 text-orange-500" />
          <h2 className="text-xl font-semibold text-white">Configure Workflow</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Content Title *
            </label>
            <input
              type="text"
              value={config.title}
              onChange={(e) => onConfigChange({ ...config, title: e.target.value })}
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
              placeholder="Enter content title..."
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Content Type
            </label>
            <select
              value={config.contentType}
              onChange={(e) => onConfigChange({ ...config, contentType: e.target.value })}
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-orange-500"
            >
              {contentTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Initial Draft (Optional)
            </label>
            <textarea
              value={config.initialDraft}
              onChange={(e) => onConfigChange({ ...config, initialDraft: e.target.value })}
              rows={4}
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
              placeholder="Provide any initial content or requirements..."
            />
          </div>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={config.useProjectDocuments}
              onChange={(e) => onConfigChange({ ...config, useProjectDocuments: e.target.checked })}
              className="w-5 h-5 text-orange-500 bg-gray-700 border-gray-600 rounded focus:ring-orange-500"
            />
            <span className="text-sm text-gray-300">Use project documents</span>
          </label>

          {error && (
            <div className="p-3 bg-red-900/20 border border-red-600/30 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={!config.title.trim() || isStarting}
            className="w-full py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium hover:from-orange-600 hover:to-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
          >
            {isStarting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Start Workflow
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default WorkflowStartInterface;