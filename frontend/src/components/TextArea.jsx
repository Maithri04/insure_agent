import React from 'react';

const TextArea = ({ label, value, onChange, placeholder, name, rows = 4 }) => {
  return (
    <div className="flex flex-col gap-1 w-full">
      {label && (
        <label className="text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <textarea
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        rows={rows}
        className="p-3 border border-gray-200 rounded-lg text-black bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow w-full resize-y"
      />
    </div>
  );
};

export default TextArea;
