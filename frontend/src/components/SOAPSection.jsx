import React, { useState } from 'react';
import Button from './Button';
import TextArea from './TextArea';

const SOAPSection = ({ soapData = {}, onSave }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    subjective: soapData.subjective || '',
    objective: soapData.objective || '',
    assessment: soapData.assessment || '',
    plan: soapData.plan || '',
    icd10_code: soapData.icd10_code || '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = () => {
    setIsEditing(false);
    if (onSave) {
      onSave(formData);
    }
  };

  const renderContent = (label, content) => (
    <div className="mb-4">
      <h4 className="font-medium text-black mb-1">{label}</h4>
      <p className="text-gray-700 whitespace-pre-wrap bg-gray-50 p-3 rounded-lg border border-gray-100">
        {content || 'No details provided.'}
      </p>
    </div>
  );

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-black">SOAP Notes</h3>
        {!isEditing ? (
          <Button variant="secondary" onClick={() => setIsEditing(true)}>
            Edit Notes
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setIsEditing(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSave}>
              Save
            </Button>
          </div>
        )}
      </div>

      <div className="space-y-4">
        {isEditing ? (
          <>
            <TextArea
              label="Subjective"
              name="subjective"
              value={formData.subjective}
              onChange={handleChange}
            />
            <TextArea
              label="Objective"
              name="objective"
              value={formData.objective}
              onChange={handleChange}
            />
            <TextArea
              label="Assessment"
              name="assessment"
              value={formData.assessment}
              onChange={handleChange}
            />
            <TextArea
              label="Plan"
              name="plan"
              value={formData.plan}
              onChange={handleChange}
            />
            <TextArea
              label="ICD-10 Code"
              name="icd10_code"
              value={formData.icd10_code}
              onChange={handleChange}
              rows={2}
            />
          </>
        ) : (
          <>
            {renderContent('Subjective', formData.subjective)}
            {renderContent('Objective', formData.objective)}
            {renderContent('Assessment', formData.assessment)}
            {renderContent('Plan', formData.plan)}
            {renderContent('ICD-10 Code', formData.icd10_code)}
          </>
        )}
      </div>
    </div>
  );
};

export default SOAPSection;
