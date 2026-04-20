import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Card from "../components/Card";
import SectionTitle from "../components/SectionTitle";
import { useAppState } from "../context/AppStateContext";
import { downloadPDF } from "../services/api";
import { useState } from "react";

export default function CaseReport() {
  const navigate = useNavigate();
  const { agentResult, caseId } = useAppState();
  const [downloading, setDownloading] = useState(false);

  if (!agentResult) {
    return (
      <Card>
        <p className="text-sm text-gray-600 mb-3">No case loaded.</p>
        <Button onClick={() => navigate("/get")}>Find Report</Button>
      </Card>
    );
  }

  const resolvedCaseId = caseId || agentResult.case_id || agentResult.caseId || "-";

  const patientName = agentResult.patient_name || agentResult.patient_details?.name || "-";
  const patientAge = agentResult.patient_age || agentResult.patient_details?.age || "-";
  const patientGender = agentResult.patient_gender || agentResult.patient_details?.gender || "-";
  const tpa = agentResult.tpa || "—";
  const disease = agentResult.disease_description || "—";
  const meds = agentResult.medications || "—";
  const approvalRec = agentResult.approval_recommendation || "—";
  const approvalPct = agentResult.approval_probability != null ? `${Math.round(agentResult.approval_probability * 100)}%` : (agentResult.insurance_approval_rate || "—");
  const icdCode = agentResult.icd_code || agentResult.icd?.code || "—";
  const icdDesc = agentResult.icd_description || agentResult.icd?.description || "—";

  const soap =
    agentResult.soap ||
    agentResult.soap_note ||
    agentResult.soap_json ||
    {};

  const handleDownload = async () => {
    if (!resolvedCaseId || resolvedCaseId === "-") return;
    setDownloading(true);
    try {
      const blob = await downloadPDF(resolvedCaseId);
      const url = window.URL.createObjectURL(new Blob([blob], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `InsureMind_${resolvedCaseId}_Report.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-5">
      <SectionTitle title="Full Case Report" description="This view matches the generated SOAP/Agent report styling." />
      <Card className="space-y-5 overflow-hidden p-0 border-0 shadow-xl ring-1 ring-slate-200">
        <div className="relative border-b border-blue-200">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-700 via-indigo-700 to-sky-700" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.26),_transparent_40%)]" />
          <div className="absolute inset-0 backdrop-blur-md" />
          <div className="relative z-10 p-6 flex items-start justify-between">
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-blue-100/90 font-semibold mb-1">
                Professional Healthcare Report
              </p>
              <h2 className="text-2xl font-bold text-white tracking-tight">InsureMind AI Medical Center</h2>
              <p className="text-sm text-blue-100">123 Medical Center Blvd, Health District</p>
              <p className="text-sm text-blue-100">Phone: (555) 123-4567 | Email: records@insuremind.ai</p>
            </div>
            <div className="text-right bg-white/15 backdrop-blur-xl border border-white/30 rounded-xl px-4 py-3 shadow-lg">
              <p className="text-[11px] tracking-widest text-blue-100 font-semibold">PRIOR AUTHORIZATION REPORT</p>
              <p className="text-base font-semibold text-white">Case ID: {resolvedCaseId}</p>
              <p className="text-xs text-blue-100">Approval: {approvalPct} · {approvalRec}</p>
            </div>
          </div>
        </div>
        <div className="h-1.5 bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-500" />

        <div className="px-6 grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            ["Patient Name", patientName],
            ["Age", `${patientAge} years`],
            ["Gender", String(patientGender).toString().charAt(0).toUpperCase() + String(patientGender).toString().slice(1)],
            ["TPA / Insurer", tpa],
            ["Disease Description", disease],
            ["Medications", meds],
            ["ICD-10 Code", icdCode],
            ["ICD-10 Description", icdDesc],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-gray-200 p-3 bg-gray-50">
              <p className="text-xs text-gray-500">{label}</p>
              <p className="font-semibold text-gray-900 break-words">{value || "—"}</p>
            </div>
          ))}
        </div>

        <div className="px-6 space-y-3">
          {[
            ["S", "Subjective", soap.subjective],
            ["O", "Objective", soap.objective],
            ["A", "Assessment", soap.assessment],
            ["P", "Plan", soap.plan],
          ].map(([letter, title, value]) => (
            <div key={title} className="rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex w-6 h-6 rounded bg-blue-100 text-blue-700 items-center justify-center text-xs font-bold">
                  {letter}
                </span>
                <h3 className="font-semibold text-gray-900">{title}</h3>
              </div>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{value || "—"}</p>
            </div>
          ))}
        </div>

        <div className="px-6 flex gap-3 flex-wrap">
          <Button variant="secondary" onClick={() => navigate("/history")}>Back to History</Button>
          <Button onClick={handleDownload} loading={downloading} disabled={downloading || resolvedCaseId === "-"}>
            Download PDF
          </Button>
        </div>
        <p className="px-6 pb-6 text-xs text-gray-500">
          This report matches the styling of generated SOAP/Agent reports. PDFs are auto-saved to History.
        </p>
      </Card>
    </div>
  );
}
