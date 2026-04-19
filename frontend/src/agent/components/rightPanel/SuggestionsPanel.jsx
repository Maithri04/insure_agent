import React from 'react';
import { useSuggestions } from '../../hooks/useSuggestions';

export const SuggestionsPanel = ({ clinicalJustification }) => {
  const { missingFields } = useSuggestions(clinicalJustification);
  
  const allFields = [
    { id: 'Duration', label: 'Duration' },
    { id: 'Prior treatment', label: 'Prior treatment' },
    { id: 'Severity', label: 'Severity' },
    { id: 'Investigations', label: 'Investigations' },
    { id: 'Specialist referral', label: 'Referral' }
  ];

  return (
    <div className="bg-white p-6 border border-gray-200 rounded-lg shadow-sm">
      <h3 className="text-lg font-semibold text-black mb-4 border-b border-gray-200 pb-2">Missing Evidence Checklist</h3>
      <ul className="space-y-3">
        {allFields.map((field) => {
          const isMissing = missingFields.includes(field.id);
          return (
            <li key={field.id} className="flex items-center space-x-3 text-sm">
              {isMissing ? (
                <span className="w-5 h-5 flex items-center justify-center rounded-full bg-red-100 text-red-600">✗</span>
              ) : (
                <span className="w-5 h-5 flex items-center justify-center rounded-full bg-green-100 text-green-600">✔</span>
              )}
              <span className={isMissing ? 'text-gray-500 line-through decoration-red-400' : 'text-black font-medium'}>
                {field.label}
              </span>
            </li>
          );
        })}
      </ul>
      <div className="mt-4 text-xs text-gray-500">
        Update dynamically as you type in the Clinical Justification section.
      </div>
    </div>
  );
};
