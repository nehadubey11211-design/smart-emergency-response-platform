/**
 * FILE: frontend/src/App.jsx
 * =================================
 * Root React Component — Routing & Auth Guard
 * =================================
 *
 * REACT ROUTER v6 CONCEPTS used here:
 *
 *   <BrowserRouter>   Uses the HTML5 History API for clean URLs (/dashboard
 *                     instead of /#/dashboard). Requires server-side config
 *                     to serve index.html for all routes in production.
 *
 *   <Routes>          Container for all <Route> elements. Renders only the
 *                     first route that matches the current URL.
 *
 *   <Route>           Maps a URL path to a component.
 *                     path="*" is a catch-all (404 handler).
 *
 *   <Navigate>        Declarative redirect — renders nothing but changes URL.
 *
 * AUTH GUARD PATTERN:
 *   ProtectedRoute wraps any route that requires authentication.
 *   It checks for a JWT token in localStorage:
 *     - Token found → render the page (with Navbar)
 *     - No token    → redirect to /login
 *
 *   This prevents unauthenticated users from accessing the dashboard
 *   even if they type the URL directly.
 *
 *   Production improvement: also validate the token expiry here (decode JWT
 *   and check the `exp` claim) rather than waiting for a 401 from the API.
 *
 * LAYOUT PATTERN:
 *   The Navbar is rendered inside ProtectedRoute, not at the App level.
 *   This means the login/home pages get NO sidebar — which is correct.
 *
 * INTERVIEW TALKING POINT:
 *   "I used a wrapper component for protected routes rather than
 *   duplicating auth checks in every page. Single Responsibility:
 *   ProtectedRoute's only job is to decide if the user can proceed."
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Navbar     from "./components/Navbar.jsx";
import Home       from "./pages/Home.jsx";
import Login      from "./pages/Login.jsx";
import Dashboard  from "./pages/Dashboard.jsx";
import Analytics  from "./pages/Analytics.jsx";
import History    from "./pages/History.jsx";


// ─── Auth Guard Component ─────────────────────────────────────────────────────

/**
 * Wraps protected pages. Redirects to /login if no token is present.
 *
 * Why check localStorage here (not in each page)?
 *   - DRY: auth logic in one place
 *   - If auth method changes (e.g. cookies instead of localStorage),
 *     only this component needs updating
 *
 * @param {{ children: React.ReactNode }} props
 */
function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");

  if (!token) {
    /**
     * <Navigate replace> replaces the current history entry instead of
     * adding to it. This means pressing the browser Back button after
     * login won't send the user back to the "you must log in" redirect.
     */
    return <Navigate to="/login" replace />;
  }

  return (
    // Layout wrapper: fixed sidebar + scrollable main content
    <div className="flex min-h-screen" style={{ background: "var(--bg-dark)" }}>
      {/* Vertical icon navbar — always visible on authenticated pages */}
      <Navbar />

      {/* Main content area — ml-16 leaves room for the 64px (w-16) navbar */}
      <main className="flex-1 ml-16 p-6 overflow-auto">
        {children}
      </main>
    </div>
  );
}


// ─── Root App Component ───────────────────────────────────────────────────────

export default function App() {
  return (
    /**
     * BrowserRouter provides the routing context to all descendant components.
     * Everything that uses useNavigate(), useParams(), Link, etc. must be
     * inside a Router.
     */
    <BrowserRouter>
      <Routes>

        {/* ── Public Routes (no auth required) ──────────────────────────── */}
        <Route path="/"      element={<Home />} />
        <Route path="/login" element={<Login />} />

        {/* ── Protected Routes (redirect to /login if not authenticated) ── */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute>
              <Analytics />
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <History />
            </ProtectedRoute>
          }
        />

        {/* ── 404 Fallback ──────────────────────────────────────────────── */}
        {/* Any unknown URL redirects to the home page */}
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </BrowserRouter>
  );
}
