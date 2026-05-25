/**
 * FILE: frontend/src/pages/History.jsx
 * ===========================================
 * Incident History — Paginated, Searchable & Severity-Filtered Table
 *                  + Map View (Leaflet / react-leaflet)
 * ===========================================
 *
 * Dependencies added (install before use):
 *   npm install leaflet react-leaflet
 *
 * Leaflet CSS is imported directly below — required for map tiles and
 * marker positioning to render correctly.
 */

import { useState, useEffect, useMemo } from "react";
import { Search, ChevronLeft, ChevronRight, Loader2, Filter, RefreshCw, Table2, Map } from "lucide-react";

// ── Leaflet ────────────────────────────────────────────────────────────
// CSS must be imported before any Leaflet component is mounted.
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";

// Fix Leaflet icon issues in React/Webpack environments
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

import { getAccidents }                        from "../services/api";
import { SEVERITY_COLOR, STATUS_COLOR,
         shortDateTime, padId, pct }           from "../utils/helpers";

// ─────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

const SEVERITY_OPTIONS = ["All", "Critical", "High", "Medium", "Low"];

const SEVERITY_LABEL_COLOR = {
  Critical: "#FF3B30",
  High:     "#FF9500",
  Medium:   "#FFD60A",
  Low:      "#30D158",
};

/** SVG dot colour per severity — used for custom Leaflet icons */
const SEVERITY_DOT_COLOR = {
  critical: "#FF3B30",
  high:     "#FF9500",
  medium:   "#FFD60A",
  low:      "#30D158",
};

/** Normalize severity values consistently across the component */
const normalizeSeverity = (severity) => {
  if (!severity) return "unknown";
  return String(severity).toLowerCase().trim();
};

const COLUMNS = [
  { label: "ID",          width: "60px"  },
  { label: "Location",    width: "200px" },
  { label: "Severity",    width: "90px"  },
  { label: "Status",      width: "100px" },
  { label: "Camera",      width: "90px"  },
  { label: "AI Score",    width: "80px"  },
  { label: "Detected At", width: "150px" },
  { label: "Resolved At", width: "150px" },
];

/** Default map centre — Pune, Maharashtra */
const PUNE_CENTER = [18.5204, 73.8567];
const DEFAULT_ZOOM = 12;

// ─────────────────────────────────────────────────────────────────────
// Custom Leaflet icon factory
// ─────────────────────────────────────────────────────────────────────

/**
 * createSeverityIcon(severity)
 *
 * Returns a L.DivIcon rendered as a coloured SVG circle so the icon
 * colour mirrors the incident severity without relying on image files.
 * *
 * @param {string} severity  - e.g. "Critical", "high", "MEDIUM" (any case)
 * @returns {L.DivIcon}
 */


function createSeverityIcon(severity) {
  // Use consistent severity normalization
  const key = normalizeSeverity(severity);

 
  if (_iconCache[key]) return _iconCache[key];

  const color     = SEVERITY_DOT_COLOR[key] ?? "#888888";
  const outerSize = 22; // px — total clickable area
  const innerSize = 13; // px — visible dot

  const html = `
    <div style="
      width:${outerSize}px;
      height:${outerSize}px;
      display:flex;
      align-items:center;
      justify-content:center;
    ">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="${innerSize}"
        height="${innerSize}"
        viewBox="0 0 ${innerSize} ${innerSize}"
      >
        <!-- outer glow ring -->
        <circle
          cx="${innerSize / 2}" cy="${innerSize / 2}" r="${innerSize / 2 - 0.5}"
          fill="${color}33"
          stroke="${color}"
          stroke-width="1.5"
        />
        <!-- solid centre -->
        <circle
          cx="${innerSize / 2}" cy="${innerSize / 2}" r="${innerSize / 2 - 3.5}"
          fill="${color}"
        />
      </svg>
    </div>`;

  
  _iconCache[key] = L.divIcon({
    html,
    className:    "",                       // suppress Leaflet's default white box
    iconSize:     [outerSize, outerSize],
    iconAnchor:   [outerSize / 2, outerSize / 2],
    popupAnchor:  [0, -(outerSize / 2)],
  });

  return _iconCache[key];
}

// ─────────────────────────────────────────────────────────────────────
// RecenterMap helper
// ─────────────────────────────────────────────────────────────────────

