/**
 * FILE: frontend/src/components/AnalyticsCard.jsx
 * ======================================================
 * KPI Summary Card — Reusable Metric Display
 * ======================================================
 *
 * This is a generic "stat card" component used across Dashboard and Analytics.
 * It demonstrates:
 *   - Props with defaults (color, trend)
 *   - Conditional rendering (only show trend icon if trend prop is provided)
 *   - CSS custom properties for theming
 *   - Absolute positioning for decorative elements
 *
 * Props:
 *   title    {string}  — Metric label (e.g. "Incidents Today")
 *   value    {any}     — The KPI value to display prominently
 *   subtitle {string}  — Context text below the value
 *   icon     {Component} — Lucide icon component
 *   color    {string}  — Hex colour for accent and value text
 *   trend    {string}  — "up" | "down" | "flat" | undefined
 */

import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export default function AnalyticsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = "#2979FF",
  trend,
}) {
  // Select the appropriate trend icon based on the trend prop
  const TrendIcon =
    trend === "up"   ? TrendingUp   :
    trend === "down" ? TrendingDown : Minus;

  const trendColor =
    trend === "up"   ? "#FF2D2D" :   // Up = more accidents = bad (red)
    trend === "down" ? "#00E676" :   // Down = fewer accidents = good (green)
    "var(--text-muted)";

  return (
    <div
      className="card relative overflow-hidden"
      style={{ borderColor: `${color}30` }}   // 30 = 19% opacity hex suffix
    >
      {/* Decorative gradient blob in top-right corner */}
      <div
        className="absolute top-0 right-0 w-16 h-16 rounded-bl-full opacity-10"
        style={{ background: color }}
        aria-hidden="true"
      />

      {/* Title row */}
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-xs uppercase tracking-widest"
          style={{
            color:      "var(--text-muted)",
            fontFamily: "'Barlow Condensed', sans-serif",
          }}
        >
          {title}
        </span>
        {Icon && (
          <Icon size={14} style={{ color }} aria-hidden="true" />
        )}
      </div>

      {/* Primary value — large and bold */}
      <div
        className="text-3xl font-bold mb-1"
        style={{
          color,
          fontFamily: "'Barlow Condensed', sans-serif",
          lineHeight: 1,
        }}
        aria-label={`${title}: ${value}`}
      >
        {value ?? "—"}
      </div>

      {/* Subtitle with optional trend indicator */}
      <div className="flex items-center gap-1.5">
        {trend && (
          <TrendIcon size={11} style={{ color: trendColor }} aria-hidden="true" />
        )}
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {subtitle}
        </span>
      </div>
    </div>
  );
}
