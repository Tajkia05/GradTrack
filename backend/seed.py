# seed.py — CREATES THE DATABASE TABLES AND FILLS THEM WITH DUMMY DATA FOR SPRINT 1.
# For generating dummy data. FOR DEVELOPMENT ONLY.
#
# Run it from the backend folder:
#   python seed.py           → creates missing tables, adds any dummy rows that are missing
#   python seed.py --reset   → DELETES ALL TABLES AND DATA, then creates everything fresh
#
# Safe to run more than once: rows that already exist are skipped.
#
# Why --reset exists: create_all() can create NEW tables, but it cannot add new
# columns to a table that already exists. If the users table was created before
# the student fields were added, you need --reset once (this deletes all users,
# including anyone who registered — fine while we only have test data).

import sys
from datetime import date
from decimal import Decimal

from sqlalchemy import inspect, select

from app.core.database import Base, SessionLocal, engine
from app.modules.faculty.models import FacultyProfile  # Register table for fresh development databases.
from app.modules.milestones.models import (
    Milestone,
    MilestonePrerequisite,
    MilestoneStatus,
    StudentMilestone,
)
# (MilestoneStatus.NOT_STARTED is never seeded: no row = not started.)
from app.modules.users import service
from app.modules.users.models import EnrollmentStatus, Role, Term

TEST_PASSWORD = "password123"

# ---------------------------------------------------------------------------
# 1. USERS
# (email, full name, role, student fields or None)
# Student fields: advanced_standing, enrollment_status, start_term, start_year, gpa, advisor's email
# ---------------------------------------------------------------------------
FACULTY_AND_STAFF = [
    ("faculty@gradtrack.edu", "Fiona Faculty", Role.FACULTY),
    ("omar@gradtrack.edu", "Omar Haddad", Role.FACULTY),
    ("grace@gradtrack.edu", "Grace Kim", Role.FACULTY),
    ("director@gradtrack.edu", "Dana Director", Role.DIRECTOR),
]

STUDENTS = [
    # Sam: year 3, on track
    ("student@gradtrack.edu", "Sam Student",
     dict(advanced_standing=False, enrollment_status=EnrollmentStatus.FULL_TIME,
          start_term=Term.FALL, start_year=2023, gpa=Decimal("3.60")),
     "faculty@gradtrack.edu"),
    # Lisa: just started, part-time, no advisor yet
    ("lisa@gradtrack.edu", "Lisa Lee",
     dict(advanced_standing=True, enrollment_status=EnrollmentStatus.PART_TIME,
          start_term=Term.SPRING, start_year=2026, gpa=Decimal("3.20")),
     None),
    # Raj: almost done, but GPA too low for candidacy
    ("raj@gradtrack.edu", "Raj Patel",
     dict(advanced_standing=True, enrollment_status=EnrollmentStatus.FULL_TIME,
          start_term=Term.FALL, start_year=2022, gpa=Decimal("2.90")),
     "omar@gradtrack.edu"),
]

# ---------------------------------------------------------------------------
# 2. MILESTONES
# (name, position, deadline semester WITH advanced standing, WITHOUT advanced standing)
# None = no deadline. Part-time doubling (and the 8-year cap on the defense) is done in code.
# ---------------------------------------------------------------------------
MILESTONES = [
    ("Coursework", 1, None, None),
    ("Advisor declaration", 2, 2, 6),
    ("Research methods course", 3, 2, 6),
    ("Comprehensive exam", 4, 4, 8),
    ("Committee formation", 5, None, None),
    ("Dissertation proposal", 6, None, None),
    ("Candidacy", 7, None, None),
    ("Dissertation defense", 8, 12, 16),
]

# ---------------------------------------------------------------------------
# 3. PREREQUISITES — "milestone needs requires first" (+ minimum semesters in between)
# Candidacy also needs GPA >= 3.0: that is checked in code, not stored here.
# ---------------------------------------------------------------------------
PREREQUISITES = [
    ("Comprehensive exam", "Committee formation", 0),
    ("Comprehensive exam", "Advisor declaration", 0),
    ("Dissertation proposal", "Committee formation", 0),
    ("Dissertation proposal", "Comprehensive exam", 0),
    ("Candidacy", "Coursework", 0),
    ("Candidacy", "Research methods course", 0),
    ("Candidacy", "Comprehensive exam", 0),
    ("Dissertation defense", "Coursework", 0),
    ("Dissertation defense", "Dissertation proposal", 1),  # at least 1 semester before
]

