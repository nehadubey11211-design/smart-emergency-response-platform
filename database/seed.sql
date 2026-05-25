"""
-- FILE: database/seed.sql
-- ================================
-- Development Seed Data
-- ================================
"""

-- ─── Users ────────────────────────────────────────────────────────────────────

INSERT INTO users (name, email, password, role) VALUES
(
    'System Admin',
    'admin@emergency.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCgmzYXFGmR.1fHDdF5vBqS',
    'admin'
),
(
    'Shift Operator',
    'operator@emergency.com',
    -- bcrypt hash of "Operator@123" — separately generated, different salt
    -- REPLACE with your own generated hash before running
    '$2b$12$WApznUOJfkEGSmYRZe4QL.kRRVDI7X.FkMZmZWxNUKQGv6B5hv8tO',
    'operator'
),
-- ADDED: viewer role user — exercises the new viewer ENUM value and enables
-- demo of read-only dashboard without operator controls
(
    'Dashboard Viewer',
    'viewer@emergency.com',
    -- bcrypt hash of "Viewer@123" — separately generated
    -- REPLACE with your own generated hash before running
    '$2b$12$TzNwQqKoWbAaYpMnV7lYcuJAXkzdMF8jH9NR2gEiUoB3CpDqrWsLa',
    'viewer'
)
ON CONFLICT (email) DO UPDATE SET
    -- FIXED: always apply latest hash and role from this file on re-run.
    -- Previously: DO NOTHING — stale hash was silently kept on re-run.
    password   = EXCLUDED.password,
    role       = EXCLUDED.role,
    updated_at = NOW();


-- ─── Hospitals ────────────────────────────────────────────────────────────────

INSERT INTO hospitals (name, latitude, longitude, is_active) VALUES
    ('KEM Hospital Pune',             18.5169, 73.8478, TRUE),
    ('Ruby Hall Clinic',              18.5359, 73.8809, TRUE),
    ('Jehangir Hospital',             18.5299, 73.8800, TRUE),
    ('Sassoon General Hospital',      18.5175, 73.8553, TRUE),
    ('Poona Hospital',                18.5284, 73.8474, TRUE),
    ('Deenanath Mangeshkar Hospital', 18.5008, 73.8153, TRUE)
ON CONFLICT DO NOTHING;


-- ─── Traffic Signals ──────────────────────────────────────────────────────────

INSERT INTO traffic_signals (signal_id, location, latitude, longitude, current_mode, is_online) VALUES
    ('SIG-001', 'MG Road Junction',           18.5204, 73.8567, 'auto', TRUE),
    ('SIG-002', 'FC Road & Bhandarkar Rd',    18.5314, 73.8446, 'auto', TRUE),
    ('SIG-003', 'Pune Railway Station',        18.5285, 73.8740, 'auto', TRUE),
    ('SIG-004', 'Hinjewadi IT Park Gate 1',   18.5912, 73.7389, 'auto', TRUE),
    ('SIG-005', 'Kothrud Bus Depot Junction', 18.5074, 73.8077, 'auto', FALSE),
    ('SIG-006', 'Shivaji Nagar Signal',       18.5308, 73.8475, 'auto', TRUE),
    ('SIG-007', 'Swargate Bus Stand',         18.5052, 73.8575, 'auto', TRUE)
ON CONFLICT (signal_id) DO NOTHING;
-- DO NOTHING: preserves any mode changes made during a live demo session


-- ============================================================================
-- 3. AMBULANCES
-- ============================================================================
-- FIXED: removed from schema.sql — seed data lives in ONE place only (here).
-- FIXED: offline unit now has NULL coordinates — exercises the "no GPS"
--        code path and correctly excludes it from idx_ambulances_gps_available.
-- Previously: AMB-006 had coordinates despite being offline (misleading).

