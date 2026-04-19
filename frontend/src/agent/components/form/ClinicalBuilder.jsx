import React from 'react';
import { TextArea } from '../common/TextArea';
import { InputField } from '../common/InputField';

export const ClinicalBuilder = ({ formData, handleChange, handleJustificationChange }) => {
  return (
    <div className="bg-white p-6 border border-gray-200 shadow-sm rounded-lg mb-6">
      <h2 className="text-lg font-semibold text-black border-b border-gray-200 pb-2 mb-4">Clinical Details</h2>
      
      <TextArea
        label="Disease Description"
        name="disease_description"
        value={formData.disease_description}
        onChange={handleChange}
        required
      />
      
      <TextArea
        label="Medications"
        name="medications"
        value={formData.medications}
        onChange={handleChange}
        required
      />

      <InputField
        label="Procedure"
        name="procedure"
        value={formData.procedure}
        onChange={handleChange}
      />

      <div className="mt-6 border-t border-gray-200 pt-4">
        <h3 className="text-md font-semibold text-black mb-4">Clinical Justification</h3>
        <p className="text-xs text-gray-500 mb-4">Provide detailed justification for better approval prediction.</p>
        
        <div className="space-y-4">
          <InputField
            label="Duration of symptoms"
            name="duration"
            value={formData.clinical_justification.duration}
            onChange={(e) => handleJustificationChange('duration', e.target.value)}
          />
          <InputField
            label="Prior treatment"
            name="prior_treatment"
            value={formData.clinical_justification.prior_treatment}
            onChange={(e) => handleJustificationChange('prior_treatment', e.target.value)}
          />
          <InputField
            label="Severity"
            name="severity"
            value={formData.clinical_justification.severity}
            onChange={(e) => handleJustificationChange('severity', e.target.value)}
          />
          <InputField
            label="Investigations"
            name="investigations"
            value={formData.clinical_justification.investigations}
            onChange={(e) => handleJustificationChange('investigations', e.target.value)}
          />
          <InputField
            label="Specialist referral"
            name="specialist_referral"
            value={formData.clinical_justification.specialist_referral}
            onChange={(e) => handleJustificationChange('specialist_referral', e.target.value)}
          />
        </div>
      </div>
    </div>
  );
};
