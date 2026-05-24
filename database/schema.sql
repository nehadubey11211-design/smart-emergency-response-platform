-- FILE: database/schema.sql
-- ================================
-- PostgreSQL Database Schema
-- ================================
-- Run to initialise from scratch:
--   psql -U postgres -d emergency_db -f database/schema.sql


-- ─── Cleanup ──────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS traffic_signal_events CASCADE;
DROP TABLE IF EXISTS traffic_signals       CASCADE;
DROP TABLE IF EXISTS accidents             CASCADE;
DROP TABLE IF EXISTS ambulances            CASCADE;
DROP TABLE IF EXISTS hospitals             CASCADE;
DROP TABLE IF EXISTS users                 CASCADE;

DROP TYPE IF EXISTS severity_level   CASCADE;
DROP TYPE IF EXISTS accident_status  CASCADE;
DROP TYPE IF EXISTS signal_mode      CASCADE;
DROP TYPE IF EXISTS ambulance_status CASCADE;


-- ─── ENUM Types ───────────────────────────────────────────────────────────────

CREATE TYPE severity_level AS ENUM (
    'low', 'medium', 'high', 'critical'
);

CREATE TYPE accident_status AS ENUM (
    'detected', 'responding', 'resolved'
);

CREATE TYPE signal_mode AS ENUM (
    'auto', 'emergency', 'manual'
);

CREATE TYPE ambulance_status AS ENUM (
    'available', 'busy', 'offline'
);


-- ─── Users ────────────────────────────────────────────────────────────────────

CREATE TABLE users (
    id            SERIAL        PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(150)  NOT NULL UNIQUE,
    password      VARCHAR(255)  NOT NULL,
    role          VARCHAR(50)   NOT NULL DEFAULT 'operator',
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ,

    CONSTRAINT email_not_empty CHECK (email <> ''),
    CONSTRAINT name_not_empty  CHECK (name  <> '')
);

CREATE INDEX idx_users_email ON users(email);


-- ─── Hospitals ────────────────────────────────────────────────────────────────

CREATE TABLE hospitals (
    id         SERIAL           PRIMARY KEY,
    name       VARCHAR(200)     NOT NULL,
    latitude   FLOAT            NOT NULL,
    longitude  FLOAT            NOT NULL,
    is_active  BOOLEAN          NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_hospital_location ON hospitals(latitude, longitude);


-- ─── Ambulances ───────────────────────────────────────────────────────────────

CREATE TABLE ambulances (
    id               SERIAL           PRIMARY KEY,
    ambulance_number VARCHAR(20)      NOT NULL UNIQUE,
    driver_name      VARCHAR(100)     NOT NULL,
    status           ambulance_status NOT NULL DEFAULT 'available',
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,
    last_updated     TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ambulances_status ON ambulances(status);
CREATE INDEX idx_ambulances_gps_available
    ON ambulances(latitude, longitude)
    WHERE status = 'available'
      AND latitude  IS NOT NULL
      AND longitude IS NOT NULL;

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


-- ─── Accidents ────────────────────────────────────────────────────────────────

CREATE TABLE accidents (
    id                      SERIAL          PRIMARY KEY,
    location                VARCHAR(255)    NOT NULL,
    latitude                FLOAT,
    longitude               FLOAT,
    dispatched_ambulance_id INTEGER         REFERENCES ambulances(id) ON DELETE SET NULL,
    severity                severity_level  NOT NULL DEFAULT 'medium',
    status                  accident_status NOT NULL DEFAULT 'detected',
    confidence              FLOAT           CHECK (confidence BETWEEN 0 AND 1),
    camera_id               VARCHAR(100),
    image_path              VARCHAR(500),
    description             TEXT,
    detected_at             TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    resolved_at             TIMESTAMPTZ,

    CONSTRAINT resolved_has_timestamp
        CHECK (status != 'resolved' OR resolved_at IS NOT NULL)
);

CREATE INDEX idx_accidents_status      ON accidents(status);
CREATE INDEX idx_accidents_detected_at ON accidents(detected_at DESC);
CREATE INDEX idx_accidents_severity    ON accidents(severity);
CREATE INDEX idx_accidents_camera      ON accidents(camera_id);


-- ─── Traffic Signals ──────────────────────────────────────────────────────────

CREATE TABLE traffic_signals (
    id           SERIAL       PRIMARY KEY,
    signal_id    VARCHAR(50)  NOT NULL UNIQUE,
    location     VARCHAR(255) NOT NULL,
    latitude     FLOAT,
    longitude    FLOAT,
    current_mode signal_mode  NOT NULL DEFAULT 'auto',
    is_online    BOOLEAN      NOT NULL DEFAULT TRUE,
    last_update  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signals_mode ON traffic_signals(current_mode);


-- ─── Traffic Signal Events (audit log) ───────────────────────────────────────

CREATE TABLE traffic_signal_events (
    id           SERIAL      PRIMARY KEY,
    signal_id    VARCHAR(50) NOT NULL REFERENCES traffic_signals(signal_id) ON DELETE CASCADE,
    from_mode    signal_mode NOT NULL,
    to_mode      signal_mode NOT NULL,
    triggered_by VARCHAR(100),
    accident_id  INTEGER     REFERENCES accidents(id) ON DELETE SET NULL,
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signal_events_signal_id   ON traffic_signal_events(signal_id);
CREATE INDEX idx_signal_events_occurred_at ON traffic_signal_events(occurred_at);


-- ─── Views ────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW active_incidents AS
    SELECT *
    FROM   accidents
    WHERE  status != 'resolved'
    ORDER BY
        CASE severity
            WHEN 'critical' THEN 1
            WHEN 'high'     THEN 2
            WHEN 'medium'   THEN 3
            WHEN 'low'      THEN 4
        END,
        detected_at DESC;

CREATE OR REPLACE VIEW todays_summary AS
    SELECT
        COUNT(*)                                             AS total_today,
        COUNT(*) FILTER (WHERE status != 'resolved')        AS active,
        COUNT(*) FILTER (WHERE status = 'resolved')         AS resolved_today,
        ROUND(AVG(
            EXTRACT(EPOCH FROM (resolved_at - detected_at)) / 60
        )::NUMERIC, 1)                                      AS avg_response_minutes
    FROM accidents
    WHERE DATE(detected_at) = CURRENT_DATE;
