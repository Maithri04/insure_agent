import React, { useEffect, useState } from "react";
import { BrowserRouter as Router, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { AppStateProvider, useAppState } from "./context/AppStateContext";

import AgentForm from "./pages/AgentForm";
import AgentResult from "./pages/AgentResult";
import CaseReport from "./pages/CaseReport";
import Chatbot from "./pages/Chatbot";
import GetReport from "./pages/GetReport";
import History from "./pages/History";
import Login from "./pages/Login";
import SoapForm from "./pages/SoapForm";
import SoapReport from "./pages/SoapReport";

function RequireAuth({ children }) {
  const { doctor } = useAppState();
  if (!doctor) return <Navigate to="/login" replace />;
  return children;
}

function DefaultRedirect() {
  return <Navigate to="/login" replace />;
}

export default function App() {
  const [showStartupCard, setShowStartupCard] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShowStartupCard(false), 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <AppStateProvider>
      {showStartupCard ? (
        <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-[#075789] via-[#0d7dbd] to-[#2da2df] flex items-center justify-center">
          <div className="absolute inset-0 opacity-20 bg-[radial-gradient(circle_at_20%_20%,rgba(255,255,255,0.35),transparent_35%),radial-gradient(circle_at_80%_80%,rgba(255,255,255,0.25),transparent_35%)]" />
          <div className="absolute -top-24 -left-24 h-72 w-72 rounded-full bg-white/15 blur-3xl" />
          <div className="absolute -bottom-24 -right-24 h-72 w-72 rounded-full bg-cyan-200/20 blur-3xl" />

          <div className="relative text-center px-8">
            <p className="text-blue-100/95 text-sm md:text-base tracking-[0.35em] uppercase mb-5 font-medium">
              InsureMind AI
            </p>
            <h1 className="text-white text-5xl md:text-7xl font-semibold tracking-[0.22em] drop-shadow-[0_6px_22px_rgba(0,0,0,0.28)]">
              INSURE AGENT
            </h1>
            <p className="mt-6 text-blue-100/95 text-sm md:text-base tracking-wider">
              Preparing your healthcare assistant...
            </p>
          </div>
        </div>
      ) : (
        <Router>
          <Routes>
            <Route path="/" element={<DefaultRedirect />} />
            <Route path="/login" element={<Login />} />
            <Route
              path="/*"
              element={(
                <RequireAuth>
                  <Layout>
                    <Routes>
                      <Route path="/soap" element={<SoapForm />} />
                      <Route path="/soap-report" element={<SoapReport />} />
                      <Route path="/agent" element={<AgentForm />} />
                      <Route path="/agent-result" element={<AgentResult />} />
                      <Route path="/chat" element={<Chatbot />} />
                      <Route path="/get" element={<GetReport />} />
                      <Route path="/history" element={<History />} />
                      <Route path="/report" element={<CaseReport />} />
                      <Route path="*" element={<Navigate to="/agent" replace />} />
                    </Routes>
                  </Layout>
                </RequireAuth>
              )}
            />
          </Routes>
        </Router>
      )}
    </AppStateProvider>
  );
}
