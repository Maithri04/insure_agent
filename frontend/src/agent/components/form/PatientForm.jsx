import React from 'react';
import { InputField } from '../common/InputField';
import { Dropdown } from '../common/Dropdown';

export const PatientForm = ({ formData, handleChange }) => {
  const genderOptions = [
    { value: 'male', label: 'Male' },
    { value: 'female', label: 'Female' },
    { value: 'other', label: 'Other' },
  ];

  return (
    <div className="bg-white p-6 border border-gray-200 shadow-sm rounded-lg mb-6">
      <h2 className="text-lg font-semibold text-black border-b border-gray-200 pb-2 mb-4">Patient Demographics</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <InputField
          label="Patient Name"
          name="patient_name"
          value={formData.patient_name}
          onChange={handleChange}
          required
        />
        <InputField
          label="Age"
          name="patient_age"
          type="number"
          value={formData.patient_age}
          onChange={handleChange}
          required
        />
        <Dropdown
          label="Gender"
          name="patient_gender"
          value={formData.patient_gender}
          onChange={handleChange}
          options={genderOptions}
          required
        />
      </div>
    </div>
  );
};
