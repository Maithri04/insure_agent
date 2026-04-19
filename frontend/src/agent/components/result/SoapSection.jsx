import React, { useState } from 'react';

export const SoapSection = ({ initialSoap }) => {
  const [soap, setSoap] = useState(initialSoap || {
    subjective: '',
    objective: '',
    assessment: '',
    plan: ''
  });
  const [isEditing, setIsEditing] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setSoap(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = () => {
    setIsEditing(false);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-8">
      <div className="flex justify-between items-center mb-6 border-b border-gray-200 pb-2">
        <h3 className="text-xl font-bold text-black">SOAP Note</h3>
        <div>
          {isEditing ? (
            <button 
              onClick={handleSave}
              className="bg-green-600 text-white px-4 py-1.5 rounded text-sm hover:bg-green-700 transition-colors"
            >
              Save Changes
            </button>
          ) : (
            <button 
              onClick={() => setIsEditing(true)}
              className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700 transition-colors"
            >
              Edit Note
            </button>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {['subjective', 'objective', 'assessment', 'plan'].map((section) => (
          <div key={section} className="bg-gray-50 p-4 rounded-lg border border-gray-100">
            <h4 className="text-md font-semibold text-blue-900 mb-2 capitalize border-b border-gray-200 pb-1 inline-block">
              {section}
            </h4>
            {isEditing ? (
              <textarea
                name={section}
                value={soap[section]}
                onChange={handleChange}
                rows="4"
                className="w-full mt-2 p-3 border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              />
            ) : (
              <p className="mt-2 text-gray-800 whitespace-pre-wrap">{soap[section] || 'Not provided'}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
