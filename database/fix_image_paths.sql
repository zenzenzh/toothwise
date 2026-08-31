-- One-time fix: strips the leading "uploads/" from any image_path values
-- that were saved before app/utils/image_utils.py was corrected. Those
-- rows store "uploads/screenings/xxx.webp" instead of the correct
-- "screenings/xxx.webp", which doubles up into a broken
-- /api/uploads/uploads/... URL on the frontend.
--
-- Safe to re-run: only touches rows that still have the bad prefix.

UPDATE screenings
SET image_path = substring(image_path FROM 9)  -- strip 'uploads/' (8 chars + 1)
WHERE image_path LIKE 'uploads/%';

-- Sanity check afterwards - should return 0 rows:
-- SELECT id, image_path FROM screenings WHERE image_path LIKE 'uploads/%';
