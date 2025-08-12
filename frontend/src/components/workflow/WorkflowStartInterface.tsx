// src/components/workflow/WorkflowStartInterface.tsx
import React, { useState } from 'react';
import { Upload, FileText, Zap, Settings, CheckCircle, AlertCircle } from 'lucide-react';

interface WorkflowStartInterfaceProps {
  projectId: string;
  onStartWorkflow: (config: WorkflowConfig) => Promise<void>;
}

interface WorkflowConfig {
  title: string;
  contentType: string;
  hasInitialDraft: boolean;
  initialDraft?: string;
  useProjectDocuments: boolean;
  enableCheckpoints: boolean;
}

export default function WorkflowStartInterface({ projectId, onStartWorkflow }: WorkflowStartInterfaceProps) {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState<WorkflowConfig>({
    title: '',
    contentType: 'article',
    hasInitialDraft: false,
    initialDraft: '',
    useProjectDocuments: true,
    enableCheckpoints: true
  });
  const [draftFile, setDraftFile] = useState<File | null>(null);

  const contentTypes = [
    { value: 'article', label: 'Article', icon: FileText },
    { value: 'blog_post', label: 'Blog Post', icon: FileText },
    { value: 'landing_page', label: 'Landing Page', icon: FileText },
    { value: 'email', label: 'Email', icon: FileText },
    { value: 'social_media', label: 'Social Media', icon: FileText },
  ];

  const handleDraftUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setDraftFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setConfig(prev => ({
          ...prev,
          initialDraft: e.target?.result as string
        }));
      };
      reader.readAsText(file);
    }
  };

  const handleStart = () => {
    if (!config.title.trim()) {
      alert('Please enter a title for your content');
      return;
    }
    onStartWorkflow(config);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-gray-800 rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 to-violet-600 p-6 text-white">
          <h2 className="text-2xl font-bold mb-2">Start SpinScribe Workflow</h2>
          <p className="text-orange-100">Configure your multi-agent content creation workflow</p>
        </div>

        {/* Progress Steps */}
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center justify-between">
            {[
              { step: 1, label: 'Content Details', icon: Settings },
              { step: 2, label: 'Initial Draft', icon: Upload },
              { step: 3, label: 'Configuration', icon: CheckCircle },
            ].map((item, index) => {
              const Icon = item.icon;
              const isActive = step === item.step;
              const isCompleted = step > item.step;
              
              return (
                <div key={item.step} className="flex items-center">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    isActive 
                      ? 'bg-gradient-to-r from-orange-500 to-violet-600 text-white'
                      : isCompleted
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-600 text-gray-300'
                  }`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="ml-3">
                    <p className={`font-medium ${
                      isActive ? 'text-orange-500' : isCompleted ? 'text-green-400' : 'text-gray-400'
                    }`}>
                      Step {item.step}
                    </p>
                    <p className={`text-sm ${
                      isActive ? 'text-white' : 'text-gray-400'
                    }`}>
                      {item.label}
                    </p>
                  </div>
                  
                  {index < 2 && (
                    <div className={`flex-1 h-0.5 mx-4 ${
                      step > item.step ? 'bg-green-400' : 'bg-gray-600'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Step Content */}
        <div className="p-6">
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Content Title *
                </label>
                <input
                  type="text"
                  value={config.title}
                  onChange={(e) => setConfig(prev => ({ ...prev, title: e.target.value }))}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                  placeholder="Enter your content title..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Content Type
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {contentTypes.map((type) => {
                    const Icon = type.icon;
                    const isSelected = config.contentType === type.value;
                    
                    return (
                      <button
                        key={type.value}
                        onClick={() => setConfig(prev => ({ ...prev, contentType: type.value }))}
                        className={`p-4 rounded-lg border transition-all duration-300 ${
                          isSelected
                            ? 'bg-gradient-to-r from-orange-500/20 to-violet-600/20 border-orange-500 text-orange-500'
                            : 'bg-gray-700 border-gray-600 text-gray-300 hover:border-gray-500'
                        }`}
                      >
                        <Icon className="w-6 h-6 mx-auto mb-2" />
                        <span className="text-sm font-medium">{type.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <div className="text-center">
                <h3 className="text-lg font-semibold text-white mb-2">Initial Draft</h3>
                <p className="text-gray-400">Do you have an initial draft to enhance?</p>
              </div>

              <div className="flex gap-4 justify-center">
                <button
                  onClick={() => setConfig(prev => ({ ...prev, hasInitialDraft: false, initialDraft: '' }))}
                  className={`px-6 py-3 rounded-lg font-medium transition-all duration-300 ${
                    !config.hasInitialDraft
                      ? 'bg-gradient-to-r from-orange-500 to-violet-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  No, create from scratch
                </button>
                <button
                  onClick={() => setConfig(prev => ({ ...prev, hasInitialDraft: true }))}
                  className={`px-6 py-3 rounded-lg font-medium transition-all duration-300 ${
                    config.hasInitialDraft
                      ? 'bg-gradient-to-r from-orange-500 to-violet-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  Yes, I have a draft
                </button>
              </div>

              {config.hasInitialDraft && (
                <div className="mt-6">
                  <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center">
                    <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <label className="cursor-pointer">
                      <span className="text-orange-500 font-medium">Upload your draft</span>
                      <span className="text-gray-400"> or drag and drop</span>
                      <input
                        type="file"
                        accept=".txt,.md,.doc,.docx"
                        onChange={handleDraftUpload}
                        className="hidden"
                      />
                    </label>
                    
                    {draftFile && (
                      <div className="mt-4 p-3 bg-gray-700 rounded-lg">
                        <p className="text-green-400 font-medium">{draftFile.name}</p>
                        <p className="text-sm text-gray-400">Draft uploaded successfully</p>
                      </div>
                    )}
                  </div>

                  {!draftFile && (
                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Or paste your draft here:
                      </label>
                      <textarea
                        value={config.initialDraft}
                        onChange={(e) => setConfig(prev => ({ ...prev, initialDraft: e.target.value }))}
                        rows={8}
                        className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                        placeholder="Paste your initial draft content here..."
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6">
              <div className="text-center">
                <h3 className="text-lg font-semibold text-white mb-2">Workflow Configuration</h3>
                <p className="text-gray-400">Configure how the agents will work</p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                  <div>
                    <h4 className="font-medium text-white">Use Project Documents</h4>
                    <p className="text-sm text-gray-400">Agents will use uploaded project documents for RAG integration</p>
                  </div>
                  <button
                    onClick={() => setConfig(prev => ({ ...prev, useProjectDocuments: !prev.useProjectDocuments }))}
                    className={`w-12 h-6 rounded-full transition-all duration-300 ${
                      config.useProjectDocuments ? 'bg-gradient-to-r from-orange-500 to-violet-600' : 'bg-gray-500'
                    }`}
                  >
                    <div className={`w-5 h-5 bg-white rounded-full transition-transform duration-300 ${
                      config.useProjectDocuments ? 'transform translate-x-6' : 'transform translate-x-0.5'
                    }`} />
                  </button>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                  <div>
                    <h4 className="font-medium text-white">Enable Human Checkpoints</h4>
                    <p className="text-sm text-gray-400">Agents will pause for your approval at key stages</p>
                  </div>
                  <button
                    onClick={() => setConfig(prev => ({ ...prev, enableCheckpoints: !prev.enableCheckpoints }))}
                    className={`w-12 h-6 rounded-full transition-all duration-300 ${
                      config.enableCheckpoints ? 'bg-gradient-to-r from-orange-500 to-violet-600' : 'bg-gray-500'
                    }`}
                  >
                    <div className={`w-5 h-5 bg-white rounded-full transition-transform duration-300 ${
                      config.enableCheckpoints ? 'transform translate-x-6' : 'transform translate-x-0.5'
                    }`} />
                  </button>
                </div>
              </div>

              {/* Configuration Summary */}
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="font-medium text-white mb-3">Configuration Summary</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Title:</span>
                    <span className="text-white">{config.title || 'Not set'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Content Type:</span>
                    <span className="text-white">{contentTypes.find(t => t.value === config.contentType)?.label}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Initial Draft:</span>
                    <span className="text-white">{config.hasInitialDraft ? 'Yes' : 'No'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Project Documents:</span>
                    <span className="text-white">{config.useProjectDocuments ? 'Enabled' : 'Disabled'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Checkpoints:</span>
                    <span className="text-white">{config.enableCheckpoints ? 'Enabled' : 'Disabled'}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="p-6 bg-gray-700 flex justify-between">
          <button
            onClick={() => setStep(step - 1)}
            disabled={step === 1}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-500 transition-all duration-300"
          >
            Previous
          </button>

          {step < 3 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={step === 1 && !config.title.trim()}
              className="px-6 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleStart}
              className="px-8 py-2 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg font-medium hover:from-green-600 hover:to-green-700 transition-all duration-300 flex items-center gap-2"
            >
              <Zap className="w-4 h-4" />
              Start Workflow
            </button>
          )}
        </div>
      </div>
    </div>
  );
}


