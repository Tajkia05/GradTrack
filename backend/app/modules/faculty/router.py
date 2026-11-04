"""Faculty dashboard, profile, student progress, and review API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.modules.faculty.schemas import (
    CommitteeInvitationOut,
    CommitteeInvitationResponse,
    CommitteeMembershipOut,
    FacultyDashboardOut,
    FacultyProfileOut,
    FacultyProfileUpdate,
    FacultyStudentProgressOut,
    MilestoneReviewRequest,
)
from app.modules.faculty.service import (
    get_committee_memberships,
    get_faculty_dashboard,
    get_faculty_profile,
    get_pending_committee_invitations,
    get_student_progress_for_faculty,
    leave_committee,
    respond_to_committee_invitation,
    review_student_milestone,
    save_faculty_profile,
)
from app.modules.milestones.models import MilestoneStatus
from app.modules.users.models import Role, User


router = APIRouter(tags=["Faculty"])


@router.get(
    "/faculty/me/dashboard",
    response_model=FacultyDashboardOut,
)
def my_dashboard(
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    """Return the logged-in faculty member's dashboard."""
    return get_faculty_dashboard(
        db,
        faculty,
    )


@router.get(
    "/faculty/me/profile",
    response_model=FacultyProfileOut,
)
def my_profile(
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    """Return the logged-in faculty member's profile."""
    return get_faculty_profile(
        db,
        faculty,
    )


@router.put(
    "/faculty/me/profile",
    response_model=FacultyProfileOut,
)
def update_my_profile(
    body: FacultyProfileUpdate,
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    """Create or update the logged-in faculty member's profile."""
    return save_faculty_profile(
        db,
        faculty,
        body,
    )


@router.get(
    "/faculty/students/{student_id}/progress",
    response_model=FacultyStudentProgressOut,
)
def student_progress(
    student_id: int,
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    """Return detailed progress for one assigned student."""
    progress = get_student_progress_for_faculty(
        db,
        faculty,
        student_id,
    )

    if progress is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Student not found or not assigned "
                "to this faculty member."
            ),
        )

    return progress


@router.patch(
    "/faculty/students/{student_id}/milestones/{milestone_id}"
)
def review_milestone(
    student_id: int,
    milestone_id: int,
    body: MilestoneReviewRequest,
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    """Approve, reject, or request revision for a milestone."""
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
        body.comment,
    )

    if progress is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Reviewable milestone not found "
                "for this faculty member"
            ),
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
    """Return pending committee invitations."""
    return get_pending_committee_invitations(
        db,
        faculty,
    )


@router.patch(
    "/faculty/committee-invitations/{invitation_id}"
)
def respond_to_invitation(
    invitation_id: int,
    body: CommitteeInvitationResponse,
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    """Approve or decline a committee invitation."""
    if body.status not in {"approved", "declined"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Committee invitation can only "
                "be approved or declined"
            ),
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


@router.get(
    "/faculty/me/committee-memberships",
    response_model=list[CommitteeMembershipOut],
)
def my_committee_memberships(
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    """Return approved committee memberships."""
    return get_committee_memberships(
        db,
        faculty,
    )


@router.delete(
    "/faculty/committee-memberships/{membership_id}"
)
def leave_committee_membership(
    membership_id: int,
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    """Leave an approved committee."""
    removed = leave_committee(
        db,
        faculty,
        membership_id,
    )

    if not removed:
        raise HTTPException(
            status_code=404,
            detail=(
                "Approved committee membership not found "
                "for this faculty member."
            ),
        )

    return {
        "message": "You have left the committee."
    }
    