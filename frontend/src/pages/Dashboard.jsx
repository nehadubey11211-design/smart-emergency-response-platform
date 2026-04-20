/**
 * FILE: frontend/src/pages/Dashboard.jsx
 * =============================================
 * Operations Dashboard — Live Incident Feed
 * =============================================
 *
 * This is a "container" component (also called a "smart" component).
 * It owns the data-fetching logic and passes data down to presentational
 * children (AlertCard, TrafficPanel, AnalyticsCard).
 *
 * CONCEPTS DEMONSTRATED:
 *
 *   1. Custom hooks for data fetching (useAccidents)
 *      Component stays clean — it just reads { data, loading, refetch }
 *
 *   2. WebSocket integration
 *      socketService.on() subscribes to real-time events.
 *      The cleanup function (return () => ...) prevents memory leaks.
 *
 *   3. Derived state
 *      Instead of storing filtered data in state, we compute it from
 *      existing state on every render (filtered = data.filter(...)).
 *      This avoids state synchronisation bugs.
 *
 *   4. useCallback for stable references
 *      handleRefetch is memoised so it doesn't change on every render,
 *      preventing unnecessary effect re-runs in children.
 *
 * DATA FLOW:
 *   API → useAccidents → accidents state
 *   WS  → NEW_ACCIDENT event → trigger refetch + show flash banner
 *   Child components receive data as props and report changes via callbacks
 *
 * INTERVIEW TALKING POINT:
 *   "The dashboard subscribes to WebSocket events and also polls via a
 *   custom hook. When a WS event arrives, it triggers a refetch to get
 *   the complete record (the WS payload is intentionally minimal to
 *   reduce bandwidth)."
 */

import { useState, useEffect, useCallback } from "react";
import { AlertTriangle, CheckCircle2, Clock, Activity, BellRing } from "lucide-react";

import { useAccidents }  from "../hooks/useAccidents";
import socketService      from "../services/socket";
import { getSummary }     from "../services/api";

import AlertCard     from "../components/AlertCard.jsx";
import TrafficPanel  from "../components/TrafficPanel.jsx";
import StatusPanel   from "../components/StatusPanel.jsx";
import AnalyticsCard from "../components/AnalyticsCard.jsx";

