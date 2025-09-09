// src/App.tsx
// FIXED VERSION - Proper routing for workflow components

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AuthModal from './components/AuthModal';
import Dashboard from './components/Dashboard';
import ProjectWorkspace from './components/ProjectWorkspace';
import WorkflowPage from './components/WorkflowPage';
import { AuthProvider, useAuth } from './contexts/AuthContext';

function AppRoutes() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-orange-500 to-violet-600 rounded-full mb-4 animate-pulse">
            <span className="text-2xl font-bold text-white">S</span>
          </div>
          <h1 className="text-xl font-semibold text-white mb-2">SpinScribe</h1>
          <p className="text-gray-300">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <AuthModal />;
  }

  return (
    <Routes>
      {/* Main Dashboard */}
      <Route path="/dashboard" element={<Dashboard />} />
      
      {/* Project Management */}
      <Route path="/project/:projectId" element={<ProjectWorkspace />} />
      
      {/* Workflow Routes - Updated to use the fixed WorkflowPage */}
      <Route path="/workflow/:projectId" element={<WorkflowPage />} />
      <Route path="/workflow/:projectId/:workflowId" element={<WorkflowPage />} />
      
      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      
      {/* Catch-all route */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-gray-900 text-white">
          <AppRoutes />
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;