// Using React Router for navigation
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

// ================= AUTH API =================
// Uses the real backend auth service via frontend/src/services/api.js

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { login, register } from "../services/api";

function getRootClasses(dark) {
  return dark
    ? "min-h-screen flex items-center justify-center relative px-4 bg-brand-dark text-white"
    : "min-h-screen flex items-center justify-center relative px-4 bg-slate-100 text-slate-900";
}

function getCardClasses(dark) {
  return dark
    ? "w-full max-w-md rounded-3xl p-6 shadow-2xl shadow-black/20 bg-brand-card"
    : "w-full max-w-md rounded-3xl p-6 shadow-2xl shadow-slate-300/20 bg-white";
}

function getInputClasses(dark) {
  return dark
    ? "w-full rounded-xl border border-slate-600 bg-slate-950 px-4 py-3 text-sm text-white placeholder:text-slate-400 outline-none transition focus:border-brand-blue focus:ring focus:ring-brand-blue/20"
    : "w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 placeholder:text-slate-500 outline-none transition focus:border-brand-blue focus:ring focus:ring-brand-blue/20";
}

function getSwitchButtonClasses(active, dark) {
  const base = "rounded-xl px-4 py-2 text-sm font-medium transition";
  if (active) {
    return `${base} bg-blue-600 text-white`;
  }
  return dark
    ? `${base} bg-slate-700 text-slate-200 hover:bg-slate-600`
    : `${base} bg-slate-200 text-slate-700 hover:bg-slate-300`;
}

function getSocialButtonClasses(dark) {
  return dark
    ? "w-full rounded-xl border border-slate-500 bg-transparent px-4 py-3 text-sm text-slate-100 transition hover:border-slate-400 hover:bg-slate-950"
    : "w-full rounded-xl border border-slate-300 bg-transparent px-4 py-3 text-sm text-slate-900 transition hover:border-slate-400 hover:bg-slate-50";
}

function ThemeToggle({ dark, toggle }) {
  return (
    <button
      type="button"
      className={`absolute right-5 top-5 rounded-full border px-3 py-2 text-base transition ${dark ? "border-slate-500 bg-slate-900/70 text-white hover:bg-slate-800" : "border-slate-300 bg-white/90 text-slate-900 hover:bg-slate-200"}`}
      onClick={toggle}
    >
      {dark ? "🌞" : "🌙"}
    </button>
  );
}

function validateSignup(form) {
  if (!form.name || !form.mobile || !form.email || !form.password) {
    return "All fields required";
  }
  if (!/^\d{10}$/.test(form.mobile)) {
    return "Mobile must be exactly 10 digits";
  }
  return "";
}

// ================= MAIN COMPONENT =================
export default function Login() {
  const navigate = useNavigate();
  const navigateToDashboard = () => navigate("/dashboard", { replace: true });

  const [form, setForm] = useState({ name: "", mobile: "", email: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isSignup, setIsSignup] = useState(false);
  const [dark, setDark] = useState(true);

  const handleChange = (e) => {
    setError("");
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSignup = async () => {
    const validationError = validateSignup(form);
    if (validationError) {
      setError(validationError);
      setLoading(false);
      return;
    }

    try {
      await register(form);
      alert("Account Created ✅ Please login");
      setIsSignup(false);
      setForm({ name: "", mobile: "", email: "", password: "" });
    } catch (err) {
      setError(err?.response?.data?.detail || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    try {
      const { data } = await login(form);
      const token = data.access_token || data.token;

      if (!token) {
        throw new Error("Invalid response from server");
      }

      localStorage.setItem("token", token);
      localStorage.setItem("user", JSON.stringify(data.user || {}));
      navigateToDashboard();
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (isSignup) {
      await handleSignup();
      return;
    }

    await handleLogin();
  };

  const pageClasses = getRootClasses(dark);
  const cardClasses = getCardClasses(dark);
  const inputClasses = getInputClasses(dark);
  const socialButtonClasses = getSocialButtonClasses(dark);

  return (
    <div className={pageClasses}>
      <ThemeToggle dark={dark} toggle={() => setDark(!dark)} />

      <div className={cardClasses}>
        <h1 className="text-center text-2xl font-semibold tracking-tight">AI ACCIDENT SYSTEM</h1>
        <h3 className="mt-2 text-center text-sm font-medium text-slate-400">
          {isSignup ? "Create Account" : "Welcome Back"}
        </h3>

        <form onSubmit={handleSubmit}>
          {isSignup && (
            <>
              <input name="name" placeholder="Full Name" value={form.name} onChange={handleChange} className={inputClasses} />
              <input name="mobile" placeholder="Mobile Number" value={form.mobile} onChange={handleChange} className={inputClasses} />
            </>
          )}

          <input name="email" placeholder="Email" value={form.email} onChange={handleChange} className={inputClasses} />

          <div className="relative">
            <input
              type={showPw ? "text" : "password"}
              name="password"
              placeholder="Password"
              value={form.password}
              onChange={handleChange}
              className={`${inputClasses} mb-0`}
            />

            <button
              type="button"
              onClick={() => setShowPw(!showPw)}
              className={`absolute right-3 top-3 transition ${dark ? "text-slate-400 hover:text-white" : "text-slate-500 hover:text-slate-900"}`}
            >
              {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="mt-4 w-full rounded-xl bg-red-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? <Loader2 className="animate-spin" size={18} /> : isSignup ? "SIGN UP" : "SIGN IN"}
          </button>
        </form>

        <div className="mt-4 flex justify-center gap-3">
          <button className={getSwitchButtonClasses(!isSignup, dark)} onClick={() => setIsSignup(false)}>
            Sign In
          </button>
          <button className={getSwitchButtonClasses(isSignup, dark)} onClick={() => setIsSignup(true)}>
            Sign Up
          </button>
        </div>

        <div className="text-center my-4 text-xs text-slate-500">
          OR
        </div>

        <div className="space-y-3">
          <button className={socialButtonClasses} onClick={() => window.location.href = "https://accounts.google.com/"}>
            🔴 Continue with Google
          </button>

          <button className={socialButtonClasses} onClick={() => window.location.href = "https://www.facebook.com/login/"}>
            🔵 Continue with Facebook
          </button>
        </div>

        <p className="mt-4 text-center text-xs text-slate-400">
          Demo: admin@test.com / Password123
        </p>
      </div>
    </div>
  );
}

