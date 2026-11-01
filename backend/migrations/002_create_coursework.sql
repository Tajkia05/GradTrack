-- Run in the Neon SQL editor, on the same database used by backend/.env.
-- Additive and repeatable: it only adds new tables and courses, and changes no existing data.
-- Course list: https://www.albany.edu/graduate-bulletin/computer-science-courses.php
-- Requirement areas: the CS PhD and MS pages of the UAlbany Graduate Bulletin.

-- Run everything below as one unit: all of it is saved, or none of it is.
BEGIN;

-- The course list that students select from.
CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY, -- A unique number for each course.
    code VARCHAR(20) NOT NULL UNIQUE, -- The course code, e.g. CSI 503.
    title VARCHAR(255) NOT NULL, -- The course name.
    min_credits INTEGER NOT NULL, -- The fewest credits it can be taken for.
    max_credits INTEGER NOT NULL, -- The most credits it can be taken for.
    area VARCHAR(20), -- core, theory, ai_ml, systems or dissertation. Empty = elective only.
    is_research BOOLEAN NOT NULL DEFAULT FALSE -- TRUE counts toward the 15-credit elective limit.
); -- End of the courses table.

-- The courses each student selected.
CREATE TABLE IF NOT EXISTS student_courses (
    id SERIAL PRIMARY KEY, -- A unique number for each row.
    student_id INTEGER NOT NULL REFERENCES users(id), -- The student who took the course.
    course_id INTEGER NOT NULL REFERENCES courses(id), -- The course they selected.
    credits INTEGER NOT NULL, -- The credits taken.
    term term NOT NULL, -- SPRING or FALL, using the database's existing term type.
    year INTEGER NOT NULL, -- The year it was taken.
    grade VARCHAR(2), -- The grade. Empty = still in progress.
    UNIQUE (student_id, course_id, term, year) -- Blocks adding a course twice in one term.
); -- End of the student_courses table.

