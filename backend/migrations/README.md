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
   is needed for the milestone, because Committee formation is worked out from these rows.
3. When they respond, notify the student by adding a `Notification` row with the
   student's id as `user_id`.

## Notification links

Apply `011_add_notification_links.sql` in the Neon SQL editor. It adds the `link` column
to `notifications`, and fills in links for the notifications that already exist. Clicking
a notification opens its `link`. New notifications get theirs from
`app/modules/notifications/links.py`, so any new notification should set one too.

## Notifications

| Event | Who is notified |
| --- | --- |
| Student declares an advisor | The advisor |
| Student invites or removes a faculty member | That faculty member |
| Student submits a milestone | The advisor |
| Advisor approves, requests a revision or rejects | The student |
| Coursework, Committee formation or Candidacy completes or reopens | The student and their advisor |

A manual database edit doesn't create a notification, except that a committee completed
this way is noticed the next time the student opens their dashboard.

# Candidacy

Apply `010_add_candidacy_proposal_rule.sql` in the Neon SQL editor. It adds the rule that
Candidacy needs an approved Dissertation proposal. Candidacy completes automatically when
Coursework is completed, the comprehensive exam and proposal are approved, and the GPA is
at least 3.0, the next time the student opens their dashboard. If a condition stops being
met, it goes back to In progress. Continuous registration isn't tracked.

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
so every teammate's backend can open them. After a rejection, the student gets one more
attempt, with a new upload and a new presentation. A second rejection is final. Presentation
dates are covered under Presentation scheduling below.

## Faculty side (still to build)

1. List a student's submissions and files with
   `GET /api/faculty/students/{student_id}/milestones/{milestone_id}/submissions`.
2. Download a file with `GET /api/milestone-documents/{id}`, sending the login token.
3. Add a comment box to the review. `review_student_milestone` already calls
   `record_status_change` from `app.modules.submissions.history`, which saves the history
   and notifies the student. Pass the reviewer's comment as its last argument. The review
   request needs an optional `comment` field for this.

## Completed or Approved

Students see "Completed" for milestones the app finishes by itself (Coursework, Advisor
declaration, Committee formation and Candidacy), and "Approved" when a person decides. In the
database, all of them still use the `approved` status. The list is `AUTOMATIC_MILESTONES`
in `app/modules/milestones/models.py`.

## Notifications

`record_status_change` saves each milestone status change with its exact time, and
notifies the student. The navbar's bell shows every user their notifications. Approvals
from before this feature, and advisor declarations, show only a date.

# Presentation scheduling

## Migration

Apply `013_create_presentations.sql` in the Neon SQL editor. It adds the `presentations`,
`presentation_options` and `presentation_availability` tables, without changing existing data.
Then apply `014_add_document_approval.sql`, which adds the empty `document_approved_at` column
to `milestone_submissions`. Then apply `015_add_hybrid_presentations.sql`, which allows
`hybrid` presentations and adds the empty `presentations.meeting_link` and
`presentation_availability.attend_mode` columns.

## How it works

The comprehensive exam, dissertation proposal and dissertation defense each need a
presentation, and their review has two steps:

1. The student uploads the document, and the milestone is `submitted`.
2. The advisor reviews the document with the usual buttons. **Approve** before the presentation
   only approves the document: it sets `document_approved_at` on the newest submission, moves the
   milestone to `under_review`, adds a `document_approved` history row, and tells the student. The
   milestone is not complete, so nothing it unlocks opens yet. Revision and Reject work as before.
3. The student proposes 1 to 3 dates, in person (a room), online (a Zoom link in `location`),
   or hybrid (a room in `location` and a Zoom link in `meeting_link`).
4. Every committee member, including the advisor, marks whether they can attend each date, and
   how they'll join (`attend_mode`: `in_person` or `online`). Joining by Zoom only counts when the
   presentation is online or hybrid, and joining in person only when it's in person or hybrid. The
   student enters the answers for external members. Dates that everyone can attend are
   highlighted, and the student chooses one of them, which notifies the advisor and the faculty
   on the committee.
5. After the chosen date has passed, **Approve** is the final decision and completes the
   milestone, as before. Approving earlier is refused with a message giving the date.

Approving the document before the presentation is the team's own step; the bulletin only says the
document goes to the committee before the presentation. The earliest allowed date is:

| Milestone | Earliest date (bulletin) |
| --- | --- |
| Comprehensive exam | Any future date |
| Dissertation proposal | 2 weeks after the upload, and 1 month after the comprehensive exam presentation |
| Dissertation defense | 1 month after the upload, and at least 1 week away, so it can be announced |

For students whose exam was approved before scheduling existed, the exam's approval day is
used instead of its presentation date. Proposing dates notifies the advisor and the faculty
on the committee. External members have no account, so the student ticks which dates they
can attend. The milestone stays `under_review` until the final decision, so it stays on the
advisor's review list. The student can cancel before the date and propose new ones. Once the chosen date
has passed, the presentation shows as held. After a revision request, the student uploads a
revised document without presenting again. After a rejection, the second attempt needs its
own presentation.

## Faculty steps by hand

Until the faculty side is built, do these steps in Neon, on test students only, because the
database is shared. Find the presentation and its dates:

```sql
SELECT p.id AS presentation, u.email AS student, m.name AS milestone, p.attempt, p.status,
       o.id AS option, o.starts_at
FROM presentations p
JOIN users u ON u.id = p.student_id
JOIN milestones m ON m.id = p.milestone_id
JOIN presentation_options o ON o.presentation_id = p.id
ORDER BY p.id DESC, o.starts_at;
```

A faculty member's answer for one date. Use the faculty member's user id, and how they'll join
(`'in_person'` or `'online'`, or `NULL` when they can't attend):

```sql
INSERT INTO presentation_availability (option_id, faculty_id, available, attend_mode)
VALUES (1, 2, true, 'online');
```

Once every member has answered yes for a date, the student chooses it on the site. If the
advisor says a presentation didn't take place, which asks the student for new dates:

```sql
UPDATE presentations SET status = 'needs_new_dates' WHERE id = 1;
```

To show a held presentation in a demo, move the chosen date into the past:

```sql
UPDATE presentation_options SET starts_at = now() - interval '1 day' WHERE id = 1;
```

A manual edit doesn't send a notification.

## Faculty side (still to build)

1. Show each committee faculty member, and the advisor, the dates their students proposed
   (`presentations` with status `awaiting_availability`), and let them add or change their
   own `presentation_availability` row for each date (`faculty_id` = their user id), with
   Can't attend / In person / Zoom. Only offer the ways the presentation allows: in person
   for `in_person`, Zoom for `online`, and both for `hybrid`.
2. When a member answers, notify the student with a `Notification` that links to
   `links.student_milestone(milestone_id)`. The student's page already highlights dates
   everyone can attend and lets the student choose one.
3. Add a "Didn't take place" button for the advisor after the date, which sets the
   presentation's `status` to `needs_new_dates`.
4. Already done in the backend: the review list leaves out a milestone whose document is
   approved until its presentation date has passed (`waiting_for_presentation`), and an early
   Approve is refused (`approve_document_if_needed`). Both are in
   `app/modules/presentations/service.py`. Optionally, show these students' upcoming
   presentation dates somewhere on the faculty dashboard.

## Notifications

| Event | Who is notified |
| --- | --- |
| Student proposes presentation dates | The advisor and the faculty on the committee |
| Student chooses the presentation date | The advisor and the faculty on the committee |
| Student cancels a presentation | The advisor and the faculty on the committee |
| Advisor approves the document before the presentation | The student |
