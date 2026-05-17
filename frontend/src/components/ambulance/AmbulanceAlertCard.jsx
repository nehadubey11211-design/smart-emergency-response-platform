/**
 * FILE : frontend/src/components/ambulance/AmbulanceAlertCard.jsx
 * --------------------------------------------
 * Presentational component — receives one alert object as a prop,
 * renders it. No state, no side effects, fully reusable.
 *
 * Used by AmbulanceDashboard.jsx inside the alert feed panel.
 */

const TYPE_CONFIG = {
  DISPATCH_ALERT:        { label: "DISPATCHED TO YOU",  color: "#ef4444", bg: "rgba(239,68,68,0.08)"  },
  NEARBY_ACCIDENT_ALERT: { label: "NEARBY ACCIDENT",    color: "#f59e0b", bg: "rgba(245,158,11,0.08)" },
  DISPATCH_ACCEPTED:     { label: "UNIT EN-ROUTE",      color: "#3b82f6", bg: "rgba(59,130,246,0.08)" },
  DISPATCH_COMPLETED:    { label: "JOB COMPLETE",       color: "#10b981", bg: "rgba(16,185,129,0.08)" },
  DEFAULT:               { label: "ALERT",              color: "#6b7280", bg: "rgba(107,114,128,0.08)"},
};

export function AmbulanceAlertCard({ alert, isLatest = false }) {
  const cfg  = TYPE_CONFIG[alert.type] || TYPE_CONFIG.DEFAULT;
  const time = new Date(alert.receivedAt).toLocaleTimeString([], {
    hour:   "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div style={{
      border:       `0.5px solid ${cfg.color}55`,
      background:   isLatest ? cfg.bg : "transparent",
      borderRadius: 10,
      padding:      "12px 14px",
      marginBottom: 8,
      transition:   "background 0.3s",
    }}>
      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <span style={{
          fontSize: 10, fontWeight: 600, letterSpacing: "0.1em",
          color: cfg.color,
        }}>
          {cfg.label}
        </span>
        <span style={{ fontSize: 10, color: "#6b7280" }}>{time}</span>
      </div>

      {/* Severity + confidence */}
      {alert.severity && (
        <p style={{ fontSize: 12, color: "#d1d5db", margin: "3px 0" }}>
          Severity:{" "}
          <strong style={{ color: "#f87171" }}>{alert.severity?.toUpperCase()}</strong>
          {alert.confidence != null && (
            <span style={{ color: "#9ca3af" }}> · {alert.confidence}% confidence</span>
          )}
        </p>
      )}

      {/* Distance + ETA */}
      {alert.distance_km != null && (
        <p style={{ fontSize: 12, color: "#d1d5db", margin: "3px 0" }}>
          Distance:{" "}
          <strong style={{ color: "#34d399" }}>{alert.distance_km} km</strong>
          {alert.eta_minutes != null && (
            <span style={{ color: "#9ca3af" }}> · ETA {alert.eta_minutes} min</span>
          )}
        </p>
      )}

      {/* Location description */}
      {alert.location && (
        <p style={{ fontSize: 11, color: "#6b7280", margin: "5px 0 0", fontStyle: "italic" }}>
          {alert.location}
        </p>
      )}

      {/* Message */}
      {alert.message && (
        <p style={{ fontSize: 11, color: "#9ca3af", margin: "5px 0 0" }}>
          {alert.message}
        </p>
      )}
    </div>
  );
}