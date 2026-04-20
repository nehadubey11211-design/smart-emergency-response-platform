/**
 * FILE: frontend/tailwind.config.js
 * ========================================
 * Tailwind CSS Configuration
 * ========================================
 *
 * Tailwind is a utility-first CSS framework.
 * Instead of writing custom CSS classes, you compose designs using
 * utility classes directly in JSX: className="flex items-center gap-2 p-4"
 *
 * CONTENT PATHS:
 *   Tailwind scans these files for class names and generates ONLY the CSS
 *   for classes that actually appear in the source.
 *   This "tree-shaking" keeps the production CSS bundle tiny (~5-20KB).
 *
 * CUSTOM THEME EXTENSIONS:
 *   extend: {} adds to the default theme without replacing it.
 *   We add our emergency system's colour palette, font families,
 *   and custom animations.
 *
 * WHY TAILWIND OVER STYLED-COMPONENTS?
 *   - No context switching between CSS and JS files
 *   - Consistent spacing/colour scale by default
 *   - Tiny production bundle (purges unused classes)
 *   - Great for rapid prototyping
 *   Trade-off: JSX can look verbose with many utility classes
 */

/** @type {import('tailwindcss').Config} */
export default {
  // Tailwind scans these files to find used utility classes
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],

  theme: {
    extend: {
      // Custom colour palette — mirrors the CSS variables in index.css
      // These can be used as Tailwind classes: bg-brand-dark, text-brand-red, etc.
      colors: {
        brand: {
          dark:   "#0A0E1A",
          panel:  "#0F1628",
          card:   "#151E35",
          border: "#1E2D4D",
          red:    "#FF2D2D",
          orange: "#FF7A00",
          yellow: "#FFD600",
          green:  "#00E676",
          blue:   "#2979FF",
        },
      },

      // Custom fonts — loaded via Google Fonts in index.html
      fontFamily: {
        display: ["'Barlow Condensed'", "sans-serif"],  // Headings, labels
        mono:    ["'JetBrains Mono'", "monospace"],     // Body text, code
      },

      // Custom animations for incident cards and status indicators
      animation: {
        "pulse-fast": "pulse 0.8s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "blink":      "blink 1.2s step-end infinite",
        "ring":       "pulse-ring 1.5s ease-in-out infinite",
      },

      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%":      { opacity: "0" },
        },
      },
    },
  },

  plugins: [],
};
