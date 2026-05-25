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
import PropTypes from 'prop-types';

export default function AnalyticsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = "#2979FF",
  trend,
}) {
  const TrendIcon =
    trend === "up"   ? TrendingUp   :
    trend === "down" ? TrendingDown : Minus;

  const trendColor =
    trend === "up"   ? "#FF2D2D" :
    trend === "down" ? "#00E676" :
    "rgba(148,163,184,0.6)"; // slate-400/60 — matches --text-muted in dark glass UI

  return (
    <div
      className="relative overflow-hidden rounded-2xl p-4 bg-white/[0.03] backdrop-blur-xl border transition-all duration-300 hover:bg-white/[0.06] hover:shadow-lg"
      style={{
        borderColor: `${color}28`,                          // ~16% opacity border tint
        boxShadow:   `0 0 20px ${color}10, inset 0 1px 0 rgba(255,255,255,0.05)`, // subtle inner highlight + outer glow
      }}
    >
      {/* Decorative corner glow — replaces hard blob */}
      <div
        className="absolute -top-4 -right-4 w-20 h-20 rounded-full blur-2xl pointer-events-none"
        style={{ background: color, opacity: 0.12 }}
        aria-hidden="true"
      />

      {/* Top row: label + icon */}
      <div className="flex items-center justify-between mb-3">
        <span
          className="text-[10px] font-semibold uppercase tracking-widest text-slate-400"
          style={{ fontFamily: "'Barlow Condensed', sans-serif" }}
        >
          {title}
        </span>

        {Icon && (
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: `${color}18` }}   // icon chip — 9% opacity tint
          >
            <Icon size={13} style={{ color }} aria-hidden="true" />
          </div>
        )}
      </div>

      {/* Primary value */}
      <div
        className="text-3xl font-bold mb-1.5 leading-none"
        style={{
          color,
          fontFamily: "'Barlow Condensed', sans-serif",
          textShadow: `0 0 20px ${color}50`,  // value glow matching card accent
        }}
        aria-label={`${title}: ${value}`}
      >
        {value ?? "—"}
      </div>

      {/* Divider line — same tint as border */}
      <div className="w-full h-px mb-2" style={{ background: `${color}18` }} />

      {/* Subtitle + trend */}
      <div className="flex items-center gap-1.5">
        {trend && (
          <TrendIcon size={11} style={{ color: trendColor }} aria-hidden="true" />
        )}
        <span className="text-[11px] text-slate-400">{subtitle}</span>
      </div>
    </div>
  );
  AnalyticsCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number
  ]).isRequired,
  subtitle: PropTypes.string,
  color: PropTypes.string,
  trend: PropTypes.string,
  icon: PropTypes.elementType
};
}
