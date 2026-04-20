import React from "react";
import { BrowserRouter as Router, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { AppStateProvider } from "./context/AppStateContext";

import AgentForm from "./pages/AgentForm";
import AgentResult from "./pages/AgentResult";
import CaseReport from "./pages/CaseReport";
import Chatbot from "./pages/Chatbot";
import GetReport from "./pages/GetReport";
import History from "./pages/History";
import SoapForm from "./pages/SoapForm";
import SoapReport from "./pages/SoapReport";

export default function App() {
  return (
    <AppStateProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/soap" replace />} />
            <Route path="/soap" element={<SoapForm />} />
            <Route path="/soap-report" element={<SoapReport />} />
            <Route path="/agent" element={<AgentForm />} />
            <Route path="/agent-result" element={<AgentResult />} />
            <Route path="/chat" element={<Chatbot />} />
            <Route path="/get" element={<GetReport />} />
            <Route path="/history" element={<History />} />
            <Route path="/report" element={<CaseReport />} />
            <Route path="*" element={<Navigate to="/soap" replace />} />
          </Routes>
        </Layout>
      </Router>
    </AppStateProvider>
  );
}
