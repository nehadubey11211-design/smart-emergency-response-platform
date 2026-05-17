// FILE: frontend/src/components/Analytics.jsx
import { motion } from "framer-motion";
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";

// ─── Animation ────────────────────────────────────────────────────────────────
const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  show: (i = 0) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.08, duration: 0.5, ease: "easeOut" },
  }),
};

// ─── Static data ──────────────────────────────────────────────────────────────
const accidentFrequency = [
  { month: "Jan", accidents: 42 }, { month: "Feb", accidents: 58 },
  { month: "Mar", accidents: 35 }, { month: "Apr", accidents: 71 },
  { month: "May", accidents: 49 }, { month: "Jun", accidents: 63 },
  { month: "Jul", accidents: 80 }, { month: "Aug", accidents: 55 },
  { month: "Sep", accidents: 67 }, { month: "Oct", accidents: 44 },
  { month: "Nov", accidents: 76 }, { month: "Dec", accidents: 52 },
];

const dangerousZones = [
  { zone: "Highway 101", count: 38 }, { zone: "Oak & 5th", count: 31 },
  { zone: "I-280 N",     count: 27 }, { zone: "Market St",  count: 24 },
  { zone: "Bay Bridge",  count: 22 }, { zone: "Van Ness",   count: 18 },
];

const timeBasedData = [
  { hour: "00:00", accidents: 4  }, { hour: "02:00", accidents: 7  },
  { hour: "04:00", accidents: 11 }, { hour: "06:00", accidents: 23 },
  { hour: "08:00", accidents: 47 }, { hour: "10:00", accidents: 29 },
  { hour: "12:00", accidents: 35 }, { hour: "14:00", accidents: 31 },
  { hour: "16:00", accidents: 52 }, { hour: "18:00", accidents: 64 },
  { hour: "20:00", accidents: 38 }, { hour: "22:00", accidents: 19 },
];

const severityData = [
  { name: "Minor",    value: 58, color: "#2979FF" },
  { name: "Major",    value: 31, color: "#FF7A00" },
  { name: "Critical", value: 11, color: "#FF2D2D" },
];

const responseTimeData = [
  { region: "North",   time: 4.2 }, { region: "South",   time: 6.8 },
  { region: "East",    time: 5.1 }, { region: "West",    time: 3.9 },
  { region: "Central", time: 7.4 }, { region: "Harbor",  time: 5.6 },
];

const recentActivity = [
  { icon: "🚨", text: "Collision detected — Highway 101 Mile 24",                         time: "12s ago",  color: "#FF2D2D" },
  { icon: "🤖", text: "AI model confidence 97.3% — pedestrian impact classified",          time: "45s ago",  color: "#2979FF" },
  { icon: "🚑", text: "Emergency unit EMS-7 dispatched to Oak & 5th St",                  time: "1m ago",   color: "#00E676" },
  { icon: "⚠️", text: "Near-miss event logged — I-280 Northbound",                        time: "2m ago",   color: "#FF7A00" },
  { icon: "🤖", text: "Traffic anomaly pattern identified — Bay Bridge west approach",     time: "3m ago",   color: "#2979FF" },
  { icon: "🚒", text: "Fire unit FD-3 cleared — Market Street incident resolved",          time: "5m ago",   color: "#00E676" },
];

const STAT_CARDS = [
  { label: "Total Accidents",     value: "1,284", delta: "+12%", icon: "💥", color: "#FF2D2D" },
  { label: "Active Emergencies",  value: "7",     delta: "Live", icon: "🚨", color: "#FF7A00" },
  { label: "Avg Response Time",   value: "5.5m",  delta: "-8%",  icon: "⏱️", color: "#2979FF" },
  { label: "Dangerous Zones",     value: "23",    delta: "+3",   icon: "📍", color: "#a855f7" },
];

// ─── Shared classes (mirrors Dashboard tokens) ────────────────────────────────
const GLASS_CARD  = "relative overflow-hidden border border-white/10 rounded-3xl bg-white/[0.02] backdrop-blur-xl";
const INNER_CARD  = "border border-white/10 rounded-2xl bg-white/[0.03] backdrop-blur-lg p-4";
const MUTED_LABEL = "text-[10px] font-semibold uppercase tracking-widest text-slate-400";
const BARLOW      = { fontFamily: "'Barlow Condensed', sans-serif" };

// ─── Tooltip ──────────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="border border-white/10 rounded-xl bg-slate-900/90 backdrop-blur-xl px-3 py-2">
      <p className="text-xs text-slate-400 mb-1" style={BARLOW}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-sm text-white">
          {p.name}: <strong style={{ color: p.color || "#2979FF" }}>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

