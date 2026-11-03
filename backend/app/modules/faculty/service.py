"""Build the faculty dashboard and handle faculty review actions."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.committee.models import CommitteeMember
from app.modules.faculty.models import FacultyProfile as FacultyProfileModel
from app.modules.faculty.schemas import (
    AssignedStudentOut,
    CommitteeInvitationOut,
    CommitteeMembershipOut,
    FacultyDashboardOut,
    FacultyProfile,
    FacultyProfileOut,
    FacultyProfileUpdate,
    FacultyStudentProgressOut,
    FacultySummary,
    PendingReviewOut,
    StudentMilestoneDetailOut,
)
from app.modules.milestones.models import (
    Milestone,
    MilestoneStatus,
    StudentMilestone,
)
from app.modules.notifications import links
from app.modules.notifications.models import Notification
from app.modules.student.service import semester_index
from app.modules.submissions.history import record_status_change
from app.modules.users.models import Role, Term, User


REVIEW_STATUSES = {
    MilestoneStatus.SUBMITTED,
    MilestoneStatus.UNDER_REVIEW,
    MilestoneStatus.REVISION_REQUESTED,
}


def _get_program_year(
    student: User,
    today: date,
) -> int | None:
    """Calculate the student's current program year."""
    if (
        student.start_year is None
        or student.start_term is None
    ):
        return None

    now = semester_index(today)

    start = (
        student.start_year * 2
        + (student.start_term == Term.FALL)
    )

    current_semester = max(
        0,
        now - start + 1,
    )

    return (
        (current_semester + 1) // 2
        if current_semester > 0
        else 0
    )


def get_faculty_dashboard(
    db: Session,
    faculty: User,
    today: date | None = None,
) -> FacultyDashboardOut:
    """Build the logged-in faculty member's dashboard."""
    today = today or datetime.now(
        ZoneInfo("America/New_York")
    ).date()

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
            select(Milestone).order_by(
                Milestone.position,
                Milestone.id,
            )
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

        student_outputs.append(
            AssignedStudentOut(
                id=student.id,
                full_name=student.full_name,
                program_year=_get_program_year(
                    student,
                    today,
                ),
                completed_milestones=completed,
                total_milestones=total,
                progress_percent=progress_percent,
            )
        )

        for row in progress_rows:
            if row.status not in REVIEW_STATUSES:
                continue

            milestone = milestone_by_id.get(
                row.milestone_id
            )

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


def review_student_milestone(
    db: Session,
    faculty: User,
    student_id: int,
    milestone_id: int,
    new_status: MilestoneStatus,
    comment: str | None = None,
) -> StudentMilestone | None:
    """Review a milestone belonging to an assigned student."""
    student = db.scalar(
        select(User).where(
            User.id == student_id,
            User.role == Role.STUDENT,
            User.advisor_id == faculty.id,
        )
    )

    if student is None:
        return None

    progress = db.scalar(
        select(StudentMilestone).where(
            StudentMilestone.student_id == student_id,
            StudentMilestone.milestone_id == milestone_id,
        )
    )

    if (
        progress is None
        or progress.status not in REVIEW_STATUSES
    ):
        return None

    progress.status = new_status

    if new_status == MilestoneStatus.APPROVED:
        progress.completed_on = datetime.now(
            ZoneInfo("America/New_York")
        ).date()
    else:
        progress.completed_on = None

    # Keep a history of the faculty decision,
    # save the optional comment, and notify the student.
    record_status_change(
        db,
        student_id,
        milestone_id,
        new_status,
        faculty.id,
        comment,
    )

    db.commit()
    db.refresh(progress)

    return progress


def get_pending_committee_invitations(
    db: Session,
    faculty: User,
) -> list[CommitteeInvitationOut]:
    """Return pending committee invitations for this faculty member."""
    rows = db.execute(
        select(CommitteeMember, User)
        .join(
            User,
            User.id == CommitteeMember.student_id,
        )
        .where(
            CommitteeMember.faculty_id == faculty.id,
            CommitteeMember.status == "pending",
        )
        .order_by(CommitteeMember.id)
    ).all()

    return [
        CommitteeInvitationOut(
            id=invitation.id,
            student_id=student.id,
            student_name=student.full_name,
            invited_on=invitation.invited_on,
        )
        for invitation, student in rows
    ]


def respond_to_committee_invitation(
    db: Session,
    faculty: User,
    invitation_id: int,
    new_status: str,
) -> CommitteeMember | None:
    """Approve or decline one pending committee invitation."""
    invitation = db.scalar(
        select(CommitteeMember).where(
            CommitteeMember.id == invitation_id,
            CommitteeMember.faculty_id == faculty.id,
        )
    )

    if invitation is None:
        return None

    if invitation.status != "pending":
        return None

    invitation.status = new_status

    action = (
        "accepted"
        if new_status == "approved"
        else "declined"
    )

    db.add(
        Notification(
            user_id=invitation.student_id,
            message=(
                f"{faculty.full_name} {action} your "
                "dissertation committee invitation."
            ),
            link=links.student_committee(db),
        )
    )

    db.commit()
    db.refresh(invitation)

    return invitation


