import React from 'react';

const MissingEvidencePanel = ({ evidence = {} }) => {
  const items = [
    { key: 'duration', label: 'Duration' },
    { key: 'treatment', label: 'Treatment' },
    { key: 'severity', label: 'Severity' },
    { key: 'investigations', label: 'Investigations' },
    { key: 'referral', label: 'Referral' },
  ];

  return (
    <div className="bg-white p-4 border border-gray-200 rounded-lg w-full">
      <h3 className="font-semibold text-lg mb-3 text-black">Evidence Checklist</h3>
      <div className="space-y-2">
        {items.map((item) => {
          const isChecked = evidence[item.key];
          return (
            <div key={item.key} className="flex items-center gap-2">
              <div
                className={`w-5 h-5 rounded flex items-center justify-center border ${
                  isChecked ? 'bg-blue-600 border-blue-600' : 'bg-gray-100 border-gray-300'
                }`}
              >
                {isChecked && (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <span className={`text-sm ${isChecked ? 'text-black font-medium' : 'text-gray-500'}`}>
                {item.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MissingEvidencePanel;
