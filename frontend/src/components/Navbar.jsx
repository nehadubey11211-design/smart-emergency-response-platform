/**
 * FILE: frontend/src/components/Navbar.jsx
 * ===============================================
 * Sidebar Navigation Component
 * ===============================================
 */

import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { LayoutDashboard, BarChart2, History, LogOut, Siren } from "lucide-react";

// --- Navigation Configuration ------------------------------------------------

const NAV_ITEMS = [
  { to: "/dashboard",   icon: LayoutDashboard, label: "Dashboard" },
  { to: "/analytics",   icon: BarChart2,        label: "Analytics" },
  { to: "/history",     icon: History,           label: "History"   },
  { to: "/ambulance/1", icon: Siren,             label: "Ambulance" },
];

export default function Navbar() {

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/login";
  };

  return (
    <nav
      className="fixed left-0 top-0 h-full w-16 flex flex-col items-center py-4 gap-1 z-50"
      style={{
        background: "var(--bg-panel)",
        borderRight: "1px solid var(--border)",
      }}
      aria-label="Main navigation"
    >

      {/* Logo / Brand Mark */}
      <div
        className="mb-6 flex items-center justify-center w-10 h-10 rounded-lg"
        style={{ background: "var(--red)" }}
        title="Emergency Response System"
      >
        <Siren size={20} color="#fff" aria-hidden="true" />
      </div>

      {/* Navigation Links */}
      {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          title={label}
          aria-label={label}
          className="group relative flex items-center justify-center w-10 h-10 rounded-lg transition-colors duration-200"
          style={({ isActive }) =>
            isActive
              ? { background: "rgba(255,45,45,0.15)", color: "var(--red)" }
              : { color: "var(--text-dim)" }
          }
        >
          <Icon
            size={18}
            aria-hidden="true"
            className="group-hover:text-white transition-colors duration-200"
          />
          <span className="absolute left-14 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity duration-150 border border-gray-700 z-50">
            {label}
          </span>
        </NavLink>
      ))}

      {/* Logout Button */}
      <button
        onClick={handleLogout}
        title="Logout"
        aria-label="Logout"
        className="mt-auto group relative flex items-center justify-center w-10 h-10 rounded-lg transition-colors duration-200 hover:bg-red-900/20"
        style={{ color: "var(--text-dim)" }}
      >
        <LogOut
          size={18}
          aria-hidden="true"
          className="group-hover:text-red-400 transition-colors duration-200"
        />
        <span className="absolute left-14 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity duration-150 border border-gray-700 z-50">
          Logout
        </span>
      </button>
    </nav>
  );
}
