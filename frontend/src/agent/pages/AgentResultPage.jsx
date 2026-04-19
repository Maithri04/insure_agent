import React, { useRef } from 'react';
import { useLocation, useNavigate, Navigate } from 'react-router-dom';
import { ApprovalScoreCard } from '../components/result/ApprovalScoreCard';
import { SoapSection } from '../components/result/SoapSection';
import { ExplanationPanel } from '../components/result/ExplanationPanel';
import { DownloadButton } from '../components/result/DownloadButton';

const AgentResultPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const reportRef = useRef(null);

  const { result, formData } = location.state || {};

  if (!result) {
    return <Navigate to="/agent" replace />;
  }

  // Fallback patient data if formData is missing somehow
  const patientData = formData || { patient_name: 'Patient', patient_age: 'N/A', patient_gender: 'N/A' };
  
  // Fake percentage for UI if testing without real ML score
  const probabilityScore = result.approval_probability || 0;
  const probabilityPercent = Math.round(probabilityScore * 100);

  return (
    <div className="max-w-6xl mx-auto pb-12">
      <div className="flex justify-between items-center mb-6">
        <button 
          onClick={() => navigate('/agent')}
          className="text-blue-600 hover:text-blue-800 transition-colors font-medium text-sm flex items-center"
        >
          &larr; Back to Form
        </button>
        <DownloadButton targetRef={reportRef} filename={`Agent_Report_${patientData.patient_name.replace(/\s+/g, '_')}.pdf`} />
      </div>

      <div ref={reportRef} className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        
        {/* TOP SECTION */}
        <div className="bg-white border-b border-gray-200 p-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
            
            <div className="col-span-2">
              <h1 className="text-3xl font-bold mb-2">🏥 {localStorage.getItem('doctorInfo') ? JSON.parse(localStorage.getItem('doctorInfo')).hospital : 'City Hospital'}</h1>
              <p className="text-gray-500 text-sm mb-6">
                123 Medical Center Blvd | (555) 123-4567 | contact@hospital.com
              </p>
              
              <div className="flex justify-between items-end border-t border-gray-200 pt-4 mt-4">
                <div>
                  <h2 className="text-lg font-bold tracking-widest text-black">PRE-AUTHORIZATION MEDICAL REPORT</h2>
                  <p className="text-sm font-medium text-gray-500 mt-1">Patient: <span className="text-black">{patientData.patient_name}</span> | {patientData.patient_age} yrs | {patientData.patient_gender}</p>
                </div>
                <div className="text-right text-sm text-gray-500 font-medium">
                  <p>Date: {new Date().toLocaleDateString()}</p>
                  <p>Case ID: {result.run_id ? result.run_id.split('-')[0].toUpperCase() : 'CAS-12345'}</p>
                </div>
              </div>
            </div>

            <div className="col-span-1">
              <ApprovalScoreCard probability={probabilityScore} label={result.approval_label || 'Calculated'} />
            </div>

          </div>
        </div>

        <div className="p-8 bg-gray-50 grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <div className="col-span-2 space-y-6">
            <SoapSection initialSoap={{
              subjective: result.soap?.subjective || formData?.disease_description,
              objective: result.soap?.objective || 'Vitals stable',
              assessment: result.soap?.assessment || result.icd10_description,
              plan: result.soap?.plan || result.final_justification
            }} />
          </div>

          <div className="col-span-1 space-y-6">
            <ExplanationPanel explanation={result.agent_summary} score={probabilityPercent} />
          </div>

        </div>
      </div>
    </div>
  );
};

export default AgentResultPage;
