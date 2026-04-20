/**
 * FILE: frontend/src/utils/helpers.js
 * ==========================================
 * Shared Utility Functions & Constants
 * ==========================================
 *
 * WHY A UTILS FILE?
 *   Utility functions that are used across multiple components live here.
 *   This avoids duplication (DRY — Don't Repeat Yourself) and makes it
 *   easy to update a formatting rule in one place.
 *
 * CONSTANTS vs MAGIC STRINGS:
 *   Instead of writing "#FF2D2D" in 6 different components, we export
 *   SEVERITY_COLOR and use SEVERITY_COLOR.critical everywhere.
 *   If the design system changes, one edit fixes everything.
 */

import { formatDistanceToNow, format } from "date-fns";

// ─── Severity Styling Maps ────────────────────────────────────────────────────
// Central lookup tables so colour changes propagate everywhere automatically.

/** Maps severity level → primary hex colour */
export const SEVERITY_COLOR = {
  critical: "#FF2D2D",
  high:     "#FF7A00",
  medium:   "#FFD600",
  low:      "#00E676",
};

/** Maps severity level → semi-transparent background for badge chips */
export const SEVERITY_BG = {
  critical: "rgba(255,45,45,0.12)",
  high:     "rgba(255,122,0,0.12)",
  medium:   "rgba(255,214,0,0.12)",
  low:      "rgba(0,230,118,0.12)",
};

/** Maps accident status → display colour */
export const STATUS_COLOR = {
  detected:   "#FF7A00",   // Orange — needs attention
  responding: "#2979FF",   // Blue   — in progress
  resolved:   "#00E676",   // Green  — done
};

/** Maps signal mode → display colour */
export const SIGNAL_MODE_COLOR = {
  auto:      "#00E676",
  emergency: "#FF2D2D",
  manual:    "#FFD600",
};

// ─── Date / Time Formatters ───────────────────────────────────────────────────

/**
 * Returns a human-friendly relative time string.
 * e.g. "5 minutes ago", "2 hours ago"
 *
 * Uses date-fns for locale-aware, reliable date arithmetic.
 * (Native JS date math is error-prone with time zones.)
 *
 * @param {string|Date} dateInput
 * @returns {string}
 */
export const timeAgo = (dateInput) => {
  try {
    return formatDistanceToNow(new Date(dateInput), { addSuffix: true });
  } catch {
    return "unknown time";
  }
};

/**
 * Short readable timestamp.
 * e.g. "14 Apr 13:22:05"
 *
 * @param {string|Date} dateInput
 * @returns {string}
 */
export const shortDateTime = (dateInput) => {
  try {
    return format(new Date(dateInput), "dd MMM HH:mm:ss");
  } catch {
    return "—";
  }
};

// ─── Number Formatters ────────────────────────────────────────────────────────

/**
 * Zero-pad an integer ID for display.
 * e.g. padId(5) → "0005"
 *
 * @param {number} id
 * @param {number} length
 * @returns {string}
 */
export const padId = (id, length = 4) => String(id).padStart(length, "0");

/**
 * Convert a 0-1 float confidence score to a percentage string.
 * e.g. pct(0.924) → "92%"
 *
 * @param {number|null} value
 * @returns {string}
 */
export const pct = (value) =>
  value != null ? `${(value * 100).toFixed(0)}%` : "—";

// ─── Auth Utilities ───────────────────────────────────────────────────────────

/**
 * Read the stored user object from localStorage.
 * Wrapped in try/catch because JSON.parse can throw on corrupt data.
 *
 * @returns {object|null}
 */
export const getStoredUser = () => {
  try {
    const raw = localStorage.getItem("user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

/**
 * Check if the currently logged-in user has the admin role.
 * Used to conditionally show admin-only UI elements.
 *
 * @returns {boolean}
 */
export const isAdmin = () => getStoredUser()?.role === "admin";

// ─── Functional Utilities ─────────────────────────────────────────────────────

/**
 * Debounce — delay a function until N ms after the last call.
 * Useful for search inputs: don't fire an API call on every keystroke,
 * only after the user stops typing for 300ms.
 *
 * Classic closure pattern: the returned function captures `timeout`
 * in its closure, so each debounced function has its own timer.
 *
 * @param {Function} fn
 * @param {number}   ms - Delay in milliseconds
 * @returns {Function}
 *
 * Usage:
 *   const debouncedSearch = debounce((query) => fetchResults(query), 300);
 *   <input onChange={(e) => debouncedSearch(e.target.value)} />
 */
export const debounce = (fn, ms = 300) => {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), ms);
  };
};

/**
 * Clamp — constrain a number within [min, max].
 * e.g. clamp(150, 0, 100) → 100
 *
 * @param {number} value
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export const clamp = (value, min, max) =>
  Math.min(Math.max(value, min), max);

/**
 * Truncate a long string with an ellipsis.
 * e.g. truncate("Long location name here", 20) → "Long location name h…"
 *
 * @param {string} str
 * @param {number} maxLen
 * @returns {string}
 */
export const truncate = (str, maxLen = 50) =>
  str && str.length > maxLen ? `${str.slice(0, maxLen)}…` : (str || "");
