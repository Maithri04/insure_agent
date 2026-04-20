import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Card from "../components/Card";
import EmptyState from "../components/EmptyState";
import Loader from "../components/Loader";
import SectionTitle from "../components/SectionTitle";
import { useAppState } from "../context/AppStateContext";
import { downloadPDF, getCaseById, getHistory } from "../services/api";

export default function History() {
  const navigate = useNavigate();
  const { setAgentResult, setCaseId } = useAppState();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState("");

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await getHistory();
        const historyData = Array.isArray(response) ? response : response.items || response.cases || [];
        setRows(historyData);
      } catch (apiError) {
        setError(apiError.message);
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, []);

  const normalizedRows = useMemo(
    () =>
      rows.map((item) => ({
        case_id: item.case_id || item.caseId || "-",
        patient_name: item.patient_name || item.patientName || "-",
        date: item.date || item.created_at || item.createdAt || "",
      })),
    [rows],
  );

  const onView = async (caseId) => {
    try {
      const report = await getCaseById(caseId);
      setAgentResult(report);
      setCaseId(caseId);
      navigate("/report");
    } catch (apiError) {
      setError(apiError.message);
    }
  };

  const onDownload = async (caseId) => {
    setDownloadingId(caseId);
    try {
      const blob = await downloadPDF(caseId);
      const url = window.URL.createObjectURL(new Blob([blob], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `${caseId}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setDownloadingId("");
    }
  };

  return (
    <div className="space-y-5">
      <SectionTitle title="History" description="Previous cases with report view and PDF download." />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <Card className="p-0 overflow-hidden">
        {loading ? (
          <Loader text="Loading history..." />
        ) : !normalizedRows.length ? (
          <div className="p-6">
            <EmptyState message="No history records found." />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3">Case ID</th>
                <th className="text-left px-4 py-3">Patient Name</th>
                <th className="text-left px-4 py-3">Date</th>
                <th className="text-left px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {normalizedRows.map((row) => (
                <tr key={row.case_id} className="border-t">
                  <td className="px-4 py-3 font-mono">{row.case_id}</td>
                  <td className="px-4 py-3">{row.patient_name}</td>
                  <td className="px-4 py-3">{row.date ? new Date(row.date).toLocaleDateString() : "-"}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <Button variant="secondary" onClick={() => onView(row.case_id)}>View</Button>
                      <Button onClick={() => onDownload(row.case_id)} loading={downloadingId === row.case_id}>
                        Download
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
