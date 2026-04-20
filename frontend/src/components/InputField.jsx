import React from 'react';

const InputField = ({ label, value, onChange, placeholder, type = 'text', name }) => {
  return (
    <div className="flex flex-col gap-1 w-full">
      {label && (
        <label className="text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="p-3 border border-gray-200 rounded-lg text-black bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow w-full"
      />
    </div>
  );
};

export default InputField;
