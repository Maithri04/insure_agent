import { useState, useEffect } from 'react';
import { agentVerify } from '../services/agentApi';

export const useSuggestions = (clinicalJustification) => {
  const [missingFields, setMissingFields] = useState([
    'Duration', 'Prior treatment', 'Severity', 'Investigations', 'Specialist referral'
  ]);

  useEffect(() => {
    const checkFields = async () => {
      try {
        const response = await agentVerify(clinicalJustification);
        setMissingFields(response.missing_fields);
      } catch (err) {
        console.error('Failed to verify fields', err);
      }
    };
    
    // Add a simple debounce
    const timeout = setTimeout(() => {
      checkFields();
    }, 500);
    
    return () => clearTimeout(timeout);
  }, [clinicalJustification]);

  return { missingFields };
};