// ─── Chart wrapper ────────────────────────────────────────────────────────────
const ChartCard = ({ title, subtitle, children, delay = 0 }) => (
  <motion.div
    variants={fadeUp} initial="hidden" whileInView="show"
    viewport={{ once: true }} custom={delay}
    className={`${GLASS_CARD} p-4`}
  >
    {/* Decorative glow — same as Dashboard header glow */}
    <div className="absolute top-[-60px] right-[-60px] w-[180px] h-[180px] bg-blue-500/10 rounded-full blur-[80px] pointer-events-none" />

    <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-3">
      <h3 className="text-xs font-bold uppercase tracking-widest text-white" style={BARLOW}>
        {title}
      </h3>
      {subtitle && <span className="text-[10px] text-slate-500">{subtitle}</span>}
    </div>
    {children}
  </motion.div>
);

// ─── Axis / grid shared props ─────────────────────────────────────────────────
const axisProps = { tick: { fill: "#475569", fontSize: 11 }, axisLine: false, tickLine: false };
const gridProps = { strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.04)" };

// ─── Main component ───────────────────────────────────────────────────────────
export default function Analytics() {
  return (
    <div className="page-enter max-w-7xl mx-auto space-y-4">

      {/* ── Page Header — identical structure to Dashboard ────────────── */}
      <motion.div
        className={`${INNER_CARD} flex items-start justify-between flex-wrap gap-4`}
        initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <div>
          {/* Badge — mirrors Dashboard "SYSTEM ONLINE" concept */}
          <span className="inline-flex items-center gap-1.5 mb-2 px-2.5 py-1 rounded-full border border-green-500/20 bg-green-500/10 text-[10px] font-semibold text-green-400 tracking-widest" style={BARLOW}>
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            SYSTEM ONLINE · REAL-TIME
          </span>
          <h1 className="text-2xl font-bold text-white" style={{ ...BARLOW, letterSpacing: "0.04em" }}>
            AI ACCIDENT <span style={{ color: "#2979FF" }}>ANALYTICS</span>
          </h1>
          <p className="text-xs mt-0.5 text-slate-400">
            Autonomous traffic intelligence · Powered by deep neural detection
          </p>
        </div>
        {/* Live indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/10 bg-white/[0.03]">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs font-semibold text-green-400 tracking-widest" style={BARLOW}>LIVE</span>
        </div>
      </motion.div>

      {/* ── Stat Cards — same grid as Dashboard KPI row ───────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CARDS.map((card, i) => (
          <motion.div
            key={card.label}
            variants={fadeUp} initial="hidden" animate="show" custom={i}
            whileHover={{ y: -2 }}
            className={`${INNER_CARD} flex items-center gap-3 cursor-default`}
            style={{ borderColor: `${card.color}22`, boxShadow: `0 0 20px ${card.color}0a` }}
          >
            {/* Icon chip */}
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
              style={{ background: `${card.color}18` }}>
              {card.icon}
            </div>
            <div className="min-w-0">
              <p className={MUTED_LABEL}>{card.label}</p>
              <p className="text-2xl font-bold leading-none mt-0.5" style={{ ...BARLOW, color: card.color,
                textShadow: `0 0 16px ${card.color}50` }}>
                {card.value}
              </p>
              <p className="text-[10px] mt-0.5" style={{ color: card.color }}>{card.delta}</p>
            </div>
            {/* Corner glow */}
            <div className="absolute -top-4 -right-4 w-16 h-16 rounded-full blur-2xl pointer-events-none"
              style={{ background: card.color, opacity: 0.1 }} />
          </motion.div>
        ))}
      </div>

      {/* ── Charts Row 1 ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Accident Frequency" subtitle="Monthly overview · 2024" delay={0}>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={accidentFrequency}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="month" {...axisProps} />
              <YAxis {...axisProps} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="accidents" stroke="#2979FF" strokeWidth={2.5}
                dot={{ fill: "#2979FF", r: 3 }}
                activeDot={{ r: 6, fill: "#2979FF", stroke: "rgba(41,121,255,0.4)", strokeWidth: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Dangerous Zones" subtitle="Top 6 accident-prone areas" delay={1}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={dangerousZones} layout="vertical">
              <CartesianGrid {...gridProps} horizontal={false} />
              <XAxis type="number" {...axisProps} />
              <YAxis dataKey="zone" type="category" {...axisProps} width={90}
                tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {dangerousZones.map((_, i) => (
                  <Cell key={i} fill={`rgba(41,121,255,${0.9 - i * 0.1})`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* ── Charts Row 2 ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Time-Based Analytics" subtitle="Accidents by hour of day" delay={0}>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={timeBasedData}>
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#2979FF" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#2979FF" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="hour" {...axisProps} tick={{ fill: "#475569", fontSize: 10 }} />
              <YAxis {...axisProps} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="accidents" stroke="#2979FF" strokeWidth={2} fill="url(#areaGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Severity Distribution" subtitle="Incident classification" delay={1}>
          <div className="flex items-center gap-6">
            <ResponsiveContainer width="55%" height={200}>
              <PieChart>
                <Pie data={severityData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                  paddingAngle={4} dataKey="value">
                  {severityData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} stroke="rgba(0,0,0,0.4)" strokeWidth={1} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-3">
              {severityData.map((s) => (
                <div key={s.name} className="flex items-center gap-2.5">
                  <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                    style={{ background: s.color, boxShadow: `0 0 6px ${s.color}` }} />
                  <div>
                    <p className={MUTED_LABEL}>{s.name}</p>
                    <p className="text-lg font-bold leading-none" style={{ ...BARLOW, color: s.color }}>
                      {s.value}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </div>

      {/* ── Emergency Response Chart ───────────────────────────────────── */}
      <ChartCard title="Emergency Response Times" subtitle="Average response time per region (minutes)" delay={0}>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={responseTimeData}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="region" {...axisProps} tick={{ fill: "#94a3b8", fontSize: 12 }} />
            <YAxis {...axisProps} domain={[0, 10]} unit="m" />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="time" radius={[4, 4, 0, 0]}>
              {responseTimeData.map((entry, i) => (
                <Cell key={i}
                  fill={entry.time > 6 ? "#FF7A00" : entry.time > 5 ? "#2979FF" : "#00E676"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        {/* Legend — same inline style as Dashboard filter row */}
        <div className="flex gap-4 mt-3 pt-3 border-t border-white/5">
          {[["#00E676", "Fast (< 5m)"], ["#2979FF", "Normal (5–6m)"], ["#FF7A00", "Slow (> 6m)"]].map(([c, l]) => (
            <span key={l} className="flex items-center gap-1.5 text-[11px] text-slate-500" style={BARLOW}>
              <span className="w-2 h-2 rounded-sm" style={{ background: c }} />{l}
            </span>
          ))}
        </div>
      </ChartCard>

      {/* ── Live Activity Feed — mirrors Dashboard incident feed card ──── */}
      <motion.div
        className={`${GLASS_CARD} p-4`}
        variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
      >
        <div className="absolute top-[-60px] right-[-60px] w-[180px] h-[180px] bg-blue-500/10 rounded-full blur-[80px] pointer-events-none" />

        {/* Feed header — exact same pattern as Dashboard incident feed header */}
        <div className="flex items-center justify-between mb-4 border border-white/10 rounded-2xl p-3 bg-white/[0.03] backdrop-blur-lg">
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400" style={BARLOW}>
            Live Activity Feed
            <span className="ml-2 normal-case font-normal text-slate-500">({recentActivity.length})</span>
          </h2>
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg border border-green-500/20 bg-green-500/10">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[10px] font-semibold text-green-400 tracking-widest" style={BARLOW}>LIVE</span>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          {recentActivity.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -16 }} whileInView={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }} viewport={{ once: true }}
              whileHover={{ x: 4 }}
              className="flex items-center gap-3 border border-white/10 rounded-2xl bg-white/[0.03] backdrop-blur-lg p-3 hover:border-blue-400/30 transition-all duration-300"
            >
              {/* Icon chip — same as KPI icon chips */}
              <div className="w-8 h-8 rounded-xl flex items-center justify-center text-base flex-shrink-0"
                style={{ background: `${item.color}18`, border: `1px solid ${item.color}30` }}>
                {item.icon}
              </div>
              <p className="flex-1 text-sm text-slate-300 leading-snug">{item.text}</p>
              <span className="text-[11px] text-slate-500 whitespace-nowrap" style={BARLOW}>{item.time}</span>
              {/* Left accent bar — mirrors alert banner border pattern */}
              <div className="absolute left-0 top-2 bottom-2 w-0.5 rounded-full"
                style={{ background: item.color, opacity: 0.6 }} />
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <div className={`${INNER_CARD} flex items-center justify-between`}>
        <span className="text-[10px] text-slate-500 tracking-widest" style={BARLOW}>
          AI ACCIDENT DETECTION SYSTEM · NEURAL ENGINE v3.1
        </span>
        <span className="text-[10px] text-slate-500" style={BARLOW}>
          LAST SYNC: <strong style={{ color: "#2979FF" }}>LIVE</strong>
        </span>
      </div>

    </div>
  );
}