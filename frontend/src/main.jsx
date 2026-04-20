/**
 * FILE: frontend/src/main.jsx
 * ==================================
 * React Application Entry Point
 * ==================================
 *
 * This is the first JavaScript file executed in the browser.
 * It mounts the React component tree into the HTML <div id="root">.
 *
 * REACT 18 CREATEROOT:
 *   React 18 introduced createRoot() as the new mounting API.
 *   The old ReactDOM.render() is deprecated.
 *
 *   createRoot() enables React 18's concurrent features:
 *     - Automatic batching: multiple setState calls in async functions
 *       are batched into a single re-render (performance improvement)
 *     - Concurrent rendering: React can pause/resume rendering
 *       to keep the UI responsive during heavy computation
 *
 * STRICT MODE:
 *   <React.StrictMode> wraps the entire app in development.
 *   It deliberately double-invokes certain lifecycle methods and renders
 *   to help you find side effects and deprecated API usage.
 *   It has ZERO impact on the production build.
 *
 *   What it catches:
 *     - Components with side effects in the render phase
 *     - Deprecated lifecycle methods
 *     - Missing cleanup in useEffect
 *
 * GLOBAL CSS:
 *   import "./index.css" is the ONLY place we import global styles.
 *   All other styling uses Tailwind utilities or inline style props.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";  // Global CSS: variables, base reset, utility classes

// Find the HTML element with id="root" (defined in public/index.html)
// and create a React root attached to it.
const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  // StrictMode activates additional checks and warnings in development.
  // Remove this wrapper if you need to suppress intentional double-renders.
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
