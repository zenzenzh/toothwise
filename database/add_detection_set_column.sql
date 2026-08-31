-- One-time fix: adds the detection_set column that the updated models.py
-- expects. Needed because SQLAlchemy's create_all() only creates missing
-- TABLES, it never ALTERs existing ones - so an already-created
-- `detections` table stays stuck on the old schema forever until you run
-- this manually.

ALTER TABLE detections
    ADD COLUMN IF NOT EXISTS detection_set VARCHAR(20) NOT NULL DEFAULT 'fused';

-- Backfill any rows inserted before this migration. Everything already in
-- the table was written by the old code (which had no detection_set
-- concept), so treat it all as "fused" - it's the safest default and
-- matches what was actually being shown on screen before.
UPDATE detections SET detection_set = 'fused' WHERE detection_set IS NULL;
