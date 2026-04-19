// Base URL for the backend API
// Adjust this to match your backend port/host
const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Calls the backend API to generate a SOAP report based on patient data
 * @param {Object} patientData - The data collected from the form
 * @returns {Promise<Object>} - The generated SOAP report
 */
export const generateSOAP = async (patientData) => {
  try {
    // In a real application, you would connect to the backend here:
    /*
    const response = await fetch(`${API_BASE_URL}/generate-soap`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(patientData),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
    */

    // For now, we simulate the backend delay and return mock data
    // This allows the frontend to work even if backend is not running
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          subjective: `Patient ${patientData.patient_name}, a ${patientData.patient_age}-year-old ${patientData.patient_gender}, presented with the following notes:\n${patientData.raw_notes}`,
          objective: `Vitals are stable. Patient appears in mild distress. Previous medications include:\n${patientData.medications}`,
          assessment: `Based on the subjective and objective findings, the primary assessment indicates a condition requiring further evaluation and potential pre-authorization for treatment.`,
          plan: `1. Continue current medications.\n2. Schedule follow-up in 2 weeks.\n3. Request pre-authorization for recommended procedure.`
        });
      }, 1500);
    });
  } catch (error) {
    console.error('Error in API call:', error);
    throw error;
  }
};
