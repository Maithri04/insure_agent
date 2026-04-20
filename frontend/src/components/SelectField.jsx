import React from 'react';

const SelectField = ({ label, value, onChange, options, name }) => {
  return (
    <div className="flex flex-col gap-1 w-full">
      {label && (
        <label className="text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <select
        name={name}
        value={value}
        onChange={onChange}
        className="p-3 border border-gray-200 rounded-lg text-black bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow w-full"
      >
        <option value="" disabled>Select an option</option>
        {options.map((opt, idx) => (
          <option key={idx} value={opt.value || opt}>
            {opt.label || opt}
          </option>
        ))}
      </select>
    </div>
  );
};

export default SelectField;
