import React, { useState, useEffect, useRef } from 'react';
import { Edit2, Check, X } from 'lucide-react';

const EditableField = ({ value, onSave, multiline = false, className = '' }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [tempValue, setTempValue] = useState(value);
  const inputRef = useRef(null);

  useEffect(() => {
    setTempValue(value);
  }, [value]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleSave = () => {
    onSave(tempValue);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setTempValue(value);
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="relative group flex items-start w-full">
        {multiline ? (
          <textarea
            ref={inputRef}
            value={tempValue}
            onChange={(e) => setTempValue(e.target.value)}
            className={`w-full p-2 border border-blue-400 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y min-h-[100px] ${className}`}
          />
        ) : (
          <input
            ref={inputRef}
            type="text"
            value={tempValue}
            onChange={(e) => setTempValue(e.target.value)}
            className={`w-full p-1 border border-blue-400 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`}
          />
        )}
        <div className="flex ml-2 space-x-1">
          <button onClick={handleSave} className="p-1 text-green-600 hover:bg-green-100 rounded" title="Save">
            <Check size={18} />
          </button>
          <button onClick={handleCancel} className="p-1 text-red-600 hover:bg-red-100 rounded" title="Cancel">
            <X size={18} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative group w-full">
      <div className={`whitespace-pre-wrap ${className}`}>
        {value || <span className="text-gray-400 italic">Empty</span>}
      </div>
      <button 
        onClick={() => setIsEditing(true)}
        className="absolute top-0 right-0 p-1 text-gray-400 bg-white border border-gray-200 rounded shadow-sm opacity-0 group-hover:opacity-100 transition-opacity hover:text-blue-600 hover:border-blue-300"
        title="Edit"
      >
        <Edit2 size={16} />
      </button>
    </div>
  );
};

export default EditableField;
