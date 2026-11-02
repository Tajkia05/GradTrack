-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Repeatable: running it again changes nothing. It adds one rule, and changes no existing rows.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- The bulletin says a student advances to candidacy after successfully presenting their proposal,
-- so Candidacy now needs an approved Dissertation proposal.
INSERT INTO milestone_prerequisites (milestone_id, requires_id, min_gap_semesters)
-- Find the two milestones by name.
SELECT candidacy.id, proposal.id, 0
FROM milestones candidacy, milestones proposal
-- Match Candidacy and the Dissertation proposal.
WHERE candidacy.name = 'Candidacy' AND proposal.name = 'Dissertation proposal'
-- Skip it if the rule already exists.
ON CONFLICT (milestone_id, requires_id) DO NOTHING;

-- Save everything above.
COMMIT;
