import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Card from "../components/Card";
import RiskBadge from "../components/RiskBadge";
import SOAPSection from "../components/SOAPSection";
import SectionTitle from "../components/SectionTitle";
import { useAppState } from "../context/AppStateContext";
import { downloadPDF } from "../services/api";

const getScoreColor = (score) => {
  if (score < 50) return "bg-red-500";
  if (score <= 85) return "bg-yellow-500";
  return "bg-green-500";
};

export default function AgentResult() {
  const navigate = useNavigate();
  const { agentResult, caseId } = useAppState();
  const [savingSoap, setSavingSoap] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [soapState, setSoapState] = useState(null);
  const score = Math.round((agentResult?.approval_probability || agentResult?.approval_score || 0) * 100);

  if (!agentResult) {
    return (
      <Card>
        <p className="text-sm text-gray-700 mb-3">No agent result available yet.</p>
        <Button onClick={() => navigate("/agent")}>Go to Agent Run</Button>
      </Card>
    );
  }

  const resolvedCaseId = caseId || agentResult?.case_id || agentResult?.caseId || "";
  const baseSoap = agentResult?.soap_note || agentResult?.soap || agentResult?.soap_json || {};
  const displayedSoap = soapState || baseSoap;
  const icd10 = displayedSoap?.icd10_code || agentResult?.icd?.code || agentResult?.icd10_code || agentResult?.icd_code || "";

  const onSoapSave = (updated) => {
    setSavingSoap(true);
    setSoapState((prev) => ({ ...(prev || baseSoap || {}), ...updated }));
    setTimeout(() => setSavingSoap(false), 300);
  };

  const onDownload = async () => {
    if (!caseId) return;
    setDownloading(true);
    try {
      const blob = await downloadPDF(caseId);
      const url = window.URL.createObjectURL(new Blob([blob], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `${caseId}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-5">
      <SectionTitle
        title="Agent Result"
        description={`Case ID: ${resolvedCaseId || "Not assigned"} | Approval prediction and explanation`}
      />
      <Card>
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm text-gray-500 mb-1">Approval Score</p>
            <p className="text-5xl font-bold">{score}%</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => navigate("/agent")}>Back</Button>
            <Button onClick={onDownload} loading={downloading} disabled={!resolvedCaseId || downloading}>Download PDF</Button>
          </div>
        </div>
        <div className="mt-4 h-3 w-full bg-gray-100 rounded-full overflow-hidden">
          <div className={`h-full ${getScoreColor(score)} transition-all`} style={{ width: `${score}%` }} />
        </div>
      </Card>

      <SOAPSection
        key={resolvedCaseId || "agent-result-soap"}
        soapData={{
          subjective: displayedSoap?.subjective,
          objective: displayedSoap?.objective,
          assessment: displayedSoap?.assessment,
          plan: displayedSoap?.plan,
          icd10_code: icd10,
        }}
        onSave={onSoapSave}
      />
      {savingSoap ? <p className="text-xs text-blue-600">SOAP updated in local state.</p> : null}

      <Card>
        <SectionTitle title="Risk Flags" />
        <div className="flex flex-wrap gap-2">
          {(agentResult?.risk_flags || []).map((flag, index) => (
            <RiskBadge key={`${flag?.level || flag?.severity}-${index}`} level={flag.level || flag.severity || "Low"} />
          ))}
          {!(agentResult?.risk_flags || []).length ? <p className="text-sm text-gray-500">No risk flags.</p> : null}
        </div>
      </Card>

      <Card>
        <SectionTitle title="AI Explanation" />
        <p className="text-sm text-gray-700 whitespace-pre-wrap">
          {agentResult?.explanation || agentResult?.analysis || "No explanation provided by backend."}
        </p>
        {(agentResult?.suggestions || []).length ? (
          <div className="mt-3">
            <p className="text-sm font-semibold mb-1">Suggestions</p>
            <ul className="text-sm text-gray-700 list-disc pl-5">
              {(agentResult?.suggestions || []).map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
