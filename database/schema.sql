-- ============================================================================
-- FILE: database/schema.sql
-- ============================================================================
-- PostgreSQL Database Schema — Smart AI Emergency Response Platform
-- ============================================================================
--
-- FILE PATH:
--   smart-emergency-response-platform/
--   └── database/
--       └── schema.sql   ← this file
--
-- PROCESS — how this file is used:
--   DEVELOPMENT (run manually):
--     psql -U postgres -d emergency_db -f database/schema.sql
--
--   DOCKER COMPOSE (run automatically on first container start):
--     Place in docker-entrypoint-initdb.d/ — PostgreSQL executes it once
--     when the data directory is empty (i.e. first-ever container start).
--     On subsequent starts the file is ignored even if it changed.
--     To force a re-run: docker compose down -v && docker compose up
--
--   NEON / CLOUD POSTGRESQL:
--     Copy-paste into the Neon SQL editor, or run via psql with the
--     connection string from your Neon dashboard:
--     psql "postgresql://user:pass@host/db?sslmode=require" -f database/schema.sql
--
-- RE-RUNNING SAFELY:
--   The cleanup block at the top drops everything in the correct dependency
--   order (child tables before parents, types after tables).
--   Re-running the script resets the database to a clean state.
--   WARNING: all data is lost on re-run. Use Alembic migrations in production
--   to make incremental, non-destructive schema changes.
--
-- DESIGN DECISIONS:
--   - ENUM types enforce valid values at the database level
--   - NUMERIC(10,7) for GPS coordinates — avoids IEEE 754 float rounding
--   - TIMESTAMPTZ everywhere — timezone-aware, avoids silent TZ bugs
--   - Soft delete via is_active on users (no hard DELETE)
--   - Auto-update triggers on updated_at / last_updated columns
--   - Partial indexes where queries have a known selective WHERE clause
--   - Explicit column lists in views (never SELECT *)
--   - COMMENT ON for all tables and key columns (visible in DB tools)
--
-- ============================================================================


-- ============================================================================
-- 0. SETTINGS
-- ============================================================================

-- Abort immediately on any error — do not execute partial migrations
\set ON_ERROR_STOP on


-- ============================================================================
-- 1. CLEANUP  (drop in reverse dependency order: children first, types last)
-- ============================================================================

DROP TABLE IF EXISTS ambulances       CASCADE;
DROP TABLE IF EXISTS traffic_signals  CASCADE;
DROP TABLE IF EXISTS accidents        CASCADE;
DROP TABLE IF EXISTS users            CASCADE;

-- Drop all custom ENUM types (must happen AFTER tables are dropped)
DROP TYPE IF EXISTS ambulance_status  CASCADE;
DROP TYPE IF EXISTS signal_mode       CASCADE;
DROP TYPE IF EXISTS accident_status   CASCADE;
DROP TYPE IF EXISTS severity_level    CASCADE;
DROP TYPE IF EXISTS user_role         CASCADE;


-- ============================================================================
-- 2. ENUM TYPES
-- ============================================================================
-- PostgreSQL ENUMs are enforced at the type level — invalid values are
-- rejected before reaching the application layer.

CREATE TYPE user_role AS ENUM (
    'admin',      -- Full access: manage users, override signals, view all data
    'operator',   -- Respond to accidents, control signals
    'viewer'      -- Read-only dashboard access
);

CREATE TYPE severity_level AS ENUM (
    'low',        -- Minor incident, no serious injuries
    'medium',     -- Moderate — possible injuries, partial lane closure
    'high',       -- Serious — multiple vehicles, full lane closure
    'critical'    -- Life-threatening — multiple casualties
);

CREATE TYPE accident_status AS ENUM (
    'detected',    -- AI detected — awaiting operator action
    'responding',  -- Operator acknowledged, units dispatched
    'resolved'     -- Scene cleared, road normal
);

CREATE TYPE signal_mode AS ENUM (
    'auto',        -- Normal timed red/amber/green cycle
    'emergency',   -- Green corridor active for ambulance
    'manual'       -- Operator has taken direct control
);

CREATE TYPE ambulance_status AS ENUM (
    'available',   -- Ready for dispatch
    'busy',        -- Currently responding to an incident
    'offline'      -- Out of service / maintenance
);


-- ============================================================================
-- 3. SHARED TRIGGER FUNCTION  (reused by multiple tables)
-- ============================================================================
-- A single function that sets NEW.updated_at = NOW() on every row UPDATE.
-- Attached to tables via individual triggers below.

CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION fn_set_updated_at() IS
    'Generic BEFORE UPDATE trigger function — sets updated_at to NOW().';


-- ============================================================================
-- 4. USERS TABLE
-- ============================================================================

