import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PatientForm } from '../components/form/PatientForm';
import { ClinicalBuilder } from '../components/form/ClinicalBuilder';
import { TPASelector } from '../components/form/TPASelector';
import { AgentStepsPanel } from '../components/rightPanel/AgentStepsPanel';
import { SuggestionsPanel } from '../components/rightPanel/SuggestionsPanel';
import { PopupHint } from '../components/rightPanel/PopupHint';
import { RiskFlagsPanel } from '../components/result/RiskFlagsPanel';
import { Button } from '../components/common/Button';
import { useAgent } from '../hooks/useAgent';
import { useSuggestions } from '../hooks/useSuggestions';

const AgentFormPage = () => {
  const navigate = useNavigate();
  const { executeAgent, loading } = useAgent();
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [isVerifying, setIsVerifying] = useState(false);
  const [hintsDismissedCount, setHintsDismissedCount] = useState(0);
  const [agentResult, setAgentResult] = useState(null);

  const [formData, setFormData] = useState({
    patient_name: '',
    patient_age: '',
    patient_gender: 'male',
    disease_description: '',
    medications: '',
    tpa_id: '',
    procedure: '',
    clinical_justification: {
      duration: '',
      prior_treatment: '',
      severity: '',
      investigations: '',
      specialist_referral: ''
    }
  });

  const { missingFields } = useSuggestions(formData.clinical_justification);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleJustificationChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      clinical_justification: {
        ...prev.clinical_justification,
        [field]: value
      }
    }));
  };

  const handleVerify = async () => {
    if (!formData.tpa_id) {
      alert("Please select a TPA first.");
      return;
    }
    
    setIsVerifying(true);
    setAgentResult(null);
    setCurrentStepIndex(0);

    try {
      // Simulate steps progressing over ~10 seconds (1700ms per step for 6 steps)
      const stepInterval = setInterval(() => {
        setCurrentStepIndex(prev => {
          if (prev >= 5) {
            clearInterval(stepInterval);
            return prev;
          }
          return prev + 1;
        });
      }, 1700);

      // Real API Call & wait at least 10 seconds
      const [result] = await Promise.all([
        executeAgent({
          ...formData,
          patient_age: parseInt(formData.patient_age, 10) || 0
        }),
        new Promise(resolve => setTimeout(resolve, 10000))
      ]);
      
      clearInterval(stepInterval);
      setCurrentStepIndex(6); // All done
      setIsVerifying(false);
      setAgentResult(result);

    } catch (err) {
      console.error(err);
      alert('Agent run failed. Check console.');
      setIsVerifying(false);
      setCurrentStepIndex(-1);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!agentResult) return;
    navigate('/agent-result', { state: { result: agentResult, formData } });
  };

  const showPopup = isVerifying && missingFields.length > 0 && hintsDismissedCount < 2;

  return (
    <div className="max-w-7xl mx-auto flex flex-col md:flex-row gap-8">
      {/* LEFT SIDE - Smart Form */}
      <div className="w-full md:w-2/3">
        <h1 className="text-3xl font-bold text-gray-900 mb-6 border-b pb-2">Smart Agent Form</h1>
        <form onSubmit={handleSubmit}>
          <PatientForm formData={formData} handleChange={handleChange} />
          <TPASelector formData={formData} handleChange={handleChange} />
          <ClinicalBuilder 
            formData={formData} 
            handleChange={handleChange} 
            handleJustificationChange={handleJustificationChange} 
          />
          <div className="flex justify-end gap-4 mb-12">
            <Button 
              type="button" 
              onClick={handleVerify} 
              disabled={isVerifying || loading} 
              variant="secondary" 
              className="text-lg px-8 py-3 shadow-md bg-blue-100 hover:bg-blue-200 text-blue-800"
            >
              {isVerifying ? 'Verifying...' : 'Verify'}
            </Button>
            <Button 
              type="submit" 
              disabled={!agentResult || isVerifying} 
              variant="primary" 
              className="text-lg px-12 py-3 shadow-md bg-green-600 hover:bg-green-700 disabled:bg-gray-400"
            >
              Submit
            </Button>
          </div>
        </form>
      </div>

      {/* RIGHT SIDE - Live Panels */}
      <div className="w-full md:w-1/3 space-y-6">
        <div className="sticky top-6">
          {isVerifying || agentResult ? (
            <AgentStepsPanel currentStepIndex={currentStepIndex} />
          ) : (
            <div className="bg-black p-6 rounded-lg shadow-lg mb-6 flex flex-col items-center justify-center text-center text-gray-400 min-h-[200px]">
              <span className="text-4xl mb-3">🤖</span>
              <p>Click "Verify" to see the agent's thought process live.</p>
            </div>
          )}
          
          <SuggestionsPanel clinicalJustification={formData.clinical_justification} />
          
          {agentResult && (
            <div className="mt-6">
              <RiskFlagsPanel flags={agentResult.risk_flags} />
            </div>
          )}
        </div>
      </div>

      {showPopup && (
        <PopupHint 
          missingCount={missingFields.length} 
          onDismiss={() => setHintsDismissedCount(prev => prev + 1)} 
        />
      )}
    </div>
  );
};

export default AgentFormPage;
