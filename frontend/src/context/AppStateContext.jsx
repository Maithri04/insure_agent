/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState } from "react";

const AppStateContext = createContext(null);

export function AppStateProvider({ children }) {
  const [soapData, setSoapData] = useState(null);
  const [agentResult, setAgentResult] = useState(null);
  const [caseId, setCaseId] = useState("");
  const [patientMeta, setPatientMeta] = useState(null);
  const [doctor, setDoctor] = useState(() => {
    try {
      const raw = localStorage.getItem("doctor");
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    try {
      if (doctor) localStorage.setItem("doctor", JSON.stringify(doctor));
      else localStorage.removeItem("doctor");
    } catch {
      // Ignore localStorage write errors.
    }
  }, [doctor]);

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
      doctor,
      setDoctor,
    }),
    [soapData, agentResult, caseId, patientMeta, doctor],
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
