import { useState } from 'react';
import { agentRun } from '../services/agentApi';

export const useAgent = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const executeAgent = async (formData) => {
    setLoading(true);
    setError(null);
    try {
      const data = await agentRun(formData);
      setResult(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { executeAgent, loading, error, result };
};
