const API_BASE_URL = 'http://localhost:8000';

export const agentVerify = async (clinicalJustification) => {
  const response = await fetch(`${API_BASE_URL}/agent-verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ clinical_justification: clinicalJustification }),
  });
  if (!response.ok) {
    throw new Error('Verify API failed');
  }
  return response.json();
};

export const agentRun = async (formData) => {
  const response = await fetch(`${API_BASE_URL}/agent-run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData),
  });
  if (!response.ok) {
    throw new Error('Run API failed');
  }
  return response.json();
};
