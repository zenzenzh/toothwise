-- ============================================================
-- TOOTHWISE — Database Schema (PostgreSQL)
-- Source of truth for the DB structure. Mirrors backend/app/models.py
-- exactly as of this version — if you add/change a column in models.py,
-- update this file too and re-run the matching ALTER statement, the same
-- way add_detection_set_column.sql patched an existing DB.
--
-- Run once, against an empty database:
--   psql -U postgres -d toothwise -f schema.sql
--
-- (Run this from your regular terminal, NOT from inside an open psql
-- prompt — if you're already at a `toothwise=#` prompt, first quit with
-- \q, then run the command above from cmd/PowerShell.)
-- ============================================================

-- ---------- Enum types ----------
-- Names match what SQLAlchemy's Enum(PythonEnumClass) auto-generates
-- (lowercased class name), so this file and app/models.py never fight
-- over type ownership.
--
-- IMPORTANT: SQLAlchemy's Enum(SomePythonEnum) stores each member's NAME
-- by default, NOT its value, unless the column is declared with
-- values_callable=. app/models.py defines:
--   RiskLevel: low="LOW", medium="MEDIUM", high="HIGH"   -> stored as "low"/"medium"/"high"
--   Sex:       male="Male", female="Female"              -> stored as "male"/"female"
--   DentistRole: dentist="dentist", receptionist=..., assistant=...  -> name == value
--   (dentist is the administrator role: full access, staff management, audit log)
-- The labels below MUST be the member NAMES (lowercase), not the
-- human-readable VALUES, or every insert/query fails with
-- "invalid input value for enum ...".
DO $$ BEGIN
    CREATE TYPE dentistrole AS ENUM ('dentist', 'receptionist', 'assistant');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE risklevel AS ENUM ('low', 'medium', 'high');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE sex AS ENUM ('male', 'female');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE appointmentstatus AS ENUM ('scheduled', 'completed', 'cancelled', 'no_show');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ---------- dentists ----------
CREATE TABLE IF NOT EXISTS dentists (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR(120)  NOT NULL,
    email           VARCHAR(150)  NOT NULL UNIQUE,
    hashed_password VARCHAR(255)  NOT NULL,
    role            dentistrole   NOT NULL DEFAULT 'dentist',
    license_no      VARCHAR(60),
    is_active       BOOLEAN       DEFAULT TRUE,
    created_at      TIMESTAMP     DEFAULT (NOW() AT TIME ZONE 'utc')
);
CREATE INDEX IF NOT EXISTS ix_dentists_email ON dentists (email);

-- ---------- patients ----------
CREATE TABLE IF NOT EXISTS patients (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR(120)  NOT NULL,
    birthdate       DATE,
    sex             sex,
    contact_number  VARCHAR(30),
    address         VARCHAR(255),
    -- Patient-portal self-service login. NULL for patients who only exist
    -- because staff added them through the clinic UI (no online account).
    email           VARCHAR(150)  UNIQUE,
    hashed_password VARCHAR(255),
    is_active       BOOLEAN       DEFAULT TRUE,
    created_at      TIMESTAMP     DEFAULT (NOW() AT TIME ZONE 'utc')
);
CREATE INDEX IF NOT EXISTS ix_patients_email ON patients (email);

-- ---------- screenings ----------
CREATE TABLE IF NOT EXISTS screenings (
    id              SERIAL PRIMARY KEY,
    patient_id      INTEGER       NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    dentist_id      INTEGER       REFERENCES dentists(id) ON DELETE SET NULL,
    image_path      VARCHAR(255)  NOT NULL,
    image_width     INTEGER       NOT NULL,
    image_height    INTEGER       NOT NULL,
    risk_level      risklevel     NOT NULL DEFAULT 'LOW',
    risk_score      INTEGER       DEFAULT 0,
    yolov8_ms       FLOAT         DEFAULT 0.0,
    yolov12_ms      FLOAT         DEFAULT 0.0,
    created_at      TIMESTAMP     DEFAULT (NOW() AT TIME ZONE 'utc')
);
CREATE INDEX IF NOT EXISTS ix_screenings_patient_id ON screenings (patient_id);
CREATE INDEX IF NOT EXISTS ix_screenings_dentist_id ON screenings (dentist_id);

