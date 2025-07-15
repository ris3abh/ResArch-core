import React, { useState } from 'react';
import { Plus, Search, Users, Calendar, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Sidebar from './Sidebar';

interface Client {
  id: string;
  name: string;
  projectCount: number;
  lastActivity: string;
  status: 'active' | 'inactive';
}

const mockClients: Client[] = [
  { id: '1', name: 'Acme Corporation', projectCount: 5, lastActivity: '2 hours ago', status: 'active' },
  { id: '2', name: 'Tech Solutions Inc', projectCount: 3, lastActivity: '1 day ago', status: 'active' },
  { id: '3', name: 'Creative Agency', projectCount: 8, lastActivity: '3 days ago', status: 'inactive' },
  { id: '4', name: 'StartUp Ventures', projectCount: 2, lastActivity: '1 week ago', status: 'active' },
];

export default function Dashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newClientName, setNewClientName] = useState('');
  const navigate = useNavigate();
  const { user } = useAuth();

  const filteredClients = mockClients.filter(client =>
    client.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleAddClient = () => {
    if (newClientName.trim()) {
      // In a real app, this would make an API call
      console.log('Adding client:', newClientName);
      setNewClientName('');
      setShowAddModal(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto">
        <div className="p-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">Client Workspaces</h1>
              <p className="text-gray-300">Manage your client projects and content workflows</p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-violet-700 transition-all duration-300 shadow-lg hover:shadow-xl"
            >
              <Plus className="w-5 h-5" />
              Add Client
            </button>
          </div>

          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search clients..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredClients.map((client) => (
              <div
                key={client.id}
                onClick={() => navigate(`/client/${client.id}`)}
                className="group p-6 bg-gradient-to-br from-gray-800 to-gray-700 backdrop-blur-xl rounded-2xl border border-gray-600 hover:border-orange-500/30 transition-all duration-300 cursor-pointer hover:shadow-2xl hover:shadow-orange-500/10"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-violet-600 rounded-lg flex items-center justify-center">
                      <Users className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white group-hover:text-orange-400 transition-colors">
                        {client.name}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <div className={`w-2 h-2 rounded-full ${client.status === 'active' ? 'bg-green-500' : 'bg-gray-500'}`} />
                        <span className="text-sm text-gray-300 capitalize">{client.status}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm text-gray-300">
                    <Activity className="w-4 h-4" />
                    <span>{client.projectCount} projects</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-300">
                    <Calendar className="w-4 h-4" />
                    <span>Last activity: {client.lastActivity}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredClients.length === 0 && (
            <div className="text-center py-12">
              <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-300">No clients found matching your search</p>
            </div>
          )}
        </div>
      </main>

      {showAddModal && (
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-800 backdrop-blur-xl p-8 rounded-2xl border border-gray-700 w-full max-w-md shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-6">Add New Client</h3>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Client name"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all duration-300 text-white placeholder-gray-400"
                autoFocus
              />
              <div className="flex gap-3">
                <button
                  onClick={handleAddClient}
                  className="flex-1 py-3 bg-gradient-to-r from-orange-500 to-violet-600 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-violet-700 transition-all duration-300"
                >
                  Add Client
                </button>
                <button
                  onClick={() => setShowAddModal(false)}
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