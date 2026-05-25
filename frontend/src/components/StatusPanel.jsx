/**
 * FILE: frontend/src/components/StatusPanel.jsx
 * ====================================================
 * System Status Bar — Live Clock, WebSocket Status, Last Event
 * ====================================================
 *
 * Demonstrates:
 *   - setInterval for a live clock (with proper cleanup)
 *   - Polling a singleton service's state (socketService.isConnected)
 *   - Subscribing to WebSocket events with cleanup on unmount
 *
 * CLEANUP PATTERN (critical React concept):
 *   Every useEffect that sets up a side effect (interval, event listener,
 *   WebSocket subscription) MUST return a cleanup function.
 *   If you forget, the effect runs forever even after the component unmounts,
 *   causing: memory leaks, errors on unmounted components, duplicate listeners.
 *
 * INTERVIEW TALKING POINT:
 *   "I always return cleanup functions from useEffect. For example, here I
 *   clear the interval and unsubscribe from WebSocket events on unmount.
 *   Without this, the interval would keep running and setState would be
 *   called on an unmounted component, causing a React warning and memory leak."
 */

import { useState, useEffect } from "react";
import { Activity, Radio, Server } from "lucide-react";

import socketService from "../services/socket";

export default function StatusPanel() {
  const [wsConnected,  setWsConnected]  = useState(false);
  const [lastEvent,    setLastEvent]    = useState(null);
  const [currentTime,  setCurrentTime]  = useState(new Date());
  const [apiHealthy, setApiHealthy] = useState(null);

  useEffect(() => {
    // ── Connect WebSocket if not already connected ──────────────────────
    socketService.connect();

    // ── Subscribe to new accident events ────────────────────────────────
    const handleNewAccident = (data) => {
      setLastEvent({ location: data.location, time: new Date() });
    };
    socketService.on("NEW_ACCIDENT", handleNewAccident);

    // ── Poll WebSocket readyState every 2s ──────────────────────────────
    // We poll instead of subscribing because there's no "connected" event
    // exposed by our SocketService — only the browser's WS readyState.
    const wsCheck = setInterval(() => {
      setWsConnected(socketService.isConnected);
    }, 2000);

    const checkApiHealth = async () => {
  try {
    const response = await fetch("v1/health");

    if (response.ok) {
      setApiHealthy(true);
    } else {
      setApiHealthy(false);
    }
  } catch {
    setApiHealthy(false);
  }
};

// Initial check
checkApiHealth();

// Repeat every 30 seconds
const apiHealthInterval = setInterval(checkApiHealth, 30000);

    // ── Live clock: update every second ─────────────────────────────────
    const clock = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    // ── Cleanup: runs when component unmounts ────────────────────────────
    return () => {
      socketService.off("NEW_ACCIDENT", handleNewAccident);  // Unsubscribe
      clearInterval(wsCheck);                                 // Stop WS polling
      clearInterval(clock);    
      clearInterval(apiHealthInterval);                               // Stop clock
    };
  }, []);  // Empty deps = run once on mount, cleanup on unmount

  return (
    <div
      className="flex items-center gap-5 px-4 py-2 rounded-md text-xs"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      role="status"
      aria-label="System status"
    >
      {/* Live clock */}
      <span className="font-mono" style={{ color: "var(--text-muted)" }}>
        {currentTime.toLocaleTimeString()}
      </span>

      {/* WebSocket connection indicator */}
      <span
        className="flex items-center gap-1.5"
        style={{ color: wsConnected ? "#00E676" : "#FF2D2D" }}
        title={wsConnected ? "Real-time feed connected" : "Disconnected — reconnecting…"}
      >
        <Radio size={11} aria-hidden="true" />
        {wsConnected ? "LIVE" : "OFFLINE"}
      </span>

      {/* API health indicator */}
      <span
        className="flex items-center gap-1.5"
        style={{
          color:
            apiHealthy === null
              ? "#FFD600"
              : apiHealthy
              ? "#00E676"
              : "#FF2D2D"
        }}
        title={
          apiHealthy === null
            ? "Checking API..."
            : apiHealthy
            ? "Backend API is reachable"
            : "Backend API is down"
        }
      >
        <Server size={11} aria-hidden="true" />

        {apiHealthy === null
          ? "CHECKING API"
          : apiHealthy
          ? "API"
          : "API OFFLINE"}
      </span>

      {/* Last received WebSocket event */}
      {lastEvent && (
        <span
          className="flex items-center gap-1.5 ml-auto"
          style={{ color: "#FF7A00" }}
        >
          <Activity size={11} aria-hidden="true" />
          Last: {lastEvent.location} at {lastEvent.time.toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}