-- ---------- detections ----------
-- x1/y1/x2/y2 are normalized (0-1) corner coordinates, not pixels, so the
-- frontend can draw the overlay at any render size.
CREATE TABLE IF NOT EXISTS detections (
    id              SERIAL PRIMARY KEY,
    screening_id    INTEGER       NOT NULL REFERENCES screenings(id) ON DELETE CASCADE,
    label           VARCHAR(40)   NOT NULL,
    confidence      FLOAT         NOT NULL,
    x1              FLOAT         NOT NULL,
    y1              FLOAT         NOT NULL,
    x2              FLOAT         NOT NULL,
    y2              FLOAT         NOT NULL,
    source_model    VARCHAR(20)   DEFAULT 'ensemble',   -- yolov8 / yolov12 / ensemble
    -- Which detection pass this row belongs to: 'fused' is the clinical
    -- result that drives risk score + recommendations; 'yolov8_raw' /
    -- 'yolov12_raw' are each model's unfused output, kept only for the
    -- model-comparison view. Without this column a fused row whose
    -- source_model happens to be 'yolov8' is indistinguishable from a
    -- genuine raw yolov8_raw row.
    detection_set   VARCHAR(20)   NOT NULL DEFAULT 'fused'
);
CREATE INDEX IF NOT EXISTS ix_detections_screening_id ON detections (screening_id);

-- ---------- recommendations ----------
CREATE TABLE IF NOT EXISTS recommendations (
    id              SERIAL PRIMARY KEY,
    screening_id    INTEGER       NOT NULL REFERENCES screenings(id) ON DELETE CASCADE,
    text            TEXT          NOT NULL,
    priority        INTEGER       DEFAULT 0,  -- 0 = normal, 1 = urgent
    order_index     INTEGER       DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_recommendations_screening_id ON recommendations (screening_id);

-- ---------- clinical_notes ----------
CREATE TABLE IF NOT EXISTS clinical_notes (
    id              SERIAL PRIMARY KEY,
    screening_id    INTEGER       NOT NULL REFERENCES screenings(id) ON DELETE CASCADE,
    dentist_id      INTEGER       REFERENCES dentists(id) ON DELETE SET NULL,
    body            TEXT          NOT NULL,
    created_at      TIMESTAMP     DEFAULT (NOW() AT TIME ZONE 'utc')
);
CREATE INDEX IF NOT EXISTS ix_clinical_notes_screening_id ON clinical_notes (screening_id);

-- ---------- appointments ----------
CREATE TABLE IF NOT EXISTS appointments (
    id              SERIAL PRIMARY KEY,
    patient_id      INTEGER       NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    dentist_id      INTEGER       REFERENCES dentists(id) ON DELETE SET NULL,
    scheduled_at    TIMESTAMP     NOT NULL,
    reason          VARCHAR(255),
    status          appointmentstatus NOT NULL DEFAULT 'scheduled',
    notes           TEXT,
    created_at      TIMESTAMP     DEFAULT (NOW() AT TIME ZONE 'utc')
);
CREATE INDEX IF NOT EXISTS ix_appointments_patient_id ON appointments (patient_id);
CREATE INDEX IF NOT EXISTS ix_appointments_dentist_id ON appointments (dentist_id);
CREATE INDEX IF NOT EXISTS ix_appointments_scheduled_at ON appointments (scheduled_at);

-- ---------- audit_logs ----------
-- Append-only: the app only ever INSERTs here, never UPDATEs/DELETEs.
CREATE TABLE IF NOT EXISTS audit_logs (
    id                SERIAL PRIMARY KEY,
    actor_dentist_id  INTEGER REFERENCES dentists(id) ON DELETE SET NULL,
    actor_email       VARCHAR(150),  -- denormalized snapshot, survives account deletion
    action            VARCHAR(60)   NOT NULL,
    entity_type       VARCHAR(40),
    entity_id         INTEGER,
    details           TEXT,
    created_at        TIMESTAMPTZ   DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);
