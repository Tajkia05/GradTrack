-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Additive and repeatable: existing users, progress and profile values are preserved.
BEGIN;

CREATE TABLE IF NOT EXISTS faculty_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    department VARCHAR(255),
    affiliation VARCHAR(255),
    research_interests TEXT,
    lab_name VARCHAR(255),
    accepting_students BOOLEAN,
    academic_url TEXT,
    bio TEXT
);

-- Create blank profiles for the existing faculty roster, without inventing data.
-- New faculty can have no profile yet; the API treats that as unknown information.
INSERT INTO faculty_profiles (user_id)
SELECT id FROM users WHERE role::text = 'FACULTY'
ON CONFLICT (user_id) DO NOTHING;

COMMIT;
