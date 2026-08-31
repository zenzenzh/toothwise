-- One-time fix: corrects the risklevel/sex enum type labels created by an
-- earlier version of schema.sql. SQLAlchemy's Enum(SomePythonEnum) stores
-- each member's NAME (low/medium/high, male/female), not its human
-- readable VALUE (LOW/MEDIUM/HIGH, Male/Female) - the old schema.sql had
-- these backwards, causing every screening/patient insert or dashboard
-- query to fail with "invalid input value for enum ...".
--
-- Safe to re-run. Uses ALTER TYPE ... RENAME VALUE (Postgres 10+), which
-- fixes the type in place - no data loss, no need to drop/recreate.

DO $$ BEGIN
    ALTER TYPE risklevel RENAME VALUE 'LOW' TO 'low';
EXCEPTION WHEN undefined_object OR others THEN NULL; END $$;

DO $$ BEGIN
    ALTER TYPE risklevel RENAME VALUE 'MEDIUM' TO 'medium';
EXCEPTION WHEN undefined_object OR others THEN NULL; END $$;

DO $$ BEGIN
    ALTER TYPE risklevel RENAME VALUE 'HIGH' TO 'high';
EXCEPTION WHEN undefined_object OR others THEN NULL; END $$;

DO $$ BEGIN
    ALTER TYPE sex RENAME VALUE 'Male' TO 'male';
EXCEPTION WHEN undefined_object OR others THEN NULL; END $$;

DO $$ BEGIN
    ALTER TYPE sex RENAME VALUE 'Female' TO 'female';
EXCEPTION WHEN undefined_object OR others THEN NULL; END $$;

-- Sanity check afterwards - should show low/medium/high and male/female:
-- SELECT enumlabel FROM pg_enum WHERE enumtypid = 'risklevel'::regtype;
-- SELECT enumlabel FROM pg_enum WHERE enumtypid = 'sex'::regtype;