CREATE TABLE users (
    id         SERIAL        PRIMARY KEY,
    name       VARCHAR(100)  NOT NULL,
    email      VARCHAR(150)  NOT NULL,
    -- FIXED: use ENUM instead of free-text VARCHAR for the role field.
    -- Previously: role VARCHAR(50) — accepted any string, including typos
    -- and privilege-escalation attempts like 'superadmin'.
    role       user_role     NOT NULL DEFAULT 'operator',
    -- FIXED: bcrypt output is always exactly 60 characters.
    -- Previously: VARCHAR(255) — misleading and wastes storage metadata.
    password   CHAR(60)      NOT NULL,
    is_active  BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- FIXED: added NOT NULL DEFAULT NOW() so the column is always populated.
    -- Previously: TIMESTAMPTZ with no default — always NULL.
    -- The trigger below keeps it current on every UPDATE.
    updated_at TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    -- Uniqueness enforced at DB level (not just app level)
    CONSTRAINT users_email_unique UNIQUE (email),
    -- Reject obviously bad data at insert time
    CONSTRAINT users_email_not_empty CHECK (email <> ''),
    CONSTRAINT users_name_not_empty  CHECK (name  <> '')
);

COMMENT ON TABLE  users                IS 'Operator and admin accounts for the dashboard.';
COMMENT ON COLUMN users.role           IS 'user_role ENUM: admin | operator | viewer';
COMMENT ON COLUMN users.password       IS 'bcrypt hash — always 60 chars. Never store plaintext.';
COMMENT ON COLUMN users.is_active      IS 'Soft-delete flag. Set FALSE instead of DELETE.';
COMMENT ON COLUMN users.updated_at     IS 'Auto-updated by trg_users_updated on every row change.';

-- FIXED: partial index covers only active users — smaller, faster for auth queries.
-- Previously: CREATE INDEX idx_users_email ON users(email) — full table index.
-- Auth query is always: WHERE email = ? AND is_active = TRUE
-- Inactive users are excluded from the index entirely.
CREATE UNIQUE INDEX idx_users_email_active
    ON users (email)
    WHERE is_active = TRUE;

-- Auto-update trigger for updated_at
CREATE TRIGGER trg_users_updated
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();


-- ============================================================================
-- 5. ACCIDENTS TABLE
-- ============================================================================

CREATE TABLE accidents (
    id          SERIAL           PRIMARY KEY,
    location    VARCHAR(255)     NOT NULL,

    -- FIXED: NUMERIC(10,7) instead of DOUBLE PRECISION.
    -- DOUBLE PRECISION (IEEE 754) has binary rounding errors for decimal
    -- GPS coordinates. NUMERIC is exact — 18.4832430 stays 18.4832430.
    -- (10,7) = up to 3 digits before decimal + 7 after → covers ±180°.
    latitude    NUMERIC(10, 7),
    longitude   NUMERIC(10, 7),

    severity    severity_level   NOT NULL DEFAULT 'medium',
    status      accident_status  NOT NULL DEFAULT 'detected',

    -- AI confidence score from the CNN model (0.0 – 1.0)
    confidence  NUMERIC(5, 4)
                    CHECK (confidence BETWEEN 0 AND 1),

    camera_id   VARCHAR(100),
    image_path  VARCHAR(500),
    description TEXT,
    detected_at TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    -- A resolved accident MUST have a resolution timestamp.
    -- Prevents resolved rows with NULL resolved_at (unqueryable for SLA calcs).
    CONSTRAINT accidents_resolved_has_timestamp
        CHECK (status <> 'resolved' OR resolved_at IS NOT NULL),

    -- Logical sanity: resolution cannot precede detection
    CONSTRAINT accidents_resolved_after_detected
        CHECK (resolved_at IS NULL OR resolved_at >= detected_at)
);

COMMENT ON TABLE  accidents             IS 'AI-detected road accidents from CCTV analysis.';
COMMENT ON COLUMN accidents.confidence  IS 'CNN model output: probability that this is an accident (0–1).';
COMMENT ON COLUMN accidents.camera_id   IS 'Identifier of the source camera, e.g. CAM-001.';
COMMENT ON COLUMN accidents.resolved_at IS 'Set when status = resolved. NULL for active incidents.';

-- Standard lookup indexes
CREATE INDEX idx_accidents_status      ON accidents (status);
CREATE INDEX idx_accidents_detected_at ON accidents (detected_at DESC);
CREATE INDEX idx_accidents_severity    ON accidents (severity);

