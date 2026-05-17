/**
 * FILE : frontend/src/services/ambulanceApi.js
 * -------------------------
 * All HTTP calls for the ambulance dispatch feature.
 * Follows the same pattern as your existing services/api.js
 * so the codebase stays consistent.
 *
 * Uses your existing axios instance if you export one from api.js.
 * Falls back to plain fetch if not.
 */

// ── If you use axios in your project, replace `request` with:
//    import api from './api';
//    export const ambulanceApi = {
//      register: (data) => api.post('/ambulances/register', data),
//      ...
//    };
//
// ── Plain fetch version (works without any extra dependency):

const BASE = import.meta.env.VITE_API_URL || "/api";

async function request(path, options = {}) {
  const token = localStorage.getItem("access_token");  // matches your JWT storage key
  const res = await fetch(`${BASE}${path}`, {// <- api/ambulances/1
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const ambulanceApi = {
  /** Register a new ambulance unit */
  register: (data) =>
    request("/ambulances/register", { method: "POST", body: JSON.stringify(data) }),

  /** List all ambulances */
  getAll: () => request("/ambulances/"),

  /** Get one ambulance by ID */
  getById: (id) => request(`/ambulances/${id}`),

  /** Push GPS location update (called every ~15 s) */
  updateLocation: (id, lat, lon) =>
    request(`/ambulances/${id}/location`, {
      method: "PUT",
      body: JSON.stringify({ latitude: lat, longitude: lon }),
    }),

  /** Change status manually */
  updateStatus: (id, status) =>
    request(`/ambulances/${id}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),

  /** Get available ambulances near coordinates */
  getNearby: (lat, lon, radiusKm = 20) =>
    request(`/ambulances/nearby?lat=${lat}&lon=${lon}&radius_km=${radiusKm}`),

  /** Manually trigger auto-dispatch */
  dispatch: (lat, lon) =>
    request(`/ambulances/dispatch?lat=${lat}&lon=${lon}`, { method: "POST" }),

  /** Driver accepts the assigned dispatch */
  acceptDispatch: (id) =>
    request(`/ambulances/${id}/accept`, { method: "POST" }),

  /** Driver marks job complete — unit returns to available */
  completeDispatch: (id, accidentId) => {
    const query = accidentId ? `?accident_id=${accidentId}` : "";
    return request(`/ambulances/${id}/complete${query}`, { method: "POST" });
  },
};