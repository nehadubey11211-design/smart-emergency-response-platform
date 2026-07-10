/**
 * FILE: frontend/src/services/api.js
 * =========================================
 * Axios HTTP Client — Centralised API Layer
 * =========================================
 *
 * WHY A CENTRALISED API MODULE?
 *   Instead of writing fetch() calls directly inside components, all HTTP
 *   requests are defined here.  Benefits:
 *     - One place to change the base URL (dev -> staging -> production)
 *     - Interceptors run for EVERY request/response automatically
 *     - Easy to mock in tests (import this module, mock its exports)
 *     - Components stay clean -- they just call getAccidents(), not axios.get(...)
 *
 * AXIOS vs FETCH:
 *   Axios is preferred here because:
 *     - Automatic JSON parsing (no response.json() needed)
 *     - Request/response interceptors (for auth headers, error handling)
 *     - Automatic error throwing on non-2xx status codes
 *     - Better TypeScript support
 *
 * INTERCEPTORS (key interview concept):
 *   Request interceptor  -- runs BEFORE the request is sent
 *     -> Attaches the JWT token to every outgoing request header
 *   Response interceptor -- runs AFTER the response arrives
 *     -> Catches 401 errors globally and redirects to login
 *
 * INTERVIEW TALKING POINT:
 *   "Using Axios interceptors means I never forget to attach the auth header.
 *   It also gives me a single place to handle token expiry -- if any request
 *   returns 401, the interceptor clears storage and redirects to login,
 *   rather than handling that in every component."
 */

import axios from "axios";

// --- Base URL ----------------------------------------------------------------
// import.meta.env reads Vite environment variables defined in frontend/.env
// VITE_API_URL=http://localhost:8000/api  (dev)
// In production: VITE_API_URL=https://api.yourdomain.com/api
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

  /**
 * Fetch dashboard summary
 * @returns {Promise<any>}
 */

// --- Axios Instance ----------------------------------------------------------
// Creating a custom instance lets us set defaults without affecting the
// global axios object -- important if you have multiple APIs in one app.
const api = axios.create({
  baseURL: BASE_URL,

  // Default headers for all requests
  headers: {
    "Content-Type": "application/json",
  },

  // Timeout after 10 seconds — prevents requests hanging indefinitely
  timeout: 60000,
});

// --- Request Interceptor -----------------------------------------------------
// Runs synchronously before every request is dispatched.
// Reads the JWT from localStorage and adds it to the Authorization header.
//
// Why localStorage?
//   Simple for demos. In production, httpOnly cookies are more secure
//   (immune to XSS attacks) but require CORS + same-site cookie setup.

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config; 
  },
  (error) => {
    // Request setup failed (e.g. network error before sending)
    return Promise.reject(error);
  }
);

// --- Response Interceptor ----------------------------------------------------
// Runs after every response arrives (both success and error paths).

api.interceptors.response.use(
  // Success path (2xx status codes) -- pass through unchanged
  (response) => response,

  // Error path (non-2xx status codes)
  (error) => {
    if (error.response?.status === 401) {
      // 401 Unauthorized = token expired or invalid
      // Clear all stored auth data and redirect to login
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("user");

      // Redirect to login page (works outside React components)
      // In a React Router context you'd use navigate() but interceptors
      // live outside the component tree.
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }

    // Always reject so the calling code's .catch() / try-catch still runs
    return Promise.reject(error);
  }
);


// --- Authentication API ------------------------------------------------------

/**
 * POST /api/auth/login
 * @param {{ email: string, password: string }} credentials
 * @returns {{ access_token: string, user: object }}
 */
export const login = (credentials) =>
  api.post("v1/auth/login", credentials);

/**
 * POST /api/auth/register
 * @param {{ name: string, email: string, password: string, role?: string }} data
 */
export const register = (data) =>
  api.post("v1/auth/register", data);

/**
 * GET /api/auth/me -- returns the currently authenticated user's profile
 * @param {string} token -- pass explicitly for page-load session restoration
 */
export const getMe = (token) =>
  api.get("v1/auth/me", { params: { token } });



/**
 * POST /api/v1/password/forgot
 * Send OTP for password reset
 * @param {{ email: string }} payload
 */
export const sendResetOtp = (payload) =>
  api.post("v1/password/forgot", payload);

/**
 * POST /api/v1/password/verify-otp
 * Verify OTP and reset password in a single call.
 * The backend verifies the OTP and updates the password atomically in one
 * request — there is no separate "reset password" step/endpoint, so this
 * payload must include new_password up front.
 * @param {{ email: string, otp: string, new_password: string }} payload
 */
export const verifyResetOtp = (payload) =>
  api.post("v1/password/verify-otp", payload);


// --- Accidents API -----------------------------------------------------------

/**
 * GET /api/accidents/
 * @param {{ status?: string, skip?: number, limit?: number }} params
 * @returns {Array} list of accident objects
 */
export const getAccidents = (params = {}) =>
  api.get("v1/accidents/", { params });

/**
 * GET /api/accidents/:id
 */
export const getAccident = (id) =>
  api.get(`v1/accidents/${id}`);

/**
 * PATCH /api/accidents/:id
 * Partial update -- only include fields you want to change
 * @param {{ status?: string, severity?: string, description?: string }} data
 */
export const updateAccident = (id, data) =>
  api.patch(`v1/accidents/${id}`, data);

/**
 * DELETE /api/accidents/:id  (admin only)
 */
export const deleteAccident = (id) =>
  api.delete(`v1/accidents/${id}`);


// --- Traffic Signals API -----------------------------------------------------

/**
 * GET /api/traffic/signals -- all signals with current mode
 */
export const getSignals = () =>
  api.get("v1/traffic/signals");

/**
 * POST /api/traffic/signals/:signalId/emergency
 * Switch a signal to EMERGENCY (green corridor) mode
 */
export const activateEmergency = (signalId) =>
  api.post(`v1/traffic/signals/${signalId}/emergency`);

/**
 * POST /api/traffic/signals/:signalId/reset
 * Return a signal to normal AUTO mode
 */
export const resetSignal = (signalId) =>
  api.post(`v1/traffic/signals/${signalId}/reset`);

/**
 * POST /api/traffic/green-corridor
 * Compute route and activate all signals along it
 */
export const createGreenCorridor = (accidentId, hospitalId) =>
  api.post("v1/traffic/green-corridor", null, {
    params: { accident_id: accidentId, hospital_id: hospitalId },
  });

/**
 * POST /api/traffic/reset-corridor -- reset all emergency signals to auto
 */
export const resetCorridor = () =>
  api.post("v1/traffic/reset-corridor");


// --- Analytics API -----------------------------------------------------------

/**
 * GET /api/analytics/summary -- KPI numbers for summary cards
 * @returns {{ total_today, active_incidents, resolved_today, avg_response_time_minutes }}
 */
export const getSummary = () =>
  api.get("v1/analytics/summary");

/**
 * GET /api/analytics/severity-breakdown -- pie chart data
 * @returns {Array<{ severity: string, count: number }>}
 */
export const getSeverityBreakdown = () =>
  api.get("v1/analytics/severity-breakdown");

/**
 * GET /api/analytics/trends -- line chart data
 * @param {number} days -- lookback window (7, 14, or 30)
 * @returns {Array<{ date: string, count: number }>}
 */
export const getTrends = (days = 7) =>
  api.get("v1/analytics/trends", { params: { days } });

/**
 * GET /api/analytics/hotspots -- top accident-prone locations
 */
export const getHotspots = (limit = 10) =>
  api.get("v1/analytics/hotspots", { params: { limit } });

export default api;
