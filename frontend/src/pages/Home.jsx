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


import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Shield,
  Camera,
  AlertTriangle,
  MapPin,
  BarChart3,
  Clock,
  Users,
  Activity,
  Zap,
  ArrowRight,
  Menu,
  X,
  Phone,
  Mail,
  Building,
  Globe,
} from "lucide-react";

function GovCard({ children, className = "", hover = false }) {
  return (
    <div className={`bg-white/10 backdrop-blur-xl border border-white/10 rounded-3xl shadow-2xl p-6 transition-all duration-500 ${
      hover ? 'hover:scale-105 hover:shadow-[0_0_40px_rgba(59,130,246,0.3)]' : ''
    } ${className}`}>
      {children}
    </div>
  );
}

function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  const navItems = [
    { name: "Home", href: "/" },
    { name: "Statistics", href: "#statistics" },
    { name: "Services", href: "#services" },
    { name: "Contact", href: "#contact" },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-black/40 backdrop-blur-2xl border-b border-white/10 shadow-sm border-t border-white/100">
      <div className="max-w-8xl mx-auto px-8 sm:px-4 lg:px-4">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <div className="flex items-center space-x-2">
              <div className="w-11 h-11 bg-gradient-to-br from-white to-white-900 rounded-xl flex items-center justify-center shadow-lg shadow-white-500/30">
                <img src="/logo.png" alt="USE Logo" className="w-10 h-10 object-contain" />
              </div>
              <div>
                <div className="text-xl font-bold text-white tracking-tight">Smart-Emergency-Response-Platform</div>
                <div className="text-lg text-red-500">AI Detection System</div>
              </div>
            </div>
          </div>

          <div className="hidden md:flex items-center space-x-10">
            {navItems.map((item) => (
              <a key={item.name} href={item.href} className="text-xl font-medium text-white-900 hover:text-blue-600 transition-colors duration-200">
                {item.name}
              </a>
            ))}
          </div>

          <div className="hidden md:flex items-center space-x-3">
            <button onClick={() => navigate("/login")} className="px-2 py-4 bg-gradient-to-r from-blue-800 to-blue-700 text-white text-sm font-semibold rounded-lg hover:scale-105 hover:shadow-[0_0_40px_rgba(59,130,246,0.6)] transition-all duration-200">
              Workspace
            </button>
            <button onClick={() => navigate("/login")} className="px-2 py-4 bg-gradient-to-r from-red-800 to-red-900 text-white text-sm font-semibold rounded-lg hover:scale-105 hover:shadow-[0_0_40px_rgba(59,130,246,0.6)] transition-all duration-200">
              Dashboard
            </button>
          </div>

          <div className="md:hidden">
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="text-gray-700 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200">
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden bg-white border-t border-gray-100">
            <div className="px-2 pt-4 pb-3 space-y-1">
              {navItems.map((item) => (
                <a key={item.name} href={item.href} className="block px-3 py-2 text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all duration-200">
                  {item.name}
                </a>
              ))}
              <div className="pt-4 pb-2 space-y-2">
                <button onClick={() => navigate("/login")} className="w-full px-3 py-2.5 text-sm font-medium text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-50 transition-all duration-200">
                  Portal Login
                </button>
                <button onClick={() => navigate("/login")} className="w-full px-3 py-2.5 text-sm font-semibold bg-gradient-to-r from-green-600 to-green-700 text-white rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-200">
                  Dashboard
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}

