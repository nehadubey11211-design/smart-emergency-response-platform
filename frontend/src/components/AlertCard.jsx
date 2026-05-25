/**
 * FILE: frontend/src/components/AlertCard.jsx
 * ==================================================
 * Accident Alert Card — Reusable Incident Display
 * ==================================================
 *
 * COMPONENT DESIGN:
 *   This is a "presentational" component (also called a "dumb" component).
 *   It receives all data via props and only knows HOW to display it.
 *   It does NOT fetch its own data — that's the parent's responsibility.
 *
 *   Benefits:
 *     - Easy to test: pass any accident object, see the output
 *     - Easy to reuse: works on Dashboard, History, anywhere
 *     - Easy to reason about: no side effects, no internal API calls
 *
 *   The ONLY side effect is the handleResolve action, which calls updateAccident
 *   and then invokes onUpdate() to tell the parent to refresh its data.
 *   This is the "lifting state up" pattern — the parent owns the data,
 *   the child requests changes via callbacks.
 *
 * PROP TYPES (what this component expects):
 *   accident  {object}   — The accident data object from the API
 *   onUpdate  {function} — Called after a status change (parent refreshes data)
 *
 * ACCESSIBILITY:
 *   - role="article" on the card for semantic HTML
 *   - aria-label on buttons for screen readers
 *   - Colour is NOT the only indicator of severity (also shows text label)
 *
 * INTERVIEW TALKING POINT:
 *   "AlertCard is a pure presentational component. It receives data via props
 *   and communicates changes upward via callbacks — following React's
 *   unidirectional data flow. This makes it trivial to test in isolation."
 */

import { useState } from "react";
import { MapPin, Clock, Camera, CheckCircle, Loader2, Zap } from "lucide-react";
import PropTypes from 'prop-types';

import { updateAccident, createGreenCorridor } from "../services/api";
import { SEVERITY_COLOR, SEVERITY_BG, timeAgo, padId, pct } from "../utils/helpers";
/**
 * @typedef {Object} Accident
 * @property {number} id
 * @property {string} location
 * @property {string} severity
 * @property {string} status
 */
/**
 * @param {{
 *  accident: Accident,
 *  onUpdate: Function
 * }} props
 */

/**
 * @param {object}   props.accident  - Accident object from the API
 * @param {Function} props.onUpdate  - Callback to trigger parent data refresh
 */
