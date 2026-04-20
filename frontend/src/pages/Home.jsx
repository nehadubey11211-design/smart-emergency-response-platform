/**
 * FILE: frontend/src/pages/Home.jsx
 * ========================================
 * Public Landing Page
 * ========================================
 *
 * This page is visible to everyone — no authentication required.
 * It's the first impression for interviewers running the project locally.
 *
 * DESIGN DECISIONS:
 *   - Data-driven feature grid: features defined as an array, rendered with .map()
 *     → adding a new feature = add one object to the array, zero JSX duplication
 *   - useNavigate hook for programmatic navigation (replaces window.location.href
 *     which does a full page reload and loses React state)
 *   - Decorative background using CSS background-image gradient (no image files)
 *   - aria-hidden on purely decorative elements (grid, icons in feature cards)
 *
 * USENAVIGATION vs ANCHOR TAG:
 *   <a href="/login">  — full page reload, loses all in-memory state
 *   useNavigate()      — client-side navigation, preserves React app state,
 *                        feels instant because only the changed component re-renders
 *
 * INTERVIEW TALKING POINT:
 *   "The landing page uses the same React Router navigation as the rest
 *   of the app — no page reloads. This is the core SPA (Single Page
 *   Application) pattern: the browser loads index.html once, then React
 *   handles all navigation by swapping components."
 */

import { useNavigate } from "react-router-dom";
import { Siren, Zap, Shield, Radio, Brain, Activity } from "lucide-react";

// ─── Feature Configuration ────────────────────────────────────────────────────
// Defining content as data keeps the JSX clean and makes it trivial to
// add/remove/reorder features without touching HTML structure.

const FEATURES = [
  {
    icon:  Siren,
    title: "Real-time Accident Detection",
    desc:  "MobileNetV2 CNN analyses live CCTV feeds at 1fps. Alerts reach operators within 1 second via WebSocket push.",
    color: "#FF2D2D",
  },
  {
    icon:  Zap,
    title: "Automatic Green Corridor",
    desc:  "When an ambulance is dispatched, all traffic signals along the optimal route switch to emergency mode automatically.",
    color: "#FF7A00",
  },
  {
    icon:  Radio,
    title: "Live WebSocket Alerts",
    desc:  "Operators see new incidents appear on the dashboard instantly — no page refresh, no polling delay.",
    color: "#2979FF",
  },
  {
    icon:  Brain,
    title: "Transfer Learning AI",
    desc:  "MobileNetV2 pretrained on ImageNet, fine-tuned on accident data. Achieves >85% accuracy with minimal training images.",
    color: "#00E676",
  },
  {
    icon:  Activity,
    title: "Analytics Dashboard",
    desc:  "Historical trend charts, severity breakdowns, response time KPIs — all from live PostgreSQL aggregation queries.",
    color: "#FFD600",
  },
  {
    icon:  Shield,
    title: "JWT Authentication",
    desc:  "Stateless auth with bcrypt password hashing and role-based access. Scales horizontally without session storage.",
    color: "#9C27B0",
  },
];

// ─── Tech Stack Badges ────────────────────────────────────────────────────────
const STACK = [
  "React 18",
  "FastAPI",
  "PostgreSQL",
  "TensorFlow",
  "WebSocket",
  "Docker",
  "Tailwind CSS",
  "MobileNetV2",
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-8"
      style={{ background: "var(--bg-dark)" }}
    >
      {/* ── Decorative background grid ──────────────────────────────── */}
      <div
        className="fixed inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(var(--border) 1px, transparent 1px), " +
            "linear-gradient(90deg, var(--border) 1px, transparent 1px)",
          backgroundSize: "50px 50px",
        }}
        aria-hidden="true"
      />

      <div className="relative max-w-4xl w-full text-center">

        {/* ── Hero Section ─────────────────────────────────────────── */}
        <div className="mb-10">
          {/* Logo mark */}
          <div
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-5"
            style={{
              background: "rgba(255,45,45,0.15)",
              border:     "2px solid rgba(255,45,45,0.4)",
            }}
          >
            <Siren size={32} style={{ color: "var(--red)" }} aria-hidden="true" />
          </div>

          <h1
            className="text-4xl lg:text-5xl font-bold mb-3"
            style={{ fontFamily: "'Barlow Condensed', sans-serif", letterSpacing: "0.06em" }}
          >
            AI EMERGENCY RESPONSE
          </h1>

          <p
            className="text-lg mb-2"
            style={{ color: "#E0EAF8", fontFamily: "'Barlow Condensed', sans-serif" }}
          >
            Real-time accident detection and intelligent traffic management
          </p>
          <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
            Full-stack project · React + FastAPI + TensorFlow + PostgreSQL + Docker
          </p>

          {/* CTA Button */}
          <button
            onClick={() => navigate("/login")}
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg font-bold
                       text-white text-sm uppercase tracking-widest transition-all
                       duration-200 hover:opacity-90 hover:scale-105"
            style={{
              background: "var(--red)",
              fontFamily: "'Barlow Condensed', sans-serif",
              letterSpacing: "0.12em",
            }}
          >
            <Shield size={16} aria-hidden="true" />
            Open Dashboard
          </button>
        </div>

        {/* ── Tech Stack Badges ─────────────────────────────────────── */}
        <div className="flex flex-wrap gap-2 justify-center mb-12">
          {STACK.map((tech) => (
            <span
              key={tech}
              className="px-3 py-1 rounded-full text-xs"
              style={{
                background:  "rgba(41,121,255,0.1)",
                border:      "1px solid rgba(41,121,255,0.25)",
                color:       "#2979FF",
                fontFamily:  "'JetBrains Mono', monospace",
              }}
            >
              {tech}
            </span>
          ))}
        </div>

        {/* ── Feature Grid ──────────────────────────────────────────── */}
        {/*
         * CSS Grid with auto-fill and minmax creates a responsive grid
         * that automatically adjusts the number of columns based on
         * available space. No media queries needed.
         */}
        <div
          className="grid gap-3"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}
        >
          {FEATURES.map(({ icon: Icon, title, desc, color }) => (
            <div
              key={title}
              className="card text-left transition-all duration-200 hover:scale-[1.01]"
              style={{ borderColor: `${color}25` }}
            >
              {/* Feature icon */}
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center mb-3"
                style={{ background: `${color}18` }}
              >
                <Icon size={16} style={{ color }} aria-hidden="true" />
              </div>

              <h3
                className="text-sm font-bold mb-1.5"
                style={{ fontFamily: "'Barlow Condensed', sans-serif", color: "#E0EAF8" }}
              >
                {title}
              </h3>

              <p
                className="text-xs leading-relaxed"
                style={{ color: "var(--text-muted)" }}
              >
                {desc}
              </p>
            </div>
          ))}
        </div>

        {/* ── Footer ───────────────────────────────────────────────── */}
        <p className="mt-10 text-xs" style={{ color: "var(--text-dim)" }}>
          Placement project · Smart AI Emergency Response System
        </p>
      </div>
    </div>
  );
}
