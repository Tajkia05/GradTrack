# Faculty profiles

## Optional demo profiles

`demo_faculty_profiles.sql` fills missing fields for the Fiona, Omar and Grace
test accounts with explicitly fictional academic profiles. Existing non-NULL
fields are preserved. Fiona and Omar accept students; Grace does not. The
example.org academic URLs are placeholders, not real faculty websites. This
script is separate from the schema migration and should only be used for demos.
Academic information appears directly on each advisor card without expanding it.

## Migration and manual maintenance

Apply `001_create_faculty_profiles.sql` in the Neon SQL editor against the database
configured in `backend/.env`, before deploying the updated backend. The script is
transactional and repeatable. It creates the table and blank profiles for existing
faculty, without overwriting any profile or changing users or milestone progress.
Do not run `seed.py --reset`.

Initial maintenance is manual, by the project team. No profile-edit endpoint or
faculty editor is provided in this sprint. To populate a verified faculty profile,
use this template in Neon. Replace the email and NULLs with actual confirmed data;
leave unknown fields as NULL. SQL string literals use single quotes; escape an
apostrophe by doubling it. Academic links should be full https:// or http:// URLs.

```sql
INSERT INTO faculty_profiles (
    user_id, department, affiliation, research_interests, lab_name,
    accepting_students, academic_url, bio
)
SELECT id,
    NULL, -- department
    NULL, -- affiliation / institution
    NULL, -- research interests (plain text)
    NULL, -- laboratory or group
    NULL, -- TRUE = accepting, FALSE = not accepting, NULL = unknown
    NULL, -- academic URL
    NULL  -- short biography
FROM users
WHERE email = 'REPLACE_WITH_FACULTY_EMAIL' AND role::text = 'FACULTY'
ON CONFLICT (user_id) DO UPDATE SET
    department = EXCLUDED.department,
    affiliation = EXCLUDED.affiliation,
    research_interests = EXCLUDED.research_interests,
    lab_name = EXCLUDED.lab_name,
    accepting_students = EXCLUDED.accepting_students,
    academic_url = EXCLUDED.academic_url,
    bio = EXCLUDED.bio;
```

This template replaces the whole profile, including NULL values. For changing only
one field, use a targeted UPDATE instead. Confirm affected rows before committing.
Do not invent faculty credentials or research interests for the shared database.

The advisor API uses a LEFT JOIN so faculty with no profile remain visible. Student
counts still come from `users.advisor_id`; no student identities are exposed here.
A faculty member marked FALSE cannot receive a new declaration. Unknown availability
remains selectable and is explicitly labeled in the modal. Existing assignments and
retries of the same declaration are preserved when availability changes.

# Coursework

## Migration

Apply `002_create_coursework.sql` in the Neon SQL editor against the database
configured in `backend/.env`, before running the backend with the coursework
endpoints. The script is transactional and repeatable. It creates the `courses` and
`student_courses` tables and adds the course list, without changing existing data.

Then apply `003_add_manual_courses.sql` the same way. It lets students enter UAlbany
courses that aren't on the course list, and it keeps all existing rows.

Then apply `004_remove_research_methods_milestone.sql`. It permanently deletes the
"Research methods course" milestone, its candidacy rule and its progress rows. CSI 790
remains a core course in Coursework, so candidacy still requires it through the
Coursework milestone, and its deadline is shown in the Coursework popup. If `seed.py`
from an older branch adds the milestone back, run this script again.

## Manually entered courses

Students can enter a UAlbany course that isn't on the list, with its code, name,
department (CS or non-CS) and whether it's independent study or research. These courses
count toward electives once they have a qualifying grade. The bulletin requires
approval for non-CS courses, but GradTrack doesn't record that approval. Courses from
other universities aren't entered here, because they need the transfer credit review.

## Optional sample courses

After the migration, run `python seed.py` from the `backend` folder to add sample
courses for the Sam, Lisa and Raj test accounts. Rows that already exist are skipped.
Do not run `seed.py --reset`, because it deletes all data in the shared database.

## Course list

The course list comes from the Graduate Bulletin's Computer Science Courses page, and
the core and breadth areas come from the CS PhD and MS pages. Load-only courses that
earn no credit are not included. To change the list, edit the rows in Neon.

# Committee formation

## Migration

Apply `005_create_committee_and_notifications.sql` in the Neon SQL editor. It adds the
`committee_members` and `notifications` tables, without changing existing data.

