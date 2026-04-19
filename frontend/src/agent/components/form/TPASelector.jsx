import React from 'react';
import { Dropdown } from '../common/Dropdown';

export const TPASelector = ({ formData, handleChange }) => {
  const tpaOptions = [
    { value: 'mediassist', label: 'Medi Assist' },
    { value: 'fhpl', label: 'Family Health Plan (FHPL)' },
    { value: 'paramount', label: 'Paramount Health' },
    { value: 'vidal', label: 'Vidal Health' },
    { value: 'healthindia', label: 'HealthIndia' },
    { value: 'demo_tpa', label: 'Demo TPA' },
  ];

  return (
    <div className="bg-white p-6 border border-gray-200 shadow-sm rounded-lg mb-6">
      <h2 className="text-lg font-semibold text-black border-b border-gray-200 pb-2 mb-4">Insurance Details</h2>
      <Dropdown
        label="TPA"
        name="tpa_id"
        value={formData.tpa_id}
        onChange={handleChange}
        options={tpaOptions}
        required
      />
    </div>
  );
};
