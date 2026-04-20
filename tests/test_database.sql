-- FILE: tests/test_database.sql
-- ======================================
-- Database Integrity & Constraint Tests
-- ======================================
--
-- These SQL tests verify that:
--   1. All required tables and columns exist
--   2. ENUM constraints reject invalid values
--   3. NOT NULL constraints are enforced
--   4. Data integrity rules hold
--   5. Indexes exist for performance
--   6. Seed data was loaded correctly
--
-- Run after seeding:
--   psql -U postgres -d emergency_db -f tests/test_database.sql
--
-- Each test uses PostgreSQL's ASSERT inside a DO block.
-- If an assertion fails, it raises an exception with the message.
-- If all pass, you'll see a series of NOTICE: PASS messages.


-- ─── Helper: Print PASS ───────────────────────────────────────────────────────
-- We use RAISE NOTICE for human-readable output.
-- In CI, check the exit code: psql returns 1 if any exception is raised.


-- ─── 1. Schema: Tables Exist ─────────────────────────────────────────────────
DO $$
BEGIN
    ASSERT (
        SELECT COUNT(*) = 3
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN ('users', 'accidents', 'traffic_signals')
    ), 'FAIL: Expected tables users, accidents, traffic_signals to exist';

    RAISE NOTICE 'PASS: All 3 required tables exist';
END $$;


-- ─── 2. Schema: Required Columns Exist ───────────────────────────────────────
DO $$
BEGIN
    -- users table
    ASSERT (SELECT COUNT(*) = 1 FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'password'),
           'FAIL: users.password column missing';

    ASSERT (SELECT COUNT(*) = 1 FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'is_active'),
           'FAIL: users.is_active column missing';

    -- accidents table
    ASSERT (SELECT COUNT(*) = 1 FROM information_schema.columns
            WHERE table_name = 'accidents' AND column_name = 'confidence'),
           'FAIL: accidents.confidence column missing';

    ASSERT (SELECT COUNT(*) = 1 FROM information_schema.columns
            WHERE table_name = 'accidents' AND column_name = 'resolved_at'),
           'FAIL: accidents.resolved_at column missing';

    -- traffic_signals table
    ASSERT (SELECT COUNT(*) = 1 FROM information_schema.columns
            WHERE table_name = 'traffic_signals' AND column_name = 'current_mode'),
           'FAIL: traffic_signals.current_mode column missing';

    RAISE NOTICE 'PASS: All required columns exist';
END $$;


-- ─── 3. ENUM Constraints ──────────────────────────────────────────────────────
DO $$
BEGIN
    -- Test that invalid severity is rejected
    BEGIN
        INSERT INTO accidents (location, severity)
        VALUES ('Test', 'invalid_severity'::severity_level);
        RAISE EXCEPTION 'FAIL: Invalid severity was accepted — ENUM constraint not working';
    EXCEPTION WHEN invalid_text_representation OR check_violation THEN
        RAISE NOTICE 'PASS: Invalid severity_level correctly rejected';
    END;

    -- Test that invalid status is rejected
    BEGIN
        INSERT INTO accidents (location, status)
        VALUES ('Test', 'invalid_status'::accident_status);
        RAISE EXCEPTION 'FAIL: Invalid status was accepted — ENUM constraint not working';
    EXCEPTION WHEN invalid_text_representation OR check_violation THEN
        RAISE NOTICE 'PASS: Invalid accident_status correctly rejected';
    END;

    -- Test that invalid signal mode is rejected
    BEGIN
        INSERT INTO traffic_signals (signal_id, location, current_mode)
        VALUES ('TEST-SIG', 'Test', 'invalid_mode'::signal_mode);
        RAISE EXCEPTION 'FAIL: Invalid signal_mode was accepted — ENUM constraint not working';
    EXCEPTION WHEN invalid_text_representation OR check_violation THEN
        RAISE NOTICE 'PASS: Invalid signal_mode correctly rejected';
    END;
END $$;