## How it works

A student's declared advisor is automatically the approved committee chair, and has no
row in `committee_members`. The student invites faculty members, who each get a row with
`status` set to `pending`. External members have no account, so they're `approved` as
soon as the student adds them. The student can remove anyone except the chair, and a
removed faculty member gets a notification. Committee formation becomes Approved once at
least 4 members have approved, with at least 3 from the CS department.
A member counts as CS when `faculty_profiles.department` is Computer Science. External
members and blank departments don't count as CS.

The milestone updates the next time the student opens their dashboard or committee
popup. If removing someone leaves the committee below the requirement, Committee
formation goes back to In progress straight away, and milestones that need it are
blocked again. Milestones that were already approved stay approved.

## Approving by hand

Until the faculty side is built, faculty approvals can be set in the database, on test
students only because the database is shared. Find the row, then update it:

```sql
SELECT c.id, u.email AS student, c.faculty_id, c.external_name, c.status
FROM committee_members c JOIN users u ON u.id = c.student_id
ORDER BY c.id;

UPDATE committee_members SET status = 'approved' WHERE id = 1;
```

Valid values are `pending`, `approved` and `declined`.

## Faculty side (still to build)

1. Show each faculty member their pending invitations: rows in `committee_members` where
   `faculty_id` is their user id and `status` is `pending`.
2. Let them approve or decline, by setting that row's `status` to `approved` or
   `declined`. Only the invited faculty member may change their own row. Nothing else
   is needed, because Committee formation is worked out from these rows.
3. Show their notifications from `GET /api/notifications/me`. Marking one as read isn't
   built yet.

# Student profile

Apply `007_create_student_profiles.sql` in the Neon SQL editor. It adds the
`student_profiles` table, without changing existing data. A student clicks their name in
the navbar and chooses Profile to view it at `/student/profile`, then clicks Edit profile to change
their name, research interests, lab, education, bio, or their website, GitHub, Google
Scholar and LinkedIn links. The name is saved in `users`, and the rest in
`student_profiles`. Their advisor, start term, enrollment and advanced standing are shown
from their record, and can't be edited there. Only the student can see or change their
own profile for now.

Then apply `008_add_student_profile_picture.sql`. It adds the columns for a profile
picture, a PNG or JPG of up to 2 MB, which shows beside the student's name in the navbar
and on their profile page. Students without a picture show their initials.

Then apply `009_update_student_profile_fields.sql`. It adds the research and link columns,
and removes the department column, because every student is in Computer Science.

# Milestone submission

## Migration

Apply `006_create_milestone_submissions.sql` in the Neon SQL editor. It adds the
`milestone_submissions`, `submission_documents` and `milestone_status_history` tables,
without changing existing data.

## How it works

The comprehensive exam, dissertation proposal and dissertation defense use this flow.
Their prerequisites come from the dashboard's rules. A student uploads up to 5 PDF, DOCX,
PPTX or PNG files of up to 10 MB each, and the status becomes `submitted`, which puts the
milestone on the advisor's review list. After a revision request, the student can submit
again as a new attempt, and earlier attempts are kept. Files are stored in the database,
so every teammate's backend can open them. Presentation dates aren't checked yet, so an
advisor can record a decision before the presentation until scheduling is built.

## Faculty side (still to build)

1. List a student's submissions and files with
   `GET /api/faculty/students/{student_id}/milestones/{milestone_id}/submissions`.
2. Download a file with `GET /api/milestone-documents/{id}`, sending the login token.
3. Add a comment box to the review. `review_student_milestone` already calls
   `record_status_change` from `app.modules.submissions.history`, which saves the history
   and notifies the student. Pass the reviewer's comment as its last argument. The review
   request needs an optional `comment` field for this.
4. When a faculty member approves or declines a committee invitation, notify the student
   by adding a `Notification` row for them.

## Completed or Approved

Students see "Completed" for milestones the app finishes by itself (Coursework, Advisor
declaration and Committee formation), and "Approved" when a person decides. In the
database, all of them still use the `approved` status. The list is `AUTOMATIC_MILESTONES`
in `app/modules/milestones/models.py`.

## Notifications

`record_status_change` saves each milestone status change with its exact time, and
notifies the student. The navbar's bell shows every user their notifications. Approvals
from before this feature, and advisor declarations, show only a date.