def get_committee_memberships(
    db: Session,
    faculty: User,
) -> list[CommitteeMembershipOut]:
    """Return committees the faculty member has joined."""
    rows = db.execute(
        select(CommitteeMember, User)
        .join(
            User,
            User.id == CommitteeMember.student_id,
        )
        .where(
            CommitteeMember.faculty_id == faculty.id,
            CommitteeMember.status == "approved",
        )
        .order_by(CommitteeMember.id)
    ).all()

    return [
        CommitteeMembershipOut(
            id=membership.id,
            student_id=student.id,
            student_name=student.full_name,
            invited_on=membership.invited_on,
        )
        for membership, student in rows
    ]


def leave_committee(
    db: Session,
    faculty: User,
    membership_id: int,
) -> bool:
    """Remove faculty from one of their approved committees."""
    membership = db.scalar(
        select(CommitteeMember).where(
            CommitteeMember.id == membership_id,
            CommitteeMember.faculty_id == faculty.id,
            CommitteeMember.status == "approved",
        )
    )

    if membership is None:
        return False

    student_id = membership.student_id

    db.add(
        Notification(
            user_id=student_id,
            message=(
                f"{faculty.full_name} left your "
                "dissertation committee."
            ),
            link=links.student_committee(db),
        )
    )

    db.delete(membership)
    db.commit()

    return True


def get_faculty_profile(
    db: Session,
    faculty: User,
) -> FacultyProfileOut:
    """Return the logged-in faculty member's profile."""
    profile = db.get(
        FacultyProfileModel,
        faculty.id,
    )

    return FacultyProfileOut(
        full_name=faculty.full_name,
        email=faculty.email,
        title=profile.title if profile else None,
        department=profile.department if profile else None,
        affiliation=profile.affiliation if profile else None,
        research_interests=(
            profile.research_interests
            if profile
            else None
        ),
        lab_name=profile.lab_name if profile else None,
        accepting_students=(
            profile.accepting_students
            if profile
            else None
        ),
        academic_url=(
            profile.academic_url
            if profile
            else None
        ),
        bio=profile.bio if profile else None,
    )


def save_faculty_profile(
    db: Session,
    faculty: User,
    data: FacultyProfileUpdate,
) -> FacultyProfileOut:
    """Create or update the logged-in faculty member's profile."""
    faculty.full_name = data.full_name.strip()

    profile = db.get(
        FacultyProfileModel,
        faculty.id,
    )

    if profile is None:
        profile = FacultyProfileModel(
            user_id=faculty.id,
        )
        db.add(profile)

    profile.title = data.title
    profile.department = data.department
    profile.affiliation = data.affiliation
    profile.research_interests = data.research_interests
    profile.lab_name = data.lab_name
    profile.accepting_students = data.accepting_students
    profile.academic_url = data.academic_url
    profile.bio = data.bio

    db.commit()
    db.refresh(faculty)
    db.refresh(profile)

    return get_faculty_profile(
        db,
        faculty,
    )


def get_student_progress_for_faculty(
    db: Session,
    faculty: User,
    student_id: int,
    today: date | None = None,
) -> FacultyStudentProgressOut | None:
    """Return detailed progress for an assigned student only."""
    student = db.scalar(
        select(User).where(
            User.id == student_id,
            User.role == Role.STUDENT,
            User.advisor_id == faculty.id,
        )
    )

    # This is also the authorization check.
    # A faculty member cannot view another advisor's student.
    if student is None:
        return None

    today = today or datetime.now(
        ZoneInfo("America/New_York")
    ).date()

    milestones = list(
        db.scalars(
            select(Milestone).order_by(
                Milestone.position,
                Milestone.id,
            )
        )
    )

    progress_rows = list(
        db.scalars(
            select(StudentMilestone).where(
                StudentMilestone.student_id == student.id
            )
        )
    )

    progress_by_milestone = {
        row.milestone_id: row
        for row in progress_rows
    }

    completed = sum(
        row.status == MilestoneStatus.APPROVED
        for row in progress_rows
    )

    total = len(milestones)
    remaining = max(
        0,
        total - completed,
    )

    progress_percent = (
        round(completed * 100 / total)
        if total
        else 0
    )

    milestone_outputs = []

    for milestone in milestones:
        progress = progress_by_milestone.get(
            milestone.id
        )

        milestone_outputs.append(
            StudentMilestoneDetailOut(
                milestone_id=milestone.id,
                milestone_name=milestone.name,
                position=milestone.position,
                status=(
                    progress.status
                    if progress is not None
                    else MilestoneStatus.NOT_STARTED
                ),
                completed_on=(
                    progress.completed_on
                    if progress is not None
                    else None
                ),
            )
        )

    return FacultyStudentProgressOut(
        student_id=student.id,
        student_name=student.full_name,
        email=student.email,
        program_year=_get_program_year(
            student,
            today,
        ),
        completed_milestones=completed,
        total_milestones=total,
        remaining_milestones=remaining,
        progress_percent=progress_percent,
        milestones=milestone_outputs,
    )
    