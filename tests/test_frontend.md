# FILE: tests/test_frontend.md
# ====================================
# Frontend Manual QA Checklist
# ====================================
#
# Run through this checklist after starting the frontend with:
#   cd frontend && npm install && npm run dev
#
# Open http://localhost:5173 in a browser.
# Ensure the backend is also running: cd backend && uvicorn app.main:app --reload
#
# Mark each item [x] when verified.
# This checklist is your "Definition of Done" for every PR that touches the frontend.

---

## 🔐 Authentication

- [ ] Visiting `/dashboard` without a token → automatically redirects to `/login`
- [ ] Visiting `/analytics` without a token → automatically redirects to `/login`
- [ ] Login form shows: email field, password field, show/hide toggle, submit button
- [ ] Entering wrong credentials → red error message appears (not a 500 crash)
- [ ] Error message does NOT distinguish "user not found" vs "wrong password" (security)
- [ ] Login with `admin@emergency.com` / `admin123` → redirects to `/dashboard`
- [ ] After login: `localStorage.getItem("token")` returns a JWT string
- [ ] After login: `localStorage.getItem("user")` returns a JSON user object
- [ ] Clicking Logout → clears localStorage, redirects to `/login`
- [ ] After logout: pressing browser Back button does NOT return to dashboard
- [ ] Refreshing the page while logged in keeps the session (token persists)

---

## 📊 Dashboard — Layout & Data

- [ ] Page title "OPERATIONS DASHBOARD" visible
- [ ] Status bar shows in the top-right with a clock updating every second
- [ ] Status bar shows "LIVE" (green) when WebSocket is connected
- [ ] Status bar shows "OFFLINE" (red) when backend is unreachable
- [ ] 4 KPI summary cards load: Incidents Today, Active Now, Resolved Today, Avg Response
- [ ] Summary card values are numbers (not "—" or undefined)
- [ ] Incident feed loads within 2 seconds
- [ ] Each AlertCard shows: severity colour strip, badge, ID, location, time ago, status
- [ ] "Active" filter shows only detected/responding incidents
- [ ] "All" filter shows all incidents including resolved (dimmed at 65% opacity)
- [ ] Empty state shows "System clear ✅" when there are no matching incidents
- [ ] Traffic panel loads with all signals from the database
- [ ] Each signal shows: online/offline icon, signal ID, location, mode badge

---

## 🚨 Dashboard — Actions

- [ ] "Mark Resolved" button on an AlertCard calls the API and card updates status
- [ ] Loading spinner appears on the button while the API call is in progress
- [ ] After resolving: card moves to the resolved state (dimmed, no action buttons)
- [ ] "Green Corridor" button shows a success alert on completion
- [ ] ⚡ Emergency button on a signal switches its mode badge to "EMERGENCY" (red)
- [ ] 🔄 Reset button on a signal switches its mode badge back to "AUTO" (green)
- [ ] While a signal action is in progress: that signal's buttons are disabled
- [ ] Other signals' buttons remain active during a signal action (per-item loading)

---

## ⚡ Real-time WebSocket (Critical Test)

- [ ] Open TWO browser tabs on `/dashboard`
- [ ] In a terminal, run:
      ```
      curl -X POST http://localhost:8000/api/accidents/ \
        -H "Content-Type: application/json" \
        -d '{"location":"Test Junction","severity":"critical","confidence":0.97,"camera_id":"CAM-TEST"}'
      ```
- [ ] BOTH tabs show the red "🚨 NEW ACCIDENT DETECTED" flash banner within 1 second
- [ ] The banner disappears automatically after 4 seconds
- [ ] The new incident appears at the top of the feed without page refresh
- [ ] The KPI "Active Now" count increments by 1 in both tabs
- [ ] Kill the backend (Ctrl+C) → status bar switches to "OFFLINE" within 3 seconds
- [ ] Restart the backend → status bar switches back to "LIVE" (auto-reconnect works)

---

## 📈 Analytics Page

- [ ] 4 KPI summary cards match the Dashboard numbers (same API endpoint)
- [ ] Trend area chart renders with the correct number of data points for "7d"
- [ ] "14d" button changes the chart to show 14 days of data
- [ ] "30d" button changes the chart to show 30 days of data
- [ ] Day selector shows the active button highlighted in blue
- [ ] Hover over a data point → dark tooltip appears with date and count
- [ ] Severity donut chart renders with correct colours per severity
- [ ] Legend below the donut shows all severity labels with counts
- [ ] "No data" message shown when there are no analytics records
- [ ] Page animates in smoothly (fadeSlideIn animation)

---

## 📋 History Page

- [ ] Table loads within 2 seconds with up to 20 rows
- [ ] All 8 columns visible: ID, Location, Severity, Status, Camera, AI Score, Detected, Resolved
- [ ] Severity column shows colour-coded badges (red=critical, orange=high, etc.)
- [ ] Status column shows colour-coded text (orange=detected, blue=responding, green=resolved)
- [ ] Resolved At column shows "—" for incidents that haven't been resolved yet
- [ ] Search box filters rows by location in real time (no button click needed)
- [ ] Search for "MG Road" → only shows rows where location contains "MG Road"
- [ ] Clear search → all rows reappear
- [ ] "Next ›" pagination button loads the next 20 rows
- [ ] "‹ Prev" pagination button is disabled on page 1
- [ ] "Next ›" pagination button is disabled when fewer than 20 rows returned (last page)
- [ ] Long location names are truncated with "…" and full text visible on hover

---

## 🏠 Home Landing Page

- [ ] Page renders without login
- [ ] "AI EMERGENCY RESPONSE" heading visible
- [ ] All 6 feature cards visible with icons and descriptions
- [ ] All 8 tech stack badge pills visible
- [ ] "Open Dashboard →" button navigates to `/login`
- [ ] No horizontal scrollbar on desktop (1280px+)

---

## 🧩 Navigation

- [ ] Navbar sidebar is visible on all protected pages (Dashboard, Analytics, History)
- [ ] Navbar is NOT visible on Home and Login pages
- [ ] Active page is highlighted in the navbar (red background)
- [ ] Hovering a navbar icon shows a tooltip with the page name
- [ ] Logo (Siren icon) is visible at the top of the sidebar
- [ ] Logout button at the bottom of the sidebar works

---

## ♿ Accessibility

- [ ] Tab key navigates through all interactive elements in logical order
- [ ] All buttons show a visible blue focus ring when focused with keyboard
- [ ] Screen reader: severity badges have meaningful aria-label text
- [ ] Screen reader: loading states use aria-busy or aria-label
- [ ] No browser console errors
- [ ] No React "Warning:" messages in the console

---

## 📱 Responsive Layout

- [ ] Dashboard: two-column layout collapses to single column below 1024px (lg breakpoint)
- [ ] Traffic panel appears below the incident feed on narrow screens
- [ ] History table is horizontally scrollable on narrow screens (no content cut off)
- [ ] Summary cards grid: 2 columns on mobile, 4 on desktop
- [ ] Navbar sidebar remains visible and functional on all screen sizes

---

## 🏁 Sign-off

Once all items above are checked, the frontend is ready for submission.

**Tested by:** ___________________  
**Date:** ___________________  
**Browser:** ___________________  
**Screen size:** ___________________