export default function AlertCard({ accident, onUpdate }) {
  // ── Local UI state (not shared with parent) ─────────────────────────────
  const [resolving,   setResolving]   = useState(false);   // Resolve button loading
  const [corridoring, setCorridoring] = useState(false);   // Green corridor loading

  const isActive  = accident.status !== "resolved";
  const color     = SEVERITY_COLOR[accident.severity] || "#888";
  const bgColor   = SEVERITY_BG[accident.severity]    || "rgba(136,136,136,0.1)";

  // ── Action Handlers ─────────────────────────────────────────────────────

  /**
   * Mark this incident as resolved.
   *
   * Pattern: optimistic UI would update state immediately before the API call.
   * We use the simpler "pessimistic" approach: wait for the API to confirm,
   * then ask the parent to refresh. Good enough for an ops dashboard.
   */
  const handleResolve = async () => {
    setResolving(true);
    try {
      await updateAccident(accident.id, { status: "resolved" });
      onUpdate?.();  // Optional chaining: safe even if onUpdate wasn't passed
    } catch (err) {
      console.error("Failed to resolve accident:", err);
      alert("Failed to mark as resolved. Please try again.");
    } finally {
      setResolving(false);
    }
  };

  /**
   * Activate a green corridor from this incident to a hardcoded demo hospital.
   * In production: show a modal to select the nearest available hospital.
   */
  const handleGreenCorridor = async () => {
    setCorridoring(true);
    try {
      await createGreenCorridor(accident.id, "HOSP-001");
      alert("✅ Green corridor activated! All signals along the route are now green.");
    } catch (err) {
      console.error("Failed to create green corridor:", err);
      alert("Failed to activate green corridor.");
    } finally {
      setCorridoring(false);
    }
  };

  return (
    <article
      role="article"
      aria-label={`Accident at ${accident.location}, severity: ${accident.severity}`}
      className="card relative overflow-hidden transition-all duration-300"
      style={{
        borderColor: isActive ? color : "var(--border)",
        // Pulse ring animation on active critical/high incidents
        boxShadow: isActive && accident.severity === "critical"
          ? `0 0 0 0 ${color}60`
          : "none",
        opacity: isActive ? 1 : 0.65,
      }}
    >
      {/* ── Left severity colour strip ────────────────────────────────── */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1"
        style={{ background: color }}
        aria-hidden="true"
      />

      <div className="pl-3">
        {/* ── Header Row ────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between mb-2">

          {/* Severity badge + ID */}
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-bold px-2 py-0.5 rounded uppercase tracking-wider"
              style={{
                color:      color,
                background: bgColor,
                fontFamily: "'Barlow Condensed', sans-serif",
              }}
            >
              {accident.severity}
            </span>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              #{padId(accident.id)}
            </span>
          </div>

          {/* Status badge */}
          <span
            className="text-xs uppercase tracking-wider"
            style={{
              color: isActive ? color : "var(--green)",
              fontFamily: "monospace",
            }}
          >
            {accident.status}
          </span>
        </div>

        {/* ── Location ──────────────────────────────────────────────────── */}
        <div className="flex items-center gap-1.5 mb-2">
          <MapPin size={12} style={{ color }} aria-hidden="true" />
          <span className="text-sm font-medium" style={{ color: "#E0EAF8" }}>
            {accident.location}
          </span>
        </div>

        {/* ── Meta Row ──────────────────────────────────────────────────── */}
        <div
          className="flex items-center gap-4 text-xs mb-3"
          style={{ color: "var(--text-muted)" }}
        >
          {/* Time since detection */}
          <span className="flex items-center gap-1">
            <Clock size={10} aria-hidden="true" />
            {timeAgo(accident.detected_at)}
          </span>

          {/* Camera ID if available */}
          {accident.camera_id && (
            <span className="flex items-center gap-1">
              <Camera size={10} aria-hidden="true" />
              {accident.camera_id}
            </span>
          )}

          {/* AI confidence score */}
          {accident.confidence != null && (
            <span title="AI model confidence">
              AI: {pct(accident.confidence)}
            </span>
          )}
        </div>

        {/* ── Optional description ──────────────────────────────────────── */}
        {accident.description && (
          <p
            className="text-xs mb-3 italic"
            style={{ color: "var(--text-muted)" }}
          >
            {accident.description}
          </p>
        )}

        {/* ── Action Buttons (only on active incidents) ─────────────────── */}
        {isActive && (
          <div className="flex gap-2 flex-wrap">

            {/* Resolve button */}
            <button
              onClick={handleResolve}
              disabled={resolving}
              aria-label="Mark this incident as resolved"
              className="flex items-center gap-1.5 text-xs px-3 py-1 rounded
                         transition-all duration-200 disabled:opacity-50"
              style={{
                background: "rgba(0,230,118,0.1)",
                border:     "1px solid rgba(0,230,118,0.3)",
                color:      "#00E676",
              }}
            >
              {resolving ? (
                <><Loader2 size={11} className="animate-spin" aria-hidden="true" /> Resolving…</>
              ) : (
                <><CheckCircle size={11} aria-hidden="true" /> Mark Resolved</>
              )}
            </button>

            {/* Green Corridor button */}
            <button
              onClick={handleGreenCorridor}
              disabled={corridoring}
              aria-label="Activate green corridor for ambulance"
              className="flex items-center gap-1.5 text-xs px-3 py-1 rounded
                         transition-all duration-200 disabled:opacity-50"
              style={{
                background: "rgba(255,45,45,0.1)",
                border:     "1px solid rgba(255,45,45,0.3)",
                color:      "var(--red)",
              }}
            >
              {corridoring ? (
                <><Loader2 size={11} className="animate-spin" aria-hidden="true" /> Activating…</>
              ) : (
                <><Zap size={11} aria-hidden="true" /> Green Corridor</>
              )}
            </button>
          </div>
        )}
      </div>
    </article>
  );
  AlertCard.propTypes = {
  accident: PropTypes.shape({
    id: PropTypes.number.isRequired,
    location: PropTypes.string.isRequired,
    severity: PropTypes.string,
    status: PropTypes.string
  }).isRequired,

  onUpdate: PropTypes.func
};
}
