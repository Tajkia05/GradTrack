-- Run in the Neon SQL editor, on the same database used by backend/.env, after 002_create_coursework.sql.
-- Additive and repeatable: existing rows keep their values, and nothing is deleted.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- Allow an empty course_id, because a manually entered course isn't on the course list.
ALTER TABLE student_courses ALTER COLUMN course_id DROP NOT NULL;
-- The code of a manually entered course, e.g. MAT 520.
ALTER TABLE student_courses ADD COLUMN IF NOT EXISTS manual_code VARCHAR(20);
-- The name of a manually entered course.
ALTER TABLE student_courses ADD COLUMN IF NOT EXISTS manual_title VARCHAR(255);
-- The department of a manually entered course: cs or non_cs.
ALTER TABLE student_courses ADD COLUMN IF NOT EXISTS manual_department VARCHAR(10);
-- TRUE if a manually entered course counts toward the 15-credit independent study or research limit.
ALTER TABLE student_courses ADD COLUMN IF NOT EXISTS manual_is_research BOOLEAN NOT NULL DEFAULT FALSE;
-- Block adding the same manually entered course twice in one term. Rows with no manual_code aren't affected.
CREATE UNIQUE INDEX IF NOT EXISTS student_courses_manual_unique ON student_courses (student_id, manual_code, term, year);

-- Save everything above.
COMMIT;
