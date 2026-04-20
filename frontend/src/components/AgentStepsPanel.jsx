import React from 'react';

const AgentStepsPanel = ({ steps = [] }) => {
  return (
    <div className="bg-black text-white p-4 rounded-lg w-full">
      <h3 className="font-semibold text-lg mb-4">Agent Progress</h3>
      <div className="space-y-3">
        {steps.map((step, index) => (
          <div key={index} className="flex items-center gap-3">
            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-800 flex items-center justify-center text-xs font-medium border border-gray-700">
              {index + 1}
            </div>
            <div className="flex-1 text-sm font-medium">
              {step.name}
            </div>
            <div className="flex-shrink-0 text-sm">
              {step.status === 'done' ? (
                <span className="text-green-400">Done</span>
              ) : step.status === 'loading' ? (
                <span className="text-blue-400 animate-pulse">Running...</span>
              ) : (
                <span className="text-gray-500">Pending</span>
              )}
            </div>
          </div>
        ))}
        {steps.length === 0 && (
          <div className="text-gray-400 text-sm italic">No steps to display</div>
        )}
      </div>
    </div>
  );
};

export default AgentStepsPanel;
