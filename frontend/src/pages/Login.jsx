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
 *   localStorage is XSS-vulnerable. We use sessionStorage by default.
 *   If "Remember me" is checked, localStorage is used for persistence.
 *   For production, prefer httpOnly cookies with CSRF protection and
 *   same-origin CORS setup.
 */

import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, Mail, Lock } from "lucide-react";
import { login, register } from "../services/api";




// ─── Tailwind class helpers (centralised, no duplication) ────────────────────

function getRootClasses(dark) {
  return dark
    ? "min-h-screen flex items-center justify-center relative px-4 bg-gradient-to-br from-navy-900 via-blue-900 to-slate-900 text-white animate-gradient"
    : "min-h-screen flex items-center justify-center relative px-4 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 text-slate-900";
}

function getCardClasses(dark) {
  return dark
    ? "w-full max-w-md rounded-3xl p-6 shadow-2xl shadow-black/20 bg-white/5 backdrop-blur-xl border border-blue-400/20 backdrop-blur-xl border border-white/20 animate-fadeInUp"
    : "w-full max-w-md rounded-3xl p-6 shadow-2xl shadow-slate-300/20 bg-white/80 backdrop-blur-xl border border-white/30 animate-fadeInUp";
}

function getInputClasses(dark) {
  return dark
    ? "w-full rounded-xl border border-slate-600/50 bg-slate-950/30 backdrop-blur-sm px-4 py-3 mt-3 text-sm text-white placeholder:text-slate-400 outline-none transition focus:border-brand-blue focus:ring focus:ring-brand-blue/20"
    : "w-full rounded-xl border border-slate-300/50 bg-white/30 backdrop-blur-sm px-4 py-3 mt-3 text-sm text-slate-900 placeholder:text-slate-500 outline-none transition focus:border-brand-blue focus:ring focus:ring-brand-blue/20";
}

function getSwitchButtonClasses(active, dark) {
  const base = "rounded-xl px-4 py-2 text-sm font-medium transition";
  if (active) return `${base} bg-blue-600 text-white`;
  return dark
    ? `${base} bg-slate-700 text-slate-200 hover:bg-slate-600`
    : `${base} bg-slate-200 text-slate-700 hover:bg-slate-300`;
}

/** Only used when VITE_ENABLE_SOCIAL_LOGIN=true */
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

/** Only used when VITE_ENABLE_SOCIAL_LOGIN=true */
function SocialLoginSection({ dark }) {
  const cls = getSocialButtonClasses(dark);
  return (
    <>
      <div className="text-center my-4 text-xs text-slate-500">OR</div>
      <div className="space-y-3">
        <button type="button" disabled className={`${cls} opacity-50 cursor-not-allowed`}>
          🔴 Continue with Google (Coming Soon)
        </button>
        <button type="button" disabled className={`${cls} opacity-50 cursor-not-allowed`}>
          🔵 Continue with Facebook (Coming Soon)
        </button>
      </div>
    </>
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

// ─── Safe session helpers ─────────────────────────────────────────────────────

const ALLOWED_USER_FIELDS = ["id", "name", "email", "role"];

function sanitiseUser(raw) {
  if (!raw || typeof raw !== "object") return {};
  return ALLOWED_USER_FIELDS.reduce((acc, key) => {
    if (Object.prototype.hasOwnProperty.call(raw, key)) acc[key] = raw[key];
    return acc;
  }, {});
}

function storeSession(token, user, rememberMe = false) {
  // localStorage only when "Remember me" is explicitly checked.
  // For production prefer httpOnly cookies with CSRF + same-origin CORS.
  const storage = rememberMe ? localStorage : sessionStorage;
  storage.setItem("token", token);
  storage.setItem("user", JSON.stringify(sanitiseUser(user)));
}

// ─── Password strength calculator ────────────────────────────────────────────
// Semantic severity colours — intentionally theme-independent.
// Dark-mode empty segment colours are handled in getStrengthSegmentColor().
const PASSWORD_STRENGTHS = [
  { score: 0, label: "", color: "" },
  { score: 1, label: "Weak",        color: "text-red-400"    },
  { score: 2, label: "Fair",        color: "text-orange-400" },
  { score: 3, label: "Good",        color: "text-yellow-400" },
  { score: 4, label: "Strong",      color: "text-lime-400"   },
  { score: 5, label: "Very Strong", color: "text-green-400"  },
];

function getPasswordStrength(password) {
  if (!password) return PASSWORD_STRENGTHS[0];
  let score = 0;
  if (password.length >= 8)  score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password))        score++;
  if (/[^\w\s]/.test(password))   score++;
  return PASSWORD_STRENGTHS[score];
}

