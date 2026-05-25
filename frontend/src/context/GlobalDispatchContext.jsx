/**
  FILE : frontend/src/context/GlobalDispatchContext.jsx
 -----------------------------------
 Provides a shared context for global dispatch state.   
  This file defines a React context that holds the current dispatch alert data and functions to open/close the dispatch modal.
  Components anywhere in the app can use the useGlobalDispatch() hook to access this state and control the dispatch modal
 */

import {
  createContext,
  useContext,
  useState,
} from "react";


// ─── Context Creation ─────────────────────────────────────

const GlobalDispatchContext = createContext(null);


// ─── Provider Component ───────────────────────────────────

export function GlobalDispatchProvider({ children }) {

  const [dispatchData, setDispatchData] = useState(null);

  const openDispatchModal = (data) => {
    setDispatchData(data);
  };

  const closeDispatchModal = () => {
    setDispatchData(null);
  };

  return (
    <GlobalDispatchContext.Provider
      value={{
        dispatchData,
        openDispatchModal,
        closeDispatchModal,
      }}
    >
      {children}
    </GlobalDispatchContext.Provider>
  );
}


// ─── Custom Hook ──────────────────────────────────────────

export function useGlobalDispatch() {

  const context = useContext(GlobalDispatchContext);

  if (!context) {
    throw new Error(
      "useGlobalDispatch must be used inside GlobalDispatchProvider"
    );
  }

  return context;
}
