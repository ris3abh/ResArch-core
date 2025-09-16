// frontend/src/components/workflow/AgentProgressDisplay.tsx
// Real-time agent progress and workflow stage display component

import React, { useState, useEffect } from 'react';
import {
  Bot,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  Zap,
  Brain,
  FileText,
  Edit3,
  Shield,
  TrendingUp,
  Activity,
  Pause,
  Play,
  ChevronRight,
  ChevronDown,
  Info
} from 'lucide-react';

interface AgentProgressDisplayProps {
  currentStage: string;
  activeAgents: string[];
  workflowStatus: 'running' | 'paused' | 'completed' | 'error';
  onCheckpointApproval?: (approved: boolean, feedback?: string) => void;
}

interface WorkflowStage {
  id: string;
  name: string;
  description: string;
  agent: string;
  icon: React.ComponentType<any>;
  status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
  progress?: number;
  startTime?: string;
  endTime?: string;
  output?: string;
}

interface AgentInfo {
  id: string;
  name: string;
  role: string;
  color: string;
  icon: React.ComponentType<any>;
  isActive: boolean;
  currentTask?: string;
  messagesCount: number;
}

// Checkpoint Approval Component
export const CheckpointApproval: React.FC<{
  checkpoint: {
    id: string;
    title: string;
    description: string;
    content?: string;
  };
  onApprove: (feedback?: string) => void;
  onReject: (feedback?: string) => void;
}> = ({ checkpoint, onApprove, onReject }) => {
  const [feedback, setFeedback] = useState('');
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4">
      <div className="flex items-start gap-3 mb-3">
        <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />
        <div className="flex-1">
          <h4 className="font-medium text-yellow-300">{checkpoint.title}</h4>
          <p className="text-sm text-gray-300 mt-1">{checkpoint.description}</p>
        </div>
      </div>

      {checkpoint.content && (
        <div className="mb-3">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center gap-2 text-sm text-yellow-400 hover:text-yellow-300 transition-colors"
          >
            {showDetails ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            View Content Preview
          </button>
          {showDetails && (
            <div className="mt-2 p-3 bg-gray-800 rounded-lg max-h-40 overflow-y-auto">
              <pre className="text-xs text-gray-300 whitespace-pre-wrap">{checkpoint.content}</pre>
            </div>
          )}
        </div>
      )}

      <div className="space-y-3">
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Add feedback (optional)..."
          className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 text-sm resize-none"
          rows={2}
        />
        <div className="flex gap-3">
          <button
            onClick={() => onApprove(feedback)}
            className="flex-1 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
          >
            <CheckCircle className="w-4 h-4" />
            Approve
          </button>
          <button
            onClick={() => onReject(feedback)}
            className="flex-1 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
          >
            <AlertCircle className="w-4 h-4" />
            Request Changes
          </button>
        </div>
      </div>
    </div>
  );
};

