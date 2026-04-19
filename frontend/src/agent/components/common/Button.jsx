import React from 'react';

export const Button = ({ children, onClick, type = 'button', variant = 'primary', disabled = false, className = '' }) => {
  const baseStyles = 'px-6 py-2 rounded font-medium transition-colors focus:outline-none focus:ring-2';
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-500',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
  };

  const style = `${baseStyles} ${variants[variant]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`;

  return (
    <button type={type} onClick={onClick} disabled={disabled} className={style}>
      {children}
    </button>
  );
};
