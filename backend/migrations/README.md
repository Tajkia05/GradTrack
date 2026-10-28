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