function getStrengthSegmentColor(score, seg, dark) {
  if (seg > score)  return dark ? "bg-slate-700" : "bg-slate-300"; // empty segment
  if (score <= 1)   return "bg-red-400";
  if (score <= 2)   return "bg-orange-400";
  if (score <= 3)   return "bg-yellow-400";
  if (score <= 4)   return "bg-lime-400";
  return "bg-green-400";
}

// ─── Rate-limit hook: prevents rapid re-submissions ──────────────────────────

// 800ms — long enough to block accidental double-clicks
// (typical double-click threshold ~500ms) but short enough
// to not frustrate users who retry after a fast validation error.
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

  // ── State ─────────────────────────────────────────────────────────────────
  const [form,      setForm]      = useState(emptyForm());
  const [showPw,    setShowPw]    = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");
  const [success,   setSuccess]   = useState("");
  const [isSignup,  setIsSignup]  = useState(false);
  const [dark,      setDark]      = useState(true);
  const [rememberMe, setRememberMe] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [pwFocused, setPwFocused] = useState(false);

  // ── Refs ──────────────────────────────────────────────────────────────────
  const formRef = useRef(emptyForm()); 

  const isSignupRef = useRef(false);
  const rememberMeRef = useRef(false);

  const canSubmit = useSubmitCooldown();

  // ── Helpers ───────────────────────────────────────────────────────────────

  const switchMode = useCallback((toSignup) => {
    setIsSignup((currentMode) => {
      if (toSignup === currentMode) return currentMode; // no-op guard
      isSignupRef.current = toSignup;
      setError("");
      setSuccess("");
      setShowPw(false);
      setRememberMe(false);
      rememberMeRef.current = false;
      setSubmitted(false);
      setForm((prev) => {
        const next = emptyForm(prev.email);
        formRef.current = next;
        return next;
      });
      return toSignup;
    });
  }, []);

  const handleChange = useCallback((e) => {
    setError("");
    setSuccess("");
    setSubmitted(false);
    setForm((prev) => {
      const next = { ...prev, [e.target.name]: e.target.value };
      formRef.current = next;
      return next;
    });
  }, []);

  const handleMobileChange = useCallback((e) => {
    setError("");
    setSuccess("");
    setSubmitted(false);
    const digitsOnly = e.target.value
      .replace(/\D/g, "").slice(0, 10);
    setForm((prev) => {
      const next = { ...prev, mobile: digitsOnly };
      formRef.current = next;
      return next;
    });
  }, []);

  const handleSignup = useCallback(async () => {
    const { data } = await register(formRef.current);
    return data;
  }, []);

  const handleLogin = useCallback(async () => {
    const { data } = await login({
      email:    formRef.current.email.trim(),
      password: formRef.current.password.trim(),
    });

    const token = data.access_token || data.token;
    if (!token) throw new Error("Invalid response from server");

    storeSession(token, data.user, rememberMeRef.current);
    setRememberMe(false);
    rememberMeRef.current = false;
    navigateToDashboard();
  }, [navigateToDashboard]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();

    if (!canSubmit()) {
      setError("Please wait before submitting again.");
      return;
    }

    const currentIsSignup = isSignupRef.current;

    const validationError = currentIsSignup
      ? validateSignup(formRef.current)
      : validateLogin(formRef.current);

    if (validationError) {
      setError(validationError);
      setSubmitted(true);
      return; // loading is still false — safe exit
    }

    setLoading(true);
    setError("");
    setSuccess("");
    setSubmitted(false);

    try {
      if (currentIsSignup) {
        await handleSignup();

        setSuccess("Account created! Please sign in.");
        setShowPw(false);
        setIsSignup(false);
        isSignupRef.current = false; 
        setRememberMe(false);
        rememberMeRef.current = false;        
        setSubmitted(false);
        setForm((prev) => {
          // Preserve email so the user can log in immediately
          const next = emptyForm(prev.email);
          formRef.current = next;
          return next;
        });
      } else {
        await handleLogin();
        setSubmitted(false);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [canSubmit, handleSignup, handleLogin]);

  // ── Derived values ────────────────────────────────────────────────────────

  const pageClasses  = getRootClasses(dark);
  const cardClasses  = getCardClasses(dark);
  const inputClasses = getInputClasses(dark);

  const pwStrength = isSignup && form.password
    ? getPasswordStrength(form.password)
    : null;

  const signInTabClasses = getSwitchButtonClasses(!isSignup, dark);
  const signUpTabClasses = getSwitchButtonClasses(isSignup, dark);

  const toggleDark = useCallback(() => setDark((d) => !d), []);

  // ── Field validation states ────────────────────────────────────────────────
  const nameInvalid    = submitted && !form.name.trim();
  const mobileInvalid  = submitted && !/^[6-9]\d{9}$/.test(form.mobile);
  const emailInvalid   = submitted &&
    (!form.email.trim() || !isValidEmail(form.email));
  const passwordInvalid = submitted && (
    isSignup
      ? form.password.trim().length < 8
      : !form.password.trim()
  );

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className={pageClasses} style={{
      backgroundImage: 'url("/backgrounds/ai-emergency-background.png")',
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat'
    }}>
      <div className="absolute left-5 top-5">
        <img
          src="/logo.png"
          alt="AI Smart Detection Logo"
          className="h-12 w-auto"
        />
      </div>
      <ThemeToggle dark={dark} toggle={toggleDark} />

      <div className={cardClasses}>
        <h1 className="text-center text-2xl font-semibold tracking-tight">
          AI ACCIDENT SYSTEM
        </h1>
        <h3 className="mt-2 text-center text-sm font-medium text-slate-400">
          {isSignup ? "Create Account" : "Welcome Back"}
        </h3>

        <form onSubmit={handleSubmit} noValidate aria-busy={loading}>

          {/* ── Email field (both login and signup) ─────────────────────── */}
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              id={isSignup ? "signup-email" : "login-email"}
              type="email"
              name="email"
              placeholder="Email Address"
              aria-label="Email address"
              aria-invalid={emailInvalid ? "true" : undefined}
              aria-errormessage={emailInvalid ? "form-error" : undefined}
              autoComplete="email"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              value={form.email}
              onChange={handleChange}
              className={`${inputClasses} pl-10`}
            />
          </div>

          {/* ── Signup-only fields ─────────────────────────────────────── */}
          {isSignup && (
            <>
              <input
                id="signup-name"
                type="text"
                name="name"
                placeholder="Full Name"
                aria-label="Full name"
                aria-invalid={nameInvalid ? "true" : undefined}
                aria-errormessage={nameInvalid ? "form-error" : undefined}
                autoComplete="name"
                autoCapitalize="words"
                spellCheck={false}
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
                aria-invalid={mobileInvalid ? "true" : undefined}
                aria-errormessage={mobileInvalid ? "form-error" : undefined}
                autoComplete="tel"
                inputMode="numeric"
                maxLength={10}
                value={form.mobile}
                onChange={handleMobileChange}
                className={inputClasses}
              />
            </>
          )}

          {/* ── Password field (both login and signup) ─────────────────────── */}
          <div className="relative mt-3">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              id={isSignup ? "signup-password" : "login-password"}
              type={showPw ? "text" : "password"}
              name="password"
              placeholder="Password"
              aria-label="Password"
              aria-describedby={isSignup ? "password-strength" : undefined}
              aria-invalid={passwordInvalid ? "true" : undefined}
              aria-errormessage={passwordInvalid ? "form-error" : undefined}
              autoComplete={isSignup ? "new-password" : "current-password"}
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              value={form.password}
              onChange={handleChange}
              className={`${inputClasses} !mt-0 pl-10 pr-10`}
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

          {/* ── Password strength bar ──────────────────────────────────── */}
          {isSignup && (
            <div id="password-strength" aria-live="polite">
              {pwStrength && (
                <>
                  <div className="flex gap-1 mb-1 mt-2">
                    {[1, 2, 3, 4, 5].map((seg) => (
                      <div
                        key={seg}
                        className={`h-1 flex-1 rounded-full transition-all ${
                          getStrengthSegmentColor(pwStrength.score, seg, dark)
                        }`}
                      />
                    ))}
                  </div>
                  <p className={`text-xs font-medium ${pwStrength.color}`}>
                    Password strength: {pwStrength.label}
                  </p>
                </>
              )}
            </div>
          )}

          {/* ── Feedback messages ──────────────────────────────────────── */}
          <p
            id="form-error"
            role="alert"
            aria-live="assertive"
            aria-hidden={!error}
            className="mt-3 text-sm text-red-400"
            style={{ display: error ? undefined : "none" }}
          >
            {error}
          </p>
          {success && (
            <p role="status" aria-live="polite" className="mt-3 text-sm text-green-400">
              {success}
            </p>
          )}

          {/* ── Remember me (LEFT) + Forgot Password (RIGHT) — same row ── */}
          {!isSignup && (
            <div className="mt-4 flex items-center justify-between gap-2">

              {/* Left: Remember me checkbox */}
              <label
                htmlFor="remember-me"
                className={`flex items-center gap-2 text-xs cursor-pointer transition ${
                  dark ? "text-slate-300 hover:text-white" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <input
                  id="remember-me"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => {
                    setRememberMe(e.target.checked);
                    rememberMeRef.current = e.target.checked;
                  }}
                  className="rounded border-slate-400"
                />
                <span>Remember me</span>
              </label>

              {/* Right: Forgot Password */}
              <a
                href="#"
                className={`text-xs transition ${
                  dark ? "text-slate-400 hover:text-white" : "text-slate-600 hover:text-slate-900"
                }`}
                onClick={(e) => {
                  e.preventDefault();
                  navigate("/forgot-password");
                }}
              >
                Forgot Password?
              </a>

            </div>
          )}

          {/* ── Toggle buttons row (both modes) ──────────────────────── */}
          <div className={`flex gap-5 mt-4 ${isSignup ? "justify-end" : "justify-center"}`}>
            <button
              type="button"
              className={signInTabClasses}
              disabled={loading}
              onClick={() => switchMode(false)}
            >
              Sign In
            </button>
            <button
              type="button"
              className={signUpTabClasses}
              disabled={loading}
              onClick={() => switchMode(true)}
            >
              Sign Up
            </button>
          </div>

          {/* ── Submit button ──────────────────────────────────────────── */}
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

        {/* ── Secured connection note ─────────────────────────────────── */}
        <div className="mt-4 text-center">
          <p className={`text-xs transition ${
            dark ? "text-slate-500" : "text-slate-400"
          }`}>
            🔒 Secured Connection
          </p>
        </div>


        
        {import.meta.env.VITE_ENABLE_SOCIAL_LOGIN === "true" && (
          <SocialLoginSection dark={dark} />
        )}
      </div>
    </div>
  );
}