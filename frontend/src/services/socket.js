/**
 * FILE: frontend/src/services/socket.js
 * ============================================
 * WebSocket Client — Real-time Incident Alerts
 * ============================================
 *
 * WHY WEBSOCKETS?
 *   HTTP is request/response — the client must ASK before the server answers.
 *   WebSocket is full-duplex — the server can PUSH data to the client at any time.
 *
 *   For emergency alerts, this matters:
 *     HTTP polling every 5s → worst-case 5s delay
 *     WebSocket push        → ~50ms delay (network latency only)
 *
 * DESIGN PATTERN — Event Emitter / Pub-Sub:
 *   Components "subscribe" to event types using .on(type, callback).
 *   When a message arrives, the service dispatches it to all subscribers.
 *   Components clean up with .off() when they unmount to prevent memory leaks.
 *
 *   This is the same pattern used by Node.js EventEmitter, browser DOM events,
 *   and most real-time libraries (Socket.IO, etc.)
 *
 * SINGLETON PATTERN:
 *   The SocketService instance is created once and exported.
 *   Every component that imports this file gets the SAME instance,
 *   sharing a single WebSocket connection. This is efficient —
 *   one connection handles unlimited message types.
 *
 * AUTO-RECONNECT:
 *   Networks drop. The onclose handler automatically reconnects after 3 seconds.
 *   This is called "exponential backoff" when the delay increases on each retry.
 *
 * INTERVIEW TALKING POINT:
 *   "I implemented the WebSocket client as a singleton with a pub-sub listener
 *   registry. Any React component can subscribe to specific event types without
 *   knowing about the other subscribers — they're fully decoupled."
 */

const WS_URL =
  import.meta.env.VITE_WS_URL ||
  "ws://localhost:8000/api/accidents/ws";

class SocketService {
  constructor() {
    /** @type {WebSocket|null} The active WebSocket connection */
    this.socket = null;

    /**
     * Listener registry: maps event type → array of callback functions
     * Example: { "NEW_ACCIDENT": [fn1, fn2], "*": [fn3] }
     * @type {Record<string, Function[]>}
     */
    this.listeners = {};

    /** Reconnection attempt counter (for exponential backoff) */
    this._reconnectAttempts = 0;

    /** Whether connect() has been called (prevents multiple connections) */
    this._intentionalDisconnect = false;
  }

  // ─── Connection Management ─────────────────────────────────────────────────

  connect() {
    // Guard: don't open a second connection if one is already open/connecting
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
       this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this._intentionalDisconnect = false;
    console.log(`🔗 Connecting to WebSocket: ${WS_URL}`);
    this.socket = new WebSocket(WS_URL);

    // ── Event Handlers ─────────────────────────────────────────────────────

    this.socket.onopen = () => {
      console.log("✅ WebSocket connected — live incident feed active");
      this._reconnectAttempts = 0;  // Reset backoff counter on successful connect
    };

    this.socket.onmessage = (event) => {
      /**
       * Parse incoming JSON message and dispatch to registered listeners.
       *
       * Expected message format from the backend:
       * {
       *   "type": "NEW_ACCIDENT",
       *   "data": { "id": 5, "location": "...", "severity": "high" }
       * }
       */
      try {
        const message = JSON.parse(event.data);

        // Dispatch to listeners registered for this specific event type
        const typeListeners = this.listeners[message.type] || [];
        typeListeners.forEach((callback) => {
          try {
            callback(message.data);
          } catch (err) {
            console.error(`Error in listener for ${message.type}:`, err);
          }
        });

        // Dispatch to wildcard listeners (subscribed to ALL event types)
        const wildcardListeners = this.listeners["*"] || [];
        wildcardListeners.forEach((callback) => {
          try {
            callback(message);
          } catch (err) {
            console.error("Error in wildcard listener:", err);
          }
        });
      } catch (parseError) {
        console.error("Failed to parse WebSocket message:", parseError);
      }
    };

    this.socket.onclose = (event) => {
      console.log(
        `🔌 WebSocket closed (code: ${event.code}, reason: ${event.reason || "none"})`
      );

      // Don't reconnect if WE closed it intentionally
      if (this._intentionalDisconnect) return;

      // Exponential backoff: wait 3s, then 6s, then 12s … up to 30s max
      const delay = Math.min(3000 * Math.pow(2, this._reconnectAttempts), 30000);
      this._reconnectAttempts++;
      console.log(`🔄 Reconnecting in ${delay / 1000}s (attempt ${this._reconnectAttempts})...`);
      setTimeout(() => this.connect(), delay);
    };

    this.socket.onerror = (error) => {
      // Most WS errors close the connection — onclose will handle reconnect
      console.error("WebSocket error:", error);
    };
  }

  disconnect() {
    /**
     * Intentionally close the connection (e.g. on logout).
     * Sets a flag so the onclose handler doesn't try to reconnect.
     */
    this._intentionalDisconnect = true;
    this.socket?.close(1000, "Client disconnecting");
    this.socket = null;
    console.log("🔌 WebSocket disconnected intentionally");
  }

  // ─── Pub-Sub API ───────────────────────────────────────────────────────────

  /**
   * Subscribe to a specific event type.
   *
   * @param {string}   type     - Event type (e.g. "NEW_ACCIDENT") or "*" for all
   * @param {Function} callback - Called with message.data when event arrives
   *
   * Usage in a React component:
   *   useEffect(() => {
   *     const handler = (data) => setAlerts(prev => [data, ...prev]);
   *     socketService.on("NEW_ACCIDENT", handler);
   *     return () => socketService.off("NEW_ACCIDENT", handler);  // cleanup!
   *   }, []);
   */
  on(type, callback) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    // Prevent duplicate registrations of the same function
    if (!this.listeners[type].includes(callback)) {
      this.listeners[type].push(callback);
    }
  }

  /**
   * Unsubscribe a specific callback from an event type.
   * IMPORTANT: Always call this in useEffect cleanup to prevent memory leaks.
   *
   * @param {string}   type     - Event type to unsubscribe from
   * @param {Function} callback - The exact function reference passed to .on()
   */
  off(type, callback) {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter(
        (fn) => fn !== callback
      );
    }
  }

  /**
   * Check if the WebSocket is currently connected.
   * Useful for rendering connection status indicators.
   * @returns {boolean}
   */
  get isConnected() {
    return this.socket?.readyState === WebSocket.OPEN;
  }
}

// ─── Singleton Export ─────────────────────────────────────────────────────────
// Every file that imports socketService gets the SAME instance.
// One WebSocket connection is shared across the entire React app.
const socketService = new SocketService();
export default socketService;
