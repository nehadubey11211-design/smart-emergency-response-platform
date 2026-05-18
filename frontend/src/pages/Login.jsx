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
import { Eye, EyeOff, Mail, Lock, ArrowLeft } from "lucide-react";
import { login, register } from "../services/api";
import Button from "../components/Button.jsx";

// ─── Constants ────────────────────────────────────────────────────────────────

const ALLOWED_USER_FIELDS = ["id", "name", "email", "role"];
const COOLDOWN_MS = 800;

const PW_STRENGTHS = [
  { score: 0, label: "",            color: "" },
  { score: 1, label: "Weak",        color: "text-red-400" },
  { score: 2, label: "Fair",        color: "text-orange-400" },
  { score: 3, label: "Good",        color: "text-yellow-400" },
  { score: 4, label: "Strong",      color: "text-lime-400" },
  { score: 5, label: "Very Strong", color: "text-green-400" },
];

const emptyForm = (keepEmail = "") => ({ name: "", mobile: "", email: keepEmail, password: "", operatorId: "" });

// ─── Helpers ──────────────────────────────────────────────────────────────────

const isValidEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

const validateLogin = ({ email, password }) => {
  if (!email.trim() || !password.trim()) return "Email and password required";
  if (!isValidEmail(email)) return "Enter a valid email address";
  return "";
};

const validateSignup = ({ name, mobile, email, password }) => {
  if (!name.trim() || !mobile.trim() || !email.trim() || !password.trim()) return "All fields required";
  if (name.trim().length < 2) return "Enter your full name";
  if (!isValidEmail(email)) return "Enter a valid email address";
  if (!/^[6-9]\d{9}$/.test(mobile)) return "Enter a valid 10-digit mobile number";
  if (password.trim().length < 8) return "Password must be at least 8 characters";
  return "";
};

const sanitiseUser = (raw) => {
  if (!raw || typeof raw !== "object") return {};
  return ALLOWED_USER_FIELDS.reduce((acc, key) => {
    if (Object.prototype.hasOwnProperty.call(raw, key)) acc[key] = raw[key];
    return acc;
  }, {});
};

const storeSession = (token, user, rememberMe = false) => {
  const s = rememberMe ? localStorage : sessionStorage;
  s.setItem("token", token);
  s.setItem("user", JSON.stringify(sanitiseUser(user)));
};

const getPwStrength = (pw) => {
  if (!pw) return PW_STRENGTHS[0];
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) s++;
  if (/\d/.test(pw)) s++;
  if (/[^\w\s]/.test(pw)) s++;
  return PW_STRENGTHS[s];
};

const segColor = (score, seg, dark) => {
  if (seg > score) return dark ? "bg-slate-700" : "bg-slate-300";
  if (score <= 1) return "bg-red-400";
  if (score <= 2) return "bg-orange-400";
  if (score <= 3) return "bg-yellow-400";
  if (score <= 4) return "bg-lime-400";
  return "bg-green-400";
};

function useSubmitCooldown() {
  const last = useRef(0);
  return useCallback(() => {
    const now = Date.now();
    if (now - last.current < COOLDOWN_MS) return false;
    last.current = now;
    return true;
  }, []);
}

// ─── Theme class builders ─────────────────────────────────────────────────────

const cx = {
  root: (d) => d
    ? "min-h-screen flex items-center justify-center relative px-3 bg-gradient-to-br from-navy-900 via-blue-900 to-slate-900 text-white animate-gradient"
    : "min-h-screen flex items-center justify-center relative px-3 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 text-slate-900",
  card: (d) => d
    ? "w-full max-w-md rounded-2xl p-6 shadow-2xl shadow-black/20 bg-white/5 backdrop-blur-xl border border-white/20 animate-fadeInUp"
    : "w-full max-w-md rounded-2xl p-6 shadow-2xl shadow-slate-300/20 bg-white/80 backdrop-blur-xl border border-white/30 animate-fadeInUp",
  input: (d) => d
    ? "w-full rounded-lg border border-slate-600/50 bg-slate-950/30 backdrop-blur-sm px-4 py-3 mt-3 text-sm text-white placeholder:text-slate-400 outline-none transition focus:border-brand-blue focus:ring focus:ring-brand-blue/20"
    : "w-full rounded-lg border border-slate-300/50 bg-white/30 backdrop-blur-sm px-4 py-3 mt-3 text-sm text-slate-900 placeholder:text-slate-500 outline-none transition focus:border-brand-blue focus:ring focus:ring-brand-blue/20",
  muted: (d) => d ? "text-slate-400 hover:text-white" : "text-slate-500 hover:text-slate-900",
};

