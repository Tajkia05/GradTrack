-- Run in the Neon SQL editor, on the same database used by backend/.env, after 007_create_student_profiles.sql.
-- Additive and repeatable: it only adds two empty columns, and changes no existing data.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- The picture's type, image/png or image/jpeg. Empty = no picture.
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS picture_type VARCHAR(20);
-- The picture's contents.
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS picture BYTEA;

-- Save everything above.
COMMIT;
