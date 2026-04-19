import React, { useEffect, useState } from 'react';

export const PopupHint = ({ missingCount, onDismiss }) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (missingCount > 0) {
      setVisible(true);
      const timer = setTimeout(() => {
        setVisible(false);
        onDismiss();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [missingCount, onDismiss]);

  if (!visible) return null;

  return (
    <div className="fixed bottom-4 right-4 bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded shadow-lg max-w-sm z-50">
      <div className="flex justify-between items-start">
        <div>
          <h4 className="text-sm font-bold text-yellow-800">Missing Information</h4>
          <p className="text-sm text-yellow-700 mt-1">
            There are {missingCount} missing clinical justification fields. Consider adding them to improve approval chances.
          </p>
        </div>
        <button 
          onClick={() => {
            setVisible(false);
            onDismiss();
          }}
          className="text-yellow-600 hover:text-yellow-800 ml-4"
        >
          &times;
        </button>
      </div>
    </div>
  );
};