// ─── Main Component ───────────────────────────────────────────────────────────

export default function Login() {
  const navigate = useNavigate();
  const navigateToDashboard = () => navigate("/dashboard", { replace: true });

  const [form,         setForm]         = useState(emptyForm());
  const [showPw,       setShowPw]       = useState(false);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState("");
  const [success,      setSuccess]      = useState("");
  const [isSignup,     setIsSignup]     = useState(false);
  const [dark,         setDark]         = useState(true);
  const [rememberMe,   setRememberMe]   = useState(false);
  const [submitted,    setSubmitted]    = useState(false);
  const [selectedRole, setSelectedRole] = useState("user");

  const formRef      = useRef(emptyForm());
  const isSignupRef  = useRef(false);
  const rememberRef  = useRef(false);
  const canSubmit    = useSubmitCooldown();

  const clearFeedback = useCallback(() => { setError(""); setSuccess(""); setSubmitted(false); }, []);

  const handleChange = useCallback((e) => {
    clearFeedback();
    setForm((prev) => { const next = { ...prev, [e.target.name]: e.target.value }; formRef.current = next; return next; });
  }, [clearFeedback]);

  const handleMobileChange = useCallback((e) => {
    clearFeedback();
    const digits = e.target.value.replace(/\D/g, "").slice(0, 10);
    setForm((prev) => { const next = { ...prev, mobile: digits }; formRef.current = next; return next; });
  }, [clearFeedback]);

  const switchMode = useCallback((toSignup) => {
    setIsSignup((cur) => {
      if (toSignup === cur) return cur;
      isSignupRef.current = toSignup;
      setError(""); setSuccess(""); setShowPw(false); setSubmitted(false);
      setRememberMe(false); rememberRef.current = false;
      setForm((prev) => { const next = emptyForm(prev.email); formRef.current = next; return next; });
      return toSignup;
    });
  }, []);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!canSubmit()) { setError("Please wait before submitting again."); return; }

    const signup = isSignupRef.current;
    const valErr = signup ? validateSignup(formRef.current) : validateLogin(formRef.current);
    if (valErr) { setError(valErr); setSubmitted(true); return; }

    setLoading(true); setError(""); setSuccess(""); setSubmitted(false);

    try {
      if (signup) {
        await register(formRef.current);
        setSuccess("Account created! Please sign in.");
        setShowPw(false); setIsSignup(false); isSignupRef.current = false;
        setRememberMe(false); rememberRef.current = false; setSubmitted(false);
        setForm((prev) => { const next = emptyForm(prev.email); formRef.current = next; return next; });
      } else {
        const { data } = await login({ email: formRef.current.email.trim(), password: formRef.current.password.trim() });
        const token = data.access_token || data.token;
        if (!token) throw new Error("Invalid response from server");
        storeSession(token, data.user, rememberRef.current);
        setRememberMe(false); rememberRef.current = false;
        navigate("/dashboard", { replace: true });
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Something went wrong");
    } finally {
      
      setLoading(false);
    }
  }, [canSubmit, navigate]);

  // ── Derived ────────────────────────────────────────────────────────────────
  const inputCls   = cx.input(dark);
  const pwStrength = isSignup && form.password ? getPwStrength(form.password) : null;

  const nameInvalid    = submitted && !form.name.trim();
  const mobileInvalid  = submitted && !/^[6-9]\d{9}$/.test(form.mobile);
  const emailInvalid   = submitted && (!form.email.trim() || !isValidEmail(form.email));
  const pwInvalid      = submitted && (isSignup ? form.password.trim().length < 8 : !form.password.trim());

  const tabBtn = (active) =>
    `flex-1 py-3 rounded-xl text-sm font-semibold transition-all duration-300 border ${
      active
        ? "bg-white text-black border-white shadow-[0_0_20px_rgba(255,255,255,0.25)]"
        : "bg-transparent text-white border-transparent hover:bg-white/10"
    }`;

  return (
    <div className={cx.root(dark)}>
      {/* Video background */}
      <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover z-0">
        <source src="/backgrounds/emergency-background-video.mp4" type="video/mp4" />
        <div style={{ backgroundImage: 'url("/backgrounds/ai-emergency-background.png")', backgroundSize: "cover", backgroundPosition: "center", position: "absolute", inset: 0, width: "90%", height: "100%" }} />
      </video>

      <div className="absolute inset-0 bg-black/4 z-10" />

      {/* Logo */}
      <div className="absolute left-5 top-4 z-20">
        <img src="/logo.png" alt="AI Smart Detection Logo" className="h-12 w-auto" />
      </div>

      {/* Theme toggle */}
      <Button variant="ghost" size="sm" onClick={() => setDark((d) => !d)}
        className="absolute right-5 top-5 rounded-full z-20"
        aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}>
        {dark ? "☀️" : "🌙"}
      </Button>
      {/* Back Button */}
