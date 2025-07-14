import React, { useState } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { FolderOpen, Brain, MessageCircle } from 'lucide-react';
import Sidebar from './Sidebar';
import ProjectsTab from './workspace/ProjectsTab';
import KnowledgeTab from './workspace/KnowledgeTab';
import ChatTab from './workspace/ChatTab';

type TabType = 'projects' | 'knowledge' | 'chat';

export default function ClientWorkspace() {
  const { clientId, projectId } = useParams<{ clientId: string; projectId?: string }>();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<TabType>(projectId ? 'chat' : 'projects');

  const tabs = [
    { id: 'projects', label: 'Projects', icon: FolderOpen },
    { id: 'knowledge', label: 'Knowledge', icon: Brain },
    { id: 'chat', label: 'Chat', icon: MessageCircle },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'projects':
        return <ProjectsTab clientId={clientId!} />;
      case 'knowledge':
        return <KnowledgeTab clientId={clientId!} />;
      case 'chat':
        return <ChatTab clientId={clientId!} projectId={projectId} />;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen bg-gray-900">
      <Sidebar />
      
      <main className="flex-1 flex flex-col">
        <div className="border-b border-gray-700 bg-gray-800 backdrop-blur-xl">
          <div className="px-8 py-6">
            <h1 className="text-2xl font-bold text-white mb-2">
              {projectId ? 'Project Chat' : (clientId === '1' ? 'Acme Corporation' : 'Client Workspace')}
            </h1>
            <p className="text-gray-300">
              {projectId ? 'Chat with AI agents for your project' : 'Manage projects, knowledge base, and chat interactions'}
            </p>
          </div>
          
          <div className="px-8">
            <div className="flex space-x-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                // Hide projects and knowledge tabs when in project chat mode
                if (projectId && (tab.id === 'projects' || tab.id === 'knowledge')) {
                  return null;
                }
                
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as TabType)}
                    className={`flex items-center gap-2 px-6 py-3 rounded-t-xl transition-all duration-300 ${
                      activeTab === tab.id
                        ? 'bg-gradient-to-r from-orange-500/20 to-violet-600/20 text-orange-500 border-t border-l border-r border-orange-500/30'
                        : 'text-gray-300 hover:text-white hover:bg-gray-700'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
        
        <div className="flex-1 overflow-hidden">
          {renderTabContent()}
        </div>
      </main>
    </div>
  );
}