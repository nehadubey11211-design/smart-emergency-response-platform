/**
 * FILE: frontend/src/pages/History.jsx
 * ===========================================
 * Incident History — Paginated & Searchable Table
 * ===========================================
 *
 * PATTERNS DEMONSTRATED:
 *
 *   1. Pagination (skip/limit)
 *      Server-side pagination — we only fetch the current page's data.
 *      skip = page * PAGE_SIZE tells the server how many records to skip.
 *
 *   2. Client-side search filter
 *      We filter the CURRENT PAGE's data in the browser.
 *      True full-text search would send the query to the server.
 *      Client-side is simpler and sufficient for small datasets.
 *
 *   3. useEffect with dependency array
 *      useEffect([page]) — re-fetches whenever the page number changes.
 *      Without the dependency, it would only run once (on mount).
 *
 *   4. Loading state per navigation action
 *      setLoading(true) before each fetch → spinner while loading.
 *      setLoading(false) in finally → always clears, even on error.
 *
 * ACCESSIBILITY:
 *   - <table> with <th scope="col"> for screen readers
 *   - Sort/filter controls have aria-label
 *   - Pagination buttons have descriptive aria-labels
 *
 * INTERVIEW TALKING POINT:
 *   "I used server-side pagination to avoid loading thousands of records
 *   into the browser. The backend's skip/limit pattern is equivalent to
 *   SQL's OFFSET/LIMIT — scalable to any dataset size."
 */

import { useState, useEffect } from "react";
import { Search, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";

import { getAccidents }                       from "../services/api";
import { SEVERITY_COLOR, STATUS_COLOR,
         shortDateTime, padId, pct, debounce } from "../utils/helpers";

const PAGE_SIZE = 20;  // Records per page — matches backend default limit

export default function History() {
  const [accidents, setAccidents] = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState(null);
  const [page,      setPage]      = useState(0);         // 0-indexed page number
  const [hasMore,   setHasMore]   = useState(false);     // Whether a next page exists
  const [search,    setSearch]    = useState("");

  // ── Fetch current page ────────────────────────────────────────────────
  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await getAccidents({
          skip:  page * PAGE_SIZE,
          limit: PAGE_SIZE,
        });
        setAccidents(data);
        // If we got a full page, there's likely a next page
        setHasMore(data.length === PAGE_SIZE);
      } catch (err) {
        setError("Failed to load incident history.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [page]);  // Re-fetch when page changes

  // ── Client-side search filter (on current page data) ─────────────────
  const filtered = search
    ? accidents.filter(
        (a) =>
          a.location.toLowerCase().includes(search.toLowerCase()) ||
          (a.camera_id || "").toLowerCase().includes(search.toLowerCase()) ||
          a.severity.toLowerCase().includes(search.toLowerCase())
      )
    : accidents;

  // Column definitions — data-driven table headers
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

  return (
    <div className="page-enter max-w-6xl mx-auto">

      {/* ── Header ───────────────────────────────────────────────────── */}
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

      {/* ── Table ────────────────────────────────────────────────────── */}
      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table
            className="w-full text-xs"
            aria-label="Incident history table"
          >
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
                <tr>
                  <td colSpan={COLUMNS.length} className="text-center py-12">
                    <Loader2
                      size={20}
                      className="animate-spin inline"
                      style={{ color: "var(--text-muted)" }}
                      aria-label="Loading…"
                    />
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td
                    colSpan={COLUMNS.length}
                    className="text-center py-10"
                    style={{ color: "var(--red)" }}
                  >
                    {error}
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={COLUMNS.length}
                    className="text-center py-10"
                    style={{ color: "var(--text-muted)" }}
                  >
                    No records found
                  </td>
                </tr>
              ) : (
                filtered.map((acc, idx) => (
                  <tr
                    key={acc.id}
                    style={{
                      borderBottom: "1px solid var(--border)",
                      // Alternating row background for readability
                      background: idx % 2 === 0
                        ? "transparent"
                        : "rgba(255,255,255,0.015)",
                    }}
                  >
                    {/* ID */}
                    <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                      #{padId(acc.id)}
                    </td>

                    {/* Location — truncated with title tooltip for long values */}
                    <td
                      className="px-4 py-3 max-w-xs"
                      style={{ color: "#E0EAF8" }}
                      title={acc.location}
                    >
                      <div className="truncate">{acc.location}</div>
                    </td>

                    {/* Severity badge */}
                    <td className="px-4 py-3">
                      <span
                        className="px-2 py-0.5 rounded text-xs uppercase"
                        style={{
                          color:      SEVERITY_COLOR[acc.severity] || "#888",
                          background: `${SEVERITY_COLOR[acc.severity] || "#888"}18`,
                          fontFamily: "'Barlow Condensed', sans-serif",
                        }}
                      >
                        {acc.severity}
                      </span>
                    </td>

                    {/* Status */}
                    <td
                      className="px-4 py-3 capitalize"
                      style={{ color: STATUS_COLOR[acc.status] || "#888" }}
                    >
                      {acc.status}
                    </td>

                    {/* Camera */}
                    <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                      {acc.camera_id || "—"}
                    </td>

                    {/* AI confidence */}
                    <td
                      className="px-4 py-3"
                      style={{ color: acc.confidence ? "#2979FF" : "var(--text-dim)" }}
                    >
                      {pct(acc.confidence)}
                    </td>

                    {/* Detected at timestamp */}
                    <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                      {shortDateTime(acc.detected_at)}
                    </td>

                    {/* Resolved at timestamp (or dash if still active) */}
                    <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                      {acc.resolved_at ? shortDateTime(acc.resolved_at) : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination Controls ─────────────────────────────────────── */}
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{ borderTop: "1px solid var(--border)" }}
        >
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            Showing {filtered.length} of {accidents.length} records on page {page + 1}
            {search && ` (filtered by "${search}")`}
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
    </div>
  );
}
