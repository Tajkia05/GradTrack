-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Additive and repeatable: it only adds three new tables, and changes no existing data.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- One row each time a student proposes presentation dates for a milestone.
CREATE TABLE IF NOT EXISTS presentations (
    id SERIAL PRIMARY KEY, -- A unique number for each presentation.
    student_id INTEGER NOT NULL REFERENCES users(id), -- The student presenting.
    milestone_id INTEGER NOT NULL REFERENCES milestones(id), -- The comprehensive exam, proposal or defense.
    attempt INTEGER NOT NULL, -- 1 for the first attempt, 2 for the second attempt after a rejection.
    status VARCHAR(25) NOT NULL DEFAULT 'awaiting_availability' -- Where the scheduling is.
        CHECK (status IN ('awaiting_availability', 'needs_new_dates', 'scheduled', 'cancelled')), -- The allowed values.
    mode VARCHAR(10) NOT NULL CHECK (mode IN ('in_person', 'online')), -- In person or online.
    location VARCHAR(255) NOT NULL, -- A room for in person, or a meeting link for online.
    chosen_option_id INTEGER, -- The date the advisor confirmed. Empty until then.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now() -- When the dates were proposed.
); -- End of the presentations table.

-- One row per date the student proposes, 1 to 3 per presentation.
CREATE TABLE IF NOT EXISTS presentation_options (
    id SERIAL PRIMARY KEY, -- A unique number for each proposed date.
    presentation_id INTEGER NOT NULL REFERENCES presentations(id), -- The presentation it belongs to.
    starts_at TIMESTAMPTZ NOT NULL -- The proposed date and time.
); -- End of the presentation_options table.

-- Link the confirmed date to its row, now that the options table exists. Dropping first keeps this repeatable.
ALTER TABLE presentations DROP CONSTRAINT IF EXISTS presentations_chosen_option_id_fkey;
-- Add the link.
ALTER TABLE presentations ADD CONSTRAINT presentations_chosen_option_id_fkey FOREIGN KEY (chosen_option_id) REFERENCES presentation_options(id);

-- A student can have only one presentation waiting or scheduled per milestone and attempt, which blocks double clicks.
CREATE UNIQUE INDEX IF NOT EXISTS presentations_one_active
    ON presentations (student_id, milestone_id, attempt) WHERE status IN ('awaiting_availability', 'scheduled');

-- One row per committee member's answer for one proposed date.
CREATE TABLE IF NOT EXISTS presentation_availability (
    id SERIAL PRIMARY KEY, -- A unique number for each answer.
    option_id INTEGER NOT NULL REFERENCES presentation_options(id), -- The proposed date.
    faculty_id INTEGER REFERENCES users(id), -- The advisor or a faculty member. Empty for an external member.
    external_member_id INTEGER REFERENCES committee_members(id) ON DELETE CASCADE, -- An external member, entered by the student.
    available BOOLEAN NOT NULL, -- True if they can attend.
    CHECK ((faculty_id IS NULL) <> (external_member_id IS NULL)), -- Exactly one of the two people columns is filled.
    UNIQUE (option_id, faculty_id), -- One answer per faculty member per date.
    UNIQUE (option_id, external_member_id) -- One answer per external member per date.
); -- End of the presentation_availability table.

-- Save everything above.
COMMIT;
