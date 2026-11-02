-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Additive and repeatable: it only adds three new tables, and changes no existing data.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- One row each time a student submits a milestone.
CREATE TABLE IF NOT EXISTS milestone_submissions (
    id SERIAL PRIMARY KEY, -- A unique number for each submission.
    student_id INTEGER NOT NULL REFERENCES users(id), -- The student who submitted.
    milestone_id INTEGER NOT NULL REFERENCES milestones(id), -- The milestone being submitted.
    attempt INTEGER NOT NULL, -- 1 for the first submission, 2 for the first resubmission, and so on.
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(), -- When it was submitted.
    UNIQUE (student_id, milestone_id, attempt) -- Blocks two submissions with the same attempt number.
); -- End of the milestone_submissions table.

-- One row per uploaded file, with the file stored in the database.
CREATE TABLE IF NOT EXISTS submission_documents (
    id SERIAL PRIMARY KEY, -- A unique number for each document.
    submission_id INTEGER NOT NULL REFERENCES milestone_submissions(id), -- The submission it belongs to.
    filename VARCHAR(255) NOT NULL, -- The file's name.
    content_type VARCHAR(100) NOT NULL, -- The file's type.
    size_bytes INTEGER NOT NULL, -- The file's size in bytes.
    data BYTEA NOT NULL -- The file's contents.
); -- End of the submission_documents table.

-- One row each time a milestone's status changes.
CREATE TABLE IF NOT EXISTS milestone_status_history (
    id SERIAL PRIMARY KEY, -- A unique number for each change.
    student_id INTEGER NOT NULL REFERENCES users(id), -- The student whose milestone changed.
    milestone_id INTEGER NOT NULL REFERENCES milestones(id), -- The milestone that changed.
    status VARCHAR(20) NOT NULL, -- The new status.
    changed_by INTEGER NOT NULL REFERENCES users(id), -- The user who made the change.
    comment TEXT, -- A reviewer's comment for the student. Empty when there isn't one.
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now() -- When it changed.
); -- End of the milestone_status_history table.

-- Save everything above.
COMMIT;
