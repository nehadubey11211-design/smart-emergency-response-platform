/**
 * FILE : frontend/src/components/GlobalDispatchModal.jsx
 * ----------------------------------
 * Global wrapper component for the on-duty ambulance driver.
 *
 * This component is mounted once at the app root and renders the
 * full-screen dispatch modal when a DISPATCH_ALERT arrives.
 *
 * It is intentionally thin: it delegates UI rendering to
 * components/ambulance/DispatchModal.jsx and uses the shared
 * global ambulance socket context for state.
 */

import { useState } from "react";

import { useGlobalAmbulanceSocket }
from "../context/AmbulanceSocketContext";

import { DispatchModal }
from "./ambulance/DispatchModal";

import { ambulanceApi }
from "../services/ambulanceApi";

export default function GlobalDispatchModal() {

  const { pendingDispatch, setPendingDispatch, setAcceptedDispatch } =
    useGlobalAmbulanceSocket();

  const [loading, setLoading] = useState(false);

  const handleAccept = async () => {
    if (!pendingDispatch) return;

    setLoading(true);

    try {
      const ambulanceId = pendingDispatch.ambulance_id;
      if (!ambulanceId) {
        throw new Error("Missing ambulance_id in dispatch payload.");
      }

      await ambulanceApi.acceptDispatch(ambulanceId);

      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${pendingDispatch.accident_lat},${pendingDispatch.accident_lon}&travelmode=driving`,
        "_blank"
      );

      setAcceptedDispatch(pendingDispatch);
      setPendingDispatch(null);
    } catch (e) {
      console.error("Accept dispatch failed:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = () => {
    setPendingDispatch(null);
  };

  return (
    <DispatchModal
      alert={pendingDispatch}
      onAccept={handleAccept}
      onReject={handleReject}
      loading={loading}
    />
  );
}