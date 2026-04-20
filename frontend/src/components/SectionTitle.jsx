import React from 'react';

const SectionTitle = ({ title, description, className = '' }) => {
  return (
    <div className={`mb-4 ${className}`}>
      <h2 className="text-lg font-semibold text-black">{title}</h2>
      {description && <p className="text-sm text-gray-500 mt-1">{description}</p>}
    </div>
  );
};

export default SectionTitle;
