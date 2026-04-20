/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo, useState } from "react";

const AppStateContext = createContext(null);

export function AppStateProvider({ children }) {
  const [soapData, setSoapData] = useState(null);
  const [agentResult, setAgentResult] = useState(null);
  const [caseId, setCaseId] = useState("");
  const [patientMeta, setPatientMeta] = useState(null);

  const value = useMemo(
    () => ({
      soapData,
      setSoapData,
      agentResult,
      setAgentResult,
      caseId,
      setCaseId,
      patientMeta,
      setPatientMeta,
    }),
    [soapData, agentResult, caseId, patientMeta],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error("useAppState must be used inside AppStateProvider");
  }
  return context;
}
