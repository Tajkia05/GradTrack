"""Build the read-only faculty dashboard from existing student and milestone data."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.faculty.schemas import (
    AssignedStudentOut,
    FacultyDashboardOut,
    FacultyProfile,
    FacultySummary,
    PendingReviewOut,
)
from app.modules.milestones.models import (
    Milestone,
    MilestoneStatus,
    StudentMilestone,
)
from app.modules.student.service import semester_index
from app.modules.users.models import Role, Term, User


REVIEW_STATUSES = {
    MilestoneStatus.SUBMITTED,
    MilestoneStatus.UNDER_REVIEW,
    MilestoneStatus.REVISION_REQUESTED,
}


def get_faculty_dashboard(
    db: Session,
    faculty: User,
    today: date | None = None,
) -> FacultyDashboardOut:
    today = today or datetime.now(ZoneInfo("America/New_York")).date()
    now = semester_index(today)

    students = list(
        db.scalars(
            select(User)
            .where(
                User.role == Role.STUDENT,
                User.advisor_id == faculty.id,
            )
            .order_by(User.full_name)
        )
    )

    milestones = list(
        db.scalars(
            select(Milestone).order_by(Milestone.position, Milestone.id)
        )
    )

    milestone_by_id = {
        milestone.id: milestone
        for milestone in milestones
    }

    student_outputs = []
    pending_reviews = []

    for student in students:
        progress_rows = list(
            db.scalars(
                select(StudentMilestone).where(
                    StudentMilestone.student_id == student.id
                )
            )
        )

        completed = sum(
            row.status == MilestoneStatus.APPROVED
            for row in progress_rows
        )

        total = len(milestones)

        progress_percent = (
            round(completed * 100 / total)
            if total
            else 0
        )

        if (
            student.start_year is not None
            and student.start_term is not None
        ):
            start = (
                student.start_year * 2
                + (student.start_term == Term.FALL)
            )

            current_semester = max(
                0,
                now - start + 1,
            )

            program_year = (
                (current_semester + 1) // 2
                if current_semester > 0
                else 0
            )
        else:
            program_year = None

        student_outputs.append(
            AssignedStudentOut(
                id=student.id,
                full_name=student.full_name,
                program_year=program_year,
                completed_milestones=completed,
                total_milestones=total,
                progress_percent=progress_percent,
            )
        )

        for row in progress_rows:
            if row.status not in REVIEW_STATUSES:
                continue

            milestone = milestone_by_id.get(row.milestone_id)

            if milestone is None:
                continue

            pending_reviews.append(
                PendingReviewOut(
                    student_id=student.id,
                    student_name=student.full_name,
                    milestone_id=milestone.id,
                    milestone_name=milestone.name,
                    status=row.status,
                )
            )

    return FacultyDashboardOut(
        faculty=FacultyProfile(
            id=faculty.id,
            full_name=faculty.full_name,
        ),
        summary=FacultySummary(
            assigned_students=len(student_outputs),
            pending_reviews=len(pending_reviews),
        ),
        students=student_outputs,
        pending_reviews=pending_reviews,
    )
