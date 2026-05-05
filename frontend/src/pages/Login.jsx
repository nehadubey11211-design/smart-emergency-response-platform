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
 * FORM SUBMISSION PATTERN:
 *   1. Validate before setting loading (so spinner never leaks)
 *   2. Set loading state (shows spinner, disables button)
 *   3. Call API
 *   4. On success: store token, redirect
 *   5. On failure: show error message
 *   6. Always clear loading state in finally block
 *
 * WHY NOT localStorage FOR THE TOKEN?
 *   localStorage is XSS-vulnerable. We now use sessionStorage as a
 *   lighter mitigation. For production, prefer httpOnly cookies with
 *   CSRF protection and same-origin CORS setup.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { login, register } from "../services/api";

// ─── Tailwind class helpers (centralised, no duplication) ────────────────────

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
    ? "w-full rounded-xl border border-slate-600 bg-slate-950 px-4 py-3 mt-3 text-sm text-white placeholder:text-slate-400 outline-none transition focus:border-brand-blue focus:ring focus:ring-brand-blue/20"
    : "w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 mt-3 text-sm text-slate-900 placeholder:text-slate-500 outline-none transition focus:border-brand-blue focus:ring focus:ring-brand-blue/20";
}

function getSwitchButtonClasses(active, dark) {
  const base = "rounded-xl px-4 py-2 text-sm font-medium transition";
  if (active) return `${base} bg-blue-600 text-white`;
  return dark
    ? `${base} bg-slate-700 text-slate-200 hover:bg-slate-600`
    : `${base} bg-slate-200 text-slate-700 hover:bg-slate-300`;
}

function getSocialButtonClasses(dark) {
  return dark
    ? "w-full rounded-xl border border-slate-500 bg-transparent px-4 py-3 text-sm text-slate-100 transition hover:border-slate-400 hover:bg-slate-950"
    : "w-full rounded-xl border border-slate-300 bg-transparent px-4 py-3 text-sm text-slate-900 transition hover:border-slate-400 hover:bg-slate-50";
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ThemeToggle({ dark, toggle }) {
  return (
    <button
      type="button"
      className={`absolute right-5 top-5 rounded-full border px-3 py-2 text-base transition ${
        dark
          ? "border-slate-500 bg-slate-900/70 text-white hover:bg-slate-800"
          : "border-slate-300 bg-white/90 text-slate-900 hover:bg-slate-200"
      }`}
      onClick={toggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {dark ? "🌞" : "🌙"}
    </button>
  );
}

// ─── Validation ───────────────────────────────────────────────────────────────

const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

/**
 * Returns an error string or "" if valid.
 * Called BEFORE setLoading(true) so a failed validation
 * never leaves the spinner running.
 */
function validateLogin(form) {
  if (!form.email.trim() || !form.password.trim()) return "Email and password required";
  if (!isValidEmail(form.email)) return "Enter a valid email address";
  return "";
}

function validateSignup(form) {
  if (!form.name.trim() || !form.mobile.trim() || !form.email.trim() || !form.password.trim())
    return "All fields required";
  if (form.name.trim().length < 2) return "Enter your full name";
  if (!isValidEmail(form.email)) return "Enter a valid email address";
  if (!/^[6-9]\d{9}$/.test(form.mobile)) return "Enter a valid 10-digit mobile number";
  if (form.password.trim().length < 8) return "Password must be at least 8 characters";
  return "";
}

// ─── Safe session helpers (avoids raw JWT + arbitrary server data in storage) ─

const ALLOWED_USER_FIELDS = ["id", "name", "email", "role"];

function sanitiseUser(raw) {
  if (!raw || typeof raw !== "object") return {};
  return ALLOWED_USER_FIELDS.reduce((acc, key) => {
    if (Object.prototype.hasOwnProperty.call(raw, key)) acc[key] = raw[key];
    return acc;
  }, {});
}

function storeSession(token, user, rememberMe = false) {
  // FIX (Warning): Use sessionStorage for security (clears on tab close).
  // If "Remember me" is checked, use localStorage for persistence.
  // For production, prefer httpOnly cookies with CSRF protection and same-origin CORS.
  const storage = rememberMe ? localStorage : sessionStorage;
  storage.setItem("token", token);
  storage.setItem("user", JSON.stringify(sanitiseUser(user)));
}

// ─── Password strength calculator ──────────────────────────────────────────

function getPasswordStrength(password) {
  if (!password) return { score: 0, label: "", color: "" };
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^\w\s]/.test(password)) score++;

  const strengths = [
    { score: 0, label: "", color: "" },
    { score: 1, label: "Weak", color: "text-red-400" },
    { score: 2, label: "Fair", color: "text-orange-400" },
    { score: 3, label: "Good", color: "text-yellow-400" },
    { score: 4, label: "Strong", color: "text-lime-400" },
    { score: 5, label: "Very Strong", color: "text-green-400" },
  ];
  return strengths[score];
}

