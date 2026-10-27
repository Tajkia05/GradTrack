-- OPTIONAL DEMO DATA, not a schema migration. Apply after migration 001.
-- All academic information below is fictional. example.org links are placeholders.
-- Only the three known test accounts are targeted; existing non-NULL fields survive.
BEGIN;

INSERT INTO faculty_profiles (
    user_id, department, affiliation, research_interests, lab_name,
    accepting_students, academic_url, bio
)
SELECT u.id, d.department, d.affiliation, d.research_interests, d.lab_name,
       d.accepting_students, d.academic_url, d.bio
FROM (VALUES
    ('faculty@gradtrack.edu', 'Computer Science', 'GradTrack Demo University',
     'Machine learning, natural language processing, and responsible AI',
     'Human-Centered AI Lab', TRUE, 'https://example.org/#fiona-faculty',
     'Fictional demo profile. Fiona mentors students exploring practical machine learning and language technologies, with an emphasis on transparent and responsible AI systems.'),
    ('omar@gradtrack.edu', 'Computer Science', 'GradTrack Demo University',
     'Distributed systems, cloud computing, and database performance',
     'Scalable Systems Lab', TRUE, 'https://example.org/#omar-haddad',
     'Fictional demo profile. Omar mentors students working on reliable distributed services, efficient data platforms, and experimental systems research.'),
    ('grace@gradtrack.edu', 'Computer Science', 'GradTrack Demo University',
     'Cybersecurity, privacy engineering, and network security',
     'Secure Computing Lab', FALSE, 'https://example.org/#grace-kim',
     'Fictional demo profile. Grace studies secure software and privacy-preserving systems. This demo profile is currently marked as not accepting new students.')
) AS d(email, department, affiliation, research_interests, lab_name,
       accepting_students, academic_url, bio)
JOIN users u ON u.email = d.email AND u.role::text = 'FACULTY'
ON CONFLICT (user_id) DO UPDATE SET
    department = COALESCE(faculty_profiles.department, EXCLUDED.department),
    affiliation = COALESCE(faculty_profiles.affiliation, EXCLUDED.affiliation),
    research_interests = COALESCE(faculty_profiles.research_interests, EXCLUDED.research_interests),
    lab_name = COALESCE(faculty_profiles.lab_name, EXCLUDED.lab_name),
    accepting_students = COALESCE(faculty_profiles.accepting_students, EXCLUDED.accepting_students),
    academic_url = COALESCE(faculty_profiles.academic_url, EXCLUDED.academic_url),
    bio = COALESCE(faculty_profiles.bio, EXCLUDED.bio);

COMMIT;