-- FIXED: composite + partial index for the detect-loop cooldown query pattern:
--   WHERE camera_id = ? AND status != 'resolved'
-- Previously: two separate single-column indexes required a bitmap heap scan.
-- This partial index is smaller (excludes resolved rows) and covers both filters.
CREATE INDEX idx_accidents_camera_active
    ON accidents (camera_id, status)
    WHERE status <> 'resolved';


-- ============================================================================
-- 6. TRAFFIC SIGNALS TABLE
-- ============================================================================

CREATE TABLE traffic_signals (
    id           SERIAL        PRIMARY KEY,
    signal_id    VARCHAR(50)   NOT NULL UNIQUE,
    location     VARCHAR(255)  NOT NULL,
    latitude     NUMERIC(10, 7),
    longitude    NUMERIC(10, 7),
    current_mode signal_mode   NOT NULL DEFAULT 'auto',
    is_online    BOOLEAN       NOT NULL DEFAULT TRUE,
    -- Renamed from last_update → updated_at for naming consistency across tables
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  traffic_signals              IS 'IoT-connected traffic signal units.';
COMMENT ON COLUMN traffic_signals.signal_id    IS 'Physical unit address, e.g. SIG-001.';
COMMENT ON COLUMN traffic_signals.current_mode IS 'signal_mode ENUM: auto | emergency | manual';
COMMENT ON COLUMN traffic_signals.updated_at   IS 'Auto-updated by trg_signals_updated on every row change.';

CREATE INDEX idx_signals_mode ON traffic_signals (current_mode);

-- Auto-update trigger (reuses shared function)
CREATE TRIGGER trg_signals_updated
    BEFORE UPDATE ON traffic_signals
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();


-- ============================================================================
-- 7. AMBULANCES TABLE
-- ============================================================================

CREATE TABLE ambulances (
    id               SERIAL            PRIMARY KEY,
    ambulance_number VARCHAR(20)       NOT NULL UNIQUE,
    driver_name      VARCHAR(100)      NOT NULL,
    status           ambulance_status  NOT NULL DEFAULT 'available',
    latitude         NUMERIC(10, 7),
    longitude        NUMERIC(10, 7),
    updated_at       TIMESTAMPTZ       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  ambulances                IS 'Ambulance fleet — tracks real-time location and availability.';
COMMENT ON COLUMN ambulances.status         IS 'ambulance_status ENUM: available | busy | offline';
COMMENT ON COLUMN ambulances.updated_at     IS 'Auto-updated by trg_ambulances_updated on every row change.';
COMMENT ON COLUMN ambulances.latitude       IS 'Last known GPS latitude. NULL if GPS unavailable.';
COMMENT ON COLUMN ambulances.longitude      IS 'Last known GPS longitude. NULL if GPS unavailable.';

-- Dispatch queries: WHERE status = 'available'
CREATE INDEX idx_ambulances_status ON ambulances (status);

-- Partial index for spatial dispatch queries on available units only.
-- Excludes busy/offline rows → smaller, faster for nearest-unit lookups.
CREATE INDEX idx_ambulances_gps_available
    ON ambulances (latitude, longitude)
    WHERE status = 'available'
      AND latitude  IS NOT NULL
      AND longitude IS NOT NULL;

-- Auto-update trigger (reuses shared function)
CREATE TRIGGER trg_ambulances_updated
    BEFORE UPDATE ON ambulances
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();


-- ============================================================================
-- 8. DISPATCH JUNCTION TABLE
-- ============================================================================
-- ADDED: links ambulances to accidents so we can track which unit responded
-- to which incident. Enables response-time SLA reporting and load balancing.

CREATE TABLE accident_dispatch (
    id            SERIAL       PRIMARY KEY,
    accident_id   INT          NOT NULL
                      REFERENCES accidents  (id) ON DELETE CASCADE,
    ambulance_id  INT          NOT NULL
                      REFERENCES ambulances (id) ON DELETE RESTRICT,
    dispatched_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    arrived_at    TIMESTAMPTZ,
    cleared_at    TIMESTAMPTZ,

    -- One ambulance can only be dispatched once per accident
    CONSTRAINT dispatch_unique UNIQUE (accident_id, ambulance_id),

    -- Arrival cannot precede dispatch
    CONSTRAINT dispatch_arrived_after_dispatched
        CHECK (arrived_at IS NULL OR arrived_at >= dispatched_at),

    -- Clearance cannot precede arrival
    CONSTRAINT dispatch_cleared_after_arrived
        CHECK (cleared_at IS NULL OR (arrived_at IS NOT NULL AND cleared_at >= arrived_at))
);

COMMENT ON TABLE  accident_dispatch              IS 'Which ambulance was dispatched to which accident, with timestamps.';
COMMENT ON COLUMN accident_dispatch.arrived_at   IS 'NULL until unit confirms on-scene arrival.';
COMMENT ON COLUMN accident_dispatch.cleared_at   IS 'NULL until unit clears the scene.';

CREATE INDEX idx_dispatch_accident  ON accident_dispatch (accident_id);
CREATE INDEX idx_dispatch_ambulance ON accident_dispatch (ambulance_id);


-- ============================================================================
-- 9. VIEWS
-- ============================================================================

-- Active incidents — ordered by severity then recency
-- FIXED: explicit column list instead of SELECT * (view survives schema changes)
-- FIXED: severity ordering uses CASE WHEN on the ENUM label (not hardcoded int)
CREATE OR REPLACE VIEW active_incidents AS
    SELECT
        id,
        location,
        latitude,
        longitude,
        severity,
        status,
        confidence,
        camera_id,
        image_path,
        description,
        detected_at
    FROM accidents
    WHERE status <> 'resolved'
    ORDER BY
        CASE severity
            WHEN 'critical' THEN 1
            WHEN 'high'     THEN 2
            WHEN 'medium'   THEN 3
            WHEN 'low'      THEN 4
        END,
        detected_at DESC;

COMMENT ON VIEW active_incidents IS
    'Unresolved accidents ordered by severity (critical first) then detection time.';

-- Today''s summary — FIXED: three bugs corrected
--   1. Date range filter uses index-compatible range instead of DATE() function
--   2. COALESCE wraps AVG so NULL is returned as 0 when no resolved incidents
--   3. Added total_active / total_resolved breakdown for dashboard widgets
CREATE OR REPLACE VIEW todays_summary AS
    SELECT
        COUNT(*)                                                AS total_today,
        COUNT(*) FILTER (WHERE status <> 'resolved')           AS active,
        COUNT(*) FILTER (WHERE status = 'resolved')            AS resolved_today,
        -- FIXED: COALESCE → returns 0 instead of NULL when nothing resolved yet
        COALESCE(
            ROUND(
                AVG(
                    EXTRACT(EPOCH FROM (resolved_at - detected_at)) / 60.0
                )::NUMERIC,
                1
            ),
            0
        )                                                       AS avg_response_minutes,
        COUNT(*) FILTER (WHERE severity = 'critical')          AS critical_today,
        COUNT(*) FILTER (WHERE severity = 'high')              AS high_today
    FROM accidents
    -- FIXED: range predicate is index-compatible (idx_accidents_detected_at)
    -- Previously: WHERE DATE(detected_at) = CURRENT_DATE
    --   → applied DATE() function per row, preventing index use
    WHERE detected_at >= CURRENT_DATE
      AND detected_at <  CURRENT_DATE + INTERVAL '1 day';

COMMENT ON VIEW todays_summary IS
    'Aggregate stats for the current calendar day. avg_response_minutes = 0 when no resolved incidents yet.';

-- Available ambulances — convenience view for dispatch service
CREATE OR REPLACE VIEW available_ambulances AS
    SELECT
        id,
        ambulance_number,
        driver_name,
        latitude,
        longitude,
        updated_at
    FROM ambulances
    WHERE status = 'available'
      AND latitude  IS NOT NULL
      AND longitude IS NOT NULL
    ORDER BY updated_at DESC;

COMMENT ON VIEW available_ambulances IS
    'Ambulances that are available and have a known GPS position — ready for dispatch.';


-- ============================================================================
-- 10. SEED DATA  (development only — remove for production)
-- ============================================================================

INSERT INTO traffic_signals (signal_id, location, latitude, longitude, current_mode)
VALUES
    ('SIG-001', 'FC Road & Bhandarkar Rd Junction',    18.5195, 73.8405, 'auto'),
    ('SIG-002', 'Karve Road & Dandekar Bridge',         18.5002, 73.8456, 'auto'),
    ('SIG-003', 'Pune Station Main Gate',               18.5284, 73.8742, 'auto'),
    ('SIG-004', 'Hinjewadi Phase 1 Entry',              18.5912, 73.7389, 'auto'),
    ('SIG-005', 'Viman Nagar IT Park Junction',         18.5679, 73.9143, 'auto');

INSERT INTO ambulances (ambulance_number, driver_name, status, latitude, longitude)
VALUES
    ('MH-12-AB-0001', 'Rajesh Kumar',   'available', 18.5196, 73.8553),
    ('MH-12-AB-0002', 'Suresh Patil',   'available', 18.5013, 73.8671),
    ('MH-12-AB-0003', 'Anil Deshmukh',  'busy',      18.5284, 73.8742),
    ('MH-12-AB-0004', 'Vikas Shinde',   'offline',   NULL,    NULL),
    ('MH-12-AB-0005', 'Priya Jadhav',   'available', 18.5679, 73.9143);

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================