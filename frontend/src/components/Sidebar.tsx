import React from 'react';
import { Users, LogOut, Settings, Home } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { icon: Home, label: 'Dashboard', path: '/clients' },
    { icon: Users, label: 'Clients', path: '/clients' },
  ];

  return (
    <div className="w-64 bg-gray-800 backdrop-blur-xl border-r border-gray-700 flex flex-col">
      <div className="p-6 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-violet-600 rounded-lg flex items-center justify-center">
            <span className="text-lg font-bold text-white">S</span>
          </div>
          <div>
            <h2 className="font-semibold text-white">SpinScribe</h2>
            <p className="text-sm text-gray-300">Portal</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4">
        <div className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 ${
                  isActive 
                    ? 'bg-gradient-to-r from-orange-500/20 to-violet-600/20 text-orange-500 border border-orange-500/30' 
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      <div className="p-4 border-t border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-violet-600 rounded-lg flex items-center justify-center">
            <span className="text-sm font-bold text-white">
              {user?.name?.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.name}</p>
            <p className="text-xs text-gray-300 truncate">{user?.email}</p>
          </div>
        </div>
        
        <div className="space-y-2">
          <button className="w-full flex items-center gap-3 px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-all duration-300">
            <Settings className="w-4 h-4" />
            <span className="text-sm">Settings</span>
          </button>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-2 text-gray-300 hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-all duration-300"
          >
            <LogOut className="w-4 h-4" />
            <span className="text-sm">Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );
}