/**
 * FILE : frontend/src/hooks/useAmbulanceSocket.js
 * ----------------------------
 * Custom React hook that manages the WebSocket connection to the
 * ambulance dispatch backend.
 *
 * Responsibilities:
 *   - Open / close the WebSocket lifecycle
 *   - Auto-reconnect on disconnect (with delay)
 *   - Keep-alive ping every 25 seconds
 *   - Route incoming messages by type
 *   - Play alert sound for DISPATCH_ALERT messages
 *   - Expose connection state + alert history to components
 *
 * Interview talking point:
 *   Custom hooks encapsulate all stateful logic so the component stays
 *   declarative — AmbulanceDashboard just reads `alerts` and `isConnected`,
 *   it never touches a WebSocket directly.
 */

import { useEffect, useRef, useState, useCallback } from "react";

const protocol =
  window.location.protocol === "https:"
    ? "wss:"
    : "ws:";

const WS_BASE =
  import.meta.env.VITE_WS_URL ||
  `${protocol}//${window.location.host}`;
const RECONNECT_DELAY  = 3_000;   // ms before reconnect attempt
const PING_INTERVAL    = 25_000;  // ms between keep-alive pings
const MAX_ALERT_HISTORY = 50;     // keep last N alerts in state
// Stable alert type set (prevents unnecessary callback recreation)
const ALERT_TYPES = new Set([
  "DISPATCH_ALERT",
  "NEARBY_ACCIDENT_ALERT",
  "DISPATCH_ACCEPTED",
  "DISPATCH_COMPLETED",
]);

export function useAmbulanceSocket(ambulanceId) {
  const wsRef        = useRef(null);
  const pingRef      = useRef(null);
  const reconnectRef = useRef(null);
  const connectRef   = useRef(null);

  const [isConnected,      setIsConnected]      = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [lastAlert,        setLastAlert]        = useState(null);
  const [alerts,           setAlerts]           = useState([]);

  // ── Pure helpers ──────────────────────────────────────────────────────

   const playAlertBeep = useCallback(() => {
  try {
    const ctx =
      new (window.AudioContext || window.webkitAudioContext)();

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.frequency.value = 880;
    osc.type = "square";

    gain.gain.setValueAtTime(0.35, ctx.currentTime);

    gain.gain.exponentialRampToValueAtTime(
      0.001,
      ctx.currentTime + 0.9
    );

    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.9);

    //  Cleanup AudioContext after sound ends
    osc.onended = () => {
      ctx.close();
    };

  } catch (_) {
    // Audio may be blocked before user interaction
  }
}, []);

  const appendAlert = useCallback((data) => {
    const stamped = { ...data, receivedAt: new Date().toISOString() };
    setLastAlert(stamped);
    setAlerts((prev) => [stamped, ...prev].slice(0, MAX_ALERT_HISTORY));
  }, []);

  // ── Message router ────────────────────────────────────────────────────

  const handleMessage = useCallback((data) => {
    if (!ALERT_TYPES.has(data.type)) return;
    if (data.type === "DISPATCH_ALERT" && data.sound) {
      playAlertBeep();
       // Browser notification
      if (Notification.permission === "granted") {
          new Notification("🚨 Emergency Dispatch", {
            body: `Accident reported near ${data.location || "your area"}`,
            icon: "/ambulance.png",
        });
      }
    }
    appendAlert(data);
  }, [playAlertBeep, appendAlert]);

  // ── Connection lifecycle ──────────────────────────────────────────────

  const connect = useCallback(() => {
    if (!ambulanceId) return;
    const token = localStorage.getItem("token") || sessionStorage.getItem("token");

    if (!token) {
      console.warn("[AmbulanceWS] No auth token — skipping connection");
      return;
    }

    const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
    const url = `${WS_BASE}/api/v1/ambulances/ws/${ambulanceId}?token=${token}`;
    const ws  = new WebSocket(url);
    wsRef.current = ws;
    setConnectionStatus("connecting");

    ws.onopen = () => {
      setIsConnected(true);
      setConnectionStatus("connected");
      console.info(`[AmbulanceWS] Connected as unit ${ambulanceId}`);

      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = ({ data }) => {
      try {
        handleMessage(JSON.parse(data));
      } catch (e) {
        console.warn("[AmbulanceWS] Failed to parse message:", e);
      }
    };

   ws.onclose = () => {

  setIsConnected(false);
  setConnectionStatus("disconnected");

  clearInterval(pingRef.current);

  reconnectRef.current = setTimeout(() => {

    connectRef.current?.();

  }, RECONNECT_DELAY);

  console.info(
    `[AmbulanceWS] Disconnected — reconnecting in ${RECONNECT_DELAY}ms`
  );
};
    ws.onerror = () => setConnectionStatus("error");
     
  }, [ambulanceId, handleMessage]);

  const sendMessage = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);
  // Always keep latest connect function reference
useEffect(() => {
  connectRef.current = connect;
}, [connect]);

  useEffect(() => {

  connect();

  const handleVisibility = () => {

    if (
      document.visibilityState === "visible" &&
      wsRef.current?.readyState !== WebSocket.OPEN
    ) {
      connect();
    }
  };

  document.addEventListener(
    "visibilitychange",
    handleVisibility
  );

  return () => {

    document.removeEventListener(
      "visibilitychange",
      handleVisibility
    );

    clearInterval(pingRef.current);
    clearTimeout(reconnectRef.current);

    wsRef.current?.close();
  };

}, [connect]);

  return { isConnected, connectionStatus, lastAlert, alerts, sendMessage };
}
