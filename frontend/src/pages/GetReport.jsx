import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Card from "../components/Card";
import InputField from "../components/InputField";
import SectionTitle from "../components/SectionTitle";
import { useAppState } from "../context/AppStateContext";
import { getCaseById } from "../services/api";

export default function GetReport() {
  const navigate = useNavigate();
  const { setAgentResult, setCaseId } = useAppState();
  const [form, setForm] = useState({ patient_name: "", case_id: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleAccess = async () => {
    if (!form.patient_name.trim() || !form.case_id.trim()) {
      setError("Both Patient Name and Case ID are required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await getCaseById(form.case_id.trim().toUpperCase());
      if (form.patient_name.trim().toLowerCase() !== (response.patient_name || "").trim().toLowerCase()) {
        throw new Error("Patient name does not match this case ID.");
      }
      setAgentResult(response);
      setCaseId(form.case_id.trim().toUpperCase());
      navigate("/report");
    } catch (apiError) {
      setError(apiError.message || "Case not found. Please verify the patient name and case ID.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <SectionTitle title="Get Report" description="Retrieve report by case ID and patient name." />
      <Card className="max-w-xl">
        <div className="space-y-4">
          <InputField label="Patient Name" name="patient_name" value={form.patient_name} onChange={set("patient_name")} />
          <InputField label="Case ID" name="case_id" value={form.case_id} onChange={set("case_id")} />
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <Button onClick={handleAccess} loading={loading} disabled={loading}>Get Report</Button>
        </div>
      </Card>
    </div>
  );
}

