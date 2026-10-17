-- ============================================================
-- TOOTHWISE — staff role change (Option B)
--   Old: dentistrole = ('admin', 'dentist')
--   New: dentistrole = ('dentist', 'receptionist', 'assistant')
--        `dentist` is now the clinic administrator (full access).
--
-- Existing databases ONLY. A fresh database created from schema.sql already
-- starts with the new labels. The backend also applies this automatically on
-- startup (see backend/app/main.py::_migrate_roles_v2), so this script is for
-- teams that prefer to migrate by hand before starting the API.
--
--   psql -U postgres -d toothwise -f update_staff_roles.sql
-- ============================================================

-- 1. Add the two new enum labels.
--    `ALTER TYPE ... ADD VALUE` cannot run inside a transaction block on
--    PostgreSQL < 12, so run these two statements on their own.
ALTER TYPE dentistrole ADD VALUE IF NOT EXISTS 'receptionist';
ALTER TYPE dentistrole ADD VALUE IF NOT EXISTS 'assistant';

-- 2. Fold the legacy `admin` role into `dentist` (the administrator role).
--    PostgreSQL cannot drop a value from an enum, so 'admin' remains in the
--    type but is never assigned once this statement has run.
UPDATE dentists SET role = 'dentist' WHERE role = 'admin';

-- 3. (Optional) verify the result:
--    SELECT role, count(*) FROM dentists GROUP BY role;
