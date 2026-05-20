-- FILE: database/schema.sql
-- ================================
-- PostgreSQL Database Schema
-- ================================
--
-- Run this to initialise the database from scratch:
--   psql -U postgres -d emergency_db -f database/schema.sql
--
-- When using Docker Compose, this file is auto-executed on first startup
-- via the docker-entrypoint-initdb.d/ volume mount.
--
-- DESIGN DECISIONS:
--   - ENUM types enforce valid values at the database level
--     (not just the application level — extra safety net)
--   - TIMESTAMPTZ stores timestamps with timezone (always use this over TIMESTAMP)
--   - Indexes on frequently filtered/sorted columns (status, detected_at)
--   - Soft delete via is_active (no hard DELETE for user records)
--   - All foreign key relationships use ON DELETE CASCADE or RESTRICT (explicitly)


-- ─── Cleanup (for re-running this script) ─────────────────────────────────────
-- DROP TABLE IF EXISTS ... handles the case where tables already exist.
-- CASCADE drops dependent objects too (foreign keys, views).

DROP TABLE IF EXISTS traffic_signals CASCADE;
DROP TABLE IF EXISTS accidents       CASCADE;
DROP TABLE IF EXISTS users           CASCADE;

-- Drop custom ENUM types if they exist (PostgreSQL requires explicit drops)
DROP TYPE IF EXISTS severity_level  CASCADE;
DROP TYPE IF EXISTS accident_status CASCADE;
DROP TYPE IF EXISTS signal_mode     CASCADE;


-- ─── ENUM Types ───────────────────────────────────────────────────────────────
-- PostgreSQL ENUM creates a new data type with a fixed set of allowed values.
-- INSERT or UPDATE with an invalid value throws an error BEFORE hitting the app.
-- This is stronger than CHECK constraints because it's enforced at the type level.

CREATE TYPE severity_level AS ENUM (
    'low',       -- Minor incident, no serious injuries
    'medium',    -- Moderate — possible injuries, partial lane closure
    'high',      -- Serious — multiple vehicles, full lane closure
    'critical'   -- Life-threatening — multiple casualties
);

CREATE TYPE accident_status AS ENUM (
    'detected',    -- AI just detected it — awaiting operator action
    'responding',  -- Operator acknowledged, units dispatched
    'resolved'     -- Scene cleared, road normal
);

CREATE TYPE signal_mode AS ENUM (
    'auto',       -- Normal timed red/amber/green cycle
    'emergency',  -- Green corridor active for ambulance
    'manual'      -- Operator has taken direct control
);


-- ─── Users Table ──────────────────────────────────────────────────────────────

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100)  NOT NULL,
    email      VARCHAR(150)  NOT NULL UNIQUE,        -- Login identifier
    password   VARCHAR(255)  NOT NULL,               -- bcrypt hash
    role       VARCHAR(50)   NOT NULL DEFAULT 'operator',  -- admin | operator
    is_active  BOOLEAN       NOT NULL DEFAULT TRUE,  -- Soft delete flag
    created_at TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,

    -- Data integrity constraints
    CONSTRAINT email_not_empty CHECK (email <> ''),
    CONSTRAINT name_not_empty  CHECK (name  <> '')
);

-- Index for fast login lookups (WHERE email = '...')
CREATE INDEX idx_users_email ON users(email);


-- ─── Accidents Table ──────────────────────────────────────────────────────────

CREATE TABLE accidents (
    id          SERIAL          PRIMARY KEY,
    location    VARCHAR(255)    NOT NULL,
    latitude    FLOAT,                               -- GPS (nullable if not available)
    longitude   FLOAT,
    severity    severity_level  NOT NULL DEFAULT 'medium',
    status      accident_status NOT NULL DEFAULT 'detected',
    confidence  FLOAT           CHECK (confidence BETWEEN 0 AND 1),  -- AI score
    camera_id   VARCHAR(100),                        -- Source camera identifier
    image_path  VARCHAR(500),                        -- Path to frame snapshot
    description TEXT,
    detected_at TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,                         -- NULL until resolved

    -- Resolved incidents must have a resolution timestamp
    CONSTRAINT resolved_has_timestamp
        CHECK (status != 'resolved' OR resolved_at IS NOT NULL)
);

