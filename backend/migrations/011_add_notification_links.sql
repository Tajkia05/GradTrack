-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Repeatable: it only fills in links that are still empty, and doesn't change any message.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- The page a notification opens when clicked. Empty = it isn't clickable.
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS link VARCHAR(255);

-- A student's notification that names a milestone opens that milestone's card.
UPDATE notifications n SET link = '/student?milestone=' || m.id
-- Look at each milestone, and the user who received the notification.
FROM milestones m, users u
-- Match students' notifications that mention the milestone.
WHERE n.link IS NULL AND u.id = n.user_id AND u.role::text = 'STUDENT' AND n.message LIKE '%' || m.name || '%';

-- A student's notification about a committee member opens the Committee formation card.
UPDATE notifications n SET link = '/student?milestone=' || m.id
-- Look at Committee formation, and the user who received the notification.
FROM milestones m, users u
-- Match students' notifications that mention their committee.
WHERE n.link IS NULL AND m.name = 'Committee formation' AND u.id = n.user_id AND u.role::text = 'STUDENT' AND n.message LIKE '%dissertation committee%';

-- A submission on a faculty member's list opens that review.
UPDATE notifications n SET link = '/faculty?student=' || s.id || '&milestone=' || m.id
-- Look at each milestone and student, and the user who received the notification.
FROM milestones m, users s, users u
-- Match "<student> submitted <milestone> for your review."
WHERE n.link IS NULL AND u.id = n.user_id AND u.role::text = 'FACULTY' AND s.role::text = 'STUDENT' AND n.message = s.full_name || ' submitted ' || m.name || ' for your review.';

-- A committee invitation opens the faculty member's invitations.
UPDATE notifications n SET link = '/faculty?section=invitations'
-- Look at the user who received the notification.
FROM users u
-- Match faculty invitations.
WHERE n.link IS NULL AND u.id = n.user_id AND u.role::text = 'FACULTY' AND n.message LIKE '%invited you to join%';

-- A removal from a committee opens the committees they're on.
UPDATE notifications n SET link = '/faculty?section=memberships'
-- Look at the user who received the notification.
FROM users u
-- Match faculty removals.
WHERE n.link IS NULL AND u.id = n.user_id AND u.role::text = 'FACULTY' AND n.message LIKE '%removed you from%';

-- Anything else a faculty member received is about their students.
UPDATE notifications n SET link = '/faculty?section=students'
-- Look at the user who received the notification.
FROM users u
-- Match the rest of the faculty's notifications.
WHERE n.link IS NULL AND u.id = n.user_id AND u.role::text = 'FACULTY';

-- Save everything above.
COMMIT;
