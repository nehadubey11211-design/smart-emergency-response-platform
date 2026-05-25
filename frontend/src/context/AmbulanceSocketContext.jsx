/**
 * FILE : frontend/src/context/AmbulanceSocketContext.jsx
 * -----------------------------------
 * Provides a shared context for ambulance WebSocket state.
 *
 * This file wraps useAmbulanceSocket() and adds global dispatch state
 * so the entire app can react to pending/accepted dispatch alerts.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import { useAmbulanceSocket } from "../hooks/useAmbulanceSocket";

const AmbulanceSocketContext = createContext(null);

export function AmbulanceSocketProvider({
  ambulanceId,
  children,
}) {

  // Original socket hook
  const socket = useAmbulanceSocket(ambulanceId);

  //  Global dispatch state
  const [pendingDispatch, setPendingDispatch] = useState(null);
  const [acceptedDispatch, setAcceptedDispatch] = useState(null);

  // Notification permission
  useEffect(() => {
    if ("Notification" in window) {
      if (Notification.permission !== "granted") {
        Notification.requestPermission();
      }
    }
  }, []);

  // Listen for new dispatch alerts
  useEffect(() => {
    if (!socket?.lastAlert) return;

    const data = socket.lastAlert;

    if (import.meta.env.DEV) {
  console.log("📨 Incoming Alert:", data);
}

    // ONLY set modal for dispatch alerts
    if (data.type === "DISPATCH_ALERT") {
      if (import.meta.env.DEV) {
  console.log("🚑 Pending Dispatch Set");
}

      setPendingDispatch(data);
    }
  }, [socket.lastAlert]);

  return (
    <AmbulanceSocketContext.Provider
      value={{
        ...socket,

        //  Added global dispatch state
        pendingDispatch,
        setPendingDispatch,
        acceptedDispatch,
        setAcceptedDispatch,
      }}
    >
      {children}
    </AmbulanceSocketContext.Provider>
  );
}

export function useGlobalAmbulanceSocket() {
  const context = useContext(AmbulanceSocketContext);

  if (!context) {
    throw new Error(
      "useGlobalAmbulanceSocket must be used inside AmbulanceSocketProvider"
    );
  }

  return context;
}
