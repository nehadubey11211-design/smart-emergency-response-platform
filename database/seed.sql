-- FILE: database/seed.sql
-- ================================
-- Development Seed Data
-- ================================
--
-- Populates the database with realistic demo data for development and demos.
-- Run AFTER schema.sql:
--   psql -U postgres -d emergency_db -f database/seed.sql
--
-- PASSWORD NOTE:
--   The bcrypt hash below corresponds to "admin123" with 12 rounds.
--   In production: never commit real credentials in seed files.
--   Generated with Python:
--     import bcrypt
--     print(bcrypt.hashpw(b"admin123", bcrypt.gensalt(12)).decode())


-- ─── Users ───────────────────────────────────────────────────────────────────

import bcrypt
print(bcrypt.hashpw(b"admin123", bcrypt.gensalt(12)).decode())

INSERT INTO users (name, email, password, role) VALUES
(
    'System Admin',
    'admin@emergency.com',
    -- bcrypt hash of "admin123"
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCgmzYXFGmR.1fHDdF5vBqS',
    'admin'
),
(
    'Shift Operator',
    'operator@emergency.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCgmzYXFGmR.1fHDdF5vBqS',
    'operator'
)
ON CONFLICT (email) DO NOTHING;


-- ─── Traffic Signals ─────────────────────────────────────────────────────────
-- Real Pune junctions used for realism in demos

INSERT INTO traffic_signals (signal_id, location, latitude, longitude, current_mode, is_online) VALUES
    ('SIG-001', 'MG Road Junction',             18.5204,  73.8567, 'auto',      TRUE),
    ('SIG-002', 'FC Road & Bhandarkar Rd',      18.5314,  73.8446, 'auto',      TRUE),
    ('SIG-003', 'Pune Railway Station',          18.5285,  73.8740, 'auto',      TRUE),
    ('SIG-004', 'Hinjewadi IT Park Gate 1',     18.5912,  73.7389, 'auto',      TRUE),
    ('SIG-005', 'Kothrud Bus Depot Junction',   18.5074,  73.8077, 'auto',      FALSE),  -- Offline (for demo)
    ('SIG-006', 'Shivaji Nagar Signal',         18.5308,  73.8475, 'auto',      TRUE),
    ('SIG-007', 'Swargate Bus Stand',           18.5052,  73.8575, 'auto',      TRUE)
ON CONFLICT (signal_id) DO NOTHING;


-- ─── Sample Accidents ─────────────────────────────────────────────────────────
-- Mix of severities and statuses for a realistic dashboard demo

INSERT INTO accidents
    (location, latitude, longitude, severity, status, confidence, camera_id, description, detected_at, resolved_at)
VALUES
-- Critical active incident (shows at the top of the dashboard)
(
    'MG Road Junction, Pune',
    18.5204, 73.8567,
    'critical', 'detected',
    0.97, 'CAM-001',
    'Multi-vehicle collision blocking 3 lanes. Ambulance dispatched.',
    NOW() - INTERVAL '8 minutes',
    NULL
),
-- High severity — in progress
(
    'FC Road & Bhandarkar Rd, Pune',
    18.5314, 73.8446,
    'high', 'responding',
    0.91, 'CAM-002',
    'Rear-end collision. Traffic backed up 400m.',
    NOW() - INTERVAL '25 minutes',
    NULL
),
-- Medium active
(
    'Hinjewadi IT Park Gate 1, Pune',
    18.5912, 73.7389,
    'medium', 'detected',
    0.83, 'CAM-004',
    'Motorbike down on service road. Minor injuries.',
    NOW() - INTERVAL '12 minutes',
    NULL
),
-- Resolved incidents (older, for history and analytics)
(
    'Shivaji Nagar Signal, Pune',
    18.5308, 73.8475,
    'high', 'resolved',
    0.89, 'CAM-006',
    'Truck vs auto-rickshaw. Road cleared.',
    NOW() - INTERVAL '3 hours',
    NOW() - INTERVAL '2 hours'
),
(
    'Swargate Bus Stand, Pune',
    18.5052, 73.8575,
    'low', 'resolved',
    0.77, 'CAM-007',
    'Minor fender-bender. Vehicles moved to shoulder.',
    NOW() - INTERVAL '5 hours',
    NOW() - INTERVAL '4 hours 30 minutes'
),
(
    'Kothrud Bus Depot Junction, Pune',
    18.5074, 73.8077,
    'medium', 'resolved',
    0.85, 'CAM-005',
    'Two-wheeler skid on wet road.',
    NOW() - INTERVAL '1 day 2 hours',
    NOW() - INTERVAL '1 day 1 hour'
),
(
    'Pune Railway Station Road',
    18.5285, 73.8740,
    'critical', 'resolved',
    0.96, 'CAM-003',
    'Head-on collision. Three ambulances dispatched. Major trauma centre alert.',
    NOW() - INTERVAL '2 days',
    NOW() - INTERVAL '1 day 22 hours'
);
