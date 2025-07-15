import React, { useState } from 'react';
import { Plus, Calendar, Activity, MessageCircle, Search, Filter, FolderOpen } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Project {
  id: string;
  name: string;
  lastUpdated: string;
  status: 'active' | 'completed' | 'on-hold';
  messageCount: number;
  stage: 'planning' | 'content' | 'review' | 'delivered';
}

const mockProjects: Project[] = [
  {
    id: '1',
    name: 'Brand Strategy Content',
    lastUpdated: '2 hours ago',
    status: 'active',
    messageCount: 24,
    stage: 'content'
  },
  {
    id: '2',
    name: 'Product Launch Campaign',
    lastUpdated: '1 day ago',
    status: 'active',
    messageCount: 18,
    stage: 'review'
  },
  {
    id: '3',
    name: 'Website Copy Refresh',
    lastUpdated: '3 days ago',
    status: 'completed',
    messageCount: 32,
    stage: 'delivered'
  },
  {
    id: '4',
    name: 'Social Media Guidelines',
    lastUpdated: '1 week ago',
    status: 'on-hold',
    messageCount: 12,
    stage: 'planning'
  },
];

const statusColors = {
  active: 'bg-green-500',
  completed: 'bg-blue-500',
  'on-hold': 'bg-yellow-500',
};

const stageColors = {
  planning: 'from-gray-500 to-gray-600',
  content: 'from-orange-500 to-orange-600',
  review: 'from-violet-500 to-violet-600',
  delivered: 'from-green-500 to-green-600',
};

interface ProjectsTabProps {
  clientId: string;
}

export default function ProjectsTab({ clientId }: ProjectsTabProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const navigate = useNavigate();

  const filteredProjects = mockProjects.filter(project => {
    const matchesSearch = project.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === 'all' || project.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const handleCreateProject = () => {
    if (newProjectName.trim()) {
      console.log('Creating project:', newProjectName);
      setNewProjectName('');
      setShowCreateModal(false);
    }
  };

  const handleProjectClick = (project: Project) => {
    navigate(`/client/${clientId}/project/${project.id}`);
  };
  return (
    <div className="h-full p-8 overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Projects</h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
          >
            <Plus className="w-4 h-4" />
            New Project
          </button>
        </div>

        <div className="flex gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="on-hold">On Hold</option>
          </select>
        </div>

        <div className="grid gap-4">
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              onClick={() => handleProjectClick(project)}
              className="group p-6 bg-gradient-to-br from-gray-800 to-gray-700 backdrop-blur-xl rounded-xl border border-gray-600 hover:border-orange-500/30 transition-all duration-300 cursor-pointer hover:shadow-2xl hover:shadow-orange-500/10"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="font-semibold text-white group-hover:text-orange-400 transition-colors mb-2">
                    {project.name}
                  </h3>
                  <div className="flex items-center gap-4 text-sm text-gray-300">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${statusColors[project.status]}`} />
                      <span className="capitalize">{project.status}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      <span>{project.lastUpdated}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MessageCircle className="w-4 h-4" />
                      <span>{project.messageCount} messages</span>
                    </div>
                  </div>
                </div>
                <div className={`px-3 py-1 bg-gradient-to-r ${stageColors[project.stage]} text-white text-sm font-medium rounded-full`}>
                  {project.stage}
                </div>
              </div>
              
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-600">
                <span className="text-sm text-gray-400">Click to open chat</span>
                <MessageCircle className="w-5 h-5 text-orange-400 group-hover:text-orange-300 transition-colors" />
              </div>
            </div>
          ))}
        </div>

        {filteredProjects.length === 0 && (
          <div className="text-center py-12">
            <FolderOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-300">No projects found</p>
          </div>
        )}


      {showCreateModal && (
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-800 backdrop-blur-xl p-8 rounded-2xl border border-gray-700 w-full max-w-md shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-6">Create New Project</h3>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Project name"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400"
                autoFocus
              />
              <div className="flex gap-3">
                <button
                  onClick={handleCreateProject}
                  className="flex-1 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
                >
                  Create Project
                </button>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-3 bg-gray-700 text-white font-semibold rounded-xl hover:bg-gray-600 transition-all duration-300"
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