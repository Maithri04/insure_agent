import React from 'react';
import { getRiskFlagColor } from '../../utils/colorUtils';

export const RiskFlagsPanel = ({ flags }) => {
  if (!flags || flags.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-6">
        <h3 className="text-lg font-semibold text-black mb-2 border-b border-gray-200 pb-2">Risk Flags</h3>
        <p className="text-green-600 font-medium">No risk flags detected. Clean case.</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-6">
      <h3 className="text-lg font-semibold text-black mb-4 border-b border-gray-200 pb-2">Risk Flags Detected</h3>
      <div className="space-y-3">
        {flags.map((flag, index) => {
          const level = flag.level || flag.severity || 'low';
          const category = flag.category || flag.field || 'General';
          const description = flag.description || flag.reason || '';

          const colorClass = getRiskFlagColor(level);
          return (
            <div key={index} className={`p-4 rounded-lg flex items-start ${colorClass}`}>
              <div className="mr-3 mt-0.5">
                <span className="w-6 h-6 flex items-center justify-center rounded-full bg-white bg-opacity-50 text-sm font-bold">
                  !
                </span>
              </div>
              <div>
                <h4 className="font-bold text-sm uppercase">{category} - {level} RISK</h4>
                <p className="mt-1 text-sm opacity-90">{description}</p>
                {flag.suggestion && (
                  <p className="mt-1 text-xs opacity-80 italic">Tip: {flag.suggestion}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
