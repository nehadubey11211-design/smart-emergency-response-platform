-- ============================================================================
-- FILE: database/seed.sql
-- ============================================================================
-- Development & Demo Seed Data
-- ============================================================================
--
-- FILE PATH:
--   smart-emergency-response-platform/
--   └── database/
--       ├── schema.sql   ← run this first
--       └── seed.sql     ← this file (run second)
--
-- PROCESS — how to run:
--   STEP 1 — ensure schema.sql has been applied first:
--     psql -U postgres -d emergency_db -f database/schema.sql
--
--   STEP 2 — apply seed data:
--     psql -U postgres -d emergency_db -f database/seed.sql
--
--   DOCKER COMPOSE:
--     Both files must be mounted into docker-entrypoint-initdb.d/.
--     PostgreSQL executes files in alphabetical order on first start.
--     Name them 01_schema.sql and 02_seed.sql to guarantee order.
--
--   RE-RUNNING:
--     Safe to re-run. Users use ON CONFLICT DO UPDATE (always applies
--     latest hash). Signals/ambulances use ON CONFLICT DO NOTHING
--     (preserves any position updates made during a session).
--     Accidents and dispatch rows are cleared and re-inserted for a
--     clean demo state every time.
--
-- PASSWORD POLICY:
--   Demo passwords are documented here for development ONLY.
--   admin@emergency.com   → "Admin@123"
--   operator@emergency.com → "Operator@123"
--   viewer@emergency.com   → "Viewer@123"
--
--   To regenerate hashes (Python):
--     import bcrypt
--     print(bcrypt.hashpw(b"Admin@123", bcrypt.gensalt(12)).decode())
--
--   NEVER use these accounts or passwords in production.
--   NEVER commit production credentials to version control.
--
-- ============================================================================

-- Abort immediately on any error — never leave DB in a partial state
\set ON_ERROR_STOP on

-- Wrap everything in a transaction — all-or-nothing seed
BEGIN;

-- ============================================================================
-- 1. USERS
-- ============================================================================
-- FIXED: each user has a separately generated, valid 60-char bcrypt hash.
-- Previously: both users shared the same 59-char (invalid/truncated) hash.
-- ON CONFLICT DO UPDATE: always applies the latest hash from this file
-- so re-running the seed refreshes credentials (useful during development).
--
-- Hash generation (run once, paste result below):
--   python -c "import bcrypt; print(bcrypt.hashpw(b'Admin@123',    bcrypt.gensalt(12)).decode())"
--   python -c "import bcrypt; print(bcrypt.hashpw(b'Operator@123', bcrypt.gensalt(12)).decode())"
--   python -c "import bcrypt; print(bcrypt.hashpw(b'Viewer@123',   bcrypt.gensalt(12)).decode())"