# ---------------------------------------------------------------------------
# 4. EACH STUDENT'S PROGRESS — milestone name → (status, completed_on)
# Only milestones with progress get a row. A milestone with NO row means
# "not started" — the dashboard shows it that way (team decision).
# ---------------------------------------------------------------------------
S = MilestoneStatus
PROGRESS = {
    "student@gradtrack.edu": {  # Sam
        "Coursework": (S.IN_PROGRESS, None),
        "Advisor declaration": (S.APPROVED, date(2024, 1, 15)),
        "Research methods course": (S.APPROVED, date(2024, 5, 10)),
        "Comprehensive exam": (S.APPROVED, date(2025, 11, 20)),
        "Committee formation": (S.APPROVED, date(2025, 3, 1)),
        "Dissertation proposal": (S.UNDER_REVIEW, None),
    },
    "lisa@gradtrack.edu": {  # Lisa
        "Coursework": (S.IN_PROGRESS, None),
        "Research methods course": (S.IN_PROGRESS, None),
    },
    "raj@gradtrack.edu": {  # Raj
        "Coursework": (S.APPROVED, date(2024, 5, 15)),
        "Advisor declaration": (S.APPROVED, date(2022, 12, 1)),
        "Research methods course": (S.APPROVED, date(2023, 5, 12)),
        "Comprehensive exam": (S.APPROVED, date(2023, 12, 10)),
        "Committee formation": (S.APPROVED, date(2023, 9, 5)),
        "Dissertation proposal": (S.APPROVED, date(2025, 12, 1)),
    },
}


# ---------------------------------------------------------------------------
# The steps
# ---------------------------------------------------------------------------
def users_table_is_outdated() -> bool:
    """True if the users table exists but is missing the new student fields."""
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return False
    columns = {c["name"] for c in inspector.get_columns("users")}
    return "advisor_id" not in columns


def seed_users(db):
    for email, name, role in FACULTY_AND_STAFF:
        if service.get_user_by_email(db, email):
            print(f"  exists:  {email}")
        else:
            service.create_user(db, email, name, role, TEST_PASSWORD)
            print(f"  created: {email}  ({role.value})")

    for email, name, fields, advisor_email in STUDENTS:
        if service.get_user_by_email(db, email):
            print(f"  exists:  {email}")
            continue
        student = service.create_user(db, email, name, Role.STUDENT, TEST_PASSWORD)
        for field, value in fields.items():
            setattr(student, field, value)
        if advisor_email:
            student.advisor_id = service.get_user_by_email(db, advisor_email).id
        db.commit()
        print(f"  created: {email}  (student)")


def seed_milestones(db) -> dict[str, Milestone]:
    """Add the milestones and return them as {name: Milestone}."""
    existing = {m.name: m for m in db.scalars(select(Milestone))}
    for name, position, deadline_adv, deadline_reg in MILESTONES:
        if name not in existing:
            m = Milestone(name=name, position=position,
                          deadline_semester_advanced=deadline_adv,
                          deadline_semester_regular=deadline_reg)
            db.add(m)
            existing[name] = m
    db.commit()
    print(f"  milestones: {len(existing)}")
    return existing


def seed_prerequisites(db, milestones: dict[str, Milestone]):
    added = 0
    for name, requires, gap in PREREQUISITES:
        key = (milestones[name].id, milestones[requires].id)
        if db.get(MilestonePrerequisite, key) is None:
            db.add(MilestonePrerequisite(milestone_id=key[0], requires_id=key[1], min_gap_semesters=gap))
            added += 1
    db.commit()
    print(f"  prerequisite rules: {len(PREREQUISITES)} ({added} new)")


def seed_progress(db, milestones: dict[str, Milestone]):
    added = 0
    for email, *_ in STUDENTS:
        student = service.get_user_by_email(db, email)
        has = set(db.scalars(select(StudentMilestone.milestone_id)
                             .where(StudentMilestone.student_id == student.id)))
        # Only the milestones listed in PROGRESS for this student get a row.
        for name, (status, completed_on) in PROGRESS[email].items():
            milestone = milestones[name]
            if milestone.id in has:
                continue
            db.add(StudentMilestone(student_id=student.id, milestone_id=milestone.id,
                                    status=status, completed_on=completed_on))
            added += 1
    db.commit()
    print(f"  student progress rows: {added} new")


def main(reset: bool = False):
    if reset:
        print("Resetting: deleting ALL tables and data...")
        Base.metadata.drop_all(engine)
    elif users_table_is_outdated():
        print("The users table is missing the new student fields.")
        print("Run:  python seed.py --reset   (this deletes all existing test data)")
        sys.exit(1)

    # Create any tables that don't exist yet (based on all the models.py files).
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        print("Users:")
        seed_users(db)
        print("Milestones:")
        milestones = seed_milestones(db)
        seed_prerequisites(db, milestones)
        seed_progress(db, milestones)
    print(f"Done. Test password for all users: {TEST_PASSWORD}")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
