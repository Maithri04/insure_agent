import React from 'react';
import { getProgressColor, getScoreColor } from '../../utils/colorUtils';
import { formatPercentage as formatPerc } from '../../utils/formatUtils';

export const ApprovalScoreCard = ({ probability, label }) => {
  const percent = probability * 100;
  const colorClass = getScoreColor(percent);
  const barColor = getProgressColor(percent);

  return (
    <div className={`p-8 rounded-xl border shadow-sm flex flex-col items-center justify-center ${colorClass} mb-8`}>
      <h2 className="text-sm font-bold uppercase tracking-widest opacity-80 mb-2">Approval Probability</h2>
      <div className="text-6xl font-black mb-2">{formatPerc(probability)}</div>
      <div className="text-xl font-medium mb-6">{label}</div>
      
      <div className="w-full max-w-md bg-white/50 rounded-full h-4 overflow-hidden shadow-inner">
        <div 
          className={`h-full ${barColor} transition-all duration-1000 ease-out`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};
