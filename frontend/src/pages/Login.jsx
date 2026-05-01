import { useState } from "react";
// NOTE: React Router removed → using window.location for navigation

// ================= FAKE API =================
// Simulates login API (replace with real backend later)
const login = async (form) => {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (form.email === "admin@test.com" && form.password === "Password123") {
        resolve({
          data: {
            access_token: "demo_token_123",
            user: { id: 1, email: form.email }
          }
        });
      } else {
        reject({ response: { data: { detail: "Invalid credentials" } } });
      }
    }, 800);
  });
};

// Simulates signup API
const signup = async (form) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ data: { message: "User created", user: form } });
    }, 1000);
  });
};

// ================= MAIN COMPONENT =================
export default function Login() {

  // Navigation without React Router
  const navigateToDashboard = () => {
    try {
      window.location.href = "/dashboard";
    } catch (e) {
      console.error("Navigation failed", e);
    }
  };

  // ================= STATE =================
  const [form, setForm] = useState({ name: "", mobile: "", email: "", password: "" });
  const [showPw, setShowPw] = useState(false); // toggle password visibility
  const [loading, setLoading] = useState(false); // button loading state
  const [error, setError] = useState(""); // error message
  const [isSignup, setIsSignup] = useState(false); // toggle login/signup
  const [dark, setDark] = useState(true); // theme toggle

  // ================= HANDLE INPUT =================
  const handleChange = (e) => {
    setError("");
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  // ================= HANDLE SUBMIT =================
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    // ===== SIGNUP LOGIC =====
    if (isSignup) {
      if (!form.name || !form.mobile || !form.email || !form.password) {
        setError("All fields required");
        setLoading(false);
        return;
      }

      // Mobile validation (10 digits)
      if (!/^\d{10}$/.test(form.mobile)) {
        setError("Mobile must be exactly 10 digits");
        setLoading(false);
        return;
      }

      try {
        await signup(form);
        alert("Account Created ✅ Please login");
        setIsSignup(false);
        setForm({ name: "", mobile: "", email: "", password: "" });
      } catch {
        setError("Signup failed");
      } finally {
        setLoading(false);
      }
      return;
    }

    // ===== LOGIN LOGIC =====
    try {
      const { data } = await login(form);

      // Save token & user (simulate auth)
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      navigateToDashboard();
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  // ================= STYLES =================
  // Inline styles used to avoid Tailwind sandbox error
  const styles = {
    container: {
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: dark ? "#0f172a" : "#f3f4f6",
      color: dark ? "#fff" : "#000",
      position: "relative",
      fontFamily: "Arial, sans-serif"
    },
    card: {
      width: "100%",
      maxWidth: "380px",
      padding: "20px",
      borderRadius: "12px",
      background: dark ? "#1e293b" : "#ffffff",
      boxShadow: "0 10px 25px rgba(0,0,0,0.2)"
    },
    input: {
      padding: "10px",
      borderRadius: "6px",
      border: "1px solid #ccc",
      width: "100%",
      marginBottom: "10px",
      outline: "none",
      background: dark ? "#0f172a" : "#ffffff",
      color: dark ? "#ffffff" : "#000000" // FIX: ensures text visible in dark/light mode
    },
    mainButton: {
      width: "100%",
      padding: "10px",
      background: "red",
      color: "white",
      border: "none",
      marginTop: "10px",
      cursor: "pointer",
      borderRadius: "6px"
    },
    switchBtn: (active) => ({
      padding: "6px 12px",
      borderRadius: "6px",
      border: "none",
      cursor: "pointer",
      background: active ? "#2563eb" : "#9ca3af",
      color: "white"
    }),
    socialBtn: {
      width: "100%",
      padding: "8px",
      marginBottom: "6px",
      borderRadius: "6px",
      border: "1px solid #ccc",
      cursor: "pointer",
      background: "transparent"
    }
  };

  // ================= UI =================
  return (
    <div style={styles.container}>

      {/* Theme Toggle Button */}
      <button onClick={() => setDark(!dark)} style={{ position: "absolute", top: 20, right: 20 }}>
        {dark ? "🌞" : "🌙"}
      </button>

      <div style={styles.card}>

        {/* Header */}
        <h1 style={{ textAlign: "center", marginBottom: 5 }}>AI ACCIDENT SYSTEM</h1>
        <h3 style={{ textAlign: "center", marginBottom: 15 }}>
          {isSignup ? "Create Account" : "Welcome Back"}
        </h3>

        {/* Form */}
        <form onSubmit={handleSubmit}>

          {/* Signup Fields */}
          {isSignup && (
            <>
              <input name="name" placeholder="Full Name" value={form.name} onChange={handleChange} style={styles.input} />
              <input name="mobile" placeholder="Mobile Number" value={form.mobile} onChange={handleChange} style={styles.input} />
            </>
          )}

          {/* Email */}
          <input name="email" placeholder="Email" value={form.email} onChange={handleChange} style={styles.input} />

          {/* Password */}
          <div style={{ position: "relative" }}>
            <input
              type={showPw ? "text" : "password"}
              name="password"
              placeholder="Password"
              value={form.password}
              onChange={handleChange}
              style={{ ...styles.input, marginBottom: 0 }}
            />

            {/* Toggle Password Visibility */}
            <button
              type="button"
              onClick={() => setShowPw(!showPw)}
              style={{ position: "absolute", right: 10, top: 10 }}
            >
              {showPw ? "👁️" : "🙈"}
            </button>
          </div>

          {/* Error Message */}
          {error && <p style={{ color: "red", fontSize: "12px" }}>{error}</p>}

          {/* Submit Button */}
          <button type="submit" style={styles.mainButton}>
            {loading ? "Processing..." : isSignup ? "SIGN UP" : "SIGN IN"}
          </button>
        </form>

        {/* Toggle Login/Signup */}
        <div style={{ display: "flex", justifyContent: "center", gap: 10, marginTop: 15 }}>
          <button style={styles.switchBtn(!isSignup)} onClick={() => setIsSignup(false)}>
            Sign In
          </button>
          <button style={styles.switchBtn(isSignup)} onClick={() => setIsSignup(true)}>
            Sign Up
          </button>
        </div>

        {/* Divider */}
        <div style={{ textAlign: "center", margin: "10px 0", fontSize: "12px", opacity: 0.6 }}>
          OR
        </div>

        {/* Social Login Buttons */}
        <div>
          <button
            style={styles.socialBtn}
            onClick={() => window.location.href = "https://accounts.google.com/"}
          >
            🔴 Continue with Google
          </button>

          <button
            style={styles.socialBtn}
            onClick={() => window.location.href = "https://www.facebook.com/login/"}
          >
            🔵 Continue with Facebook
          </button>
        </div>

        {/* Demo Credentials */}
        <p style={{ textAlign: "center", marginTop: 10, fontSize: "12px" }}>
          Demo: admin@test.com / Password123
        </p>

      </div>
    </div>
  );
}

// ================= TEST CASES =================
// 1. Login success → admin@test.com / Password123
// 2. Login fail → wrong password shows error
// 3. Signup empty → shows "All fields required"
// 4. Signup invalid mobile → shows "Mobile must be 10 digits"
// 5. Signup success → shows alert and switches to login
// 6. Toggle Sign In/Sign Up → form updates correctly
// 7. Theme toggle → background changes
// 8. Password toggle → 👁️ / 🙈 works correctly
