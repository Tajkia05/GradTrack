-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- This DELETES the "Research methods course" milestone, and its rows can't be restored afterward.
-- CSI 790 stays a core course in Coursework, and its deadline is shown there.
-- Repeatable: running it again changes nothing. Students' CSI 790 course rows aren't touched.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- Delete the candidacy rule that needs this milestone, and any rule this milestone has.
DELETE FROM milestone_prerequisites
-- Match rows that point to the milestone from either side.
WHERE milestone_id IN (SELECT id FROM milestones WHERE name = 'Research methods course')
   -- The other side of the same rule.
   OR requires_id IN (SELECT id FROM milestones WHERE name = 'Research methods course');

-- Delete every student's progress on this milestone.
DELETE FROM student_milestones
-- Match only this milestone's rows.
WHERE milestone_id IN (SELECT id FROM milestones WHERE name = 'Research methods course');

-- Delete the milestone itself.
DELETE FROM milestones
-- Match only this milestone.
WHERE name = 'Research methods course';

-- Save everything above.
COMMIT;
