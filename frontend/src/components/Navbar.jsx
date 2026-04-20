/**
 * FILE: frontend/src/components/Navbar.jsx
 * ===============================================
 * Sidebar Navigation Component
 * ===============================================
 *
 * COMPONENT DESIGN DECISIONS:
 *
 *   Data-driven rendering:
 *     The nav items are defined as a plain array (NAV_ITEMS), and the JSX
 *     maps over it. Adding a new page = add one object to the array.
 *     This is the "configuration over code" principle.
 *
 *   NavLink vs Link:
 *     React Router's <NavLink> adds an "active" class/style when its `to`
 *     prop matches the current URL. We use this to highlight the current page.
 *     A plain <Link> doesn't know whether it's the active route.
 *
 *   Icon-only with tooltips:
 *     Narrow sidebar (w-16) keeps the layout compact on small screens.
 *     CSS-only tooltips (no library needed) show the label on hover.
 *
 *   Logout:
 *     Clears localStorage (JWT token + user profile) and redirects.
 *     Using window.location.href instead of navigate() to force a full
 *     page reload — ensures all in-memory state (WebSocket, etc.) is cleared.
 *
 * INTERVIEW TALKING POINT:
 *   "I used a data-driven nav array so adding a new page to the app
 *   only requires adding one line of config — no JSX duplication."
 */

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  BarChart2,
  History,
  LogOut,
  Siren,
} from "lucide-react";

// ─── Navigation Configuration ─────────────────────────────────────────────────
// Each object maps a label → route → Lucide icon component.
// Adding a new page = add one entry here and create the route in App.jsx.

const NAV_ITEMS = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/analytics", icon: BarChart2,       label: "Analytics" },
  { to: "/history",   icon: History,         label: "History"   },
];

export default function Navbar() {
  /** Clear auth data and hard-redirect to login on logout */
  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    // Full page reload ensures WebSocket connections are closed
    // and no stale state persists in memory
    window.location.href = "/login";
  };

  return (
    <nav
      className="fixed left-0 top-0 h-full w-16 flex flex-col items-center py-4 gap-1 z-50"
      style={{
        background:  "var(--bg-panel)",
        borderRight: "1px solid var(--border)",
      }}
      aria-label="Main navigation"
    >
      {/* ── Logo / Brand Mark ─────────────────────────────────────────── */}
      <div
        className="mb-6 flex items-center justify-center w-10 h-10 rounded-lg"
        style={{ background: "var(--red)" }}
        title="Emergency Response System"
      >
        <Siren size={20} color="#fff" aria-hidden="true" />
      </div>

      {/* ── Nav Links ─────────────────────────────────────────────────── */}
      {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          title={label}           // Native browser tooltip (fallback)
          aria-label={label}      // Screen reader accessibility
          className="group relative flex items-center justify-center w-10 h-10 rounded-lg transition-colors duration-200"
          /**
           * NavLink's style prop accepts a function that receives { isActive }.
           * We use this to apply different styles for the active route.
           */
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

          {/*
           * CSS-only tooltip — no JS library needed.
           * opacity-0 → group-hover:opacity-100 creates the fade-in effect.
           * pointer-events-none prevents the tooltip from interfering with clicks.
           * whitespace-nowrap prevents multi-line wrapping for long labels.
           */}
          <span
            className="absolute left-14 bg-gray-900 text-white text-xs px-2 py-1 rounded
                       opacity-0 group-hover:opacity-100 pointer-events-none
                       whitespace-nowrap transition-opacity duration-150
                       border border-gray-700 z-50"
          >
            {label}
          </span>
        </NavLink>
      ))}

      {/* ── Logout Button — pinned to bottom ──────────────────────────── */}
      {/*
       * mt-auto pushes this to the bottom of the flex column.
       * Using a <button> (not <a>) because it performs an action, not navigation.
       */}
      <button
        onClick={handleLogout}
        title="Logout"
        aria-label="Logout"
        className="mt-auto group relative flex items-center justify-center
                   w-10 h-10 rounded-lg transition-colors duration-200
                   hover:bg-red-900/20"
        style={{ color: "var(--text-dim)" }}
      >
        <LogOut
          size={18}
          aria-hidden="true"
          className="group-hover:text-red-400 transition-colors duration-200"
        />
        <span
          className="absolute left-14 bg-gray-900 text-white text-xs px-2 py-1 rounded
                     opacity-0 group-hover:opacity-100 pointer-events-none
                     whitespace-nowrap transition-opacity duration-150
                     border border-gray-700 z-50"
        >
          Logout
        </span>
      </button>
    </nav>
  );
}
