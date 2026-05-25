/**
 * FILE: frontend/src/hooks/useAnalytics.js
 * ===============================================
 * Custom React Hook — Analytics Data Fetching
 * ===============================================
 *
 * Demonstrates the pattern of batching multiple related API calls into
 * one hook, so the component receives all the data it needs in one place.
 *
 * Promise.all() vs sequential awaits:
 *   Sequential:   3 requests × 200ms each = 600ms total
 *   Promise.all:  3 requests run in parallel = ~200ms total
 *
 *   Promise.all resolves when ALL promises resolve, or rejects if ANY fail.
 *   This is the right choice when the requests are independent of each other.
 */

import { useState, useEffect, useCallback } from "react";
import { getSummary, getSeverityBreakdown, getTrends } from "../services/api";

/**
 * @param {number} days - Trend lookback window (7, 14, or 30 days)
 * @returns {{ summary, breakdown, trends, loading, error, refetch }}
 */
export function useAnalytics(days = 7) {
  const [summary,   setSummary]   = useState(null);
  const [breakdown, setBreakdown] = useState({});
  const [trends,    setTrends]    = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      /**
       * Promise.all fires all 3 requests simultaneously.
       * Array destructuring maps each result to a named variable.
       * This is cleaner than three separate await calls.
       */
      const [summaryRes, breakdownRes, trendsRes] = await Promise.all([
        getSummary(),
        getSeverityBreakdown(),
        getTrends(days),
      ]);
       console.log("SUMMARY:", summaryRes.data);
       console.log("BREAKDOWN:", breakdownRes.data);
       console.log("TRENDS:", trendsRes.data);

      setSummary(summaryRes.data);
      setBreakdown(breakdownRes.data);
      setTrends(trendsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load analytics data");
      console.error("useAnalytics error:", err);
    } finally {
      setLoading(false);
    }
  }, [days]);  // Re-fetch automatically when the days window changes

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { summary, breakdown, trends, loading, error, refetch: fetchAll };
}
