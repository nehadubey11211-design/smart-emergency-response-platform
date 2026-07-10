/**
 * FILE: frontend/src/components/ForgotPassword.jsx
 * =========================================================
 * Forgot Password Page — Multi-step Recovery Flow
 * =========================================================
 * Forgot Password Page - Professional AI Emergency System
 * Multi-step password recovery flow with OTP verification
 * 
 * FLOW:
 * 1. Enter email → Send OTP
 * 2. Enter OTP + new password together → backend verifies OTP and resets
 *    password in a single call → redirect to login
 */

import { useState, useRef, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, Mail, Lock, ArrowLeft, Shield } from "lucide-react";
import { sendResetOtp, verifyResetOtp } from "../services/api";


// ─── Tailwind class helpers (matching Login.jsx) ────────────────────────────

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

// ─── Sub-components ───────────────────────────────────────────────────────────

function ThemeToggle({ dark, toggle }) {
  return (
    <button
      type="button"
      className={`fixed right-5 top-5 rounded-full border px-3 py-2 text-base transition z-50 ${
        dark
          ? "border-slate-500 bg-slate-900/70 text-white hover:bg-slate-800"
          : "border-slate-300 bg-white/90 text-slate-900 hover:bg-slate-200"
      }`}
      onClick={toggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {dark ? "☀️" : "🌙"}
    </button>
  );
}

function BackButton({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
     className="fixed left-5 top-5 rounded-full border px-3 py-2 text-base transition hover:bg-slate-800/50 border-slate-500 bg-slate-900/70 text-white z-50"
    >
      <ArrowLeft size={25} />
    </button>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function ForgotPassword() {
  const navigate = useNavigate();
  
  // State management
  const [dark, setDark] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitted, setSubmitted] = useState(false);
  
  // Form state
  const [step, setStep] = useState(1); // 1: email, 2: otp, 3: reset
  const [emailOrMobile, setEmailOrMobile] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  // Timer state
    const [otpTimer, setOtpTimer] = useState(0);
    const [resendDisabled, setResendDisabled] = useState(false);
    const [resendCooldown, setResendCooldown] = useState(0);
  // Refs
  const formRef = useRef({ emailOrMobile: "", otp: "", newPassword: "", confirmPassword: "" });
  const otpTimerRef = useRef(null);

  // Update refs when state changes
  formRef.current = { emailOrMobile, otp, newPassword, confirmPassword };

  // Toggle dark mode
  const toggleDark = useCallback(() => setDark((d) => !d), []);
  
  // OTP timer using setInterval
const timerRef = useRef(null);

const startTimer = useCallback((seconds) => {
  setOtpTimer(seconds);
  setResendDisabled(true);

  clearInterval(timerRef.current);

  timerRef.current = setInterval(() => {
    setOtpTimer((prev) => {
      if (prev <= 1) {
        clearInterval(timerRef.current);
        setResendDisabled(false);
        return 0;
      }

      return prev - 1;
    });
  }, 1000);
}, []);

useEffect(() => {
  return () => clearInterval(timerRef.current);
}, []);

// Resend cooldown effect
useEffect(() => {
  if (resendCooldown <= 0) return;

  const t = setTimeout(() => {
    setResendCooldown((prev) => prev - 1);
  }, 1000);

  return () => clearTimeout(t);
}, [resendCooldown]);

  // Validation functions
  const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const isValidOTP = (otp) => /^\d{6}$/.test(otp);

  
 

  // API handlers
  const handleSendOTP = async (e) => {
    e.preventDefault();
    setSubmitted(true);
    setError("");
    setSuccess("");

    // Validation
    if (!emailOrMobile.trim()) {
      setError("Email address is required");
      return;
    }

    if (!isValidEmail(emailOrMobile)) {
      setError("Enter a valid email address");
      return;
    }

    setLoading(true);

    try {
      const payload = { email: emailOrMobile };

      await sendResetOtp(payload);
      
      setSuccess("OTP sent successfully! Please check your email.");
      setStep(2);
      setSubmitted(false);
      startTimer(300); // 5 minutes
      setResendCooldown(30);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyAndReset = async (e) => {
    e.preventDefault();
    setSubmitted(true);
    setError("");
    setSuccess("");

    // Validation — OTP
    if (!otp.trim()) {
      setError("OTP is required");
      return;
    }

    if (!isValidOTP(otp)) {
      setError("OTP must be 6 digits");
      return;
    }

    // Validation — new password
    if (!newPassword.trim()) {
      setError("New password is required");
      return;
    }

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    if (!confirmPassword.trim()) {
      setError("Please confirm your password");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);

    try {
      const payload = {
        email: emailOrMobile,
        otp,
        new_password: newPassword,
      };

      await verifyResetOtp(payload);

      setSuccess("Password reset successfully! Redirecting to login...");
      setSubmitted(false);

      // Redirect to login after 2 seconds
      setTimeout(() => {
        navigate("/login");
      }, 2000);

    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Invalid OTP or unable to reset password");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    if (resendDisabled) return;
    
    setError("");
    setSuccess("");
    
    try {
      const payload = { email: emailOrMobile };

      await sendResetOtp(payload);
      
      setSuccess("OTP resent successfully! Please check your email.");
      startTimer(300);
      setResendCooldown(30);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to resend OTP");
    }
  };

  // Derived values
  const pageClasses = getRootClasses(dark);
  const cardClasses = getCardClasses(dark);
  const inputClasses = getInputClasses(dark);

  return (
    
  <div className={`${pageClasses} overflow-hidden`}>

    {/* Video Background */}
    <video
      autoPlay
      loop
      muted
      playsInline
      className="absolute inset-0 w-full h-full object-cover z-0"
    >
       <source
      src="https://res.cloudinary.com/dcy4ufnnb/video/upload/v1779630245/emergency-background-video_turvld.mp4"
      type="video/mp4"
    />

      {/* Fallback Background Image */}
      <div
        style={{
          backgroundImage:
            'url("https://res.cloudinary.com/dcy4ufnnb/image/upload/v1779630245/ai-emergency-background.png")',
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
        }}
      />
    </video>

    {/* Dark Overlay */}
    <div className="absolute inset-0 bg-black/4 z-10" />
      <div className="relative z-20">
  <BackButton onClick={() => navigate("/login")} />
</div>

<div className="relative z-20">
  <ThemeToggle dark={dark} toggle={toggleDark} />
</div>

      <div className={`${cardClasses} relative z-20`}>
        <div className="text-center mb-6">
          <div className="mx-auto w-16 h-16 rounded-full bg-blue-500/20 flex items-center justify-center mb-4">
            <Shield className="text-blue-500" size={32} />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">
            Recover Your Account
          </h1>
          <p className="text-sm text-slate-400">
            {step === 1 && "Enter your registered email address"}
            {step === 2 && "Enter the OTP and choose your new password"}
          </p>
        </div>

        {/* Step 1: Email Input */}
        {step === 1 && (
          <form onSubmit={handleSendOTP}>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type="email"
                placeholder="Email Address"
                value={emailOrMobile}
                onChange={(e) => setEmailOrMobile(e.target.value)}
                className={`${inputClasses} pl-10 ${submitted && !emailOrMobile.trim() ? 'border-red-500' : ''}`}
                aria-label="Email address"
                aria-invalid={submitted && !emailOrMobile.trim() ? "true" : undefined}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-6 w-full rounded-xl bg-blue-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? (
                <Loader2 className="animate-spin mx-auto" size={18} />
              ) : (
                "Send OTP"
              )}
            </button>
          </form>
        )}

        {/* Step 2: OTP + New Password (combined — backend verifies and resets in one call) */}
        {step === 2 && (
          <form onSubmit={handleVerifyAndReset}>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type="text"
                placeholder="Enter 6-digit OTP"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className={`${inputClasses} pl-10 text-center text-lg font-mono ${submitted && (!otp.trim() || !isValidOTP(otp)) ? 'border-red-500' : ''}`}
                aria-label="OTP"
                aria-invalid={submitted && (!otp.trim() || !isValidOTP(otp)) ? "true" : undefined}
                maxLength={6}
              />
            </div>

            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-slate-400">
                {otpTimer > 0 && `OTP expires in ${Math.floor(otpTimer / 60)}:${(otpTimer % 60).toString().padStart(2, '0')}`}
              </span>
              <button
                type="button"
                onClick={handleResendOTP}
                disabled={resendDisabled}
                className="text-xs text-red-400 hover:text-red-300 disabled:text-slate-500 disabled:cursor-not-allowed"
              >
                {resendDisabled ? `Resend in ${resendCooldown}s` : "Resend OTP"}
              </button>
            </div>

            <div className="relative mt-3">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type={showPassword ? "text" : "password"}
                placeholder="New Password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className={`${inputClasses} !mt-0 pl-10 pr-10 ${submitted && (!newPassword.trim() || newPassword.length < 8) ? 'border-red-500' : ''}`}
                aria-label="New password"
                aria-invalid={submitted && (!newPassword.trim() || newPassword.length < 8) ? "true" : undefined}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            <div className="relative mt-3">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type={showConfirmPassword ? "text" : "password"}
                placeholder="Confirm New Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`${inputClasses} pl-10 pr-10 ${submitted && (!confirmPassword.trim() || confirmPassword !== newPassword) ? 'border-red-500' : ''}`}
                aria-label="Confirm new password"
                aria-invalid={submitted && (!confirmPassword.trim() || confirmPassword !== newPassword) ? "true" : undefined}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-6 w-full rounded-xl bg-red-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? (
                <Loader2 className="animate-spin mx-auto" size={18} />
              ) : (
                "Reset Password"
              )}
            </button>
          </form>
        )}

        {/* Error/Success Messages */}
        {error && (
          <p
            role="alert"
            aria-live="assertive"
            className="mt-4 text-sm text-red-400"
          >
            {error}
          </p>
        )}
        
        {success && (
          <p
            role="status"
            aria-live="polite"
            className="mt-4 text-sm text-green-400"
          >
            {success}
          </p>
        )}

        {/* Security Note */}
        <div className="mt-6 text-center">
          <p className="text-xs text-slate-500">
            🔒 Secured Connection • OTP Protected
          </p>
        </div>
      </div>
    </div>
  );
}
