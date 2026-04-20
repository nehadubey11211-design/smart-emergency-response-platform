/**
 * FILE: frontend/src/components/TrafficPanel.jsx
 * =====================================================
 * Traffic Signal Control Panel
 * =====================================================
 *
 * Demonstrates:
 *   - setInterval polling for near-real-time data refresh
 *   - Async action handlers with per-item loading state
 *   - Conditional rendering based on signal mode
 *   - Extracting config (MODE_STYLES) from JSX for clean code
 *
 * PER-ITEM LOADING STATE:
 *   Instead of a global "loading" boolean, we track WHICH signal is being
 *   acted on (actionSignalId).  This lets us disable just that signal's
 *   buttons while leaving others interactive.
 *
 *   Pattern:
 *     setActionSignalId("SIG-003")   // disable SIG-003 buttons
 *     await api call
 *     setActionSignalId(null)        // re-enable all buttons
 *
 * INTERVIEW TALKING POINT:
 *   "I used per-item loading state so the user gets visual feedback on
 *   exactly which signal is being changed, without blocking the whole UI."
 */

import { useState, useEffect, useCallback } from "react";
import { Wifi, WifiOff, Zap, RotateCcw, Loader2 } from "lucide-react";

import { getSignals, activateEmergency, resetSignal } from "../services/api";
import { SIGNAL_MODE_COLOR } from "../utils/helpers";

/** Maps signal mode to a display label */
const MODE_LABEL = {
  auto:      "AUTO",
  emergency: "EMERGENCY",
  manual:    "MANUAL",
};

export default function TrafficPanel() {
  const [signals,        setSignals]        = useState([]);
  const [loading,        setLoading]        = useState(true);
  const [actionSignalId, setActionSignalId] = useState(null);  // Which signal is acting

  // ── Fetch signals ────────────────────────────────────────────────────────
  const fetchSignals = useCallback(async () => {
    try {
      const { data } = await getSignals();
      setSignals(data);
    } catch (err) {
      console.error("Failed to fetch signals:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSignals();
    // Refresh every 10 seconds — signals change infrequently
    const interval = setInterval(fetchSignals, 10000);
    return () => clearInterval(interval);
  }, [fetchSignals]);

  // ── Action handlers ──────────────────────────────────────────────────────
  const handleEmergency = async (signalId) => {
    setActionSignalId(signalId);
    try {
      await activateEmergency(signalId);
      await fetchSignals();  // Re-fetch to show updated mode
    } catch (err) {
      console.error("Emergency activation failed:", err);
    } finally {
      setActionSignalId(null);
    }
  };

  const handleReset = async (signalId) => {
    setActionSignalId(signalId);
    try {
      await resetSignal(signalId);
      await fetchSignals();
    } catch (err) {
      console.error("Signal reset failed:", err);
    } finally {
      setActionSignalId(null);
    }
  };

  if (loading) {
    return (
      <div className="panel p-4">
        <p className="text-xs text-center py-6" style={{ color: "var(--text-muted)" }}>
          Loading signals…
        </p>
      </div>
    );
  }

  return (
    <div className="panel p-4">
      {/* Header */}
      <h2
        className="text-xs font-bold uppercase tracking-widest mb-4"
        style={{ color: "var(--text-muted)", fontFamily: "'Barlow Condensed', sans-serif" }}
      >
        Traffic Signals
        <span className="ml-2 normal-case font-normal">({signals.length})</span>
      </h2>

      {/* Signal list */}
      <div className="flex flex-col gap-2">
        {signals.length === 0 && (
          <p className="text-xs py-4 text-center" style={{ color: "var(--text-muted)" }}>
            No signals registered.
            <br />Add rows to the traffic_signals table via seed.sql.
          </p>
        )}

        {signals.map((signal) => {
          const mode  = signal.current_mode;
          const color = SIGNAL_MODE_COLOR[mode] || "#888";
          const busy  = actionSignalId === signal.signal_id;

          return (
            <div
              key={signal.signal_id}
              className="flex items-center justify-between rounded-md px-3 py-2"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              {/* Signal info */}
              <div className="flex items-center gap-2 min-w-0">
                {/* Online/offline indicator */}
                {signal.is_online
                  ? <Wifi    size={12} style={{ color: "#00E676", flexShrink: 0 }} aria-label="Online" />
                  : <WifiOff size={12} style={{ color: "var(--text-dim)", flexShrink: 0 }} aria-label="Offline" />
                }
                <div className="min-w-0">
                  <div className="text-xs font-bold truncate">{signal.signal_id}</div>
                  <div
                    className="text-xs truncate"
                    style={{ color: "var(--text-muted)" }}
                    title={signal.location}
                  >
                    {signal.location}
                  </div>
                </div>
              </div>

              {/* Mode badge + action buttons */}
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {/* Current mode badge */}
                <span
                  className="text-xs px-2 py-0.5 rounded"
                  style={{
                    color,
                    background:  `${color}18`,
                    fontFamily:  "'Barlow Condensed', sans-serif",
                    letterSpacing: "0.05em",
                    minWidth: "70px",
                    textAlign: "center",
                  }}
                >
                  {MODE_LABEL[mode] || mode.toUpperCase()}
                </span>

                {/* Activate emergency button (hidden in emergency mode) */}
                {mode !== "emergency" && signal.is_online && (
                  <button
                    disabled={busy}
                    onClick={() => handleEmergency(signal.signal_id)}
                    aria-label={`Activate emergency mode on ${signal.signal_id}`}
                    title="Activate Emergency Mode"
                    className="p-1 rounded transition-opacity hover:opacity-80 disabled:opacity-40"
                    style={{ background: "rgba(255,45,45,0.15)", color: "#FF2D2D" }}
                  >
                    {busy ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
                  </button>
                )}

                {/* Reset button (hidden in auto mode) */}
                {mode !== "auto" && (
                  <button
                    disabled={busy}
                    onClick={() => handleReset(signal.signal_id)}
                    aria-label={`Reset ${signal.signal_id} to auto mode`}
                    title="Reset to Auto"
                    className="p-1 rounded transition-opacity hover:opacity-80 disabled:opacity-40"
                    style={{ background: "rgba(0,230,118,0.1)", color: "#00E676" }}
                  >
                    {busy ? <Loader2 size={11} className="animate-spin" /> : <RotateCcw size={11} />}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