export default function Dashboard() {
  // ── Data from custom hook ─────────────────────────────────────────────
  // Fetch active incidents and auto-refresh every 30s
  const { data: accidents, loading, refetch } = useAccidents({}, 30000);

  // ── Local UI state ────────────────────────────────────────────────────
  const [filter,    setFilter]    = useState("active");  // "active" | "all"
  const [summary,   setSummary]   = useState(null);
  const [newAlert,  setNewAlert]  = useState(false);     // Flash banner state

  // ── Fetch summary cards ───────────────────────────────────────────────
  useEffect(() => {
    getSummary()
      .then((res) => setSummary(res.data))
      .catch((err) => console.error("Summary fetch failed:", err));
  }, [accidents]);  // Re-fetch summary when the accident list changes

  // ── WebSocket: react to live accidents ───────────────────────────────
  useEffect(() => {
    const handleNewAccident = () => {
      // Show the flash banner for 4 seconds
      setNewAlert(true);
      setTimeout(() => setNewAlert(false), 4000);

      // Refresh the accident list to include the new record
      refetch();
    };

    socketService.on("NEW_ACCIDENT", handleNewAccident);

    // Cleanup: unsubscribe when component unmounts
    return () => socketService.off("NEW_ACCIDENT", handleNewAccident);
  }, [refetch]);

  // ── Derived state: apply filter without extra state ───────────────────
  // Computing filtered data directly in render is cleaner than storing
  // it in a separate useState — no risk of stale/out-of-sync state.
  const filteredAccidents =
    filter === "active"
      ? accidents.filter((a) => a.status !== "resolved")
      : accidents;

  return (
    <div className="page-enter max-w-7xl mx-auto">

      {/* ── Page Header ──────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-5 gap-4 flex-wrap">
        <div>
          <h1
            className="text-2xl font-bold"
            style={{ fontFamily: "'Barlow Condensed', sans-serif", letterSpacing: "0.04em" }}
          >
            OPERATIONS DASHBOARD
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            Real-time incident monitoring and traffic signal control
          </p>
        </div>
        <StatusPanel />
      </div>

      {/* ── Real-time Alert Banner ────────────────────────────────────── */}
      {/*
       * Conditional rendering: only mount this element when a new alert arrives.
       * React adds/removes it from the DOM — no invisible empty divs.
       */}
      {newAlert && (
        <div
          role="alert"
          aria-live="assertive"
          className="flex items-center gap-2 px-4 py-2 rounded-md mb-4 text-sm font-bold"
          style={{
            background: "rgba(255,45,45,0.15)",
            border:     "1px solid var(--red)",
            color:      "var(--red)",
          }}
        >
          <BellRing size={14} className="animate-bounce" aria-hidden="true" />
          🚨 NEW ACCIDENT DETECTED — Dashboard refreshed automatically
        </div>
      )}

      {/* ── KPI Summary Cards ─────────────────────────────────────────── */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <AnalyticsCard
            title="Incidents Today"
            value={summary.total_today}
            subtitle="Detected in last 24h"
            icon={AlertTriangle}
            color="#FF2D2D"
          />
          <AnalyticsCard
            title="Active Now"
            value={summary.active_incidents}
            subtitle="Awaiting response"
            icon={Activity}
            color="#FF7A00"
            trend={summary.active_incidents > 0 ? "up" : "flat"}
          />
          <AnalyticsCard
            title="Resolved Today"
            value={summary.resolved_today}
            subtitle="Incidents cleared"
            icon={CheckCircle2}
            color="#00E676"
          />
          <AnalyticsCard
            title="Avg Response"
            value={`${summary.avg_response_time_minutes}m`}
            subtitle="Minutes to resolve"
            icon={Clock}
            color="#2979FF"
          />
        </div>
      )}

      {/* ── Main Two-Column Layout ────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Left: Incident feed (2 of 3 columns) */}
        <div className="lg:col-span-2">

          {/* Feed header + filter toggle */}
          <div className="flex items-center justify-between mb-3">
            <h2
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: "var(--text-muted)", fontFamily: "'Barlow Condensed', sans-serif" }}
            >
              Incident Feed
              <span className="ml-2 normal-case font-normal">
                ({filteredAccidents.length})
              </span>
            </h2>

            {/* Filter toggle: Active / All */}
            <div
              className="flex gap-0.5 rounded-md p-0.5"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
              role="group"
              aria-label="Incident filter"
            >
              {["active", "all"].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  aria-pressed={filter === f}
                  className="px-3 py-1 rounded text-xs uppercase transition-all"
                  style={{
                    fontFamily: "'Barlow Condensed', sans-serif",
                    background: filter === f ? "var(--red)" : "transparent",
                    color:      filter === f ? "#fff" : "var(--text-muted)",
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Incident cards */}
          {loading ? (
            <p className="text-xs text-center py-8" style={{ color: "var(--text-muted)" }}>
              Loading incidents…
            </p>
          ) : filteredAccidents.length === 0 ? (
            <div className="card text-center py-10">
              <CheckCircle2 size={28} style={{ color: "#00E676", margin: "0 auto 8px" }} aria-hidden="true" />
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                {filter === "active" ? "No active incidents. System clear. ✅" : "No incidents found."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {filteredAccidents.map((accident) => (
                <AlertCard
                  key={accident.id}
                  accident={accident}
                  onUpdate={refetch}   // Card calls this after marking resolved
                />
              ))}
            </div>
          )}
        </div>

        {/* Right: Traffic signal panel (1 of 3 columns) */}
        <div className="lg:col-span-1">
          <TrafficPanel />
        </div>
      </div>
    </div>
  );
}
