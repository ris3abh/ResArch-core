import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AuthModal from './components/AuthModal';
import Dashboard from './components/Dashboard';
import ClientWorkspace from './components/ClientWorkspace';
import { AuthProvider, useAuth } from './contexts/AuthContext';

function AppRoutes() {
  const { user } = useAuth();

  if (!user) {
    return <AuthModal />;
  }

  return (
    <Routes>
      <Route path="/clients" element={<Dashboard />} />
      <Route path="/client/:clientId" element={<ClientWorkspace />} />
      <Route path="/client/:clientId/project/:projectId" element={<ClientWorkspace />} />
      <Route path="/" element={<Navigate to="/clients" replace />} />
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