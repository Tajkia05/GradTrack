-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Additive and repeatable: it allows a third way of presenting and adds two empty columns. No existing data changes.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- Allow "hybrid": in a room, with a Zoom link for those joining online. Dropping first keeps this repeatable.
ALTER TABLE presentations DROP CONSTRAINT IF EXISTS presentations_mode_check;
-- Add the rule back with the new value.
ALTER TABLE presentations ADD CONSTRAINT presentations_mode_check CHECK (mode IN ('in_person', 'online', 'hybrid'));

-- The Zoom link for a hybrid presentation. An online presentation keeps its link in location. Empty otherwise.
ALTER TABLE presentations ADD COLUMN IF NOT EXISTS meeting_link VARCHAR(255);

-- How a committee member will join on that date: 'in_person' or 'online'. Empty when they can't attend.
ALTER TABLE presentation_availability ADD COLUMN IF NOT EXISTS attend_mode VARCHAR(10);
-- Only those two values are allowed. Dropping first keeps this repeatable.
ALTER TABLE presentation_availability DROP CONSTRAINT IF EXISTS presentation_availability_attend_mode_check;
-- Add the rule.
ALTER TABLE presentation_availability ADD CONSTRAINT presentation_availability_attend_mode_check CHECK (attend_mode IN ('in_person', 'online'));

-- Save everything above.
COMMIT;
