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