-- Add every course that earns credit. Load-only courses (CSI 680C, 697C, 698C, 699C, 899) earn none.
INSERT INTO courses (code, title, min_credits, max_credits, area, is_research) VALUES -- Columns, in order.
    ('CSI 503', 'Algorithms and Data Structures', 3, 3, 'core', FALSE), -- Core.
    ('CSI 790', 'Research Methods in Computing', 3, 3, 'core', FALSE), -- Core.
    ('CSI 501', 'Computational Linear Algebra, Nonlinear Algebra, and Optimization', 3, 3, 'theory', FALSE), -- Breadth: Theoretical CS.
    ('CSI 509', 'Automata and Theory of Computation', 3, 3, 'theory', FALSE), -- Breadth: Theoretical CS.
    ('CSI 519', 'Advanced Programming Concepts', 3, 3, 'theory', FALSE), -- Breadth: Theoretical CS.
    ('CSI 521', 'Discrete Mathematics with Applications', 3, 3, 'theory', FALSE), -- Breadth: Theoretical CS.
    ('CSI 526', 'Cryptography', 3, 3, 'theory', FALSE), -- Breadth: Theoretical CS.
    ('CSI 529', 'Probability and Computing', 3, 3, 'theory', FALSE), -- Breadth: Theoretical CS.
    ('CSI 538', 'Computational Logic', 3, 3, 'theory', FALSE), -- Breadth: Theoretical CS.
    ('CSI 609', 'Formal Languages and Theory of Computation', 3, 3, 'theory', FALSE), -- Breadth: Theoretical CS.
    ('CSI 663', 'Topics in Theoretical Computer Science', 3, 3, 'theory', FALSE), -- Breadth: Theoretical CS.
    ('CSI 531', 'Data Mining', 3, 3, 'ai_ml', FALSE), -- Breadth: AI & ML.
    ('CSI 533', 'Theory and Practice of Multimedia Computing', 3, 3, 'ai_ml', FALSE), -- Breadth: AI & ML.
    ('CSI 535', 'Artificial Intelligence I', 3, 3, 'ai_ml', FALSE), -- Breadth: AI & ML.
    ('CSI 536', 'Machine Learning', 3, 3, 'ai_ml', FALSE), -- Breadth: AI & ML.
    ('CSI 552', 'Robotics', 3, 3, 'ai_ml', FALSE), -- Breadth: AI & ML.
    ('CSI 571', 'Introduction to Computer Vision', 3, 3, 'ai_ml', FALSE), -- Breadth: AI & ML.
    ('CSI 636', 'Natural Language Processing', 3, 3, 'ai_ml', FALSE), -- Breadth: AI & ML.
    ('CSI 661', 'Topics in Artificial Intelligence', 3, 3, 'ai_ml', FALSE), -- Breadth: AI & ML.
    ('CSI 671', 'Computer Vision', 3, 3, 'ai_ml', FALSE), -- Breadth: AI & ML.
    ('CSI 500', 'Operating Systems', 3, 3, 'systems', FALSE), -- Breadth: Systems or CSI 518.
    ('CSI 504', 'Advanced Computer Architecture', 3, 3, 'systems', FALSE), -- Breadth: Systems or CSI 518.
    ('CSI 508', 'Database Systems I', 3, 3, 'systems', FALSE), -- Breadth: Systems or CSI 518.
    ('CSI 516', 'Computer Communications Networks', 3, 3, 'systems', FALSE), -- Breadth: Systems or CSI 518.
    ('CSI 518', 'Software Engineering', 4, 4, 'systems', FALSE), -- Breadth: Systems or CSI 518.
    ('CSI 524', 'Computer Security', 3, 3, 'systems', FALSE), -- Breadth: Systems or CSI 518.
    ('CSI 525', 'Mobile Wireless Networks', 3, 3, 'systems', FALSE), -- Breadth: Systems or CSI 518.
    ('CSI 561', 'Software Testing', 3, 3, 'systems', FALSE), -- Breadth: Systems or CSI 518.
    ('CSI 662', 'Topics in Systems', 3, 3, 'systems', FALSE), -- Breadth: Systems or CSI 518.
    ('CSI 898', 'Doctoral Dissertation Research', 1, 12, 'dissertation', TRUE), -- Dissertation research.
    ('CSI 502', 'Computer Graphics', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 511', 'Programming Languages and Systems Concepts', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 517', 'Compiler Design I', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 520', 'Topics in Distributed and Parallel Computing', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 522', 'Intro to VLSI', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 523', 'Computational Geometry', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 532', 'Network Science', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 534', 'Reconfigurable Computing', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 542', 'An Introduction to Quantum Computation, Information, and Simulation', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 551', 'Bayesian Data Analysis and Signal Processing', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 553', 'Cyber-Physical Systems', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 600', 'Distributed Systems', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 601', 'Computability and Undecidability', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 604', 'Computers and Computational Intractability', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 608', 'Database II', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 616', 'Computer Communication Networks II', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 628', 'Cryptographic Protocols', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 635', 'Artificial Intelligence II', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 660', 'Topics in Computer Science', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 665', 'Topics in Computer Graphics', 1, 3, NULL, FALSE), -- Elective, variable credits.
    ('CSI 666', 'Topics in Theory of Computation', 1, 3, NULL, FALSE), -- Elective, variable credits.
    ('CSI 667', 'Topics in Algorithms', 1, 3, NULL, FALSE), -- Elective, variable credits.
    ('CSI 668', 'Topics in Systems Architecture', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 680', 'Master''s Project', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 681', 'Compiler Project', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 682', 'Database Project', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 683', 'Systems Programming Project', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 684', 'Computational Science Project', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 694', 'Directed Readings in Computer Science', 1, 3, NULL, TRUE), -- Elective, independent study.
    ('CSI 696', 'Independent Teaching and Learning', 1, 3, NULL, FALSE), -- Elective, variable credits.
    ('CSI 697', 'Independent Study and Research', 1, 3, NULL, TRUE), -- Elective, independent study.
    ('CSI 698', 'Internship', 3, 3, NULL, FALSE), -- Elective.
    ('CSI 699', 'Master''s Thesis', 3, 6, NULL, TRUE), -- Elective, research.
    ('CSI 890', 'Independent Study and Research', 3, 19, NULL, TRUE) -- Elective, independent study.
ON CONFLICT (code) DO NOTHING; -- Skip courses that already exist, so this file can be run again.

-- Save everything above.
COMMIT;
