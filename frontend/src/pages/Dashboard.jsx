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
import { useState, useEffect, useCallback, useMemo } from "react";
import { AlertTriangle, CheckCircle2, Clock, Activity, BellRing } from "lucide-react";

import { useAccidents }  from "../hooks/useAccidents";
import socketService      from "../services/socket";
import { getSummary }     from "../services/api";

import AlertCard     from "../components/AlertCard.jsx";
import TrafficPanel  from "../components/TrafficPanel.jsx";
import StatusPanel   from "../components/StatusPanel.jsx";
import AnalyticsCard from "../components/AnalyticsCard.jsx";

// ─── Static data (defined outside — never recreated on render) ────────────────

const FILTER_OPTIONS = ["active", "all"];

const KPI_CONFIG = [
  { key: "total_today",              title: "Incidents Today",  subtitle: "Detected in last 24h",   icon: AlertTriangle, color: "#FF2D2D" },
  { key: "active_incidents",         title: "Active Now",       subtitle: "Awaiting response",       icon: Activity,      color: "#FF7A00" },
  { key: "resolved_today",           title: "Resolved Today",   subtitle: "Incidents cleared",       icon: CheckCircle2,  color: "#00E676" },
  { key: "avg_response_time_minutes",title: "Avg Response",     subtitle: "Minutes to resolve",      icon: Clock,         color: "#2979FF" },
];

export default function Dashboard() {
  const { data: accidents, loading, refetch } = useAccidents({}, 30000);

  const [filter,   setFilter]   = useState("active");
  const [summary,  setSummary]  = useState(null);
  const [newAlert, setNewAlert] = useState(false);

  // ── Summary fetch: only re-run when accidents reference changes ───────────
  useEffect(() => {
    getSummary()
      .then((res) => setSummary(res.data))
      .catch((err) => console.error("Summary fetch failed:", err));
  }, [accidents]);

  // ── WebSocket subscription ────────────────────────────────────────────────
  useEffect(() => {
    const handleNewAccident = () => {
      setNewAlert(true);
      setTimeout(() => setNewAlert(false), 4000);
      refetch();
    };
    socketService.on("NEW_ACCIDENT", handleNewAccident);
    return () => socketService.off("NEW_ACCIDENT", handleNewAccident);
  }, [refetch]);

  // ── Derived: O(n) filter memoised — only recomputes when inputs change ────
  // Previously ran as an inline expression on every render regardless of deps.
  const filteredAccidents = useMemo(
    () => filter === "active" ? accidents.filter((a) => a.status !== "resolved") : accidents,
    [filter, accidents]
  );

  // ── Stable filter setter (avoids recreating on every render) ─────────────
  const handleFilterChange = useCallback((f) => setFilter(f), []);

  // ── KPI values: O(1) lookup per card instead of ad-hoc property access ───
  const kpiValues = useMemo(() => {
    if (!summary) return null;
    return KPI_CONFIG.map((cfg) => ({
      ...cfg,
      value: cfg.key === "avg_response_time_minutes"
        ? `${summary[cfg.key]}m`
        : summary[cfg.key],
      trend: cfg.key === "active_incidents"
        ? (summary[cfg.key] > 0 ? "up" : "flat")
        : undefined,
    }));
  }, [summary]);

  return (
    <div className="page-enter max-w-7xl mx-auto relative border border-white/10 rounded-3xl p-6 bg-white/[0.02] backdrop-blur-xl shadow-[0_0_40px_rgba(59,130,246,0.08)] overflow-hidden">

      {/* Background Glow */}
      <div className="absolute top-[-100px] right-[-100px] w-[300px] h-[300px] bg-blue-500/10 rounded-full blur-[140px] pointer-events-none" />

      {/* ── Page Header ────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-5 gap-4 flex-wrap border border-white/10 rounded-2xl p-4 bg-white/[0.03] backdrop-blur-lg">
        <div>
          <h1 className="text-2xl font-bold" style={{ fontFamily: "'Barlow Condensed', sans-serif", letterSpacing: "0.04em" }}>
            OPERATIONS DASHBOARD
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            Real-time incident monitoring and traffic signal control
          </p>
        </div>
        <StatusPanel />
      </div>

      {/* ── Real-time Alert Banner ──────────────────────────────────────── */}
      {newAlert && (
        <div role="alert" aria-live="assertive"
          className="flex items-center gap-2 px-4 py-3 rounded-2xl mb-4 text-sm font-bold border border-red-500/30 bg-red-500/10 backdrop-blur-xl"
          style={{ color: "var(--red)" }}>
          <BellRing size={14} className="animate-bounce" aria-hidden="true" />
          🚨 NEW ACCIDENT DETECTED — Dashboard refreshed automatically
        </div>
      )}

      {/* ── KPI Summary Cards ───────────────────────────────────────────── */}
      {kpiValues && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {kpiValues.map(({ key, title, value, subtitle, icon, color, trend }) => (
            <div key={key} className="rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-lg p-2">
              <AnalyticsCard title={title} value={value} subtitle={subtitle} icon={icon} color={color} trend={trend} />
            </div>
          ))}
        </div>
      )}

      {/* ── Main Two-Column Layout ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Left: Incident Feed */}
        <div className="lg:col-span-2 border border-white/10 rounded-3xl p-4 bg-white/[0.02] backdrop-blur-xl">

          {/* Feed Header */}
          <div className="flex items-center justify-between mb-4 border border-white/10 rounded-2xl p-3 bg-white/[0.03] backdrop-blur-lg">
            <h2 className="text-xs font-bold uppercase tracking-widest"
              style={{ color: "var(--text-muted)", fontFamily: "'Barlow Condensed', sans-serif" }}>
              Incident Feed
              <span className="ml-2 normal-case font-normal">({filteredAccidents.length})</span>
            </h2>

            <div className="flex gap-1 rounded-xl p-1 bg-white/5 border border-white/10 backdrop-blur-lg"
              role="group" aria-label="Incident filter">
              {FILTER_OPTIONS.map((f) => (
                <button key={f} onClick={() => handleFilterChange(f)} aria-pressed={filter === f}
                  className={`px-4 py-1.5 rounded-lg text-xs uppercase transition-all duration-300 ${
                    filter === f ? "bg-red-500 text-white shadow-lg" : "text-slate-300 hover:bg-white/10"
                  }`}
                  style={{ fontFamily: "'Barlow Condensed', sans-serif" }}>
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Incident Cards */}
          {loading ? (
            <p className="text-xs text-center py-8" style={{ color: "var(--text-muted)" }}>Loading incidents…</p>
          ) : filteredAccidents.length === 0 ? (
            <div className="rounded-2xl border border-green-500/20 bg-green-500/5 backdrop-blur-xl text-center py-10">
              <CheckCircle2 size={28} style={{ color: "#00E676", margin: "0 auto 8px" }} aria-hidden="true" />
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                {filter === "active" ? "No active incidents. System clear. ✅" : "No incidents found."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {filteredAccidents.map((accident) => (
                <div key={accident.id}
                  className="border border-white/10 rounded-2xl bg-white/[0.03] backdrop-blur-lg p-2 hover:border-blue-400/30 transition-all duration-300">
                  <AlertCard accident={accident} onUpdate={refetch} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Traffic Panel */}
        <div className="lg:col-span-1 border border-white/10 rounded-3xl p-4 bg-white/[0.02] backdrop-blur-xl">
          <TrafficPanel />
        </div>
      </div>
    </div>
  );
}