-- ─── 4. NOT NULL Constraints ─────────────────────────────────────────────────
DO $$
BEGIN
    -- accidents.location must not be NULL
    BEGIN
        INSERT INTO accidents (location) VALUES (NULL);
        RAISE EXCEPTION 'FAIL: NULL location was accepted';
    EXCEPTION WHEN not_null_violation THEN
        RAISE NOTICE 'PASS: accidents.location NOT NULL enforced';
    END;

    -- users.email must not be NULL
    BEGIN
        INSERT INTO users (name, email, password) VALUES ('Test', NULL, 'hash');
        RAISE EXCEPTION 'FAIL: NULL email was accepted';
    EXCEPTION WHEN not_null_violation THEN
        RAISE NOTICE 'PASS: users.email NOT NULL enforced';
    END;
END $$;


-- ─── 5. Unique Constraints ────────────────────────────────────────────────────
DO $$
BEGIN
    -- users.email must be unique
    BEGIN
        -- Insert the same email twice
        INSERT INTO users (name, email, password)
        VALUES ('User A', 'duplicate@test.com', 'hash1');

        INSERT INTO users (name, email, password)
        VALUES ('User B', 'duplicate@test.com', 'hash2');

        RAISE EXCEPTION 'FAIL: Duplicate email was accepted';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: users.email UNIQUE enforced';
    END;

    -- Clean up
    DELETE FROM users WHERE email = 'duplicate@test.com';
END $$;


-- ─── 6. Seed Data ─────────────────────────────────────────────────────────────
DO $$
BEGIN
    ASSERT (SELECT COUNT(*) >= 1 FROM users),
           'FAIL: No users in database — run seed.sql';

    ASSERT (SELECT COUNT(*) >= 1 FROM traffic_signals),
           'FAIL: No traffic signals — run seed.sql';

    ASSERT (SELECT COUNT(*) >= 1 FROM accidents),
           'FAIL: No accidents — run seed.sql';

    RAISE NOTICE 'PASS: Seed data present in all tables';
END $$;


-- ─── 7. Data Quality ─────────────────────────────────────────────────────────
DO $$
BEGIN
    -- No resolved accident should have NULL resolved_at
    ASSERT (
        SELECT COUNT(*) = 0
        FROM accidents
        WHERE status = 'resolved'
          AND resolved_at IS NULL
    ), 'FAIL: Resolved accidents found with NULL resolved_at';

    RAISE NOTICE 'PASS: All resolved accidents have resolved_at timestamp';

    -- Confidence values must be in [0, 1]
    ASSERT (
        SELECT COUNT(*) = 0
        FROM accidents
        WHERE confidence IS NOT NULL
          AND (confidence < 0 OR confidence > 1)
    ), 'FAIL: confidence values found outside [0, 1]';

    RAISE NOTICE 'PASS: All confidence values are in valid range [0, 1]';
END $$;


-- ─── 8. Indexes ───────────────────────────────────────────────────────────────
DO $$
BEGIN
    ASSERT (
        SELECT COUNT(*) >= 1
        FROM pg_indexes
        WHERE tablename = 'accidents' AND indexname LIKE '%status%'
    ), 'FAIL: Index on accidents.status missing — queries will be slow';

    ASSERT (
        SELECT COUNT(*) >= 1
        FROM pg_indexes
        WHERE tablename = 'accidents' AND indexname LIKE '%detected_at%'
    ), 'FAIL: Index on accidents.detected_at missing';

    RAISE NOTICE 'PASS: Performance indexes exist';
END $$;


-- ─── 9. Analytics Queries (Smoke Test) ───────────────────────────────────────
-- Run the analytics queries and verify they return without error.

DO $$
DECLARE
    v_count    INT;
    v_avg      NUMERIC;
BEGIN
    -- Severity breakdown query (used by /api/analytics/severity-breakdown)
    SELECT COUNT(*) INTO v_count
    FROM (
        SELECT severity, COUNT(*) AS cnt
        FROM accidents
        GROUP BY severity
    ) breakdown;

    RAISE NOTICE 'PASS: Severity breakdown query executed (%s severity groups)', v_count;

    -- Average response time query (used by /api/analytics/summary)
    SELECT COALESCE(ROUND(AVG(
        EXTRACT(EPOCH FROM (resolved_at - detected_at)) / 60
    )::NUMERIC, 1), 0) INTO v_avg
    FROM accidents
    WHERE resolved_at IS NOT NULL;

    RAISE NOTICE 'PASS: Avg response time query executed (avg: % minutes)', v_avg;
END $$;


-- ─── Summary ─────────────────────────────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '====================================';
    RAISE NOTICE 'All database tests passed! ✅';
    RAISE NOTICE '====================================';
END $$;
