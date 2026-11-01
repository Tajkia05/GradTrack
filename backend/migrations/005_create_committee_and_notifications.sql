-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Additive and repeatable: it only adds two new tables, and changes no existing data.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- The people each student invited to their dissertation committee. The advisor isn't stored here.
CREATE TABLE IF NOT EXISTS committee_members (
    id SERIAL PRIMARY KEY, -- A unique number for each row.
    student_id INTEGER NOT NULL REFERENCES users(id), -- The student whose committee this is.
    faculty_id INTEGER REFERENCES users(id), -- The invited faculty member. Empty = an external member.
    external_name VARCHAR(255), -- An external member's name. Empty for faculty.
    external_affiliation VARCHAR(255), -- An external member's university or company. Empty for faculty.
    status VARCHAR(10) NOT NULL DEFAULT 'pending', -- pending, approved or declined.
    invited_on DATE NOT NULL, -- The day the student added this person.
    UNIQUE (student_id, faculty_id) -- Blocks inviting the same faculty member twice.
); -- End of the committee_members table.

-- Messages shown to a user inside the app.
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY, -- A unique number for each notification.
    user_id INTEGER NOT NULL REFERENCES users(id), -- The user who should see it.
    message TEXT NOT NULL, -- The message to show.
    is_read BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE once the user has read it.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now() -- When it was created.
); -- End of the notifications table.

-- Save everything above.
COMMIT;
