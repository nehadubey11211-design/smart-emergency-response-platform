/**
 * FILE: frontend/src/hooks/useAccidents.js
 * ===============================================
 * Custom React Hook — Accident Data Fetching
 * ===============================================
 *
 * WHY CUSTOM HOOKS?
 *   React hooks let you extract stateful logic from components so it can be
 *   reused without component inheritance or render props.
 *
 *   Without this hook:
 *     Every page that shows accidents would duplicate:
 *       useState(data), useState(loading), useState(error),
 *       useEffect(fetch), useEffect(interval), try/catch...
 *
 *   With this hook:
 *     const { data, loading, error, refetch } = useAccidents({ status: "detected" });
 *     One line, consistent behaviour everywhere.
 *
 *   This is the Separation of Concerns principle applied to React:
 *     - Hook:      HOW to fetch the data
 *     - Component: HOW to display the data
 *
 * RULES OF HOOKS (important for interviews):
 *   1. Only call hooks at the top level (not inside if/for/while)
 *   2. Only call hooks from React functions (components or other hooks)
 *   3. Hook names must start with "use"
 *
 * INTERVIEW TALKING POINT:
 *   "I extracted data-fetching logic into custom hooks to keep components
 *   focused on rendering. The hook encapsulates loading state, error handling,
 *   and auto-refresh — the component just reads the values."
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { getAccidents } from "../services/api";

/**
 * Fetches and auto-refreshes the accidents list.
 *
 * @param {object} params          - Query params: { status, skip, limit }
 * @param {number} refreshInterval - Auto-refresh in ms. 0 = disabled.
 * @returns {{ data, loading, error, refetch }}
 *
 * Example:
 *   const { data: accidents, loading, refetch } = useAccidents({ status: "detected" }, 15000);
 */
export function useAccidents(params = {}, refreshInterval = 30000) {
  const [data,    setData]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  /**
   * Stable serialisation of params for useCallback dependency.
   * Without this, a new object literal on every render would cause
   * an infinite re-fetch loop.
   */
  const paramsKey = JSON.stringify(params);

  /**
   * useCallback memoises the fetch function.
   * It only recreates when paramsKey changes (i.e. the query params changed).
   * This prevents the useEffect below from running on every render.
   */
  const fetchData = useCallback(async () => {
    try {
      const response = await getAccidents(JSON.parse(paramsKey));
      setData(response.data);
      setError(null);
    } catch (err) {
      // Extract the most useful error message available
      const message =
        err.response?.data?.detail ||
        err.message ||
        "Failed to fetch accidents";
      setError(message);
      console.error("useAccidents error:", message);
    } finally {
      setLoading(false);
    }
  }, [paramsKey]);  // Only re-create if params change

  useEffect(() => {
    // Fetch immediately on mount
    fetchData();

    // Set up auto-refresh interval if requested
    if (refreshInterval > 0) {
      const interval = setInterval(fetchData, refreshInterval);
      // Cleanup: clear the interval when the component unmounts
      // (prevents calling setState on an unmounted component)
      return () => clearInterval(interval);
    }
  }, [fetchData, refreshInterval]);

  return {
    data,      // The accidents array
    loading,   // True while the first fetch is in progress
    error,     // Error message string, or null
    refetch: fetchData,  // Call this to manually trigger a refresh
  };
}
