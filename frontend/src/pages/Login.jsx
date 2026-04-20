/**
 * FILE: frontend/src/pages/Login.jsx
 * =========================================
 * Login Page — Controlled Form with JWT Auth
 * =========================================
 *
 * CONTROLLED COMPONENTS:
 *   In React, a "controlled" input has its value driven by state.
 *   Every keystroke calls onChange → setForm → re-render.
 *   This gives us full control: we can validate, transform, or clear
 *   the input value from JavaScript at any time.
 *
 *   Contrast with "uncontrolled" inputs (using refs), which store their
 *   own state in the DOM — easier to set up but harder to validate.
 *
 * FORM SUBMISSION PATTERN:
 *   1. Prevent default browser form submission (e.preventDefault())
 *   2. Set loading state (shows spinner, disables button)
 *   3. Call API
 *   4. On success: store token, redirect
 *   5. On failure: show error message
 *   6. Always clear loading state in finally block
 *
 * WHY localStorage FOR THE TOKEN?
 *   Simple and works across page reloads.
 *   Production alternative: httpOnly cookies (immune to XSS but require
 *   same-origin CORS setup and CSRF protection).
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Siren, Eye, EyeOff, Loader2 } from "lucide-react";
import { login } from "../services/api";

export default function Login() {
  const navigate = useNavigate();

  // ── Form state ─────────────────────────────────────────────────────────
  // Single object for related fields keeps updates simple: spread + override
  const [form,    setForm]    = useState({ email: "", password: "" });
  const [showPw,  setShowPw]  = useState(false);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");

  /** Generic field updater — works for any input in the form object */
  const handleChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();  // Prevent browser's default form POST + page reload
    setLoading(true);
    setError("");

    try {
      const { data } = await login(form);

      // Store auth data for use across pages
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user",  JSON.stringify(data.user));

      // Redirect to dashboard — replace() so Back button doesn't return to Login
      navigate("/dashboard", { replace: true });
    } catch (err) {
      // Show the backend's error message, or a generic fallback
      setError(err.response?.data?.detail || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Shared input style — defined once, applied to both inputs
  const inputStyle = {
    background:  "var(--bg-dark)",
    border:      "1px solid var(--border)",
    color:       "#E0EAF8",
    fontFamily:  "'JetBrains Mono', monospace",
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: "var(--bg-dark)" }}
    >
      {/* Decorative background grid */}
      <div
        className="absolute inset-0 opacity-5 pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(var(--border) 1px, transparent 1px), " +
            "linear-gradient(90deg, var(--border) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
        aria-hidden="true"
      />

      <div className="relative w-full max-w-sm">

        {/* Brand / Logo */}
        <div className="text-center mb-8">
          <div
            className="inline-flex items-center justify-center w-14 h-14 rounded-xl mb-4"
            style={{
              background: "rgba(255,45,45,0.15)",
              border:     "1px solid rgba(255,45,45,0.4)",
            }}
          >
            <Siren size={28} style={{ color: "var(--red)" }} aria-hidden="true" />
          </div>
          <h1
            className="text-2xl font-bold tracking-wider"
            style={{ fontFamily: "'Barlow Condensed', sans-serif" }}
          >
            EMERGENCY RESPONSE
          </h1>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            AI-Powered Incident Management System
          </p>
        </div>

        {/* Login card */}
        <div className="panel p-6">
          <form onSubmit={handleSubmit} noValidate>
            <div className="flex flex-col gap-4">

              {/* Email field */}
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="email"
                  className="text-xs uppercase tracking-widest"
                  style={{ color: "var(--text-muted)", fontFamily: "'Barlow Condensed', sans-serif" }}
                >
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="operator@emergency.com"
                  value={form.email}
                  onChange={handleChange}
                  className="w-full px-3 py-2 rounded-md text-sm outline-none transition-colors"
                  style={inputStyle}
                  onFocus={(e) => (e.target.style.borderColor = "var(--red)")}
                  onBlur={(e)  => (e.target.style.borderColor = "var(--border)")}
                />
              </div>

              {/* Password field with show/hide toggle */}
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="password"
                  className="text-xs uppercase tracking-widest"
                  style={{ color: "var(--text-muted)", fontFamily: "'Barlow Condensed', sans-serif" }}
                >
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    name="password"
                    type={showPw ? "text" : "password"}
                    required
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={form.password}
                    onChange={handleChange}
                    className="w-full px-3 py-2 pr-10 rounded-md text-sm outline-none transition-colors"
                    style={inputStyle}
                    onFocus={(e) => (e.target.style.borderColor = "var(--red)")}
                    onBlur={(e)  => (e.target.style.borderColor = "var(--border)")}
                  />
                  {/* Show/hide password toggle */}
                  <button
                    type="button"
                    onClick={() => setShowPw((v) => !v)}
                    aria-label={showPw ? "Hide password" : "Show password"}
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                    style={{ color: "var(--text-dim)" }}
                  >
                    {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              {/* Error message */}
              {error && (
                <p
                  role="alert"
                  className="text-xs px-3 py-2 rounded-md"
                  style={{
                    background: "rgba(255,45,45,0.1)",
                    border:     "1px solid rgba(255,45,45,0.2)",
                    color:      "var(--red)",
                  }}
                >
                  {error}
                </p>
              )}

              {/* Submit button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-md font-bold text-sm uppercase
                           tracking-widest flex items-center justify-center gap-2
                           transition-opacity duration-200 disabled:opacity-60"
                style={{
                  background: "var(--red)",
                  color:      "#fff",
                  fontFamily: "'Barlow Condensed', sans-serif",
                  letterSpacing: "0.1em",
                }}
              >
                {loading ? (
                  <><Loader2 size={14} className="animate-spin" aria-hidden="true" /> Authenticating…</>
                ) : (
                  "SIGN IN"
                )}
              </button>
            </div>
          </form>

          {/* Demo hint */}
          <p className="text-center text-xs mt-4" style={{ color: "var(--text-dim)" }}>
            Demo: admin@emergency.com / admin123
          </p>
        </div>
      </div>
    </div>
  );
}
