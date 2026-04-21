import React from "react";
import { NavLink } from "react-router-dom";
import { useAppState } from "../context/AppStateContext";
import FlashCard from "./FlashCard";

const Sidebar = () => {
  const { doctor } = useAppState();
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
        <div className="mt-3">
          <FlashCard />
        </div>
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
      <div className="border-t border-gray-200 p-4">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-gray-600">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21a8 8 0 1 0-16 0" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </span>
          <span>{doctor?.name || "Profile"}</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