function HeroSection() {
  const navigate = useNavigate();

  return (
    <section className="relative min-h-[89vh] flex items-center overflow-hidden bg-black pt-2" style={{ backgroundImage: 'url(/back.png)', backgroundSize: 'cover', backgroundPosition: 'center' }}>
      <div className="absolute inset-0 bg-gradient-to-r from-black/70 via-black/10 to-transparent"></div>

      <div className="relative max-w-5xl mx-9 px-6 sm:px-4 lg:px-4 pt-0.5">
        <div className="grid lg:grid-cols-1 gap-14 items-center">
          <motion.div
            initial={{ opacity: 0, y: 80 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1 }}
            className="text-left relative z-10"
          >
            <div className="mb-2">
              <span className="inline-flex items-center px-4 py-2 bg-red-600/90 backdrop-blur-sm text-white text-sm font-semibold rounded-full shadow-lg shadow-red-500/25">
                <AlertTriangle className="mr-2" size={16} />
                Emergency
              </span>
            </div>

            <h1 className="text-7xl md:text-7xl lg:text-7xl font-black text-white mb-7 leading-[1.05] tracking-tight">
              <span className="block mb-2">Smart-Emergency</span>
              <span className="block text-red-600">Response Platform</span>
              <span className="block text-5xl lg:text-5xl font-bold text-red-600 mt-3">AI Detection System</span>
            </h1>

            <p className="text-lg lg:text-xl text-gray-100 mb-8 max-w-2xl leading-relaxed font-light">
              Advanced AI-powered accident detection with real-time alerts,
              instant emergency response, and comprehensive analytics dashboard for national highway safety.
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              <button onClick={() => navigate("/login")} className="px-2 py-2 bg-gradient-to-r from-green-600 to-green-700 text-white text-base font-semibold rounded-xl hover:from-red-700 hover:to-green-800 shadow-lg shadow-green-500/25 hover:shadow-xl hover:shadow-green-500/30 transition-all duration-300 transform hover:scale-105">
                Access Panel
                <ArrowRight className="inline ml-4" size={14} />
              </button>
              <button onClick={() => navigate("/login")} className="px-5 py-2 bg-white/10 backdrop-blur-sm text-white text-base font-semibold border border-white/20 rounded-xl hover:bg-yellow-500/20 transition-all duration-300">
                More
              </button>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="absolute inset-0 pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 bg-cyan-400 rounded-full opacity-30 animate-ping"
            style={{
              top: `${Math.random() * 100}%`,
              left: `${Math.random() * 100}%`,
              animationDuration: `${2 + Math.random() * 5}s`,
            }}
          />
        ))}
      </div>
    </section>
  );
}

