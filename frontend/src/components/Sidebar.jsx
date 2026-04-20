import React from "react";
import { NavLink } from "react-router-dom";

const Sidebar = () => {
  const links = [
    { name: "Chatbot", path: "/chat" },
    { name: "SOAP Generation", path: "/soap" },
    { name: "Agent Run", path: "/agent" },
    { name: "Get Report", path: "/get" },
    { name: "History", path: "/history" },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 h-full flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-blue-600">InsureMind AI</h1>
        <p className="text-xs text-gray-500 mt-1">Hospital prior-authorization assistant</p>
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {links.map((link) => (
          <NavLink
            key={link.name}
            to={link.path}
            className={({ isActive }) =>
              `block p-3 rounded-lg transition-colors ${
                isActive ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700 hover:bg-gray-50"
              }`
            }
          >
            {link.name}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
