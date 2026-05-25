// FILE: frontend/src/components/Analytics.jsx
import { useAnalytics } from "../hooks/useAnalytics";
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



// ─── Shared classes (mirrors Dashboard tokens) ────────────────────────────────
const GLASS_CARD  = "relative overflow-hidden border border-white/10 rounded-3xl bg-white/[0.02] backdrop-blur-xl";
const INNER_CARD  = "border border-white/10 rounded-2xl bg-white/[0.03] backdrop-blur-lg p-4";
const MUTED_LABEL = "text-[10px] font-semibold uppercase tracking-widest text-slate-400";
const BARLOW      = { fontFamily: "'Barlow Condensed', sans-serif" };

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="border border-white/10 rounded-xl bg-slate-900/90 backdrop-blur-xl px-3 py-2">
      <p className="text-xs text-slate-400 mb-1" style={BARLOW}>
        {label}
      </p>

      {payload.map((p, i) => (
        <p key={i} className="text-sm text-white">
          {p.name}:{" "}
          <strong style={{ color: p.color || "#2979FF" }}>
            {p.value}
          </strong>
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

  const {
    summary,
    breakdown,
    trends,
    loading,
    error,
  } = useAnalytics(30);

   if (loading) {
  return (
    <div className="page-enter max-w-7xl mx-auto space-y-4">

      {/* Header Skeleton */}
      <div className="loading-skeleton h-24 rounded-3xl" />

      {/* Stat Cards Skeleton */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="loading-skeleton h-32 rounded-3xl"
          />
        ))}
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {[...Array(2)].map((_, i) => (
          <div
            key={i}
            className="loading-skeleton h-72 rounded-3xl"
          />
        ))}
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {[...Array(2)].map((_, i) => (
          <div
            key={i}
            className="loading-skeleton h-72 rounded-3xl"
          />
        ))}
      </div>

      {/* Bottom Chart */}
      <div className="loading-skeleton h-80 rounded-3xl" />

      {/* Activity Feed */}
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="loading-skeleton h-16 rounded-2xl"
          />
        ))}
      </div>

    </div>
  );
}

  if (error) {
    return (
      <div className="text-red-500 p-6">
        {error}
      </div>
    );
  }

  // ── API DATA ─────────────────────────────

  const accidentFrequency = trends?.map((item) => ({
    month: item.date,
    accidents: item.count,
  })) || [];

  const dangerousZones = breakdown?.zones?.map((zone) => ({
    zone: zone.name,
    count: zone.accidents,
  })) || [];

  const timeBasedData = breakdown?.hourly?.map((item) => ({
    hour: item.hour,
    accidents: item.count,
  })) || [];

  const severityData = breakdown?.severity?.map((item) => ({
    name: item.level,
    value: item.percentage,
    color:
      item.level === "Critical"
        ? "#FF2D2D"
        : item.level === "Major"
        ? "#FF7A00"
        : "#2979FF",
  })) || [];

  const responseTimeData = breakdown?.responseTimes?.map((item) => ({
    region: item.region,
    time: item.avg_time,
  })) || [];

  const STAT_CARDS = [
    {
      label: "Total Accidents",
      value: summary?.total_accidents || 0,
      delta: "+12%",
      icon: "💥",
      color: "#FF2D2D",
    },
    {
      label: "Active Emergencies",
      value: summary?.active_emergencies || 0,
      delta: "Live",
      icon: "🚨",
      color: "#FF7A00",
    },
    {
      label: "Avg Response Time",
      value: `${summary?.avg_response_time || 0}m`,
      delta: "-8%",
      icon: "⏱️",
      color: "#2979FF",
    },
    {
      label: "Dangerous Zones",
      value: dangerousZones.length,
      delta: "+3",
      icon: "📍",
      color: "#a855f7",
    },
  ];
  const recentActivity = breakdown?.recentActivity || [];