function StatisticsSection() {
  const stats = [
    {
      icon: Activity,
      title: "Detection Accuracy",
      value: "95.8%",
      subtitle: "AI Precision",
      gradient: "from-cyan-400 via-blue-500 to-indigo-600",
      glow: "shadow-cyan-500/30",
      border: "border-cyan-400/20",
    },
    {
      icon: Clock,
      title: "Response Time",
      value: "2.3s",
      subtitle: "Emergency Alert",
      gradient: "from-green-400 via-emerald-500 to-green-700",
      glow: "shadow-green-500/30",
      border: "border-green-400/20",
    },
    {
      icon: AlertTriangle,
      title: "Incidents Tracked",
      value: "68+",
      subtitle: "Live Monitoring",
      gradient: "from-yellow-400 via-orange-500 to-red-600",
      glow: "shadow-yellow-500/30",
      border: "border-yellow-400/20",
    },
    {
      icon: MapPin,
      title: "Cities Connected",
      value: "10+",
      subtitle: "Nationwide Coverage",
      gradient: "from-purple-400 via-pink-500 to-fuchsia-600",
      glow: "shadow-purple-500/30",
      border: "border-purple-400/20",
    },
  ];

  return (
    <section id="statistics" className="relative py-12 bg-[#030712] overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
            backgroundSize: "20px 60px",
          }}
        />
        <div className="absolute top-5 left-10 w-[250px] h-[250px] bg-cyan-500/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-5 right-10 w-[250px] h-[250px] bg-purple-500/10 blur-[120px] rounded-full" />
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="absolute h-[1px] bg-cyan-400/10 animate-pulse" style={{ top: `${i * 10}%`, width: "100%", animationDuration: `${2 + i}s` }} />
          ))}
        </div>
      </div>

      <div className="relative max-w-7x1 mx-auto px-8 sm:px-8 lg:px-14">
        <motion.div
          initial={{ opacity: 0, y: 70 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-cyan-500/10 border border-cyan-400/20 mb-6 backdrop-blur-xl">
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-ping" />
            <span className="text-cyan-300 text-sm tracking-widest uppercase">Live AI Monitoring</span>
          </div>
          <h2 className="text-5xl lg:text-5xl font-black text-white mb-4 leading-tight">
            National Highway
            <span className="block bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">Intelligence Center</span>
          </h2>
          <p className="text-gray-200 text-lg max-w-3xl mx-auto leading-relaxed">
            Advanced artificial intelligence continuously monitors, analyzes, and protects highways with real-time emergency response systems.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-1 lg:grid-cols-4 gap-9">
          {stats.map((stat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 80 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: index * 0.15 }}
              viewport={{ once: true }}
              className="group"
            >
              <div className={`relative h-full rounded-[25px] p-[1px] bg-gradient-to-br ${stat.gradient}`}>
                <div className={`relative h-full rounded-[25px] bg-[#0b1120]/90 backdrop-blur-2xl border ${stat.border} overflow-hidden p-2 transition-all duration-500 hover:-translate-y-2 hover:${stat.glow} hover:shadow-2xl`}>
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-all duration-700">
                    <div className="absolute top-0 -left-full w-[200%] h-full bg-gradient-to-r from-transparent via-white/10 to-transparent rotate-12 animate-[shine_2s_linear_infinite]" />
                  </div>
                  <div className={`absolute -top-24 right-0 w-40 h-40 bg-gradient-to-br ${stat.gradient} opacity-20 blur-[90px]`} />
                  <div className={`relative w-10 h-10 rounded-3xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-2xl mb-8`}>
                    <stat.icon size={30} className="text-white" />
                  </div>
                  <div className="relative">
                    <h3 className="text-5xl font-black text-white tracking-tight">{stat.value}</h3>
                    <div className={`mt-2 h-1 w-20 rounded-full bg-gradient-to-r ${stat.gradient}`} />
                  </div>
                  <div className="mt-6">
                    <p className="text-xl font-semibold text-white">{stat.title}</p>
                    <p className="text-gray-400 text-sm mt-2 tracking-wide">{stat.subtitle}</p>
                  </div>
                  <div className="mt-8 flex items-center justify-between text-xs text-gray-500">
                    <span>LIVE STATUS</span>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                      ACTIVE
                    </div>
                  </div>
                  <div className="absolute top-4 right-4 w-12 h-12 border-t border-r border-white/10 rounded-tr-2xl" />
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 80 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          viewport={{ once: true }}
          className="mt-20"
        >
          <div className="relative rounded-[30px] border border-cyan-400/10 bg-white/5 backdrop-blur-2xl overflow-hidden p-8">
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-transparent to-blue-500/5" />
            <div className="relative flex flex-col lg:flex-row items-center justify-between gap-8">
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <Zap className="text-cyan-400" size={24} />
                  <h3 className="text-2xl font-bold text-white">AI Command Center Status</h3>
                </div>
                <p className="text-gray-400 max-w-2xl">
                  Real-time intelligent traffic monitoring with predictive accident analysis and automated emergency coordination.
                </p>
              </div>
              <div className="flex items-center gap-10">
                <div>
                  <div className="text-3xl font-black text-cyan-400">248</div>
                  <div className="text-gray-500 text-sm">Cameras Online</div>
                </div>
                <div>
                  <div className="text-3xl font-black text-green-400">24/7</div>
                  <div className="text-gray-500 text-sm">Monitoring</div>
                </div>
                <div>
                  <div className="text-3xl font-black text-yellow-400">LIVE</div>
                  <div className="text-gray-500 text-sm">System Health</div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function ServicesSection() {
  const services = [
    {
      icon: Camera,
      title: "AI Accident Detection",
      description: "Real-time computer vision system detects highway accidents with ultra-fast deep learning analysis.",
      gradient: "from-cyan-400 via-blue-500 to-indigo-600",
      border: "border-cyan-400/20",
      glow: "shadow-cyan-500/30",
      status: "ACTIVE",
    },
    {
      icon: AlertTriangle,
      title: "Instant  Alerts",
      description: "Automatically sends emergency notifications to hospitals, police, and rescue teams within seconds.",
      gradient: "from-red-400 via-orange-500 to-yellow-500",
      border: "border-orange-400/20",
      glow: "shadow-orange-500/30",
      status: "LIVE",
    },
    {
      icon: MapPin,
      title: "Smart GPS Tracking",
      description: "Advanced live location tracking with route optimization and emergency navigation support.",
      gradient: "from-green-400 via-emerald-500 to-teal-600",
      border: "border-green-400/20",
      glow: "shadow-green-500/30",
      status: "ONLINE",
    },
    {
      icon: BarChart3,
      title: "AI Analytics Dashboard",
      description: "Powerful analytics with accident prediction,live reports, and intelligent insights.",
      gradient: "from-purple-400 via-fuchsia-500 to-pink-600",
      border: "border-purple-400/20",
      glow: "shadow-purple-500/30",
      status: "RUNNING",
    },
    {
      icon: Shield,
      title: "Cyber Security System",
      description: "Enterprise-grade encrypted infrastructure with secure AI monitoring and protected data flow.",
      gradient: "from-yellow-400 via-amber-500 to-orange-600",
      border: "border-yellow-400/20",
      glow: "shadow-yellow-500/30",
      status: "SECURED",
    },
    {
      icon: Users,
      title: "Emergency Coordination",
      description: "Smart communication system connecting traffic police, ambulance teams, and rescue operators.",
      gradient: "from-pink-400 via-rose-500 to-red-600",
      border: "border-pink-400/20",
      glow: "shadow-pink-500/30",
      status: "CONNECTED",
    },
  ];

  return (
    <section id="services" className="relative py-12 bg-[#020817] overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
            backgroundSize: "40px 70px",
          }}
        />
        <div className="absolute top-0 left-0 w-[200px] h-[200px] bg-cyan-500/10 blur-[120px]" />
        <div className="absolute bottom-0 right-0 w-[200px] h-[200px] bg-purple-500/10 blur-[120px]" />
      </div>

      <div className="relative max-w-6xl mx-auto px-5 sm:px-4 lg:px-2">
        <motion.div
          initial={{ opacity: 0, y: 70 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-cyan-500/10 border border-cyan-400/20 mb-6 backdrop-blur-xl">
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-ping" />
            <span className="text-cyan-300 text-sm tracking-widest uppercase">Advanced AI Services</span>
          </div>
          <h2 className="text-5xl lg:text-5xl font-black text-white leading-tight">
            Intelligent Highway
            <span className="block bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">Protection System</span>
          </h2>
          <p className="text-gray-200 text-lg max-w-3xl mx-auto mt-4 leading-relaxed">
            Advanced AI-powered technologies delivering real-time monitoring, emergency coordination, predictive analytics, and intelligent highway safety management.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {services.map((service, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 80 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: index * 0.15 }}
              viewport={{ once: true }}
              className="group"
            >
              <div className={`relative rounded-[32px] p-[1px] bg-gradient-to-br ${service.gradient}`}>
                <div className={`relative h-full rounded-[32px] bg-[#0b1120]/90 backdrop-blur-2xl border ${service.border} overflow-hidden p-8 transition-all duration-700 hover:-translate-y-3 hover:${service.glow} hover:shadow-2xl`}>
                  <div className={`absolute -top-24 right-0 w-40 h-40 bg-gradient-to-br ${service.gradient} opacity-20 blur-[90px]`} />
                  <div className={`w-10 h-10 rounded-3xl bg-gradient-to-br ${service.gradient} flex items-center justify-center shadow-2xl mb-8`}>
                    <service.icon size={38} className="text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-4">{service.title}</h3>
                  <p className="text-gray-400 leading-relaxed text-base">{service.description}</p>
                  <div className="mt-8 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                      <span className="text-sm text-gray-400">{service.status}</span>
                    </div>
                    <ArrowRight size={20} className="text-white group-hover:translate-x-2 transition-transform duration-300" />
                  </div>
                  <div className="absolute top-4 right-4 w-14 h-14 border-t border-r border-white/10 rounded-tr-2xl" />
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProcessSection() {
  const steps = [
    {
      icon: Camera,
      title: "AI Camera Monitoring",
      description: "Smart highway cameras continuously capture live traffic using AI-powered systems.",
      gradient: "from-cyan-400 to-blue-600",
    },
    {
      icon: Activity,
      title: "Real-Time AI Analysis",
      description: "Deep learning algorithms instantly analyze accidents, traffic density, and dangerous activities.",
      gradient: "from-green-400 to-emerald-600",
    },
    {
      icon: AlertTriangle,
      title: "Alert System",
      description: "Automatic emergency alerts are sent to hospitals, police stations, and rescue teams.",
      gradient: "from-yellow-400 to-orange-600",
    },
    {
      icon: Shield,
      title: "Rapid  Action",
      description: "AI command center coordinates emergency response and traffic control in real-time.",
      gradient: "from-purple-400 to-pink-600",
    },
  ];

  return (
    <section id="about" className="relative py-12 bg-[#020617] overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
            backgroundSize: "70px 70px",
          }}
        />
        <div className="absolute top-0 left-0 w-[200px] h-[200px] bg-cyan-500/10 blur-[140px] rounded-full" />
        <div className="absolute bottom-0 right-0 w-[200px] h-[200px] bg-purple-500/10 blur-[140px] rounded-full" />
      </div>

      <div className="relative max-w-8xl mx-auto px-2 sm:px-2 lg:px-14">
        <motion.div
          initial={{ opacity: 0, y: 80 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
          viewport={{ once: true }}
          className="text-center mb-24"
        >
          <div className="inline-flex items-center gap-3 px-5 py-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 backdrop-blur-xl mb-8">
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-ping" />
            <span className="text-cyan-300 uppercase tracking-[0.3em] text-sm">AI Workflow System</span>
          </div>
          <h2 className="text-5xl lg:text-5xl font-black text-white leading-tight">
            How The AI System
            <span className="block bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">Works In Real-Time</span>
          </h2>
          <p className="mt-5 text-gray-200 text-lg max-w-3xl mx-auto leading-relaxed">
            Intelligent accident detection powered by artificial intelligence, automated monitoring, and rapid emergency coordination.
          </p>
        </motion.div>

        <div className="relative">
          <div className="hidden lg:block absolute top-36 left-0 w-full h-[2px] bg-gradient-to-r from-cyan-500 via-green-500 via-yellow-500 to-pink-500 opacity-30" />
          <div className="grid lg:grid-cols-4 gap-14 relative z-10">
            {steps.map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 80 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: index * 0.2 }}
                viewport={{ once: true }}
                className="group relative"
              >
                {index !== steps.length - 1 && (
                  <div className="lg:hidden absolute left-1/2 top-full w-[2px] h-14 bg-white/10 -translate-x-1/2" />
                )}
                <div className="relative rounded-[32px] p-[1px] bg-gradient-to-br from-white/10 to-white/5">
                  <div className="relative h-full rounded-[32px] bg-[#0b1120]/90 border border-white/10 backdrop-blur-2xl overflow-hidden p-8 transition-all duration-700 hover:-translate-y-4 hover:border-cyan-400/30 hover:shadow-[0_0_60px_rgba(34,211,238,0.15)]">
                    <div className={`absolute -top-24 right-0 w-40 h-40 bg-gradient-to-br ${step.gradient} opacity-20 blur-[100px]`} />
                    <div className="absolute top-5 right-5 text-5xl font-black text-white/5">0{index + 1}</div>
                    <div className={`relative w-10 h-10 rounded-3xl bg-gradient-to-br ${step.gradient} flex items-center justify-center shadow-2xl mb-8 group-hover:scale-110 transition-transform duration-500`}>
                      <step.icon size={42} className="text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-5">{step.title}</h3>
                    <p className="text-gray-400 leading-relaxed text-base">{step.description}</p>
                    <div className="mt-8 flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm text-green-400">
                        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                        ACTIVE
                      </div>
                      <ArrowRight className="text-white/30 group-hover:text-cyan-400 transition-colors duration-500" size={22} />
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 80 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          viewport={{ once: true }}
          className="mt-28"
        >
          
        </motion.div>
      </div>
    </section>
  );
}

function ContactSection() {
  const navigate = useNavigate();

  return (
    <section id="contact" className="relative py-12 bg-[#020617] overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
            backgroundSize: "50px 70px",
          }}
        />
        <div className="absolute top-0 left-0 w-[200px] h-[200px] bg-cyan-500/10 blur-[140px] rounded-full" />
        <div className="absolute bottom-0 right-0 w-[200px] h-[200px] bg-blue-500/10 blur-[140px] rounded-full" />
      </div>

      <div className="relative max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 60 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <div className="inline-flex items-center gap-3 px-5 py-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 mb-8">
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-ping" />
            <span className="text-cyan-300 uppercase tracking-[0.3em] text-sm">Contact AI Command Center</span>
          </div>
          <h2 className="text-5xl lg:text-5xl font-black text-white leading-tight">
            Connect With
            <span className="block bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">Emergency Intelligence</span>
          </h2>
          <p className="mt-5 text-gray-200 text-lg max-w-3xl mx-auto leading-relaxed">
            Get access to intelligent highway monitoring, AI accident detection, and real-time emergency response systems.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-10">
          <motion.div
            initial={{ opacity: 0, x: -60 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 1 }}
            viewport={{ once: true }}
            className="relative rounded-[35px] border border-white/10 bg-white/5 backdrop-blur-2xl overflow-hidden p-10"
          >
            <div className="absolute top-0 right-0 w-[250px] h-[250px] bg-cyan-500/10 blur-[100px]" />
            <h3 className="text-3xl font-bold text-white mb-10">AI Emergency Support</h3>
            <div className="space-y-8">
              <div className="flex items-start gap-5">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-2xl">
                  <Phone className="text-white" size={28} />
                </div>
                <div>
                  <h4 className="text-xl font-semibold text-white">Emergency Helpline</h4>
                  <p className="text-gray-400 mt-2">24/7 AI integrated emergency response center.</p>
                  <div className="text-cyan-400 mt-3 text-lg font-semibold">1033-100-108-102</div>
                </div>
              </div>
              <div className="flex items-start gap-5">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-2xl">
                  <Mail className="text-white" size={28} />
                </div>
                <div>
                  <h4 className="text-xl font-semibold text-white"> Mail</h4>
                  <p className="text-gray-400 mt-2">Connect directly with  administrators.</p>
                  <div className="text-green-400 mt-3 text-lg font-semibod">smartalert@gmail.com</div>
                </div>
              </div>
              <div className="flex items-start gap-5">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center shadow-2xl">
                  <MapPin className="text-white" size={28} />
                </div>
                <div>
                  <h4 className="text-xl font-semibold text-white">Command Center</h4>
                  <p className="text-gray-400 mt-2">National AI highway surveillance headquarters.</p>
                  <div className="text-purple-400 mt-3 text-lg font-semibold">SRCOE Pune, India</div>
                </div>
              </div>
            </div>
            <div className="mt-12 rounded-3xl border border-cyan-400/10 bg-cyan-500/5 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-semibold text-lg">AI System Status</div>
                  <div className="text-gray-400 text-sm mt-2">All monitoring systems operational.</div>
                </div>
                <div className="flex items-center gap-3 text-green-400 font-semibold">
                  <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse" />
                  ONLINE
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 60 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 1 }}
            viewport={{ once: true }}
            className="relative rounded-[35px] border border-white/10 bg-white/5 backdrop-blur-2xl overflow-hidden p-10"
          >
            <div className="absolute bottom-0 left-0 w-[250px] h-[250px] bg-blue-500/10 blur-[100px]" />
            <h3 className="text-3xl font-bold text-white mb-10">Send Request</h3>
            <div className="space-y-6">
              <div>
                <label className="text-gray-300 text-sm mb-3 block">Full Name</label>
                <input type="text" placeholder="Enter your name" className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-4 text-white placeholder:text-gray-500 outline-none focus:border-cyan-400/40 transition-all duration-300" />
              </div>
              <div>
                <label className="text-gray-300 text-sm mb-3 block">Email Address</label>
                <input type="email" placeholder="Enter your email" className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-4 text-white placeholder:text-gray-500 outline-none focus:border-cyan-400/40 transition-all duration-300" />
              </div>
              <div>
                <label className="text-gray-300 text-sm mb-3 block">Message</label>
                <textarea rows="5" placeholder="Type your message..." className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-4 text-white placeholder:text-gray-500 outline-none resize-none focus:border-cyan-400/40 transition-all duration-300" />
              </div>
              <button onClick={() => navigate("/login")} className="w-full py-5 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-lg font-semibold hover:scale-[1.02] transition-all duration-300 shadow-[0_0_40px_rgba(34,211,238,0.25)]">
                Send
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="py-9 bg-gray-900 text-gray-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-4 gap-9">
          <div>
            <div className="flex items-center space-x-3 mb-5">
              <div className="w-80 h-90 bg-gray-100 rounded-lg flex items-center justify-center">
                <img src="/logo.png" alt="USE Logo" className="w-18 h-18 object-contain" />
              </div>
              <div>
                <div className="text-sm font-bold text-white">Smart-Emergency-Response-Platform</div>
                <div className="text-xs text-gray-400">AI Detection System</div>
              </div>
            </div>
            <p className="text-sm text-gray-400">Creating safer journeys with AI-based highway monitoring.</p>
          </div>

          <div>
            <h3 className="text-white font-semibold mb-4 text-sm">Quick Links</h3>
            <ul className="space-y-2">
              {["About System", "Services", "Documentation", "Support"].map((link) => (
                <li key={link}>
                  <a href="#" className="text-gray-400 hover:text-white transition-colors duration-200 text-sm">{link}</a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-white font-semibold mb-4 text-sm">Contact</h3>
            <ul className="space-y-2 text-gray-400 text-sm">
              <li className="flex items-center space-x-2">
                <Phone size={14} />
                <span>📞 1033-HIGHWAY</span>
              </li>
              <li className="flex items-center space-x-2">
                <Mail size={14} />
                <span>info@highwaysafety.gov</span>
              </li>
              <li className="flex items-center space-x-2">
                <Building size={14} />
                <span>Ambulance 108/102</span>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-white font-semibold mb-4 text-sm">Official</h3>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Globe size={14} />
                <span className="text-sm text-gray-400">.Official Site</span>
              </div>
              <div className="text-xs text-gray-500">Certified System</div>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-gray-700 text-center">
          <p className="text-sm text-gray-400">
            © 2026 National Highway Safety AI Detection System Official Website.
          </p>
        </div>
      </div>
    </footer>
  );
}

export default function Home() {
  return (
    <div className="min-h-screen bg-[#050816] text-white overflow-hidden">
      <Navbar />
      <HeroSection />
      <StatisticsSection />
      <ServicesSection />
      <ProcessSection />
      <ContactSection />
      <Footer />
    </div>
  );
}
