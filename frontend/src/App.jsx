import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Layout
import Layout from './layout/Layout';

// Pages
import SplashScreen from './pages/SplashScreen';
import LoginPage from './pages/LoginPage';
import FormPage from './pages/FormPage';
import SOAPPage from './pages/SOAPPage';

// New Agent Pages
import AgentFormPage from './agent/pages/AgentFormPage';
import AgentResultPage from './agent/pages/AgentResultPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<SplashScreen />} />
        <Route path="/login" element={<LoginPage />} />
        
        {/* Protected routes wrapped in Layout */}
        <Route element={<Layout />}>
          <Route path="/home" element={<div className="p-8 text-2xl font-bold">Dashboard Home</div>} />
          <Route path="/form" element={<FormPage />} />
          <Route path="/soap" element={<SOAPPage />} />
          <Route path="/agent" element={<AgentFormPage />} />
          <Route path="/agent-result" element={<AgentResultPage />} />
        </Route>
        
        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
