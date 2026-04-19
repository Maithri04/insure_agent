import React from 'react';

export const ExplanationPanel = ({ explanation, score }) => {
  if (score >= 85) return null; // Only show if score is not high

  return (
    <div className="bg-gray-50 p-6 rounded-lg shadow-sm border border-gray-200 mt-6">
      <h3 className="text-lg font-semibold text-black mb-3 flex items-center">
        <span className="mr-2 text-xl">💡</span> AI Explanation
      </h3>
      <p className="text-gray-700 leading-relaxed text-sm">
        {explanation || "The probability score is low due to missing evidence or conflicting codes. Please review the Risk Flags and ensure the SOAP note explicitly contains detailed symptom duration, prior treatment history, and relevant investigations."}
      </p>
    </div>
  );
};
