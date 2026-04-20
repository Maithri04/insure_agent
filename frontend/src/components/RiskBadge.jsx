import React from 'react';

const RiskBadge = ({ level }) => {
  const normalizedLevel = level?.toLowerCase();
  
  let bgClass = "bg-gray-100 text-gray-800";
  let borderClass = "border-gray-200";

  if (normalizedLevel === 'high') {
    bgClass = "bg-red-50 text-red-700";
    borderClass = "border-red-200";
  } else if (normalizedLevel === 'medium') {
    bgClass = "bg-yellow-50 text-yellow-700";
    borderClass = "border-yellow-200";
  } else if (normalizedLevel === 'low') {
    bgClass = "bg-green-50 text-green-700";
    borderClass = "border-green-200";
  }

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${bgClass} ${borderClass}`}>
      {level || 'Unknown'} Risk
    </span>
  );
};

export default RiskBadge;
