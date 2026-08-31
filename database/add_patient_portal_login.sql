-- One-time fix: adds the patient self-service portal login columns to an
-- existing patients table (email, hashed_password, is_active). Safe to
-- re-run - each ADD COLUMN is guarded with IF NOT EXISTS.

ALTER TABLE patients ADD COLUMN IF NOT EXISTS email VARCHAR(150) UNIQUE;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);
ALTER TABLE patients ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS ix_patients_email ON patients (email);