/**
 * RecenterMap
 *
 * Must be rendered inside a <MapContainer> (react-leaflet context required).
 * Calls map.setView() smoothly whenever `center` changes — no re-mount,
 * no flicker, no tile reload.
 *
 * ADD: replaces the previous dynamic `key` prop on MapContainer which
 * caused a full destroy/recreate cycle on every filter or search change.
 */
function RecenterMap({ center }) {
  const map = useMap();

  useEffect(() => {
    if (center && center.length === 2) {
      map.setView(center, map.getZoom(), { animate: true });
    }
  }, [center, map]);

  // Renders nothing — side-effect only
  return null;
}

// ─────────────────────────────────────────────────────────────────────
// MapView sub-component
// ─────────────────────────────────────────────────────────────────────

/**
 * MapView
 *
 * Renders a Leaflet map with one Marker per filtered accident that has
 * valid lat/lng coordinates.  Records missing coordinates are silently
 * skipped — no runtime errors.
 *
 * Props:
 *   filtered {Array} — already-filtered accidents from the parent
 *

 */
function MapView({ filtered }) {
  
  const validMarkers = useMemo(() =>
    filtered.reduce((acc, item) => {
      
      const lat = parseFloat(item.latitude);
      const lng = parseFloat(item.longitude);
      if (!isFinite(lat) || !isFinite(lng)) return acc;   // skip silently
      acc.push({ ...item, _lat: lat, _lng: lng });
      return acc;
    }, []),
  [filtered]);

  
  const center = validMarkers.length > 0
    ? [validMarkers[0]._lat, validMarkers[0]._lng]
    : PUNE_CENTER;

  // REPLACE: check validMarkers (coord-validated), not filtered (all records).
  // filtered.length === 0 wrongly hides the empty state when records exist
  // but none have usable lat/lng coordinates.
  if (validMarkers.length === 0) {
    return (
      <div
        className="flex items-center justify-center"
        style={{
          height:       "600px",
          borderRadius: "8px",
          border:       "1px solid var(--border)",
          color:        "var(--text-muted)",
          fontSize:     "13px",
          fontFamily:   "'JetBrains Mono', monospace",
          background:   "var(--bg-card)",
        }}
      >
        No data to display on map
      </div>
    );
  }

  return (
    <div
      style={{
        borderRadius: "8px",
        overflow:     "hidden",
        border:       "1px solid var(--border)",
        height:       "600px",
      }}
    >
      <MapContainer
        center={center}
        zoom={DEFAULT_ZOOM}
        style={{ height: "100%", width: "100%", background: "#111827" }}
        preferCanvas={false}
      >
        {/* ADD: RecenterMap smoothly pans to new center via map.setView()
                 whenever `center` changes — no destroy/recreate cycle. */}
        <RecenterMap center={center} />

        {/* Dark-toned tile layer (CartoDB Dark Matter) */}
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap contributors'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />


        {validMarkers.map((acc) => {
         
          const icon = createSeverityIcon(acc.severity);

         
          const key = acc.id != null
            ? `marker-${acc.id}`
            : `marker-${acc._lat}-${acc._lng}`;

          
          const normalized = normalizeSeverity(acc.severity);
const proper = normalized.charAt(0).toUpperCase() + normalized.slice(1);
const badgeColor = SEVERITY_LABEL_COLOR[proper] ?? "#888888";

          return (
            <Marker key={key} position={[acc._lat, acc._lng]} icon={icon}>
              
              <Popup>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize:   "11px",
                    color:      "#E0EAF8",
                    minWidth:   "160px",
                    lineHeight: "1.7",
                  }}
                >
                  {/* Location */}
                  <div style={{ fontWeight: 700, marginBottom: "4px", fontSize: "12px" }}>
                    {acc.location ?? "—"}
                  </div>

                  {/* Severity badge — FIX 1: badgeColor already uses original casing */}
                  <div style={{ marginBottom: "3px" }}>
                    <span
                      style={{
                        color:         badgeColor,
                        background:    `${badgeColor}22`,
                        padding:       "1px 6px",
                        borderRadius:  "3px",
                        fontSize:      "10px",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        fontFamily:    "'Barlow Condensed', sans-serif",
                      }}
                    >
                      {acc.severity ?? "—"}
                    </span>
                  </div>

                  {/* Camera ID */}
                  <div style={{ color: "var(--text-muted, #888)", fontSize: "10px" }}>
                    Camera: {acc.camera_id ?? "—"}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────

export default function History() {
  // ── Existing state ────────────────────────────────────────────────
  const [accidents,       setAccidents]       = useState([]);
  const [loading,         setLoading]         = useState(true);
  const [error,           setError]           = useState(null);
  const [page,            setPage]            = useState(0);
  const [hasMore,         setHasMore]         = useState(false);

  const [search,          setSearch]          = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [severityFilter,  setSeverityFilter]  = useState("All");
  const [retryKey,        setRetryKey]        = useState(0);

  // ── NEW: active view state ────────────────────────────────────────
  // "table" (default) | "map"
  const [view, setView] = useState("table");

  // ── Effect 1: Reset page on raw search change ─────────────────────
  useEffect(() => {
    setPage(0);
  }, [search]);

  // ── Effect 2: Debounce search value used for fetching ─────────────
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // ── Effect 3: Fetch current page ──────────────────────────────────
  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setAccidents([]);
    setError(null);

    const fetchPage = async () => {
      try {
         const { data } = await getAccidents(
  {
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,

    // Search
    search: debouncedSearch.trim() || undefined,

    // Severity filter
    severity:
      severityFilter !== "All"
        ? severityFilter.toLowerCase()
        : undefined,
  },
  { signal: controller.signal }
);
        setAccidents(data);
        setHasMore(data.length >= PAGE_SIZE);
      } catch (err) {
        if (err.name === "AbortError") return;
        setError("Failed to load incident history.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchPage();
    return () => controller.abort();

  }, [page, debouncedSearch, severityFilter, retryKey]);

  // ── Memoised client-side filtering (shared by both views) ─────────
  const filtered = useMemo(() => {
    const isAll        = severityFilter === "All";
    const severityNorm = isAll ? "" : severityFilter.toLowerCase();
    const searchNorm   = debouncedSearch.trim().toLowerCase();
    const hasSearch    = searchNorm.length > 0;

    return accidents.filter((acc) => {
      const location = (acc.location  ?? "").toLowerCase();
      const severity = normalizeSeverity(acc.severity);
      const cameraId = (acc.camera_id ?? "").toLowerCase();

      const matchesSeverity = isAll || severity === severityNorm;
      const matchesSearch   =
        !hasSearch ||
        location.includes(searchNorm) ||
        cameraId.includes(searchNorm) ||
        severity.includes(searchNorm);

      return matchesSeverity && matchesSearch;
    });
  }, [accidents, debouncedSearch, severityFilter]);

  
  // call inside JSX on every render of the map-view footer.
  const validMarkerCount = useMemo(() =>
    filtered.filter(
      (a) => isFinite(parseFloat(a.latitude)) && isFinite(parseFloat(a.longitude))
    ).length,
  [filtered]);

  // ── Context-aware empty-state message ─────────────────────────────
  const emptyMessage = useMemo(() => {
    const hasSeverity = severityFilter !== "All";
    const hasSearch   = debouncedSearch.trim().length > 0;

    if (hasSeverity && hasSearch)
      return `No accidents found for "${severityFilter}" severity and search "${debouncedSearch.trim()}"`;
    if (hasSeverity)
      return `No accidents found for "${severityFilter}" severity`;
    if (hasSearch)
      return `No accidents found for search "${debouncedSearch.trim()}"`;
    return "No records found";
  }, [severityFilter, debouncedSearch]);

  // ── Shared button style helper ────────────────────────────────────
  const viewBtnStyle = (active) => ({
    display:        "inline-flex",
    alignItems:     "center",
    gap:            "5px",
    padding:        "6px 14px",
    borderRadius:   "6px",
    fontSize:       "11px",
    fontFamily:     "'Barlow Condensed', sans-serif",
    letterSpacing:  "0.06em",
    textTransform:  "uppercase",
    cursor:         "pointer",
    transition:     "background 0.15s, color 0.15s",
    border:         active ? "1px solid var(--border-active, #2979FF)" : "1px solid var(--border)",
    background:     active ? "rgba(41,121,255,0.12)"                  : "var(--bg-card)",
    color:          active ? "#2979FF"                                 : "var(--text-muted)",
    fontWeight:     active ? 700                                       : 400,
  });

  // ─────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────
  return (
    <div className="page-enter max-w-6xl mx-auto">

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1
            className="text-2xl font-bold"
            style={{ fontFamily: "'Barlow Condensed', sans-serif", letterSpacing: "0.04em" }}
          >
            INCIDENT HISTORY
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            Full historical log — page {page + 1}
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">

          {/* ── NEW: View toggle (Table | Map) ────────────────────── */}
          <div
            style={{
              display:      "flex",
              gap:          "4px",
              background:   "var(--bg-card)",
              border:       "1px solid var(--border)",
              borderRadius: "8px",
              padding:      "3px",
            }}
            role="group"
            aria-label="Switch view"
          >
            <button
              onClick={() => setView("table")}
              style={viewBtnStyle(view === "table")}
              aria-pressed={view === "table"}
              aria-label="Table view"
            >
              <Table2 size={12} aria-hidden="true" />
              Table
            </button>
            <button
              onClick={() => setView("map")}
              style={viewBtnStyle(view === "map")}
              aria-pressed={view === "map"}
              aria-label="Map view"
            >
              <Map size={12} aria-hidden="true" />
              Map
            </button>
          </div>

          {/* Severity filter dropdown */}
          <div className="relative flex items-center gap-2">
            <Filter size={13} style={{ color: "var(--text-muted)" }} aria-hidden="true" />
            <select
              aria-label="Filter by severity"
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(0);
              }}
              className="appearance-none pl-3 pr-8 py-2 rounded-md text-xs outline-none cursor-pointer"
              style={{
                background:         "var(--bg-card)",
                border:             "1px solid var(--border)",
                color:              severityFilter === "All"
                                      ? "#E0EAF8"
                                      : SEVERITY_LABEL_COLOR[severityFilter] || "#E0EAF8",
                fontFamily:         "'JetBrains Mono', monospace",
                backgroundImage:    `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E")`,
                backgroundRepeat:   "no-repeat",
                backgroundPosition: "right 8px center",
                minWidth:           "130px",
              }}
            >
              {SEVERITY_OPTIONS.map((opt) => (
                <option
                  key={opt}
                  value={opt}
                  style={{
                    color:      opt === "All" ? "#E0EAF8" : SEVERITY_LABEL_COLOR[opt],
                    background: "var(--bg-card, #1a1f2e)",
                  }}
                >
                  {opt}
                </option>
              ))}
            </select>
          </div>

          {/* Search box */}
          <div className="relative">
            <Search
              size={13}
              className="absolute left-3 top-1/2 -translate-y-1/2"
              style={{ color: "var(--text-muted)" }}
              aria-hidden="true"
            />
            <input
              type="search"
              aria-label="Search incidents"
              placeholder="Search by location, camera, severity…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-4 py-2 rounded-md text-xs outline-none"
              style={{
                background: "var(--bg-card)",
                border:     "1px solid var(--border)",
                color:      "#E0EAF8",
                width:      "260px",
                fontFamily: "'JetBrains Mono', monospace",
              }}
            />
          </div>
        </div>
      </div>

      {/* ── Content: Table OR Map ────────────────────────────────────── */}
      {view === "table" ? (

        /* ════════════════════════════════════════════════════════════
           TABLE VIEW  (unchanged from original)
           ════════════════════════════════════════════════════════════ */
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs" aria-label="Incident history table">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {COLUMNS.map(({ label, width }) => (
                    <th
                      key={label}
                      scope="col"
                      className="text-left px-4 py-3 uppercase tracking-widest font-semibold"
                      style={{
                        color:      "var(--text-muted)",
                        fontFamily: "'Barlow Condensed', sans-serif",
                        minWidth:   width,
                      }}
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {loading ? (
                    [...Array(8)].map((_, i) => (
                      <tr key={i}>
                        <td colSpan={COLUMNS.length} className="px-4 py-2">
                          <div className="loading-skeleton h-16 rounded-lg" />
                        </td>
                      </tr>
                    ))
                  )
                 : error ? (
                  <tr>
                    <td colSpan={COLUMNS.length} className="text-center py-10">
                      <span style={{ color: "var(--red)" }}>{error}</span>
                      <button
                        onClick={() => setRetryKey((k) => k + 1)}
                        aria-label="Retry loading incidents"
                        className="inline-flex items-center gap-1 ml-3 px-2 py-1 rounded text-xs transition-opacity hover:opacity-70"
                        style={{
                          background: "var(--bg-card)",
                          border:     "1px solid var(--border)",
                          color:      "#E0EAF8",
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                      >
                        <RefreshCw size={11} aria-hidden="true" />
                        Retry
                      </button>
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={COLUMNS.length} className="text-center py-10" style={{ color: "var(--text-muted)" }}>
                      {emptyMessage}
                    </td>
                  </tr>
                ) : (
                  filtered.map((acc, idx) => (
                    <tr
                      key={acc.id ?? `fallback-${idx}`}
                      style={{
                        borderBottom: "1px solid var(--border)",
                        background:   idx % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)",
                      }}
                    >
                      <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                        #{padId(acc.id)}
                      </td>
                      <td className="px-4 py-3 max-w-xs" style={{ color: "#E0EAF8" }} title={acc.location ?? ""}>
                        <div className="truncate">{acc.location ?? "—"}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className="px-2 py-0.5 rounded text-xs uppercase"
                          style={{
                            color:      SEVERITY_COLOR[acc.severity] || "#888",
                            background: `${SEVERITY_COLOR[acc.severity] || "#888"}18`,
                            fontFamily: "'Barlow Condensed', sans-serif",
                          }}
                        >
                          {acc.severity ?? "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3 capitalize" style={{ color: STATUS_COLOR[acc.status] || "#888" }}>
                        {acc.status ?? "—"}
                      </td>
                      <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                        {acc.camera_id ?? "—"}
                      </td>
                      <td className="px-4 py-3" style={{ color: acc.confidence ? "#2979FF" : "var(--text-dim)" }}>
                        {pct(acc.confidence)}
                      </td>
                      <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                        {shortDateTime(acc.detected_at)}
                      </td>
                      <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                        {acc.resolved_at ? shortDateTime(acc.resolved_at) : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* ── Pagination Controls ──────────────────────────────────── */}
          <div
            className="flex items-center justify-between px-4 py-3"
            style={{ borderTop: "1px solid var(--border)" }}
          >
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              Showing {filtered.length} of {accidents.length} records on page {page + 1}
              {debouncedSearch && ` (search: "${debouncedSearch.trim()}")`}
              {severityFilter !== "All" && ` · severity: ${severityFilter}`}
            </span>

            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                aria-label="Previous page"
                className="p-1.5 rounded transition-opacity disabled:opacity-30"
                style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "#E0EAF8" }}
              >
                <ChevronLeft size={14} />
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
                aria-label="Next page"
                className="p-1.5 rounded transition-opacity disabled:opacity-30"
                style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "#E0EAF8" }}
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>

      ) : (

        /* ════════════════════════════════════════════════════════════
           MAP VIEW  (new)
           ════════════════════════════════════════════════════════════ */
        <div className="panel overflow-hidden">

          {/* Loading / error states mirror the table view */}
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2
                size={20}
                className="animate-spin"
                style={{ color: "var(--text-muted)" }}
                aria-label="Loading…"
              />
            </div>
          ) : error ? (
            <div className="text-center py-10">
              <span style={{ color: "var(--red)" }}>{error}</span>
              <button
                onClick={() => setRetryKey((k) => k + 1)}
                aria-label="Retry loading incidents"
                className="inline-flex items-center gap-1 ml-3 px-2 py-1 rounded text-xs transition-opacity hover:opacity-70"
                style={{
                  background: "var(--bg-card)",
                  border:     "1px solid var(--border)",
                  color:      "#E0EAF8",
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                <RefreshCw size={11} aria-hidden="true" />
                Retry
              </button>
            </div>
          ) : (
            <>
              {/* Map */}
              <MapView filtered={filtered} />

              {/* Footer — consistent with table pagination bar */}
              <div
                className="flex items-center justify-between px-4 py-3"
                style={{ borderTop: "1px solid var(--border)" }}
              >
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  
                  {validMarkerCount} markers shown
                  {debouncedSearch && ` (search: "${debouncedSearch.trim()}")`}
                  {severityFilter !== "All" && ` · severity: ${severityFilter}`}
                </span>

                {/* Severity legend */}
                <div className="flex items-center gap-3">
                  {Object.entries(SEVERITY_DOT_COLOR).map(([sev, color]) => (
                    <span
                      key={sev}
                      className="flex items-center gap-1 text-xs capitalize"
                      style={{ color: "var(--text-muted)", fontFamily: "'JetBrains Mono', monospace" }}
                    >
                      <svg width="8" height="8" viewBox="0 0 8 8" aria-hidden="true">
                        <circle cx="4" cy="4" r="4" fill={color} />
                      </svg>
                      {sev}
                    </span>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
