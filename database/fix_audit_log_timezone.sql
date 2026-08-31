-- One-time fix: audit_logs.created_at was TIMESTAMP (no timezone), storing
-- naive UTC clock values. The API serialized those without a 'Z'/offset,
-- so the frontend's `new Date(...)` parsed them as if they were already in
-- the *browser's* local time instead of UTC - e.g. an event logged at
-- 05:30 UTC (1:30 PM in Manila) showed up as "5:30 AM" instead of "1:30 PM".
--
-- This converts the column to TIMESTAMPTZ, telling Postgres the existing
-- values are UTC (their true value), so it can correctly convert to any
-- timezone from here on. No data is lost or shifted - safe to re-run.

ALTER TABLE audit_logs
    ALTER COLUMN created_at TYPE TIMESTAMPTZ
    USING created_at AT TIME ZONE 'utc';

ALTER TABLE audit_logs
    ALTER COLUMN created_at SET DEFAULT NOW();
