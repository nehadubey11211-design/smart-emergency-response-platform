/**
 * FILE : frontend/src/pages/AmbulanceDashboard.jsx
 * -----------------------------
 * Main driver-facing dashboard page.
 * Features:
 *  Stadia Alidade Smooth Dark tiles — matches Google Maps dark navy theme
 *   Real-time WebSocket dispatch alerts with sound
 *    Dispatch banner with Accept / Reject buttons (wired up correctly)
 *    Live ambulance + accident  on map
 *   Hospital markers (named only, debounced, cleared on reject/complete)
 *    Triple-layer route line (shadow + blue + dashed highlight)
 *    GPS tracking → backend every tick
 *    Status badge + Go Offline toggle
 *    Complete Job button
 *    Route overview panel with hospital count
 *    Alert history feed
 *
 * Route: /ambulance/:ambulanceId
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import debounce from "lodash.debounce";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  useMap,
} from "react-leaflet";

import { useGlobalAmbulanceSocket } from "../context/AmbulanceSocketContext.jsx";
import { ambulanceApi }             from "../services/ambulanceApi";
import { getSignals }               from "../services/api";
import { AmbulanceAlertCard }       from "../components/ambulance/AmbulanceAlertCard";


delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// ── Accident site red pin ─────────────────────────────────────────────────────
const redIcon = new L.Icon({
  iconUrl:     "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl:   "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize:    [25, 41],
  iconAnchor:  [12, 41],
  popupAnchor: [1, -34],
});

// ── Ambulance emoji marker ────────────────────────────────────────────────────
const ambulanceIcon = L.divIcon({
  html: `<div style="
    width:32px;height:32px;
    display:flex;align-items:center;justify-content:center;
    font-size:24px;
    filter:drop-shadow(0 2px 4px rgba(0,0,0,0.8));
  ">🚑</div>`,
  
  className:   "custom-div-icon",
  iconSize:    [32, 32],
  iconAnchor:  [16, 16],
  popupAnchor: [0, -16],
});

// ── Hospital marker — red badge with glow ring ────────────────────────────────
const hospitalIcon = L.divIcon({
  html: `<div style="
    background:#ef4444;
    border:2.5px solid #fff;
    border-radius:7px;
    width:30px;height:30px;
    display:flex;align-items:center;justify-content:center;
    font-size:16px;
    box-shadow:0 0 0 3px rgba(239,68,68,0.4),0 2px 8px rgba(0,0,0,0.7);
    cursor:pointer;
  ">🏥</div>`,
  
  className:   "custom-div-icon",
  iconSize:    [30, 30],
  iconAnchor:  [15, 15],
  popupAnchor: [0, -18],
});

// ── Map fly-to helper ─────────────────────────────────────────────────────────
function MapFlyTo({ center }) {
  const map     = useMap();
  const prevRef = useRef(null);
  useEffect(() => {
    if (!center) return;
    const prev = prevRef.current;
    if (prev && prev[0] === center[0] && prev[1] === center[1]) return;
    prevRef.current = center;
    map.flyTo(center, map.getZoom(), { duration: 1.5, easeLinearity: 0.25 });
  }, [center, map]);
  return null;
}

// ── Encoded polyline decoder (Mapbox / OSRM) ──────────────────────────────────
function decodePolyline(encoded) {
  const coords = [];
  let index = 0, lat = 0, lng = 0;
  while (index < encoded.length) {
    let b, shift = 0, result = 0;
    do { b = encoded.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
    lat += (result & 1) ? ~(result >> 1) : result >> 1;
    shift = 0; result = 0;
    do { b = encoded.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
    lng += (result & 1) ? ~(result >> 1) : result >> 1;
    coords.push([lat / 1e5, lng / 1e5]);
  }
  return coords;
}

// ── Haversine distance in metres ──────────────────────────────────────────────
function haversineDistance([lat1, lon1], [lat2, lon2]) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat  = toRad(lat2 - lat1), dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2
          + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ── Traffic signal colour ─────────────────────────────────────────────────────
function getSignalColor(signal, myPosition) {
  if (signal.current_mode === "emergency") return "#22c55e";
  if (myPosition && haversineDistance(myPosition, [signal.latitude, signal.longitude]) < 120)
    return "#22c55e";
  if (signal.current_mode === "manual") return "#f59e0b";
  return "#60a5fa";
}

// ── Status display config ─────────────────────────────────────────────────────
const STATUS = {
  available: { label: "AVAILABLE",   dot: "#10b981", border: "#10b981", bg: "rgba(16,185,129,0.12)"  },
  busy:      { label: "ON DISPATCH", dot: "#f59e0b", border: "#f59e0b", bg: "rgba(245,158,11,0.12)"  },
  offline:   { label: "OFFLINE",     dot: "#6b7280", border: "#374151", bg: "rgba(107,114,128,0.10)" },
};

const HOSPITAL_REFETCH_M = 200;

// ════════════════════════════════════════════════════════════════════════════
export default function AmbulanceDashboard() {
  const { ambulanceId } = useParams();
  const id = parseInt(ambulanceId, 10) || 1;

  useEffect(() => { localStorage.setItem("ambulance_id", String(id)); }, [id]);

  const [unit,          setUnit]          = useState(null);
  const [loading,       setLoading]       = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const {
    isConnected, connectionStatus, lastAlert, alerts,
    pendingDispatch, acceptedDispatch,
    setPendingDispatch, setAcceptedDispatch,
  } = useGlobalAmbulanceSocket();

  const [myPosition,     setMyPosition]     = useState(null);
  const [accidentPos,    setAccidentPos]    = useState(null);
  const [trafficSignals, setTrafficSignals] = useState([]);
  const [routePath,      setRoutePath]      = useState([]);
  const [routeLoading,   setRouteLoading]   = useState(false);
  const [mapCenter,      setMapCenter]      = useState([18.5204, 73.8567]);
  const [hospitals,      setHospitals]      = useState([]);

  
  const lastHospitalFetchRef = useRef(null);




  const updateLocationDebounced = useCallback(

  debounce((lat, lon) => {

    ambulanceApi
      .updateLocation(id, lat, lon)
      .catch(() => {});

  }, 10_000),

[id]);

  // ── Initial load ──────────────────────────────────────────────────────────
  useEffect(() => {
    ambulanceApi.getById(id)
      .then(setUnit)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  // ── WebSocket: incoming dispatch alert ────────────────────────────────────
  useEffect(() => {
    if (!lastAlert) return;
    if (lastAlert.type === "DISPATCH_ALERT") {
      setPendingDispatch(lastAlert);
      setAccidentPos([lastAlert.accident_lat, lastAlert.accident_lon]);
      setMapCenter([lastAlert.accident_lat, lastAlert.accident_lon]);
    }
  }, [lastAlert, setPendingDispatch]);

  useEffect(() => {
    if (!acceptedDispatch) return;
    setAccidentPos([acceptedDispatch.accident_lat, acceptedDispatch.accident_lon]);
    setMapCenter([acceptedDispatch.accident_lat, acceptedDispatch.accident_lon]);
  }, [acceptedDispatch]);

  // ── Fetch nearby hospitals from Overpass API ──────────────────────────────
  const fetchHospitals = useCallback(async (lat, lon) => {
    // Only re-fetch if moved more than HOSPITAL_REFETCH_M metres
    const last = lastHospitalFetchRef.current;
    if (last && haversineDistance([last.lat, last.lon], [lat, lon]) < HOSPITAL_REFETCH_M) return;
    lastHospitalFetchRef.current = { lat, lon };

    const query = `
      [out:json][timeout:25];
      (
        node["amenity"="hospital"]["name"](around:3000,${lat},${lon});
        way["amenity"="hospital"]["name"](around:3000,${lat},${lon});
      );
      out center body;
    `;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 25000);

    try {
    
      const res = await fetch("https://overpass-api.de/api/interpreter", {
        method: "POST",
        body:   query,
        signal: controller.signal,
      });
      clearTimeout(timer);

    
      if (!res.ok) {
        throw new Error(`Overpass error: ${res.status}`);
      }

      const data = await res.json();
      setHospitals(
        (data.elements || [])
          .map((el) => ({ ...el, lat: el.lat ?? el.center?.lat, lon: el.lon ?? el.center?.lon }))
          .filter((el) => el.lat && el.lon)
      );
    } catch (err) {
      clearTimeout(timer);
      if (err.name === "AbortError") {
        console.warn("Overpass timeout — skipping hospitals");
      } else {
        console.warn("Overpass fetch failed:", err.message);
      }
    }
  }, []);

  // Accident position takes priority over GPS for hospital fetch center
  useEffect(() => {
    if (!accidentPos) return;
    fetchHospitals(accidentPos[0], accidentPos[1]);
  }, [accidentPos, fetchHospitals]);

  useEffect(() => {
    if (!myPosition || accidentPos) return;
    fetchHospitals(myPosition[0], myPosition[1]);
  }, [myPosition, accidentPos, fetchHospitals]);

  // ── Traffic signals polling ───────────────────────────────────────────────
  useEffect(() => {
    let active = true;
    const load = async () => {
      try { const { data } = await getSignals(); if (active) setTrafficSignals(data || []); }
      catch (err) { console.error("Signal load failed:", err); }
    };
    load();
    const iv = setInterval(load, 15_000);
    return () => { active = false; clearInterval(iv); };
  }, []);

  // ── Route geometry fetch ──────────────────────────────────────────────────
  const fetchRouteGeometry = useCallback(async (from, to) => {
    if (!from || !to) return [];
    const fLon = from.lon ?? from[1], fLat = from.lat ?? from[0];
    const tLon = to.lon   ?? to[1],   tLat = to.lat   ?? to[0];
    const tok  = import.meta.env.VITE_MAPBOX_TOKEN;
    try {
      if (tok) {
        const r = await fetch(`https://api.mapbox.com/directions/v5/mapbox/driving/${fLon},${fLat};${tLon},${tLat}?geometries=polyline&overview=full&access_token=${tok}`);
        if (!r.ok) throw new Error("Mapbox failed");
        const d = await r.json();
        const enc = d.routes?.[0]?.geometry;
        return enc ? decodePolyline(enc) : [];
      }
      const r = await fetch(`https://router.project-osrm.org/route/v1/driving/${fLon},${fLat};${tLon},${tLat}?overview=full&geometries=polyline`);
      if (!r.ok) throw new Error("OSRM failed");
      const d = await r.json();
      const enc = d.routes?.[0]?.geometry;
      return enc ? decodePolyline(enc) : [];
    } catch (err) { console.error("Route fetch failed:", err); return []; }
  }, []);

  useEffect(() => {
    let active = true;
    const build = async () => {
      if (!acceptedDispatch) { setRoutePath([]); return; }
      const from = acceptedDispatch.route?.from
        ? { lat: acceptedDispatch.route.from.lat, lon: acceptedDispatch.route.from.lon }
        : myPosition ? { lat: myPosition[0], lon: myPosition[1] }
        : { lat: unit?.latitude, lon: unit?.longitude };
      const to = acceptedDispatch.route?.to
        ? { lat: acceptedDispatch.route.to.lat, lon: acceptedDispatch.route.to.lon }
        : { lat: acceptedDispatch.accident_lat, lon: acceptedDispatch.accident_lon };
      if (!from?.lat || !to?.lat) { setRoutePath([]); return; }
      setRouteLoading(true);
      const path = await fetchRouteGeometry(from, to);
      if (active) {setRoutePath(path);
      setRouteLoading(false)};
    };
    build();
    return () => { active = false; };
  }, [acceptedDispatch, fetchRouteGeometry, myPosition, unit]);

  // ── GPS tracking ──────────────────────────────────────────────────────────
  useEffect(() => {

    if (!navigator.geolocation) return;

    const watchId = navigator.geolocation.watchPosition(

      ({ coords }) => {

        setMyPosition([
          coords.latitude,
          coords.longitude
        ]);

        updateLocationDebounced(
          coords.latitude,
          coords.longitude
        );
      },

      (err) =>
        console.warn("GPS unavailable:", err),

      {
        enableHighAccuracy: true,
        maximumAge: 15_000,
      }
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
      updateLocationDebounced.cancel();
    };

  }, [updateLocationDebounced]);

  // ── Accept dispatch ───────────────────────────────────────────────────────
  const handleAccept = useCallback(async () => {
    setActionLoading(true);
    try {
      await ambulanceApi.acceptDispatch(id);
      setUnit((prev) => ({ ...prev, status: "busy" }));
      if (pendingDispatch) {
        setAcceptedDispatch(pendingDispatch);
        setMapCenter([pendingDispatch.accident_lat, pendingDispatch.accident_lon]);
      }
      setPendingDispatch(null);
    } catch (e) { console.error("Accept failed:", e); }
    finally { setActionLoading(false); }
  }, [id, pendingDispatch, setAcceptedDispatch, setPendingDispatch]);

  const handleReject = useCallback(() => {
    setPendingDispatch(null);
    setAcceptedDispatch(null);
    setAccidentPos(null);
    setRoutePath([]);
    setHospitals([]);
    lastHospitalFetchRef.current = null;
  }, [setAcceptedDispatch, setPendingDispatch]);

  // ── Complete job ──────────────────────────────────────────────────────────
  const handleComplete = useCallback(async () => {
    setActionLoading(true);
    try {
      await ambulanceApi.completeDispatch(id, acceptedDispatch?.accident_id);
      setUnit((prev) => ({ ...prev, status: "available" }));
      setAccidentPos(null);
      setAcceptedDispatch(null);
      setRoutePath([]);
      setHospitals([]);
      lastHospitalFetchRef.current = null;
    } catch (e) { console.error("Complete failed:", e); }
    finally { setActionLoading(false); }
  }, [id, acceptedDispatch, setAcceptedDispatch]);

  // ── Go offline / online ───────────────────────────────────────────────────
  const toggleOffline = useCallback(async () => {
    if (!unit) return;
    const next = unit.status === "offline" ? "available" : "offline";
    try { await ambulanceApi.updateStatus(id, next); setUnit((p) => ({ ...p, status: next })); }
    catch (e) { console.error("Status update failed:", e); }
  }, [id, unit]);

  // ─────────────────────────────────────────────────────────────────────────
  if (loading) return (
    <div style={styles.loadingScreen}>
      <div style={styles.spinner} />
      <p style={{ color: "#9ca3af", marginTop: 16, fontFamily: "monospace", fontSize: 13 }}>
        Connecting to dispatch system...
      </p>
    </div>
  );

  const signalCounts = trafficSignals.reduce(
    (acc, sig) => { acc[sig.current_mode] = (acc[sig.current_mode] || 0) + 1; return acc; }, {}
  );

  const fallbackPos = myPosition ?? (unit?.latitude ? [unit.latitude, unit.longitude] : [18.5204, 73.8567]);
  const straightLine = acceptedDispatch
    ? [fallbackPos, [acceptedDispatch.accident_lat, acceptedDispatch.accident_lon]]
    : [];

  const st = STATUS[unit?.status || "offline"];

  return (
    <div style={styles.root}>

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={{ fontSize: 26 }}>🚑</span>
          <div>
            <h1 style={styles.headerTitle}>DISPATCH</h1>
            <p style={styles.headerSub}>
              {unit?.ambulance_number || `AMB-${id}`} · {unit?.driver_name || "Driver"}
            </p>
          </div>
        </div>
        <div style={styles.headerRight}>
          <div style={styles.wsRow}>
            <span style={{ ...styles.wsDot, background: isConnected ? "#10b981" : connectionStatus === "connecting" ? "#f59e0b" : "#ef4444" }} />
            <span style={styles.wsLabel}>{isConnected ? "LIVE" : connectionStatus.toUpperCase()}</span>
          </div>
          <div style={{ ...styles.statusBadge, borderColor: st.border, background: st.bg }}>
            <span style={{ ...styles.statusDot, background: st.dot }} />
            {st.label}
          </div>
          <button style={styles.btnSecondary} onClick={toggleOffline}>
            {unit?.status === "offline" ? "Go Online" : "Go Offline"}
          </button>
          {unit?.status === "busy" && (
            <button style={styles.btnComplete} onClick={handleComplete} disabled={actionLoading}>
              {actionLoading ? "..." : "✓ Complete Job"}
            </button>
          )}
        </div>
      </header>

      {pendingDispatch && (
        <div style={styles.dispatchBanner}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 22 }}>🚨</span>
            <div>
              <strong style={{ color: "#fff", fontSize: 13 }}>
                DISPATCH — {(pendingDispatch.severity || "").toUpperCase()}
              </strong>
              <p style={{ margin: 0, fontSize: 11, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>
                {pendingDispatch.location} · {pendingDispatch.distance_km} km · ETA {pendingDispatch.eta_minutes} min
              </p>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={styles.btnAccept} onClick={handleAccept} disabled={actionLoading}>
              {actionLoading ? "..." : "✓ Accept"}
            </button>
            <button style={styles.btnReject} onClick={handleReject}>✕ Reject</button>
          </div>
        </div>
      )}

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      <div style={styles.body}>

        {/* ── Map ── */}
        <div style={styles.mapWrap}>
          <MapContainer
            center={mapCenter} zoom={13}
            style={{ height: "100%", width: "100%", borderRadius: 12 }}
            scrollWheelZoom doubleClickZoom touchZoom dragging zoomControl
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='© <a href="https://openstreetmap.org">OpenStreetMap</a>'
            />

            <MapFlyTo center={mapCenter} />

            {myPosition && (
              <Marker position={myPosition} icon={ambulanceIcon}>
                <Popup>🚑 {unit?.ambulance_number} — Your location</Popup>
              </Marker>
            )}

            {acceptedDispatch && (
              <>
                <Marker position={[acceptedDispatch.accident_lat, acceptedDispatch.accident_lon]} icon={redIcon}>
                  <Popup>🚨 Accident — {acceptedDispatch.severity}</Popup>
                </Marker>

                {routePath.length > 0 ? (
                  <>
                    <Polyline positions={routePath} pathOptions={{ color: "rgba(0,0,0,0.55)", weight: 16, opacity: 0.5 }} />
                    <Polyline positions={routePath} pathOptions={{ color: "#4285F4", weight: 8, opacity: 1 }} />
                    <Polyline positions={routePath} pathOptions={{ color: "#93c5fd", weight: 3, opacity: 0.85, dashArray: "8, 14" }} />
                  </>
                ) : (
                  <Polyline positions={straightLine} pathOptions={{ color: "#4285F4", weight: 6, opacity: 0.85, dashArray: "6, 10" }} />
                )}

                {trafficSignals.map((signal) => (
                  <CircleMarker
                    key={signal.signal_id}
                    center={[signal.latitude, signal.longitude]}
                    pathOptions={{ color: getSignalColor(signal, myPosition), fillColor: getSignalColor(signal, myPosition), fillOpacity: 0.95 }}
                    radius={8}
                  >
                    <Popup>
                      <strong>Traffic signal</strong><br />
                      Mode: {signal.current_mode}<br />
                      {signal.location || ""}
                    </Popup>
                  </CircleMarker>
                ))}
              </>
            )}

            {hospitals.map((h) => (
              <Marker key={h.id} position={[h.lat, h.lon]} icon={hospitalIcon}>
                <Popup>
                  <div style={{ fontFamily: "Arial, sans-serif", minWidth: 160 }}>
                    <strong style={{ color: "#ef4444", display: "block", marginBottom: 4 }}>
                      🏥 {h.tags?.name || "Hospital"}
                    </strong>
                    {h.tags?.["addr:street"] && (
                      <span style={{ display: "block", fontSize: 12, color: "#555" }}>📍 {h.tags["addr:street"]}</span>
                    )}
                    {h.tags?.phone && (
                      <span style={{ display: "block", fontSize: 12, color: "#555", marginTop: 2 }}>📞 {h.tags.phone}</span>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}

          </MapContainer>

          {acceptedDispatch && (
            <div style={styles.routeOverlay}>
              <strong style={{ display: "block", marginBottom: 10, fontSize: 12 }}>Route overview</strong>
              {routeLoading ? <span style={{ opacity: 0.6, fontSize: 12 }}>Loading route…</span> : (
                <>
                  <OverlayRow label="Signals"   value={trafficSignals.length} />
                  <OverlayRow label="Emergency" value={signalCounts.emergency || 0} color="#22c55e" />
                  <OverlayRow label="Auto"      value={signalCounts.auto      || 0} />
                  <OverlayRow label="Manual"    value={signalCounts.manual    || 0} color="#f59e0b" />
                  <OverlayRow label="Hospitals" value={hospitals.length}            color="#fca5a5" />
                </>
              )}
            </div>
          )}
        </div>

        {/* ── Alert feed ───────────────────────────────────────────────────── */}
        <aside style={styles.feed}>
          <div style={styles.feedHeader}>
            <span>ALERT FEED</span>
            {alerts.length > 0 && <span style={styles.feedBadge}>{alerts.length}</span>}
          </div>
          <div style={styles.feedBody}>
            {alerts.length === 0 ? (
              <div style={styles.feedEmpty}>
                <span style={{ fontSize: 32 }}>📡</span>
                <p>Monitoring for emergencies…</p>
              </div>
            ) : (
           
              // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              alerts.map((a) => (
                <AmbulanceAlertCard
                  key={`${a.type}-${a.receivedAt}`}
                  alert={a}
                  isLatest={a === alerts[0]}
                />
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

// ── Route overview row helper ─────────────────────────────────────────────────
function OverlayRow({ label, value, color = "rgba(255,255,255,0.6)" }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5, fontSize: 12 }}>
      <span style={{ color: "rgba(255,255,255,0.38)" }}>{label}</span>
      <span style={{ color, fontWeight: 600 }}>{value}</span>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const styles = {
  root: {
    minHeight: "100vh", background: "#0b0f1e", color: "#e2e8f0",
    fontFamily: "'JetBrains Mono','Fira Code','Courier New',monospace",
    display: "flex", flexDirection: "column",
  },
  loadingScreen: {
    minHeight: "100vh", background: "#0b0f1e", display: "flex",
    flexDirection: "column", alignItems: "center", justifyContent: "center",
  },
  spinner: {
    width: 36, height: 36,
    border: "3px solid rgba(255,255,255,0.1)", borderTopColor: "#10b981",
    borderRadius: "50%", animation: "spin 0.75s linear infinite",
  },
  header: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "12px 20px", background: "#0f172a",
    borderBottom: "0.5px solid rgba(255,255,255,0.08)",
    flexWrap: "wrap", gap: 12, zIndex: 10,
  },
  headerLeft:  { display: "flex", alignItems: "center", gap: 12 },
  headerTitle: { margin: 0, fontSize: 16, fontWeight: 700, letterSpacing: "0.2em", color: "#fff" },
  headerSub:   { margin: 0, fontSize: 10, color: "rgba(255,255,255,0.35)", marginTop: 2 },
  headerRight: { display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" },

  dispatchBanner: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "12px 20px", background: "rgba(239,68,68,0.1)",
    borderBottom: "1px solid rgba(239,68,68,0.25)",
    flexWrap: "wrap", gap: 12, zIndex: 10,
  },

  btnAccept: {
    padding: "7px 18px", background: "#10b981", border: "none",
    color: "#fff", borderRadius: 6, cursor: "pointer",
    fontSize: 12, fontWeight: 700, fontFamily: "inherit",
  },
  btnReject: {
    padding: "7px 18px", background: "transparent",
    border: "0.5px solid rgba(239,68,68,0.5)", color: "#ef4444",
    borderRadius: 6, cursor: "pointer", fontSize: 12, fontFamily: "inherit",
  },

  wsRow:   { display: "flex", alignItems: "center", gap: 5 },
  wsDot:   { width: 7, height: 7, borderRadius: "50%", display: "inline-block" },
  wsLabel: { fontSize: 10, color: "rgba(255,255,255,0.45)", letterSpacing: "0.15em" },

  statusBadge: {
    display: "flex", alignItems: "center", gap: 6,
    padding: "5px 12px", borderRadius: 20, border: "0.5px solid",
    fontSize: 10, fontWeight: 700, letterSpacing: "0.12em",
  },
  statusDot: { width: 6, height: 6, borderRadius: "50%" },

  btnSecondary: {
    padding: "6px 12px", background: "transparent",
    border: "0.5px solid rgba(255,255,255,0.2)", color: "rgba(255,255,255,0.5)",
    borderRadius: 6, cursor: "pointer", fontSize: 11, fontFamily: "inherit",
  },
  btnComplete: {
    padding: "6px 14px", background: "rgba(16,185,129,0.12)",
    border: "0.5px solid #10b981", color: "#10b981",
    borderRadius: 6, cursor: "pointer", fontSize: 11, fontWeight: 700, fontFamily: "inherit",
  },

  body: {
    flex: 1, display: "grid", gridTemplateColumns: "1fr 320px", overflow: "hidden",
  },

  mapWrap: {
    padding: 14, position: "relative", minHeight: "calc(100vh - 68px)",
  },

  routeOverlay: {
    position: "absolute", left: 28, bottom: 28, zIndex: 1000,
    background: "rgba(15,23,42,0.94)", color: "#f8fafc",
    padding: "14px 16px", borderRadius: 14,
    boxShadow: "0 8px 32px rgba(0,0,0,0.4)", minWidth: 210, lineHeight: 1.5,
  },

  feed: {
    background: "#0f172a", borderLeft: "0.5px solid rgba(255,255,255,0.08)",
    display: "flex", flexDirection: "column", overflow: "hidden",
  },
  feedHeader: {
    padding: "12px 16px", borderBottom: "0.5px solid rgba(255,255,255,0.07)",
    fontSize: 10, letterSpacing: "0.18em", color: "rgba(255,255,255,0.3)",
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  feedBadge: {
    background: "rgba(239,68,68,0.2)", color: "#ef4444",
    borderRadius: 10, padding: "1px 8px", fontSize: 10,
  },
  feedBody:  { flex: 1, overflowY: "auto", padding: "10px 12px" },
  feedEmpty: {
    textAlign: "center", color: "rgba(255,255,255,0.15)",
    padding: "40px 16px", fontSize: 12, lineHeight: 2.5,
  },
};
