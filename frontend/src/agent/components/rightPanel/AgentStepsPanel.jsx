import React from 'react';

export const AgentStepsPanel = ({ currentStepIndex }) => {
  const steps = [
    { id: 1, name: 'Understanding patient (LLM)' },
    { id: 2, name: 'Validating data (rules)' },
    { id: 3, name: 'Fixing issues (logic)' },
    { id: 4, name: 'Improving justification (LLM loop)' },
    { id: 5, name: 'Analyzing risk (rules)' },
    { id: 6, name: 'Predicting approval (ML)' }
  ];

  return (
    <div className="bg-black p-6 rounded-lg shadow-lg mb-6">
      <h3 className="text-white font-semibold mb-4 text-lg border-b border-gray-700 pb-2">Agent Processing Steps</h3>
      <div className="space-y-3">
        {steps.map((step, index) => {
          let statusColor = 'text-gray-500';
          let statusText = 'Pending';
          
          if (currentStepIndex > index) {
            statusColor = 'text-green-400';
            statusText = 'Completed';
          } else if (currentStepIndex === index) {
            statusColor = 'text-blue-400 animate-pulse';
            statusText = 'In Progress...';
          }

          return (
            <div key={step.id} className="flex justify-between items-center text-sm">
              <div className="flex items-center space-x-3">
                <span className={`w-6 h-6 flex items-center justify-center rounded-full text-xs font-bold ${
                  currentStepIndex > index ? 'bg-green-500 text-black' : 
                  currentStepIndex === index ? 'bg-blue-500 text-white' : 'bg-gray-800 text-gray-500'
                }`}>
                  {step.id}
                </span>
                <span className={currentStepIndex >= index ? 'text-white' : 'text-gray-500'}>
                  {step.name}
                </span>
              </div>
              <span className={statusColor}>{statusText}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