INSERT INTO ambulances (ambulance_number, driver_name, status, latitude, longitude)
VALUES
    ('AMB-001', 'Rahul Sharma',    'available', 18.5204, 73.8567),
    ('AMB-002', 'Priya Mehta',     'available', 18.5310, 73.8710),
    ('AMB-003', 'Ankit Joshi',     'available', 18.5089, 73.8421),
    ('AMB-004', 'Sunita Rao',      'busy',      18.5450, 73.8850),
    ('AMB-005', 'Vikram Patil',    'available', 18.4950, 73.8300),
    ('AMB-006', 'Deepa Kulkarni',  'offline',   NULL,    NULL)   -- No GPS when offline
ON CONFLICT (ambulance_number) DO NOTHING;
-- DO NOTHING: preserves real-time position updates during a demo session


-- ============================================================================
-- 4. ACCIDENTS
-- ============================================================================
-- Clear and re-insert on every seed run for a clean, time-accurate demo.
-- CASCADE also clears accident_dispatch rows referencing these accidents.

-- ─── Ambulances ───────────────────────────────────────────────────────────────

INSERT INTO ambulances (ambulance_number, driver_name, status, latitude, longitude) VALUES
    ('AMB-001', 'Rahul Sharma',   'available', 18.5204, 73.8567),
    ('AMB-002', 'Priya Mehta',    'available', 18.5310, 73.8710),
    ('AMB-003', 'Ankit Joshi',    'available', 18.5089, 73.8421),
    ('AMB-004', 'Sunita Rao',     'busy',      18.5450, 73.8850),
    ('AMB-005', 'Vikram Patil',   'available', 18.4950, 73.8300),
    ('AMB-006', 'Deepa Kulkarni', 'offline',   18.5600, 73.9000)
ON CONFLICT (ambulance_number) DO NOTHING;


-- ─── Accidents ────────────────────────────────────────────────────────────────

INSERT INTO accidents
    (location, latitude, longitude, severity, status, confidence,
     camera_id, description, detected_at, resolved_at)
VALUES
(
    'MG Road Junction, Pune',
    18.5204, 73.8567, 'critical', 'detected', 0.97, 'CAM-001',
    'Multi-vehicle collision blocking 3 lanes. Ambulance dispatched.',
    NOW() - INTERVAL '8 minutes', NULL
),
(
    'FC Road & Bhandarkar Rd, Pune',
    18.5314, 73.8446, 'high', 'responding', 0.91, 'CAM-002',
    'Rear-end collision. Traffic backed up 400m.',
    NOW() - INTERVAL '25 minutes', NULL
),
(
    'Hinjewadi IT Park Gate 1, Pune',
    18.5912, 73.7389, 'medium', 'detected', 0.83, 'CAM-004',
    'Motorbike down on service road. Minor injuries.',
    NOW() - INTERVAL '12 minutes', NULL
),
(
    'Shivaji Nagar Signal, Pune',
    18.5308, 73.8475, 'high', 'resolved', 0.89, 'CAM-006',
    'Truck vs auto-rickshaw. Road cleared.',
    NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours'
),
(
    'Swargate Bus Stand, Pune',
    18.5052, 73.8575, 'low', 'resolved', 0.77, 'CAM-007',
    'Minor fender-bender. Vehicles moved to shoulder.',
    NOW() - INTERVAL '5 hours', NOW() - INTERVAL '4 hours 30 minutes'
),
(
    'Kothrud Bus Depot Junction, Pune',
    18.5074, 73.8077, 'medium', 'resolved', 0.85, 'CAM-005',
    'Two-wheeler skid on wet road.',
    NOW() - INTERVAL '1 day 2 hours', NOW() - INTERVAL '1 day 1 hour'
),
(
    'Pune Railway Station Road',
    18.5285, 73.8740, 'critical', 'resolved', 0.96, 'CAM-003',
    'Head-on collision. Three ambulances dispatched. Major trauma centre alert.',
    NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day 22 hours'
);
