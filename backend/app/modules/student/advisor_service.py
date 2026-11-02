"""Immediate advisor declaration and optional academic profiles."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
# Tells the advisor about a new declaration.
from app.modules.notifications.models import Notification
from app.modules.users.models import Role, User
from app.modules.faculty.models import FacultyProfile


def list_advisors(db: Session, advisor_id: int | None = None):
    # All faculty remain visible, even when their optional profile is missing.
    counts = (select(User.advisor_id, func.count(User.id).label("advisee_count"))
              .where(User.role == Role.STUDENT, User.advisor_id.is_not(None))
              .group_by(User.advisor_id).subquery())
    rows = db.execute(select(User.id, User.full_name, User.email,
                             FacultyProfile.department, FacultyProfile.affiliation,
                             FacultyProfile.research_interests, FacultyProfile.lab_name,
                             FacultyProfile.accepting_students, FacultyProfile.academic_url,
                             FacultyProfile.bio,
                             func.coalesce(counts.c.advisee_count, 0).label("advisee_count"))
                      .outerjoin(counts, counts.c.advisor_id == User.id)
                      .outerjoin(FacultyProfile, FacultyProfile.user_id == User.id)
                      .where(User.id == advisor_id if advisor_id is not None else True)
                      .where(User.role == Role.FACULTY).order_by(User.full_name, User.id))
    return [dict(row) for row in rows.mappings()]


def get_declaration_details(db: Session, student: User):
    progress = db.scalar(select(StudentMilestone).join(Milestone)
                         .where(StudentMilestone.student_id == student.id,
                                Milestone.name == "Advisor declaration",
                                StudentMilestone.status == MilestoneStatus.APPROVED))
    if progress is None or student.advisor_id is None:
        raise HTTPException(404, "No completed advisor declaration was found. Refresh your dashboard.")
    advisors = list_advisors(db, student.advisor_id)
    if not advisors:
        raise HTTPException(404, "Your advisor's profile is unavailable. Contact your program coordinator.")
    return {"declared_on": progress.completed_on, "advisor": advisors[0]}


def declare_advisor(db: Session, student_id: int, advisor_id: int) -> User:
    try:
        # Serialize declarations for this student on PostgreSQL. Refresh the
        # identity-map object loaded by authentication after acquiring the lock.
        student = db.scalar(select(User).where(User.id == student_id, User.role == Role.STUDENT)
                            .with_for_update().execution_options(populate_existing=True))
        if student is None:
            raise HTTPException(404, "Student not found.")
        if student.advisor_id is not None and student.advisor_id != advisor_id:
            raise HTTPException(409, "You already have a declared advisor. Contact your program coordinator to request a change.")

        advisor = db.scalar(select(User).where(User.id == advisor_id, User.role == Role.FACULTY))
        if advisor is None:
            raise HTTPException(422, "Choose an available faculty member as your advisor.")

        profile = db.get(FacultyProfile, advisor_id)
        if student.advisor_id != advisor_id and profile is not None and profile.accepting_students is False:
            raise HTTPException(409, "This faculty member is not accepting new students. Please choose another advisor.")

        milestone = db.scalar(select(Milestone).where(Milestone.name == "Advisor declaration"))
        if milestone is None:
            raise HTTPException(409, "The advisor declaration milestone is not configured. Contact your program coordinator.")

        progress = db.scalar(select(StudentMilestone).where(
            StudentMilestone.student_id == student.id,
            StudentMilestone.milestone_id == milestone.id,
        ))
        today = datetime.now(ZoneInfo("America/New_York")).date()
        if progress is None:
            progress = StudentMilestone(student_id=student.id, milestone_id=milestone.id)
            db.add(progress)
        # Retrying the same declaration must not change its original completion date.
        if progress.status != MilestoneStatus.APPROVED or progress.completed_on is None:
            progress.completed_on = today
        progress.status = MilestoneStatus.APPROVED
        # A new declaration tells the advisor. Retrying the same one doesn't send it twice.
        if student.advisor_id != advisor.id:
            db.add(Notification(user_id=advisor.id, message=f"{student.full_name} declared you as their research advisor."))
        student.advisor_id = advisor.id
        db.commit()  # All the records succeed together, or none are saved.
        db.refresh(student)
        return student
    except Exception:
        db.rollback()
        raise
