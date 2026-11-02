-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Additive and repeatable: it only adds one new table, and changes no existing data.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- The extra information a student can edit about themselves. Their name stays in users.
CREATE TABLE IF NOT EXISTS student_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, -- The student this belongs to.
    department VARCHAR(255), -- Their department.
    education TEXT, -- Their education background.
    bio TEXT, -- A short biography.
    portfolio_url VARCHAR(500) -- A link to their portfolio.
); -- End of the student_profiles table.

-- Save everything above.
COMMIT;
