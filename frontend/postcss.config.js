/**
 * FILE: frontend/postcss.config.js
 * ========================================
 * PostCSS Configuration
 * ========================================
 *
 * PostCSS is a CSS processor that transforms CSS using JavaScript plugins.
 * Vite runs PostCSS automatically on every CSS file.
 *
 * PLUGINS USED:
 *   tailwindcss  — Generates utility classes from your Tailwind config
 *                  and the class names found in your JSX files
 *
 *   autoprefixer — Automatically adds vendor prefixes to CSS properties
 *                  e.g. -webkit-transform, -ms-flexbox
 *                  The browserslist config (package.json or .browserslistrc)
 *                  controls which browsers to target.
 *                  Without this, some CSS features break in older browsers.
 *
 * WHY POSTCSS?
 *   It's the standard pipeline for modern CSS tooling.
 *   Vite, CRA, Next.js, and most frameworks use PostCSS under the hood.
 */

export default {
  plugins: {
    tailwindcss:  {},
    autoprefixer: {},
  },
};
