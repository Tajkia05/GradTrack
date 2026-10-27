"""Immediate advisor declaration; no faculty approval or schema migration needed."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
from app.modules.users.models import Role, User


def list_advisors(db: Session):
    # The prototype's faculty roster is the advisor catalog. Appointment type and
    # department eligibility are not represented in the current schema.
    counts = (select(User.advisor_id, func.count(User.id).label("advisee_count"))
              .where(User.role == Role.STUDENT, User.advisor_id.is_not(None))
              .group_by(User.advisor_id).subquery())
    rows = db.execute(select(User.id, User.full_name, User.email,
                             func.coalesce(counts.c.advisee_count, 0).label("advisee_count"))
                      .outerjoin(counts, counts.c.advisor_id == User.id)
                      .where(User.role == Role.FACULTY).order_by(User.full_name, User.id))
    return [dict(row) for row in rows.mappings()]


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
        student.advisor_id = advisor.id
        db.commit()  # Both records succeed together, or neither is saved.
        db.refresh(student)
        return student
    except Exception:
        db.rollback()
        raise
