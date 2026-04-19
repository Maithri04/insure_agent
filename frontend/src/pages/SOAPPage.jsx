import React, { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import EditableField from '../components/EditableField';
import DownloadButton from '../components/DownloadButton';
import { ArrowLeft } from 'lucide-react';

const SOAPPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const reportRef = useRef(null);
  const [doctorInfo, setDoctorInfo] = useState({ name: '', hospital: '', email: '', registration: '' });
  
  // Data passed from form page
  const initialSoapData = location.state?.soapData || {
    subjective: "Patient reports feeling unwell...",
    objective: "Patient presents with...",
    assessment: "Probable diagnosis...",
    plan: "Prescribed medication..."
  };
  
  const initialPatientData = location.state?.patientData || {
    patient_name: "Unknown",
    patient_age: "0",
    patient_gender: "Unknown"
  };

  const [soapData, setSoapData] = useState(initialSoapData);
  const [patientData] = useState(initialPatientData);

  useEffect(() => {
    // If no data was passed, we might want to redirect back to form
    // but for now, we'll use fallback data for demo purposes
    const storedInfo = localStorage.getItem('doctorInfo');
    if (storedInfo) {
      setDoctorInfo(JSON.parse(storedInfo));
    }
  }, []);

  const handleUpdateSection = (section, newValue) => {
    setSoapData(prev => ({
      ...prev,
      [section]: newValue
    }));
  };

  const currentDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric'
  });
  const caseId = `CAS-${Math.floor(100000 + Math.random() * 900000)}`;

  return (
    <div className="max-w-4xl mx-auto pb-12">
      <div className="flex justify-between items-center mb-6">
        <button 
          onClick={() => navigate('/form')}
          className="flex items-center text-gray-600 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Form
        </button>
        <DownloadButton targetRef={reportRef} filename={`${patientData.patient_name.replace(/\s+/g, '_')}_SOAP_Report.pdf`} />
      </div>

      <div 
        ref={reportRef} 
        className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden"
      >
        {/* Header Section */}
        <div className="bg-blue-600 text-white p-8">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-blue-400 pb-6 mb-6">
            <div>
              <h1 className="text-3xl font-bold mb-2">🏥 {doctorInfo.hospital || 'Hospital Name'}</h1>
              <p className="text-blue-100 text-sm">
                123 Medical Center Blvd, City, State | (555) 123-4567 | {doctorInfo.email || 'contact@hospital.com'}
              </p>
            </div>
            <div className="mt-4 md:mt-0 text-right">
              <h2 className="text-xl font-bold tracking-wider mb-1">PRE-AUTHORIZATION</h2>
              <h3 className="text-lg text-blue-100">MEDICAL REPORT</h3>
            </div>
          </div>

          <div className="flex justify-between text-sm font-medium text-blue-50">
            <div>
              <p>Doctor: {doctorInfo.name || 'N/A'} ({doctorInfo.registration || 'N/A'})</p>
            </div>
            <div className="text-right">
              <p>Date: {currentDate}</p>
              <p>Case ID: {caseId}</p>
            </div>
          </div>
        </div>

        {/* Patient Details Section */}
        <div className="p-8 bg-gray-50 border-b border-gray-200">
          <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4">Patient Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-gray-500">Name</p>
              <p className="font-semibold text-gray-900">{patientData.patient_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Age</p>
              <p className="font-semibold text-gray-900">{patientData.patient_age} Years</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Gender</p>
              <p className="font-semibold text-gray-900 capitalize">{patientData.patient_gender}</p>
            </div>
          </div>
        </div>

        {/* SOAP Report Section */}
        <div className="p-8 space-y-8">
          <div className="bg-white border border-gray-100 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
            <h3 className="text-lg font-bold text-blue-800 mb-3 border-b border-gray-100 pb-2">S - Subjective</h3>
            <EditableField 
              value={soapData.subjective} 
              onSave={(val) => handleUpdateSection('subjective', val)} 
              multiline 
              className="text-gray-700 leading-relaxed min-h-[60px]"
            />
          </div>

          <div className="bg-white border border-gray-100 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
            <h3 className="text-lg font-bold text-blue-800 mb-3 border-b border-gray-100 pb-2">O - Objective</h3>
            <EditableField 
              value={soapData.objective} 
              onSave={(val) => handleUpdateSection('objective', val)} 
              multiline 
              className="text-gray-700 leading-relaxed min-h-[60px]"
            />
          </div>

          <div className="bg-white border border-gray-100 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
            <h3 className="text-lg font-bold text-blue-800 mb-3 border-b border-gray-100 pb-2">A - Assessment</h3>
            <EditableField 
              value={soapData.assessment} 
              onSave={(val) => handleUpdateSection('assessment', val)} 
              multiline 
              className="text-gray-700 leading-relaxed min-h-[60px]"
            />
          </div>

          <div className="bg-white border border-gray-100 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
            <h3 className="text-lg font-bold text-blue-800 mb-3 border-b border-gray-100 pb-2">P - Plan</h3>
            <EditableField 
              value={soapData.plan} 
              onSave={(val) => handleUpdateSection('plan', val)} 
              multiline 
              className="text-gray-700 leading-relaxed min-h-[60px]"
            />
          </div>
        </div>
        
        {/* Footer */}
        <div className="p-8 pt-0 text-center">
          <div className="border-t border-gray-200 pt-6 mt-4">
            <p className="text-xs text-gray-400">
              This document is electronically generated and serves as a pre-authorization medical report.
              <br />
              Generated by InsureMind AI
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SOAPPage;
