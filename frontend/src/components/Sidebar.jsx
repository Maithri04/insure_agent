import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { FileText, Bot, LogOut } from 'lucide-react';

const Sidebar = () => {
  const navigate = useNavigate();
  const doctorInfo = JSON.parse(localStorage.getItem('doctorInfo') || '{}');

  const handleLogout = () => {
    localStorage.removeItem('doctorInfo');
    navigate('/login');
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full shadow-sm">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-xl font-bold text-blue-600">InsureMind AI</h2>
        <div className="mt-4">
          <p className="text-sm font-medium text-gray-800">{doctorInfo.name || 'Doctor'}</p>
          <p className="text-xs text-gray-500">{doctorInfo.hospital || 'Hospital'}</p>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        <NavLink
          to="/form"
          className={({ isActive }) =>
            `flex items-center px-4 py-3 rounded-lg transition-colors ${
              isActive
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`
          }
        >
          <FileText className="w-5 h-5 mr-3" />
          Form Filling
        </NavLink>

        <NavLink
          to="/agent"
          className={({ isActive }) =>
            `flex items-center px-4 py-3 rounded-lg transition-colors ${
              isActive
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`
          }
        >
          <Bot className="w-5 h-5 mr-3" />
          Agent
        </NavLink>
      </nav>

      <div className="p-4 border-t border-gray-200">
        <button
          onClick={handleLogout}
          className="flex items-center w-full px-4 py-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5 mr-3" />
          Logout
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
