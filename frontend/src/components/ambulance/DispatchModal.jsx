/**
 * FILE : frontend/src/components/ambulance/DispatchModal.jsx
 * ----------------------------------------
 * Full-screen overlay shown when a DISPATCH_ALERT arrives.
 * Driver must Accept or Reject before it dismisses.
 *
 * Props:
 *   alert       — the DISPATCH_ALERT payload from WebSocket
 *   onAccept()  — called when driver taps Accept
 *   onReject()  — called when driver taps Reject
 *   loading     — disables buttons while API call is in-flight
 */

export function DispatchModal({ alert, onAccept, onReject, loading }) {
  if (!alert) return null;

  return (
    <div style={{
      position:       "fixed",
      inset:          0,
      background:     "rgba(0,0,0,0.82)",
      zIndex:         1000,
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      backdropFilter: "blur(6px)",
      WebkitBackdropFilter: "blur(6px)",
    }}>
      <div style={{
        background:   "#0f172a",
        border:       "1.5px solid #ef4444",
        borderRadius: 16,
        padding:      "32px 28px",
        width:        "min(460px, 92vw)",
        boxShadow:    "0 0 60px rgba(239,68,68,0.2)",
        animation:    "fadeInScale 0.2s ease",
      }}>

        {/* Title */}
        <p style={{
          textAlign:    "center",
          fontSize:     11,
          letterSpacing:"0.2em",
          color:        "#ef4444",
          fontWeight:   700,
          marginBottom: 6,
        }}>
          EMERGENCY DISPATCH
        </p>
        <h2 style={{
          textAlign:   "center",
          fontSize:    22,
          fontWeight:  700,
          color:       "#fff",
          margin:      "0 0 24px",
        }}>
          🚨 You Have Been Assigned
        </h2>

        {/* Detail grid */}
        <div style={{
          display:             "grid",
          gridTemplateColumns: "1fr 1fr",
          gap:                 10,
          marginBottom:        20,
        }}>
          {[
            { label: "SEVERITY",    value: alert.severity?.toUpperCase(),  color: "#f87171" },
            { label: "CONFIDENCE",  value: `${alert.confidence}%`,         color: "#e2e8f0" },
            { label: "DISTANCE",    value: `${alert.distance_km} km`,      color: "#e2e8f0" },
            { label: "ETA",         value: `${alert.eta_minutes} min`,     color: "#34d399" },
          ].map(({ label, value, color }) => (
            <div key={label} style={{
              background:   "rgba(255,255,255,0.05)",
              borderRadius: 10,
              padding:      "14px 16px",
            }}>
              <p style={{ margin: 0, fontSize: 9, letterSpacing: "0.15em", color: "#6b7280" }}>
                {label}
              </p>
              <p style={{ margin: "6px 0 0", fontSize: 22, fontWeight: 700, color }}>
                {value}
              </p>
            </div>
          ))}
        </div>

        {/* Location */}
        {alert.location && (
          <p style={{
            textAlign:    "center",
            fontSize:     12,
            color:        "#9ca3af",
            marginBottom: 20,
          }}>
            📍 {alert.location}
          </p>
        )}

        {/* Time */}
        <p style={{
          textAlign:    "center",
          fontSize:     11,
          color:        "#4b5563",
          marginBottom: 24,
        }}>
          Detected at {new Date(alert.time_detected || Date.now()).toLocaleTimeString()}
        </p>

        {/* Action buttons */}
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onReject}
            disabled={loading}
            style={{
              flex:         1,
              padding:      "13px",
              background:   "transparent",
              border:       "1px solid rgba(239,68,68,0.4)",
              color:        "#ef4444",
              borderRadius: 10,
              cursor:       "pointer",
              fontSize:     13,
              fontWeight:   600,
              letterSpacing:"0.05em",
              opacity:      loading ? 0.5 : 1,
            }}
          >
            ✕ Reject
          </button>
          <button
            onClick={onAccept}
            disabled={loading}
            style={{
              flex:         2,
              padding:      "13px",
              background:   "rgba(16,185,129,0.15)",
              border:       "1.5px solid #10b981",
              color:        "#10b981",
              borderRadius: 10,
              cursor:       "pointer",
              fontSize:     13,
              fontWeight:   700,
              letterSpacing:"0.05em",
              opacity:      loading ? 0.5 : 1,
            }}
          >
            {loading ? "Confirming..." : "✓ Accept & Navigate"}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes fadeInScale {
          from { opacity: 0; transform: scale(0.95); }
          to   { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}
