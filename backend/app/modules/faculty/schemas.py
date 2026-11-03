"""Faculty dashboard, milestone review, and committee response models."""

from datetime import date

from pydantic import BaseModel

from app.modules.milestones.models import MilestoneStatus


class FacultyProfile(BaseModel):
    id: int
    full_name: str


class AssignedStudentOut(BaseModel):
    id: int
    full_name: str
    program_year: int | None
    completed_milestones: int
    total_milestones: int
    progress_percent: int


class PendingReviewOut(BaseModel):
    student_id: int
    student_name: str
    milestone_id: int
    milestone_name: str
    status: MilestoneStatus


class FacultySummary(BaseModel):
    assigned_students: int
    pending_reviews: int


class FacultyDashboardOut(BaseModel):
    faculty: FacultyProfile
    summary: FacultySummary
    students: list[AssignedStudentOut]
    pending_reviews: list[PendingReviewOut]


class MilestoneReviewRequest(BaseModel):
    status: MilestoneStatus
    comment: str | None = None


class CommitteeInvitationOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    invited_on: date


class CommitteeInvitationResponse(BaseModel):
    status: str


class CommitteeMembershipOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    invited_on: date
    