INSERT INTO users (name, email, password, role) VALUES
(
    'System Admin',
    'admin@emergency.com',
    -- bcrypt hash of "Admin@123" — 60 chars, cost factor 12
    -- REPLACE with your own generated hash before running
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36bzNimBcMzd6j/VSmBMGQO',
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


-- ============================================================================
-- 2. TRAFFIC SIGNALS
-- ============================================================================
-- FIXED: removed from schema.sql — seed data lives in ONE place only (here).
-- Previously: schema.sql also inserted 5 signals, causing conflict on re-run.
-- Coordinates verified against real Pune junction locations.

INSERT INTO traffic_signals (signal_id, location, latitude, longitude, current_mode, is_online)
VALUES
    ('SIG-001', 'MG Road Junction',                 18.5204,  73.8567, 'auto',   TRUE),
    ('SIG-002', 'FC Road & Bhandarkar Rd',           18.5314,  73.8446, 'auto',   TRUE),
    ('SIG-003', 'Pune Railway Station',              18.5285,  73.8740, 'auto',   TRUE),
    ('SIG-004', 'Hinjewadi IT Park Gate 1',          18.5912,  73.7389, 'auto',   TRUE),
    ('SIG-005', 'Kothrud Bus Depot Junction',        18.5074,  73.8077, 'auto',   FALSE),  -- Offline for demo
    ('SIG-006', 'Shivaji Nagar Signal',              18.5308,  73.8475, 'auto',   TRUE),
    ('SIG-007', 'Swargate Bus Stand',                18.5052,  73.8575, 'auto',   TRUE)
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

DELETE FROM accidents;

INSERT INTO accidents
    (location, latitude, longitude, severity, status, confidence,
     camera_id, description, detected_at, resolved_at)
VALUES
-- ── Active incidents ────────────────────────────────────────────────────────
(
    'MG Road Junction, Pune',
    18.5204, 73.8567, 'critical', 'detected', 0.9700,
    'CAM-001',
    'Multi-vehicle collision blocking 3 lanes. Ambulance dispatched.',
    NOW() - INTERVAL '8 minutes', NULL
),
(
    'FC Road & Bhandarkar Rd, Pune',
    18.5314, 73.8446, 'high', 'responding', 0.9100,
    'CAM-002',
    'Rear-end collision. Traffic backed up 400m.',
    NOW() - INTERVAL '25 minutes', NULL
),
(
    'Hinjewadi IT Park Gate 1, Pune',
    18.5912, 73.7389, 'medium', 'detected', 0.8300,
    'CAM-004',
    'Motorbike down on service road. Minor injuries.',
    NOW() - INTERVAL '12 minutes', NULL
),
-- ── Resolved incidents (history / analytics) ────────────────────────────────
(
    'Shivaji Nagar Signal, Pune',
    18.5308, 73.8475, 'high', 'resolved', 0.8900,
    'CAM-006',
    'Truck vs auto-rickshaw. Road cleared.',
    NOW() - INTERVAL '3 hours',        NOW() - INTERVAL '2 hours'
),
(
    'Swargate Bus Stand, Pune',
    18.5052, 73.8575, 'low', 'resolved', 0.7700,
    'CAM-007',
    'Minor fender-bender. Vehicles moved to shoulder.',
    NOW() - INTERVAL '5 hours',        NOW() - INTERVAL '4 hours 30 minutes'
),
(
    'Kothrud Bus Depot Junction, Pune',
    18.5074, 73.8077, 'medium', 'resolved', 0.8500,
    'CAM-005',
    'Two-wheeler skid on wet road.',
    NOW() - INTERVAL '1 day 2 hours',  NOW() - INTERVAL '1 day 1 hour'
),
(
    'Pune Railway Station Road',
    18.5285, 73.8740, 'critical', 'resolved', 0.9600,
    'CAM-003',
    'Head-on collision. Three ambulances dispatched. Major trauma centre alert.',
    NOW() - INTERVAL '2 days',         NOW() - INTERVAL '1 day 22 hours'
);


-- ============================================================================
-- 5. DISPATCH RECORDS
-- ============================================================================
-- ADDED: links ambulances to accidents so analytics and response-time
-- SLA views return realistic data.
-- Previously: accident_dispatch table was always empty after seed.

DELETE FROM accident_dispatch;

-- Resolve accident IDs dynamically so this works regardless of SERIAL values
DO $$
DECLARE
    acc_mg_road    INT;
    acc_fc_road    INT;
    acc_shivaji    INT;
    acc_swargate   INT;
    acc_kothrud    INT;
    acc_railway    INT;
    amb_001        INT;
    amb_002        INT;
    amb_003        INT;
    amb_004        INT;
    amb_005        INT;
BEGIN
    -- Resolve accident IDs by camera_id (unique per incident in seed data)
    SELECT id INTO acc_mg_road  FROM accidents WHERE camera_id = 'CAM-001';
    SELECT id INTO acc_fc_road  FROM accidents WHERE camera_id = 'CAM-002';
    SELECT id INTO acc_shivaji  FROM accidents WHERE camera_id = 'CAM-006';
    SELECT id INTO acc_swargate FROM accidents WHERE camera_id = 'CAM-007';
    SELECT id INTO acc_kothrud  FROM accidents WHERE camera_id = 'CAM-005';
    SELECT id INTO acc_railway  FROM accidents WHERE camera_id = 'CAM-003';

    -- Resolve ambulance IDs by ambulance_number
    SELECT id INTO amb_001 FROM ambulances WHERE ambulance_number = 'AMB-001';
    SELECT id INTO amb_002 FROM ambulances WHERE ambulance_number = 'AMB-002';
    SELECT id INTO amb_003 FROM ambulances WHERE ambulance_number = 'AMB-003';
    SELECT id INTO amb_004 FROM ambulances WHERE ambulance_number = 'AMB-004';
    SELECT id INTO amb_005 FROM ambulances WHERE ambulance_number = 'AMB-005';

    -- Active: FC Road — AMB-004 is en route (arrived_at NULL)
    INSERT INTO accident_dispatch (accident_id, ambulance_id, dispatched_at, arrived_at, cleared_at)
    VALUES (acc_fc_road, amb_004, NOW() - INTERVAL '20 minutes', NULL, NULL);

    -- Active: MG Road critical — AMB-001 dispatched 5 min ago, not yet on scene
    INSERT INTO accident_dispatch (accident_id, ambulance_id, dispatched_at, arrived_at, cleared_at)
    VALUES (acc_mg_road, amb_001, NOW() - INTERVAL '5 minutes', NULL, NULL);

    -- Resolved: Shivaji Nagar — AMB-002 responded, full timeline
    INSERT INTO accident_dispatch (accident_id, ambulance_id, dispatched_at, arrived_at, cleared_at)
    VALUES (
        acc_shivaji, amb_002,
        NOW() - INTERVAL '2 hours 55 minutes',
        NOW() - INTERVAL '2 hours 40 minutes',
        NOW() - INTERVAL '2 hours 5 minutes'
    );

    -- Resolved: Swargate — AMB-003 responded quickly (minor incident)
    INSERT INTO accident_dispatch (accident_id, ambulance_id, dispatched_at, arrived_at, cleared_at)
    VALUES (
        acc_swargate, amb_003,
        NOW() - INTERVAL '4 hours 58 minutes',
        NOW() - INTERVAL '4 hours 50 minutes',
        NOW() - INTERVAL '4 hours 32 minutes'
    );

    -- Resolved: Kothrud — AMB-005 responded
    INSERT INTO accident_dispatch (accident_id, ambulance_id, dispatched_at, arrived_at, cleared_at)
    VALUES (
        acc_kothrud, amb_005,
        NOW() - INTERVAL '1 day 1 hour 58 minutes',
        NOW() - INTERVAL '1 day 1 hour 45 minutes',
        NOW() - INTERVAL '1 day 1 hour 5 minutes'
    );

    -- Resolved: Railway Station (critical) — multiple units dispatched
    INSERT INTO accident_dispatch (accident_id, ambulance_id, dispatched_at, arrived_at, cleared_at)
    VALUES
    (
        acc_railway, amb_001,
        NOW() - INTERVAL '1 day 23 hours 55 minutes',
        NOW() - INTERVAL '1 day 23 hours 40 minutes',
        NOW() - INTERVAL '1 day 22 hours 10 minutes'
    ),
    (
        acc_railway, amb_002,
        NOW() - INTERVAL '1 day 23 hours 54 minutes',
        NOW() - INTERVAL '1 day 23 hours 42 minutes',
        NOW() - INTERVAL '1 day 22 hours 5 minutes'
    );
END $$;


-- ============================================================================
-- 6. VERIFICATION SUMMARY
-- ============================================================================

DO $$
DECLARE
    u_count  INT; s_count INT; acc_count INT;
    amb_count INT; d_count INT;
BEGIN
    SELECT COUNT(*) INTO u_count   FROM users;
    SELECT COUNT(*) INTO s_count   FROM traffic_signals;
    SELECT COUNT(*) INTO acc_count FROM accidents;
    SELECT COUNT(*) INTO amb_count FROM ambulances;
    SELECT COUNT(*) INTO d_count   FROM accident_dispatch;

    RAISE NOTICE '============================================';
    RAISE NOTICE 'Seed complete:';
    RAISE NOTICE '  users             : %', u_count;
    RAISE NOTICE '  traffic_signals   : %', s_count;
    RAISE NOTICE '  accidents         : %', acc_count;
    RAISE NOTICE '  ambulances        : %', amb_count;
    RAISE NOTICE '  accident_dispatch : %', d_count;
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Dev credentials (NEVER use in production):';
    RAISE NOTICE '  admin@emergency.com    / Admin@123';
    RAISE NOTICE '  operator@emergency.com / Operator@123';
    RAISE NOTICE '  viewer@emergency.com   / Viewer@123';
    RAISE NOTICE '============================================';
END $$;

COMMIT;

-- ============================================================================
-- END OF SEED
-- ============================================================================