// Main Component
const AgentProgressDisplay: React.FC<AgentProgressDisplayProps> = ({
  currentStage,
  activeAgents,
  workflowStatus,
  onCheckpointApproval
}) => {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [showStageDetails, setShowStageDetails] = useState(true);

  // Define workflow stages
  const workflowStages: WorkflowStage[] = [
    {
      id: 'initialization',
      name: 'Initialization',
      description: 'Setting up workflow and loading project context',
      agent: 'coordinator',
      icon: Zap,
      status: currentStage === 'Initializing' ? 'active' : 
              ['style_analysis', 'content_planning', 'content_generation', 'editing_qa', 'completion'].includes(currentStage) ? 'completed' : 'pending'
    },
    {
      id: 'style_analysis',
      name: 'Style Analysis',
      description: 'Analyzing brand voice and content requirements',
      agent: 'style_analysis',
      icon: Brain,
      status: currentStage === 'style_analysis' ? 'active' : 
              ['content_planning', 'content_generation', 'editing_qa', 'completion'].includes(currentStage) ? 'completed' : 'pending'
    },
    {
      id: 'content_planning',
      name: 'Content Planning',
      description: 'Creating content structure and outline',
      agent: 'content_planning',
      icon: FileText,
      status: currentStage === 'content_planning' ? 'active' : 
              ['content_generation', 'editing_qa', 'completion'].includes(currentStage) ? 'completed' : 'pending'
    },
    {
      id: 'content_generation',
      name: 'Content Generation',
      description: 'Writing the actual content',
      agent: 'content_generation',
      icon: Edit3,
      status: currentStage === 'content_generation' ? 'active' : 
              ['editing_qa', 'completion'].includes(currentStage) ? 'completed' : 'pending'
    },
    {
      id: 'editing_qa',
      name: 'Editing & QA',
      description: 'Review, editing, and quality assurance',
      agent: 'editing_qa',
      icon: Shield,
      status: currentStage === 'editing_qa' ? 'active' : 
              currentStage === 'completion' ? 'completed' : 'pending'
    },
    {
      id: 'completion',
      name: 'Finalization',
      description: 'Finalizing and delivering content',
      agent: 'coordinator',
      icon: CheckCircle,
      status: currentStage === 'completion' ? 'active' : 'pending'
    }
  ];

  // Define agent information
  const agentInfoMap: { [key: string]: AgentInfo } = {
    'coordinator': {
      id: 'coordinator',
      name: 'Workflow Coordinator',
      role: 'Orchestrates the entire workflow',
      color: 'from-blue-500 to-blue-600',
      icon: Zap,
      isActive: activeAgents.includes('coordinator'),
      currentTask: currentStage === 'Initializing' ? 'Setting up workflow' : 
                   currentStage === 'completion' ? 'Finalizing content' : undefined,
      messagesCount: 0
    },
    'style_analysis': {
      id: 'style_analysis',
      name: 'Style Analyst',
      role: 'Analyzes brand voice and style',
      color: 'from-purple-500 to-purple-600',
      icon: Brain,
      isActive: activeAgents.includes('style_analysis'),
      currentTask: currentStage === 'style_analysis' ? 'Analyzing brand guidelines' : undefined,
      messagesCount: 0
    },
    'content_planning': {
      id: 'content_planning',
      name: 'Content Planner',
      role: 'Creates content structure',
      color: 'from-indigo-500 to-indigo-600',
      icon: FileText,
      isActive: activeAgents.includes('content_planning'),
      currentTask: currentStage === 'content_planning' ? 'Building content outline' : undefined,
      messagesCount: 0
    },
    'content_generation': {
      id: 'content_generation',
      name: 'Content Creator',
      role: 'Writes the actual content',
      color: 'from-green-500 to-green-600',
      icon: Edit3,
      isActive: activeAgents.includes('content_generation') || activeAgents.includes('Content Creator'),
      currentTask: currentStage === 'content_generation' ? 'Writing content' : undefined,
      messagesCount: 0
    },
    'editing_qa': {
      id: 'editing_qa',
      name: 'Editor & QA',
      role: 'Reviews and polishes content',
      color: 'from-yellow-500 to-yellow-600',
      icon: Shield,
      isActive: activeAgents.includes('editing_qa'),
      currentTask: currentStage === 'editing_qa' ? 'Reviewing content quality' : undefined,
      messagesCount: 0
    },
    'Content Strategist': {
      id: 'content_strategist',
      name: 'Content Strategist',
      role: 'Strategic content planning',
      color: 'from-pink-500 to-pink-600',
      icon: TrendingUp,
      isActive: activeAgents.includes('Content Strategist'),
      currentTask: undefined,
      messagesCount: 0
    }
  };

  // Get active stage progress
  const getStageProgress = (stage: WorkflowStage): number => {
    if (stage.status === 'completed') return 100;
    if (stage.status === 'active') return 50; // Could be enhanced with real progress
    return 0;
  };

  // Calculate overall progress
  const overallProgress = Math.round(
    workflowStages.reduce((acc, stage) => acc + getStageProgress(stage), 0) / workflowStages.length
  );

  return (
    <div className="space-y-4">
      {/* Overall Progress */}
      <div className="bg-gray-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white font-semibold">Workflow Progress</h3>
          <span className="text-sm text-gray-400">{overallProgress}%</span>
        </div>
        
        <div className="bg-gray-700 rounded-full h-2 overflow-hidden mb-3">
          <div 
            className="bg-gradient-to-r from-orange-500 to-violet-600 h-full transition-all duration-500"
            style={{ width: `${overallProgress}%` }}
          />
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Current Stage:</span>
          <span className="text-orange-400 font-medium">{currentStage}</span>
        </div>

        <div className="flex items-center justify-between text-sm mt-1">
          <span className="text-gray-400">Status:</span>
          <div className="flex items-center gap-2">
            {workflowStatus === 'running' && (
              <>
                <Activity className="w-4 h-4 text-green-400 animate-pulse" />
                <span className="text-green-400">Running</span>
              </>
            )}
            {workflowStatus === 'paused' && (
              <>
                <Pause className="w-4 h-4 text-yellow-400" />
                <span className="text-yellow-400">Paused</span>
              </>
            )}
            {workflowStatus === 'completed' && (
              <>
                <CheckCircle className="w-4 h-4 text-blue-400" />
                <span className="text-blue-400">Completed</span>
              </>
            )}
            {workflowStatus === 'error' && (
              <>
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span className="text-red-400">Error</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Workflow Stages */}
      <div className="bg-gray-800 rounded-xl p-4">
        <button
          onClick={() => setShowStageDetails(!showStageDetails)}
          className="w-full flex items-center justify-between mb-3"
        >
          <h3 className="text-white font-semibold">Workflow Stages</h3>
          {showStageDetails ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
        </button>

        {showStageDetails && (
          <div className="space-y-2">
            {workflowStages.map((stage, index) => {
              const Icon = stage.icon;
              return (
                <div 
                  key={stage.id}
                  className={`relative flex items-center gap-3 p-3 rounded-lg transition-all ${
                    stage.status === 'active' 
                      ? 'bg-gradient-to-r from-orange-500/20 to-violet-600/20 border border-orange-500/30' 
                      : 'bg-gray-700/50'
                  }`}
                >
                  {/* Connection Line */}
                  {index < workflowStages.length - 1 && (
                    <div className={`absolute left-7 top-12 w-0.5 h-8 ${
                      stage.status === 'completed' ? 'bg-green-500' : 'bg-gray-600'
                    }`} />
                  )}

                  {/* Stage Icon */}
                  <div className={`relative flex items-center justify-center w-8 h-8 rounded-full ${
                    stage.status === 'completed' ? 'bg-green-500' :
                    stage.status === 'active' ? 'bg-gradient-to-r from-orange-500 to-violet-600' :
                    stage.status === 'error' ? 'bg-red-500' :
                    'bg-gray-600'
                  }`}>
                    {stage.status === 'completed' ? (
                      <CheckCircle className="w-4 h-4 text-white" />
                    ) : stage.status === 'active' ? (
                      <Loader2 className="w-4 h-4 text-white animate-spin" />
                    ) : stage.status === 'error' ? (
                      <AlertCircle className="w-4 h-4 text-white" />
                    ) : (
                      <Icon className="w-4 h-4 text-gray-300" />
                    )}
                  </div>

                  {/* Stage Info */}
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className={`font-medium ${
                        stage.status === 'active' ? 'text-orange-400' :
                        stage.status === 'completed' ? 'text-green-400' :
                        stage.status === 'error' ? 'text-red-400' :
                        'text-gray-300'
                      }`}>
                        {stage.name}
                      </h4>
                      {stage.status === 'active' && stage.progress !== undefined && (
                        <span className="text-xs text-gray-400">{stage.progress}%</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{stage.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Active Agents */}
      <div className="bg-gray-800 rounded-xl p-4">
        <h3 className="text-white font-semibold mb-3">Active Agents</h3>
        
        {activeAgents.length === 0 ? (
          <p className="text-sm text-gray-400">No agents active yet</p>
        ) : (
          <div className="space-y-2">
            {activeAgents.map(agentId => {
              const agent = agentInfoMap[agentId] || {
                id: agentId,
                name: agentId,
                role: 'AI Agent',
                color: 'from-gray-500 to-gray-600',
                icon: Bot,
                isActive: true,
                messagesCount: 0
              };
              
              const Icon = agent.icon;
              const isExpanded = expandedAgent === agentId;

              return (
                <div 
                  key={agentId}
                  className="bg-gray-700/50 rounded-lg overflow-hidden"
                >
                  <button
                    onClick={() => setExpandedAgent(isExpanded ? null : agentId)}
                    className="w-full flex items-center gap-3 p-3 hover:bg-gray-700/70 transition-colors"
                  >
                    <div className={`w-8 h-8 rounded-full bg-gradient-to-r ${agent.color} flex items-center justify-center`}>
                      <Icon className="w-4 h-4 text-white" />
                    </div>
                    
                    <div className="flex-1 text-left">
                      <h4 className="text-sm font-medium text-white">{agent.name}</h4>
                      {agent.currentTask && (
                        <p className="text-xs text-gray-400">{agent.currentTask}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {agent.isActive && (
                        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                      )}
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="px-3 pb-3 border-t border-gray-600">
                      <div className="mt-2 space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-400">Role:</span>
                          <span className="text-gray-300">{agent.role}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-400">Status:</span>
                          <span className="text-green-400">Active</span>
                        </div>
                        {agent.currentTask && (
                          <div className="flex justify-between text-xs">
                            <span className="text-gray-400">Current Task:</span>
                            <span className="text-gray-300">{agent.currentTask}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Workflow Info */}
      <div className="bg-gray-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Info className="w-4 h-4 text-gray-400" />
          <h3 className="text-white font-semibold">Workflow Info</h3>
        </div>
        
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Type:</span>
            <span className="text-gray-300">Multi-Agent Content Creation</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Agents:</span>
            <span className="text-gray-300">{activeAgents.length} active</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Checkpoints:</span>
            <span className="text-gray-300">Enabled</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentProgressDisplay;