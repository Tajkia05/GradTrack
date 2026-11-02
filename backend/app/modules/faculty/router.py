"""Faculty dashboard, milestone review, and committee invitation API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.modules.faculty.schemas import (
    CommitteeInvitationOut,
    CommitteeInvitationResponse,
    FacultyDashboardOut,
    MilestoneReviewRequest,
)
from app.modules.faculty.service import (
    get_faculty_dashboard,
    get_pending_committee_invitations,
    respond_to_committee_invitation,
    review_student_milestone,
)
from app.modules.milestones.models import MilestoneStatus
from app.modules.users.models import Role, User


router = APIRouter(tags=["Faculty"])


@router.get("/faculty/me/dashboard", response_model=FacultyDashboardOut)
def my_dashboard(
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    return get_faculty_dashboard(db, faculty)


@router.patch("/faculty/students/{student_id}/milestones/{milestone_id}")
def review_milestone(
    student_id: int,
    milestone_id: int,
    body: MilestoneReviewRequest,
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    allowed_statuses = {
        MilestoneStatus.APPROVED,
        MilestoneStatus.REVISION_REQUESTED,
        MilestoneStatus.REJECTED,
    }

    if body.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid review action",
        )

    progress = review_student_milestone(
        db,
        faculty,
        student_id,
        milestone_id,
        body.status,
    )

    if progress is None:
        raise HTTPException(
            status_code=404,
            detail="Reviewable milestone not found for this faculty member",
        )

    return {
        "student_id": progress.student_id,
        "milestone_id": progress.milestone_id,
        "status": progress.status,
        "completed_on": progress.completed_on,
    }


@router.get(
    "/faculty/me/committee-invitations",
    response_model=list[CommitteeInvitationOut],
)
def my_committee_invitations(
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    return get_pending_committee_invitations(db, faculty)


@router.patch("/faculty/committee-invitations/{invitation_id}")
def respond_to_invitation(
    invitation_id: int,
    body: CommitteeInvitationResponse,
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    if body.status not in {"approved", "declined"}:
        raise HTTPException(
            status_code=400,
            detail="Committee invitation can only be approved or declined",
        )

    invitation = respond_to_committee_invitation(
        db,
        faculty,
        invitation_id,
        body.status,
    )

    if invitation is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Committee invitation not found or no longer pending. "
                "The student may have removed it. Refresh the page."
            ),
        )

    return {
        "id": invitation.id,
        "student_id": invitation.student_id,
        "status": invitation.status,
    }
    