import React from 'react';

const EmptyState = ({ message = "No data found", icon }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 bg-gray-50 rounded-lg border border-dashed border-gray-300 w-full">
      {icon ? (
        <div className="text-gray-400 mb-4">
          {icon}
        </div>
      ) : (
        <svg 
          className="w-16 h-16 text-gray-300 mb-4" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={1.5} 
            d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
          />
        </svg>
      )}
      <p className="text-gray-500 font-medium text-center">{message}</p>
    </div>
  );
};

export default EmptyState;
