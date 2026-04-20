import axios from "axios";

const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
});

function parseError(err) {
  const status = err?.response?.status;
  const data = err?.response?.data;

  // FastAPI 422 validation errors: { detail: [{ loc: [...], msg: "..." }, ...] }
  if (status === 422 && data?.detail && Array.isArray(data.detail)) {
    const lines = data.detail.map((item) => {
      const loc = Array.isArray(item?.loc) ? item.loc.filter(Boolean).join(".") : "field";
      return `${loc}: ${item?.msg || "Validation error"}`;
    });
    return new Error(lines.join(", "));
  }

  const detail = data?.detail || data?.message;
  if (typeof detail === "string" && detail.trim()) return new Error(detail);
  return new Error(err?.message || "Request failed");
}

export async function generateSOAP(payload) {
  try {
    const { data } = await client.post("/soap", payload);
    return data;
  } catch (err) {
    throw parseError(err);
  }
}

export async function runAgent(payload) {
  try {
    const { data } = await client.post("/agent-run", payload);
    return data;
  } catch (err) {
    throw parseError(err);
  }
}

export async function getCaseById(caseId) {
  try {
    const { data } = await client.get(`/case/${encodeURIComponent(caseId)}`);
    return data;
  } catch (err) {
    throw parseError(err);
  }
}

export async function getHistory() {
  try {
    const { data } = await client.get("/history");
    return data;
  } catch (err) {
    throw parseError(err);
  }
}

export async function downloadPDF(caseId) {
  try {
    const res = await client.get(`/history/${encodeURIComponent(caseId)}`, {
      responseType: "blob",
    });
    return res.data;
  } catch (err) {
    throw parseError(err);
  }
}

export async function chat(payload) {
  try {
    const { data } = await client.post("/chat", payload);
    return data;
  } catch (err) {
    throw parseError(err);
  }
}
