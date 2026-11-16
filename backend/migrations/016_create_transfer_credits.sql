-- Apply after 015. Additive and repeatable; preserves existing student data.
BEGIN;

CREATE TABLE IF NOT EXISTS transfer_credit_requests (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id),
    source_key VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'more_information_required')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    approved JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_transfer_student_source UNIQUE (student_id, source_key)
);
CREATE INDEX IF NOT EXISTS ix_transfer_student ON transfer_credit_requests(student_id);

CREATE TABLE IF NOT EXISTS transfer_credit_submissions (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES transfer_credit_requests(id),
    version INTEGER NOT NULL CHECK (version > 0),
    details JSON NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_transfer_submission_version UNIQUE (request_id, version)
);
CREATE INDEX IF NOT EXISTS ix_transfer_submission_request ON transfer_credit_submissions(request_id);

CREATE TABLE IF NOT EXISTS transfer_credit_documents (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES transfer_credit_submissions(id),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 10485760),
    data BYTEA NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_transfer_document_submission ON transfer_credit_documents(submission_id);

CREATE TABLE IF NOT EXISTS transfer_credit_history (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES transfer_credit_requests(id),
    submission_id INTEGER NOT NULL REFERENCES transfer_credit_submissions(id),
    status VARCHAR(32) NOT NULL,
    changed_by INTEGER NOT NULL REFERENCES users(id),
    comment TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_transfer_history_request ON transfer_credit_history(request_id);

ALTER TABLE student_courses ADD COLUMN IF NOT EXISTS transfer_request_id INTEGER
    REFERENCES transfer_credit_requests(id);
ALTER TABLE student_courses ADD COLUMN IF NOT EXISTS transfer_area VARCHAR(20);
CREATE UNIQUE INDEX IF NOT EXISTS uq_course_transfer_request ON student_courses(transfer_request_id);

COMMIT;
