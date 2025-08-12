// src/components/workflow/AgentProgressDisplay.tsx
import React, { useState, useEffect } from 'react';
import { Bot, CheckCircle, Clock, AlertTriangle, Zap, FileText, Palette, PenTool, Search } from 'lucide-react';

interface AgentProgressDisplayProps {
  workflowId: string;
  onCheckpointRequired: (checkpointId: string, data: any) => void;
}

interface AgentStage {
  id: string;
  name: string;
  agent: string;
  icon: React.ComponentType<any>;
  color: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  progress: number;
  message?: string;
  output?: string;
  timestamp?: string;
}

interface CheckpointData {
  id: string;
  type: string;
  title: string;
  description: string;
  data: any;
  status: 'pending' | 'approved' | 'rejected';
}

export default function AgentProgressDisplay({ workflowId, onCheckpointRequired }: AgentProgressDisplayProps) {
  const [stages, setStages] = useState<AgentStage[]>([
    {
      id: 'document_processing',
      name: 'Document Processing',
      agent: 'Document Processor',
      icon: FileText,
      color: 'from-blue-500 to-blue-600',
      status: 'pending',
      progress: 0
    },
    {
      id: 'style_analysis',
      name: 'Style Analysis',
      agent: 'Style Analysis Agent',
      icon: Palette,
      color: 'from-purple-500 to-purple-600',
      status: 'pending',
      progress: 0
    },
    {
      id: 'content_planning',
      name: 'Content Planning',
      agent: 'Content Planning Agent',
      icon: Search,
      color: 'from-indigo-500 to-indigo-600',
      status: 'pending',
      progress: 0
    },
    {
      id: 'content_generation',
      name: 'Content Generation',
      agent: 'Content Generation Agent',
      icon: PenTool,
      color: 'from-green-500 to-green-600',
      status: 'pending',
      progress: 0
    },
    {
      id: 'quality_assurance',
      name: 'Quality Assurance',
      agent: 'QA Agent',
      icon: CheckCircle,
      color: 'from-orange-500 to-orange-600',
      status: 'pending',
      progress: 0
    }
  ]);

  const [currentCheckpoint, setCurrentCheckpoint] = useState<CheckpointData | null>(null);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    // Establish WebSocket connection
    const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/workflows/${workflowId}`);
    
    ws.onopen = () => {
      setConnectionStatus('connected');
      console.log('WebSocket connected to workflow:', workflowId);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      console.log('WebSocket disconnected');
      
      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        setConnectionStatus('connecting');
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('disconnected');
    };

    setWebsocket(ws);

    return () => {
      ws.close();
    };
  }, [workflowId]);

  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'stage_update':
        updateStageProgress(message.stage, message.progress, message.message);
        break;
        
      case 'checkpoint_required':
        handleCheckpointRequired(message);
        break;
        
      case 'agent_output':
        updateStageOutput(message.stage, message.output);
        break;
        
      case 'workflow_completed':
        markAllStagesCompleted();
        break;
        
      case 'workflow_failed':
        markWorkflowFailed(message.error);
        break;
    }
  };

  const updateStageProgress = (stageId: string, progress: number, message?: string) => {
    setStages(prevStages => 
      prevStages.map(stage => {
        if (stage.id === stageId) {
          return {
            ...stage,
            status: progress >= 100 ? 'completed' : 'active',
            progress,
            message,
            timestamp: new Date().toLocaleTimeString()
          };
        }
        // Mark previous stages as completed
        const stageIndex = prevStages.findIndex(s => s.id === stageId);
        const currentIndex = prevStages.findIndex(s => s.id === stage.id);
        if (currentIndex < stageIndex && stage.status !== 'completed') {
          return {
            ...stage,
            status: 'completed',
            progress: 100
          };
        }
        return stage;
      })
    );
  };

  const updateStageOutput = (stageId: string, output: string) => {
    setStages(prevStages =>
      prevStages.map(stage =>
        stage.id === stageId
          ? { ...stage, output }
          : stage
      )
    );
  };

  const handleCheckpointRequired = (message: any) => {
    const checkpoint: CheckpointData = {
      id: message.checkpoint_id,
      type: message.checkpoint_data.type,
      title: message.checkpoint_data.title,
      description: message.checkpoint_data.description,
      data: message.checkpoint_data,
      status: 'pending'
    };
    
    setCurrentCheckpoint(checkpoint);
    onCheckpointRequired(checkpoint.id, checkpoint.data);
  };

  const markAllStagesCompleted = () => {
    setStages(prevStages =>
      prevStages.map(stage => ({
        ...stage,
        status: 'completed',
        progress: 100
      }))
    );
  };

  const markWorkflowFailed = (error: string) => {
    setStages(prevStages => {
      const activeStageIndex = prevStages.findIndex(s => s.status === 'active');
      return prevStages.map((stage, index) => ({
        ...stage,
        status: index === activeStageIndex ? 'failed' : stage.status,
        message: index === activeStageIndex ? `Failed: ${error}` : stage.message
      }));
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'active':
        return <div className="w-5 h-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />;
      case 'failed':
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getConnectionStatusIndicator = () => {
    switch (connectionStatus) {
      case 'connected':
        return <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />;
      case 'connecting':
        return <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />;
      default:
        return <div className="w-2 h-2 bg-red-500 rounded-full" />;
    }
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-semibold text-white mb-1">Agent Workflow Progress</h3>
          <p className="text-gray-400">Real-time multi-agent collaboration</p>
        </div>
        
        <div className="flex items-center gap-2">
          {getConnectionStatusIndicator()}
          <span className="text-sm text-gray-400">
            {connectionStatus === 'connected' ? 'Live' : 
             connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Progress Overview */}
      <div className="mb-8">
        <div className="flex items-center justify-between text-sm text-gray-400 mb-2">
          <span>Overall Progress</span>
          <span>
            {Math.round(stages.reduce((acc, stage) => acc + stage.progress, 0) / stages.length)}%
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div 
            className="bg-gradient-to-r from-orange-500 to-violet-600 h-2 rounded-full transition-all duration-500"
            style={{ width: `${stages.reduce((acc, stage) => acc + stage.progress, 0) / stages.length}%` }}
          />
        </div>
      </div>

      {/* Agent Stages */}
      <div className="space-y-4">
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          const isActive = stage.status === 'active';
          const isCompleted = stage.status === 'completed';
          const isFailed = stage.status === 'failed';

          return (
            <div 
              key={stage.id}
              className={`rounded-lg border transition-all duration-500 ${
                isActive 
                  ? 'bg-gradient-to-r from-orange-500/10 to-violet-600/10 border-orange-500/50'
                  : isCompleted
                    ? 'bg-green-900/20 border-green-500/50'
                    : isFailed
                      ? 'bg-red-900/20 border-red-500/50'
                      : 'bg-gray-700/50 border-gray-600'
              }`}
            >
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg bg-gradient-to-r ${stage.color} flex items-center justify-center`}>
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h4 className="font-medium text-white">{stage.name}</h4>
                      <p className="text-sm text-gray-400">{stage.agent}</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {stage.timestamp && (
                      <span className="text-xs text-gray-500">{stage.timestamp}</span>
                    )}
                    {getStatusIcon(stage.status)}
                  </div>
                </div>

                {/* Progress Bar */}
                {stage.status === 'active' && (
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span>Progress</span>
                      <span>{stage.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-600 rounded-full h-1.5">
                      <div 
                        className={`bg-gradient-to-r ${stage.color} h-1.5 rounded-full transition-all duration-300`}
                        style={{ width: `${stage.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Current Message */}
                {stage.message && (
                  <div className="bg-gray-700 rounded-lg p-3 mb-3">
                    <p className="text-sm text-gray-300">{stage.message}</p>
                  </div>
                )}

                {/* Agent Output */}
                {stage.output && (
                  <div className="bg-gray-900 rounded-lg p-3 border-l-4 border-blue-500">
                    <p className="text-xs text-blue-400 mb-1">Agent Output:</p>
                    <p className="text-sm text-gray-300 leading-relaxed">{stage.output}</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Current Checkpoint */}
      {currentCheckpoint && currentCheckpoint.status === 'pending' && (
        <div className="mt-6 bg-gradient-to-r from-yellow-900/20 to-orange-900/20 border border-yellow-500/50 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-yellow-500 mt-1" />
            <div className="flex-1">
              <h4 className="font-medium text-yellow-300 mb-1">Checkpoint Required</h4>
              <h5 className="text-white font-medium mb-2">{currentCheckpoint.title}</h5>
              <p className="text-gray-300 text-sm leading-relaxed">{currentCheckpoint.description}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Checkpoint Approval Component
interface CheckpointApprovalProps {
  checkpoint: CheckpointData;
  onApprove: (checkpointId: string, feedback: string) => void;
  onReject: (checkpointId: string, feedback: string) => void;
}

export function CheckpointApproval({ checkpoint, onApprove, onReject }: CheckpointApprovalProps) {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleApprove = async () => {
    setIsSubmitting(true);
    await onApprove(checkpoint.id, feedback);
    setIsSubmitting(false);
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    await onReject(checkpoint.id, feedback);
    setIsSubmitting(false);
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-yellow-500/50">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-12 h-12 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-lg flex items-center justify-center">
          <AlertTriangle className="w-6 h-6 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">{checkpoint.title}</h3>
          <p className="text-gray-400">Checkpoint ID: {checkpoint.id}</p>
        </div>
      </div>

      <div className="bg-gray-700 rounded-lg p-4 mb-4">
        <p className="text-gray-300 leading-relaxed">{checkpoint.description}</p>
      </div>

      {/* Checkpoint Data Display */}
      {checkpoint.data && (
        <div className="bg-gray-900 rounded-lg p-4 mb-4">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Content for Review:</h4>
          <div className="max-h-64 overflow-y-auto">
            <pre className="text-sm text-gray-400 whitespace-pre-wrap">
              {JSON.stringify(checkpoint.data, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Feedback Input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Feedback (Optional)
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
          placeholder="Provide feedback or instructions for the agents..."
        />
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleApprove}
          disabled={isSubmitting}
          className="flex-1 px-4 py-2 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg font-medium hover:from-green-600 hover:to-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2"
        >
          {isSubmitting ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <CheckCircle className="w-4 h-4" />
          )}
          Approve & Continue
        </button>
        
        <button
          onClick={handleReject}
          disabled={isSubmitting}
          className="px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center gap-2"
        >
          <AlertTriangle className="w-4 h-4" />
          Request Changes
        </button>
      </div>
    </div>
  );
}