<button
  type="button"
  onClick={() => navigate("/")}
  className="absolute left-5 top-5 z-20 rounded-full border border-slate-500 bg-slate-900/70 px-3 py-2 text-white transition hover:bg-slate-800/50"
  aria-label="Go Back"
>
  <ArrowLeft size={18} />
</button>

      <div className={`${cx.card(dark)} relative z-20`}>
        <h1 className="text-center text-lg font-semibold tracking-tight">AI ACCIDENT SYSTEM</h1>
        <h3 className="mt-1 text-center text-xs font-medium text-slate-400">
          {isSignup ? "Create Account" : "Welcome Back"}
        </h3>

        <form onSubmit={handleSubmit} noValidate aria-busy={loading}>

          {/* Email */}
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input type="email" name="email" placeholder="Email Address" aria-label="Email address"
              aria-invalid={emailInvalid || undefined} autoComplete="email" autoCapitalize="none"
              autoCorrect="off" spellCheck={false} value={form.email} onChange={handleChange}
              className={`${inputCls} pl-12`} />
          </div>

          {/* Signup-only fields */}
          {isSignup && (
            <>
              <input type="text" name="name" placeholder="Full Name" aria-label="Full name"
                aria-invalid={nameInvalid || undefined} autoComplete="name" autoCapitalize="words"
                spellCheck={false} value={form.name} onChange={handleChange} className={inputCls} />

              <input type="tel" name="mobile" placeholder="Mobile Number" aria-label="Mobile number"
                aria-invalid={mobileInvalid || undefined} autoComplete="tel" inputMode="numeric"
                maxLength={10} value={form.mobile} onChange={handleMobileChange} className={inputCls} />
            </>
          )}

          {/* Password */}
          <div className="relative mt-3">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input type={showPw ? "text" : "password"} name="password" placeholder="Password"
              aria-label="Password" aria-describedby={isSignup ? "pw-strength" : undefined}
              aria-invalid={pwInvalid || undefined} autoComplete={isSignup ? "new-password" : "current-password"}
              autoCapitalize="none" autoCorrect="off" spellCheck={false} value={form.password}
              onChange={handleChange} className={`${inputCls} !mt-0 pl-12 pr-12`} />
            <button type="button" aria-label={showPw ? "Hide password" : "Show password"}
              onClick={() => setShowPw((v) => !v)}
              className={`absolute right-3 top-1/2 -translate-y-1/2 transition ${cx.muted(dark)}`}>
              {showPw ? <Eye size={16} /> : <EyeOff size={16} />}
            </button>
          </div>

          {/* Password strength */}
          {isSignup && pwStrength && (
            <div id="pw-strength" aria-live="polite">
              <div className="flex gap-1 mb-1 mt-2">
                {[1, 2, 3, 4, 5].map((seg) => (
                  <div key={seg} className={`h-1 flex-1 rounded-full transition-all ${segColor(pwStrength.score, seg, dark)}`} />
                ))}
              </div>
              <p className={`text-xs font-medium ${pwStrength.color}`}>Password strength: {pwStrength.label}</p>
            </div>
          )}

          {/* Role selection */}
          {isSignup && (
            <div className="mt-4">
              <p className="text-sm text-slate-300 mb-2">Register as</p>
              <div className="flex gap-3">
                {[["user", "As User", "blue"], ["operator", "As Operator", "red"]].map(([role, label, color]) => (
            <button
              key={role}
              type="button"
              onClick={() => setSelectedRole(role)}
              className={`flex-1 py-3 rounded-xl border text-white font-medium backdrop-blur-md transition-all duration-300 ${
                selectedRole === role
                  ? role === "user"
                    ? "bg-green-500 border-green-400"
                    : "bg-red-500 border-red-400"
                    : "bg-white/10 border-white/20 hover:bg-white/20"
                }`}
                  >
               {label}
            </button>            
                ))}
              </div>
              {selectedRole === "operator" && (
                <input type="text" name="operatorId" placeholder="Enter Operator ID"
                  value={form.operatorId} onChange={handleChange} className={`${inputCls} mt-4`} />
              )}
            </div>
          )}

          {/* Feedback */}
          <p id="form-error" role="alert" aria-live="assertive" aria-hidden={!error}
            className="mt-3 text-sm text-red-400" style={{ display: error ? undefined : "none" }}>
            {error}
          </p>
          {success && <p role="status" aria-live="polite" className="mt-3 text-sm text-green-400">{success}</p>}

          {/* Remember me + Forgot password */}
          {!isSignup && (
            <div className="mt-4 flex items-center justify-between gap-2">
              <label htmlFor="remember-me" className={`flex items-center gap-2 text-xs cursor-pointer transition ${dark ? "text-slate-300 hover:text-white" : "text-slate-600 hover:text-slate-900"}`}>
                <input id="remember-me" type="checkbox" checked={rememberMe}
                  onChange={(e) => { setRememberMe(e.target.checked); rememberRef.current = e.target.checked; }}
                  className="rounded border-slate-400" />
                <span>Remember me</span>
              </label>
              <a href="#" onClick={(e) => { e.preventDefault(); navigate("/forgot-password"); }}
                className={`text-xs transition ${dark ? "text-slate-400 hover:text-white" : "text-slate-600 hover:text-slate-900"}`}>
                Forgot Password?
              </a>
            </div>
          )}

          {/* Sign In / Sign Up tabs */}
          <div className="flex gap-3 mt-6 p-1 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl">
            <button type="button" disabled={loading} onClick={() => switchMode(false)} className={tabBtn(!isSignup)}>Sign In</button>
            <button type="button" disabled={loading} onClick={() => switchMode(true)}  className={tabBtn(isSignup)}>Sign Up</button>
          </div>

          {/* Submit */}
          <Button type="submit" size="lg" loading={loading} fullWidth
            className={`mt-6 rounded-xl border transition-all duration-200 ${
              isSignup
                ? "bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-400 hover:to-blue-500 border-cyan-400/30 shadow-[0_0_25px_rgba(34,211,238,0.35)] text-white"
                : "bg-gradient-to-r from-blue-400 to-blue-500 hover:from-red-400 hover:to-blue-500 border-pink-400/30 shadow-[0_0_25px_rgba(168,85,247,0.35)] text-white"
            }`}>
            {isSignup ? "Create Account" : "Continue"}
          </Button>
        </form>

        <div className="mt-4 text-center">
          <p className={`text-xs transition ${dark ? "text-slate-500" : "text-slate-400"}`}>🔒 Secured Connection</p>
        </div>

        {import.meta.env.VITE_ENABLE_SOCIAL_LOGIN === "true" && (
          <>
            <div className="text-center my-4 text-xs text-slate-500">OR</div>
            <div className="space-y-3">
              {[["🔴", "Google"], ["🔵", "Facebook"]].map(([icon, name]) => (
                <button key={name} type="button" disabled
                  className={`w-full rounded-xl border px-4 py-3 text-sm opacity-50 cursor-not-allowed transition ${dark ? "border-slate-500 bg-transparent text-slate-100 hover:border-slate-400 hover:bg-slate-950" : "border-slate-300 bg-transparent text-slate-900 hover:border-slate-400 hover:bg-slate-50"}`}>
                  {icon} Continue with {name} (Coming Soon)
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
