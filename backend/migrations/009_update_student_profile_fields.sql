-- Run in the Neon SQL editor, on the same database used by backend/.env, after 008_add_student_profile_picture.sql.
-- Repeatable: running it again changes nothing. It removes the department column, since every student is in CS.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- What the student researches.
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS research_interests TEXT;
-- Their lab or research group.
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS lab_name VARCHAR(255);
-- A link to their GitHub profile.
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS github_url VARCHAR(500);
-- A link to their Google Scholar profile.
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS scholar_url VARCHAR(500);
-- A link to their LinkedIn profile.
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(500);
-- Remove the department, which is the same for every student.
ALTER TABLE student_profiles DROP COLUMN IF EXISTS department;

-- Save everything above.
COMMIT;
