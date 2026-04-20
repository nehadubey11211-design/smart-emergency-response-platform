/**
 * FILE: frontend/src/pages/Analytics.jsx
 * =============================================
 * Analytics Page — Charts & KPIs
 * =============================================
 *
 * RECHARTS CONCEPTS:
 *   Recharts is a React-native charting library built on D3.
 *   Each chart is a composition of components:
 *     <AreaChart data={...}>         — the chart container + data
 *       <XAxis />                    — horizontal axis
 *       <YAxis />                    — vertical axis
 *       <Tooltip />                  — hover tooltip
 *       <Area dataKey="count" />     — the actual data series
 *     </AreaChart>
 *
 *   <ResponsiveContainer> makes the chart fill its parent's width.
 *
 * CUSTOM TOOLTIP:
 *   Recharts' default tooltip has white background — ugly on dark themes.
 *   We pass a custom content component to <Tooltip content={<DarkTooltip />}>
 *   to render a styled popup matching our dark colour scheme.
 *
 * DAY SELECTOR STATE:
 *   The days state drives the useAnalytics hook.
 *   When the user clicks "14d", days changes → useAnalytics re-fetches
 *   with the new window → chart updates.
 *   This demonstrates controlled UI state driving data fetching.
 */

import { useState } from "react";
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { AlertTriangle, Activity, CheckCircle2, Clock } from "lucide-react";

import { useAnalytics }  from "../hooks/useAnalytics";
import AnalyticsCard     from "../components/AnalyticsCard.jsx";
import { SEVERITY_COLOR } from "../utils/helpers";

// ─── Custom Dark Tooltip ──────────────────────────────────────────────────────
/**
 * Recharts passes { active, payload, label } to custom tooltip components.
 * We render nothing if not active (hovering) or no data.
 */
const DarkTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="px-3 py-2 rounded-md text-xs"
      style={{
        background: "var(--bg-panel)",
        border:     "1px solid var(--border)",
        color:      "#E0EAF8",
      }}
    >
      <p style={{ color: "var(--text-muted)", marginBottom: 4 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color || "#E0EAF8" }}>
          {p.dataKey}: {p.value}
        </p>
      ))}
    </div>
  );
};

export default function Analytics() {
  // ── Days selector state drives the analytics hook ─────────────────────
  const [days, setDays] = useState(7);

  const { summary, breakdown, trends, loading, error } = useAnalytics(days);

  if (loading) {
    return (
      <div
        className="flex items-center justify-center h-64 text-xs"
        style={{ color: "var(--text-muted)" }}
        aria-busy="true"
      >
        Loading analytics…
      </div>
    );
  }

  if (error) {
    return (
      <div className="card text-center py-8" style={{ color: "var(--red)" }}>
        {error} — Is the backend running?
      </div>
    );
  }

  return (
    <div className="page-enter max-w-6xl mx-auto">

      {/* Page header */}
      <div className="mb-6">
        <h1
          className="text-2xl font-bold"
          style={{ fontFamily: "'Barlow Condensed', sans-serif", letterSpacing: "0.04em" }}
        >
          ANALYTICS
        </h1>
        <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
          Historical incident data and system performance metrics
        </p>
      </div>

      {/* KPI summary cards */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <AnalyticsCard title="Today's Incidents" value={summary.total_today}             icon={AlertTriangle} color="#FF2D2D" subtitle="Detected today" />
          <AnalyticsCard title="Active"            value={summary.active_incidents}        icon={Activity}      color="#FF7A00" subtitle="Unresolved now" />
          <AnalyticsCard title="Resolved Today"    value={summary.resolved_today}          icon={CheckCircle2}  color="#00E676" subtitle="Closed today" />
          <AnalyticsCard title="Avg Response"      value={`${summary.avg_response_time_minutes}m`} icon={Clock} color="#2979FF" subtitle="Time to resolve" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Trend area chart — 2 columns */}
        <div className="panel p-4 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2
              className="text-xs uppercase tracking-widest font-bold"
              style={{ color: "var(--text-muted)", fontFamily: "'Barlow Condensed', sans-serif" }}
            >
              Incident Trend
            </h2>

            {/* Day range selector */}
            <div className="flex gap-1" role="group" aria-label="Trend window">
              {[7, 14, 30].map((d) => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  aria-pressed={days === d}
                  className="px-2 py-0.5 rounded text-xs transition-all"
                  style={{
                    fontFamily: "'Barlow Condensed', sans-serif",
                    background: days === d ? "rgba(41,121,255,0.2)" : "transparent",
                    color:      days === d ? "#2979FF" : "var(--text-muted)",
                    border:     `1px solid ${days === d ? "#2979FF" : "transparent"}`,
                  }}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>

          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={trends} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
              {/* SVG gradient definition — referenced by fill="url(#grad)" */}
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#2979FF" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#2979FF" stopOpacity={0}    />
                </linearGradient>
              </defs>

              <XAxis
                dataKey="date"
                tick={{ fill: "var(--text-dim)", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: "var(--text-dim)", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<DarkTooltip />} />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#2979FF"
                strokeWidth={2}
                fill="url(#areaGrad)"
                dot={false}           /* No dots on data points — cleaner look */
                activeDot={{ r: 4, fill: "#2979FF" }}
              />
            </AreaChart>
          </ResponsiveContainer>

          {trends.length === 0 && (
            <p className="text-xs text-center mt-4" style={{ color: "var(--text-muted)" }}>
              No data for this period — create some accidents via the AI module or API.
            </p>
          )}
        </div>

        {/* Severity pie chart — 1 column */}
        <div className="panel p-4">
          <h2
            className="text-xs uppercase tracking-widest font-bold mb-4"
            style={{ color: "var(--text-muted)", fontFamily: "'Barlow Condensed', sans-serif" }}
          >
            By Severity
          </h2>

          {breakdown.length === 0 ? (
            <p className="text-xs text-center py-8" style={{ color: "var(--text-muted)" }}>
              No data yet
            </p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={breakdown}
                    dataKey="count"
                    nameKey="severity"
                    cx="50%"
                    cy="50%"
                    innerRadius={40}   /* Donut chart: inner hole */
                    outerRadius={65}
                    strokeWidth={0}    /* No border between segments */
                  >
                    {breakdown.map((entry) => (
                      <Cell
                        key={entry.severity}
                        fill={SEVERITY_COLOR[entry.severity] || "#888"}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<DarkTooltip />} />
                </PieChart>
              </ResponsiveContainer>

              {/* Manual legend */}
              <div className="flex flex-col gap-1.5 mt-2">
                {breakdown.map((entry) => (
                  <div key={entry.severity} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-2">
                      <span
                        className="w-2 h-2 rounded-sm"
                        style={{ background: SEVERITY_COLOR[entry.severity] }}
                        aria-hidden="true"
                      />
                      <span
                        style={{ color: "var(--text-muted)", textTransform: "capitalize" }}
                      >
                        {entry.severity}
                      </span>
                    </span>
                    <span style={{ color: "#E0EAF8", fontWeight: "bold" }}>
                      {entry.count}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
