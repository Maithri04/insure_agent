import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Card from "../components/Card";
import SectionTitle from "../components/SectionTitle";
import { useAppState } from "../context/AppStateContext";
import { downloadPDF } from "../services/api";
import { useState } from "react";

export default function SoapReport() {
  const navigate = useNavigate();
  const { soapData, patientMeta } = useAppState();
  const [downloading, setDownloading] = useState(false);

  if (!soapData) {
    return (
      <Card>
        <p className="text-sm text-gray-600 mb-3">No SOAP data available. Generate one first.</p>
        <Button onClick={() => navigate("/soap")}>Go to SOAP Form</Button>
      </Card>
    );
  }

  const caseId = soapData.case_id || "-";

  const handleDownload = async () => {
    if (!soapData.case_id) return;
    setDownloading(true);
    try {
      const blob = await downloadPDF(soapData.case_id);
      const url = window.URL.createObjectURL(new Blob([blob], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `InsureMind_${soapData.case_id}_Report.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Generated SOAP Report"
        description="Professional hospital SOAP document generated and saved to database."
      />
      <Card className="space-y-5 overflow-hidden p-0 border-0 shadow-xl ring-1 ring-slate-200">
        <div className="relative border-b border-blue-200">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-700 via-indigo-700 to-sky-700" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.26),_transparent_40%)]" />
          <div className="absolute inset-0 backdrop-blur-md" />
          <div className="relative z-10 p-6 flex items-start justify-between">
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-blue-100/90 font-semibold mb-1">Professional Healthcare Report</p>
              <h2 className="text-2xl font-bold text-white tracking-tight">InsureMind AI Medical Center</h2>
              <p className="text-sm text-blue-100">123 Medical Center Blvd, Health District</p>
              <p className="text-sm text-blue-100">Phone: (555) 123-4567 | Email: records@insuremind.ai</p>
            </div>
            <div className="text-right bg-white/15 backdrop-blur-xl border border-white/30 rounded-xl px-4 py-3 shadow-lg">
              <p className="text-[11px] tracking-widest text-blue-100 font-semibold">PRIOR AUTHORIZATION REPORT</p>
              <p className="text-base font-semibold text-white">Case ID: {caseId}</p>
              <p className="text-xs text-blue-100">
                Generated: {new Date().toLocaleString()}
              </p>
            </div>
          </div>
        </div>
        <div className="h-1.5 bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-500" />
        <div className="px-6 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-lg border border-gray-200 p-3 bg-gray-50">
            <p className="text-xs text-gray-500">Patient Name</p>
            <p className="font-semibold text-gray-900">{patientMeta?.patient_name || "-"}</p>
          </div>
          <div className="rounded-lg border border-gray-200 p-3 bg-gray-50">
            <p className="text-xs text-gray-500">Age</p>
            <p className="font-semibold text-gray-900">{patientMeta?.patient_age || "-"} years</p>
          </div>
          <div className="rounded-lg border border-gray-200 p-3 bg-gray-50">
            <p className="text-xs text-gray-500">Gender</p>
            <p className="font-semibold text-gray-900 capitalize">{patientMeta?.patient_gender || "-"}</p>
          </div>
          <div className="rounded-lg border border-gray-200 p-3 bg-gray-50">
            <p className="text-xs text-gray-500">ICD-10 Code</p>
            <p className="font-semibold text-gray-900">{soapData.icd10_code || "-"}</p>
          </div>
        </div>

        <div className="px-6 space-y-3">
          {[
            ["S", "Subjective", soapData.subjective],
            ["O", "Objective", soapData.objective],
            ["A", "Assessment", soapData.assessment],
            ["P", "Plan", soapData.plan],
          ].map(([letter, title, value]) => (
            <div key={title} className="rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex w-6 h-6 rounded bg-blue-100 text-blue-700 items-center justify-center text-xs font-bold">
                  {letter}
                </span>
                <h3 className="font-semibold text-gray-900">{title}</h3>
              </div>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{value || "-"}</p>
            </div>
          ))}
        </div>

        <div className="px-6 flex gap-3 flex-wrap">
          <Button variant="secondary" onClick={() => navigate("/soap")}>Regenerate</Button>
          <Button onClick={handleDownload} loading={downloading} disabled={!soapData.case_id || downloading}>
            Download Professional PDF
          </Button>
          <Button onClick={() => navigate("/agent")}>Continue to Agent Run</Button>
        </div>
        <p className="px-6 pb-6 text-xs text-gray-500">
          This SOAP report is generated by AI and saved in the database with case ID `{caseId}`.
        </p>
      </Card>
    </div>
  );
}