return (
  
  <div className="page-enter max-w-7xl mx-auto space-y-4">

    {/* ── Header ───────────────────────────────────── */}
    <motion.div
      className={`${INNER_CARD} flex items-start justify-between flex-wrap gap-4`}
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div>
        <span
          className="inline-flex items-center gap-1.5 mb-2 px-2.5 py-1 rounded-full border border-green-500/20 bg-green-500/10 text-[10px] font-semibold text-green-400 tracking-widest"
          style={BARLOW}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          SYSTEM ONLINE · REAL-TIME
        </span>

        <h1
          className="text-2xl font-bold text-white"
          style={{ ...BARLOW, letterSpacing: "0.04em" }}
        >
          AI ACCIDENT <span style={{ color: "#2979FF" }}>ANALYTICS</span>
        </h1>

        <p className="text-xs mt-1 text-slate-400">
          Real-time traffic intelligence dashboard
        </p>
      </div>

      <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/10 bg-white/[0.03]">
        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        <span
          className="text-xs font-semibold text-green-400 tracking-widest"
          style={BARLOW}
        >
          LIVE
        </span>
      </div>
    </motion.div>

    {/* ── Stat Cards ───────────────────────────────────── */}
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {STAT_CARDS.map((card, i) => (
        <motion.div
          key={card.label}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          custom={i}
          whileHover={{ y: -2 }}
          className={`${INNER_CARD} flex items-center gap-3 relative overflow-hidden`}
          style={{
            borderColor: `${card.color}22`,
            boxShadow: `0 0 20px ${card.color}0a`,
          }}
        >
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
            style={{ background: `${card.color}18` }}
          >
            {card.icon}
          </div>

          <div>
            <p className={MUTED_LABEL}>{card.label}</p>

            <p
              className="text-2xl font-bold"
              style={{
                ...BARLOW,
                color: card.color,
              }}
            >
              {card.value}
            </p>

            <p className="text-[10px]" style={{ color: card.color }}>
              {card.delta}
            </p>
          </div>
        </motion.div>
      ))}
    </div>

    {/* ── Charts Row 1 ───────────────────────────────────── */}
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

      {/* Accident Frequency */}
      <ChartCard
        title="Accident Frequency"
        subtitle="Monthly overview"
      >
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={accidentFrequency}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="month" {...axisProps} />
            <YAxis {...axisProps} />

            <Tooltip content={<CustomTooltip />} />

            <Line
              type="monotone"
              dataKey="accidents"
              stroke="#2979FF"
              strokeWidth={3}
              dot={{ fill: "#2979FF", r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Dangerous Zones */}
      <ChartCard
        title="Dangerous Zones"
        subtitle="Top accident-prone areas"
      >
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={dangerousZones}>
            <CartesianGrid {...gridProps} />

            <XAxis dataKey="zone" {...axisProps} />
            <YAxis {...axisProps} />

            <Tooltip content={<CustomTooltip />} />

            <Bar
              dataKey="count"
              fill="#FF7A00"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>

    {/* ── Charts Row 2 ───────────────────────────────────── */}
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

      {/* Time Based */}
      <ChartCard
        title="Time-Based Analytics"
        subtitle="Accidents by hour"
      >
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={timeBasedData}>

            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor="#2979FF"
                  stopOpacity={0.3}
                />
                <stop
                  offset="95%"
                  stopColor="#2979FF"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>

            <CartesianGrid {...gridProps} />

            <XAxis dataKey="hour" {...axisProps} />
            <YAxis {...axisProps} />

            <Tooltip content={<CustomTooltip />} />

            <Area
              type="monotone"
              dataKey="accidents"
              stroke="#2979FF"
              fill="url(#areaGrad)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Severity */}
      <ChartCard
        title="Severity Distribution"
        subtitle="Incident classification"
      >
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>

            <Pie
              data={severityData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={80}
              innerRadius={45}
            >
              {severityData.map((entry, index) => (
                <Cell
                  key={index}
                  fill={entry.color}
                />
              ))}
            </Pie>

            <Tooltip content={<CustomTooltip />} />

          </PieChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>

    {/* ── Response Time ───────────────────────────────────── */}
    <ChartCard
      title="Emergency Response Times"
      subtitle="Average response time by region"
    >
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={responseTimeData}>

          <CartesianGrid {...gridProps} />

          <XAxis dataKey="region" {...axisProps} />
          <YAxis {...axisProps} />

          <Tooltip content={<CustomTooltip />} />

          <Bar
            dataKey="time"
            fill="#00E676"
            radius={[6, 6, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>

    {/* ── Activity Feed ───────────────────────────────────── */}
    <motion.div
      className={`${GLASS_CARD} p-4`}
      variants={fadeUp}
      initial="hidden"
      whileInView="show"
    >
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-xs font-bold uppercase tracking-widest text-slate-400"
          style={BARLOW}
        >
          Live Activity Feed
        </h2>
      </div>

      <div className="space-y-3">

        {recentActivity.length === 0 && (
          <div className="text-slate-500 text-sm">
            No recent activity
          </div>
        )}

        {recentActivity.map((item, i) => (
          <div
            key={i}
            className="border border-white/10 rounded-xl bg-white/[0.03] p-3"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-300">
                {item.text || "Activity detected"}
              </p>

              <span className="text-xs text-slate-500">
                {item.time || "now"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </motion.div>

  </div>
);

}