-- Frequently queried columns get indexes for fast lookups
CREATE INDEX idx_accidents_status      ON accidents(status);
CREATE INDEX idx_accidents_detected_at ON accidents(detected_at DESC);
CREATE INDEX idx_accidents_severity    ON accidents(severity);
CREATE INDEX idx_accidents_camera      ON accidents(camera_id);


-- ─── Traffic Signals Table ────────────────────────────────────────────────────

CREATE TABLE traffic_signals (
    id           SERIAL       PRIMARY KEY,
    signal_id    VARCHAR(50)  NOT NULL UNIQUE,   -- e.g. "SIG-001" (IoT address)
    location     VARCHAR(255) NOT NULL,
    latitude     FLOAT,
    longitude    FLOAT,
    current_mode signal_mode  NOT NULL DEFAULT 'auto',
    is_online    BOOLEAN      NOT NULL DEFAULT TRUE,
    last_update  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signals_mode ON traffic_signals(current_mode);


-- ─── Useful Views ────────────────────────────────────────────────────────────
-- Views are saved queries — useful for common reporting needs.

-- Active incidents view (status != resolved)
CREATE OR REPLACE VIEW active_incidents AS
    SELECT *
    FROM   accidents
    WHERE  status != 'resolved'
    ORDER  BY
        CASE severity
            WHEN 'critical' THEN 1
            WHEN 'high'     THEN 2
            WHEN 'medium'   THEN 3
            WHEN 'low'      THEN 4
        END,
        detected_at DESC;

-- Today's summary view
CREATE OR REPLACE VIEW todays_summary AS
    SELECT
        COUNT(*)                                            AS total_today,
        COUNT(*) FILTER (WHERE status != 'resolved')       AS active,
        COUNT(*) FILTER (WHERE status = 'resolved')        AS resolved_today,
        ROUND(AVG(
            EXTRACT(EPOCH FROM (resolved_at - detected_at)) / 60
        )::NUMERIC, 1)                                     AS avg_response_minutes
    FROM accidents
    WHERE DATE(detected_at) = CURRENT_DATE;

-- ENUM type for ambulance operational status.
-- Stored in the DB so even raw SQL inserts are validated.
DO $$ BEGIN
    CREATE TYPE ambulance_status AS ENUM ('available', 'busy', 'offline');
EXCEPTION
    WHEN duplicate_object THEN NULL;  -- safe to re-run
END $$;
 
-- Main ambulances table
CREATE TABLE IF NOT EXISTS ambulances (
    id               SERIAL          PRIMARY KEY,
    ambulance_number VARCHAR(20)     NOT NULL UNIQUE,
    driver_name      VARCHAR(100)    NOT NULL,
    status           ambulance_status NOT NULL DEFAULT 'available',
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,
    last_updated     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
 
-- Index on status: dispatch queries always filter WHERE status = 'available'
CREATE INDEX IF NOT EXISTS idx_ambulances_status
    ON ambulances (status);
 
-- Partial index on coordinates for available units only.
-- The dispatch service only queries available units with valid GPS.
-- Partial index is smaller and faster than a full index.
CREATE INDEX IF NOT EXISTS idx_ambulances_gps_available
    ON ambulances (latitude, longitude)
    WHERE status = 'available'
      AND latitude  IS NOT NULL
      AND longitude IS NOT NULL;
 
-- Trigger: keep last_updated current on every row change
CREATE OR REPLACE FUNCTION update_ambulance_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
 
DROP TRIGGER IF EXISTS trg_ambulance_updated ON ambulances;
CREATE TRIGGER trg_ambulance_updated
    BEFORE UPDATE ON ambulances
    FOR EACH ROW EXECUTE FUNCTION update_ambulance_timestamp();
 
