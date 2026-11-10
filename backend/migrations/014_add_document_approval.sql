-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Additive and repeatable: it only adds one empty column, and changes no existing data.

-- When the advisor approved this submission's document, before the presentation. Empty = not approved yet.
ALTER TABLE milestone_submissions ADD COLUMN IF NOT EXISTS document_approved_at TIMESTAMPTZ;