// ─── Rate-limit hook: prevents rapid re-submissions ──────────────────────────

const COOLDOWN_MS = 800;

function useSubmitCooldown() {
  const lastSubmit = useRef(0);
  return useCallback(() => {
    const now = Date.now();
    if (now - lastSubmit.current < COOLDOWN_MS) return false;
    lastSubmit.current = now;
    return true;
  }, []);
}

// ─── Default form state factory ───────────────────────────────────────────────

const emptyForm = (keepEmail = "") => ({
  name: "",
  mobile: "",
  email: keepEmail,
  password: "",
});

// ─── Main component ───────────────────────────────────────────────────────────

export default function Login() {
  const navigate = useNavigate();
  const navigateToDashboard = useCallback(
    () => navigate("/dashboard", { replace: true }),
    [navigate]
  );

  const [form, setForm] = useState(emptyForm());
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSignup, setIsSignup] = useState(false);
  const [dark, setDark] = useState(true);
  const [rememberMe, setRememberMe] = useState(false);

  const formRef = useRef(form);
  useEffect(() => {
    formRef.current = form;
  }, [form]);

  const canSubmit = useSubmitCooldown();

  // ── Centralised mode switcher (FIX Suggestion: no drift across 3 handlers) ──
  const switchMode = useCallback(
    (toSignup) => {
      if (loading) return;
      setIsSignup(toSignup);
      setError("");
      setSuccess("");
      setForm(emptyForm(formRef.current.email)); // preserve email, clear everything else
      setShowPw(false);
    },
    [loading]
  );

  const handleChange = (e) => {
    setError("");
    setSuccess("");
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleMobileChange = (e) => {
    setError("");
    setSuccess("");
    const digitsOnly = e.target.value.replace(/\D/g, "").slice(0, 10);
    setForm((prev) => ({ ...prev, mobile: digitsOnly }));
  };

  /**
   * FIX (Critical): handleSignup no longer has an inner try/catch.
   * It throws on API error so handleSubmit's single catch handles everything.
   * Validation is done in handleSubmit BEFORE setLoading, so early-return
   * never leaves the spinner running.
   */
  const handleSignup = useCallback(async () => {
    const { data } = await register(form);
    return data;
  }, [form]);

  /**
   * FIX (Critical): handleLogin throws on error — no swallowing.
   */
  const handleLogin = useCallback(async () => {
    const { data } = await login({
      email: form.email.trim(),
      password: form.password.trim(),
    });

    const token = data.access_token || data.token;
    if (!token) throw new Error("Invalid response from server");

    storeSession(token, data.user, rememberMe);
    navigateToDashboard();
  }, [form, navigateToDashboard, rememberMe]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // FIX (Warning): lightweight submission debounce
    if (!canSubmit()) return;

    // ── FIX (Critical): ALL validation runs BEFORE setLoading ───────────────
    // This guarantees the spinner never leaks on a validation failure.
    const validationError = isSignup ? validateSignup(form) : validateLogin(form);
    if (validationError) {
      setError(validationError);
      return; // safe: loading is still false
    }

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      if (isSignup) {
        await handleSignup();
        setSuccess("Account created! Please sign in.");
        setShowPw(false);
        switchMode(false);
      } else {
        await handleLogin();
      }
    } catch (err) {
      // Single, unified error handler for both branches
      setError(err?.response?.data?.detail || err?.message || "Something went wrong");
    } finally {
      // FIX (Critical): always clears — no manual setLoading(false) above
      setLoading(false);
    }
  };

  const pageClasses = getRootClasses(dark);
  const cardClasses = getCardClasses(dark);
  const inputClasses = getInputClasses(dark);
  const socialButtonClasses = getSocialButtonClasses(dark);

  return (
    <div className={pageClasses}>
      <ThemeToggle dark={dark} toggle={() => setDark((d) => !d)} />

      <div className={cardClasses}>
        <h1 className="text-center text-2xl font-semibold tracking-tight">AI ACCIDENT SYSTEM</h1>
        <h3 className="mt-2 text-center text-sm font-medium text-slate-400">
          {isSignup ? "Create Account" : "Welcome Back"}
        </h3>

        <form onSubmit={handleSubmit} noValidate>
          {/* FIX (Intentional): noValidate disables browser validation.
              We handle ALL validation in JavaScript (validateLogin/validateSignup).
              This gives us full control: custom error messages, styling, timing.
              Do not remove without refactoring error handling. */}
          {isSignup && (
            <>
              <input
                id="signup-name"
                type="text"
                name="name"
                placeholder="Full Name"
                aria-label="Full name"
                autoComplete="name"
                value={form.name}
                onChange={handleChange}
                className={inputClasses}
              />

              <input
                id="signup-mobile"
                type="tel"
                name="mobile"
                placeholder="Mobile Number"
                aria-label="Mobile number"
                autoComplete="tel"
                inputMode="numeric"
                maxLength={10}
                value={form.mobile}
                onChange={handleMobileChange}
                className={inputClasses}
              />
            </>
          )}

          <input
            id={isSignup ? "signup-email" : "login-email"}
            type="email"
            name="email"
            placeholder="Email"
            aria-label="Email address"
            autoComplete={isSignup ? "email" : "username"}
            value={form.email}
            onChange={handleChange}
            className={inputClasses}
          />

          <div className="relative mt-3">
            <input
              id={isSignup ? "signup-password" : "login-password"}
              type={showPw ? "text" : "password"}
              name="password"
              placeholder="Password"
              aria-label="Password"
              autoComplete={isSignup ? "new-password" : "current-password"}
              value={form.password}
              onChange={handleChange}
              className={`${inputClasses} !mt-0`}
            />
            <button
              type="button"
              aria-label={showPw ? "Hide password" : "Show password"}
              onClick={() => setShowPw((v) => !v)}
              className={`absolute right-3 top-1/2 -translate-y-1/2 transition ${
                dark ? "text-slate-400 hover:text-white" : "text-slate-500 hover:text-slate-900"
              }`}
            >
              {showPw ? <Eye size={16} /> : <EyeOff size={16} />}
            </button>
          </div>

          {isSignup && form.password && (
            <p className={`mt-2 text-xs font-medium ${getPasswordStrength(form.password).color}`}>
              Password strength: {getPasswordStrength(form.password).label}
            </p>
          )}

          {error && (
            <p role="alert" aria-live="assertive" className="mt-3 text-sm text-red-400">
              {error}
            </p>
          )}
          {success && (
            <p role="status" aria-live="polite" className="mt-3 text-sm text-green-400">
              {success}
            </p>
          )}

          {!isSignup && (
            <label className={`mt-4 flex items-center gap-2 text-xs ${
              dark ? "text-slate-300 hover:text-white" : "text-slate-600 hover:text-slate-900"
            } cursor-pointer transition`}>
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="rounded border-slate-400"
                aria-label="Remember me on this device"
              />
              <span>Remember me (saves login locally)</span>
            </label>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-4 w-full rounded-xl bg-red-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? (
              <Loader2 className="animate-spin mx-auto" size={18} />
            ) : isSignup ? (
              "SIGN UP"
            ) : (
              "SIGN IN"
            )}
          </button>
        </form>

        <div className="mt-4 flex justify-center gap-3">
          <button
            type="button"
            className={getSwitchButtonClasses(!isSignup, dark)}
            disabled={loading}
            onClick={() => switchMode(false)}
          >
            Sign In
          </button>
          <button
            type="button"
            className={getSwitchButtonClasses(isSignup, dark)}
            disabled={loading}
            onClick={() => switchMode(true)}
          >
            Sign Up
          </button>
        </div>

        {/* Social login buttons disabled until feature ships.
            Hiding the "OR" divider + buttons to avoid misleading users
            about available authentication options. */}
        {false && (
          <>
            <div className="text-center my-4 text-xs text-slate-500">OR</div>
            <div className="space-y-3">
              <button disabled className={`${socialButtonClasses} opacity-50 cursor-not-allowed`}>
                🔴 Continue with Google (Coming Soon)
              </button>
              <button disabled className={`${socialButtonClasses} opacity-50 cursor-not-allowed`}>
                🔵 Continue with Facebook (Coming Soon)
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}