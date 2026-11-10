"""Faculty dashboard, milestone review, and committee response models."""

from datetime import date

from pydantic import BaseModel

from app.modules.milestones.models import MilestoneStatus
# One advisee's presentation and the stage it's at.
from app.modules.presentations.schemas import AdvisorPresentationOut


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
    # The advisees' exam, proposal and defense presentations, after the document is approved.
    presentations: list[AdvisorPresentationOut] = []


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
    

class FacultyProfileOut(BaseModel):
    full_name: str
    email: str
    title: str | None = None
    department: str | None = None
    affiliation: str | None = None
    research_interests: str | None = None
    lab_name: str | None = None
    accepting_students: bool | None = None
    academic_url: str | None = None
    bio: str | None = None


class FacultyProfileUpdate(BaseModel):
    full_name: str
    title: str | None = None
    department: str | None = None
    affiliation: str | None = None
    research_interests: str | None = None
    lab_name: str | None = None
    accepting_students: bool | None = None
    academic_url: str | None = None
    bio: str | None = None


class StudentMilestoneDetailOut(BaseModel):
    milestone_id: int
    milestone_name: str
    position: int
    status: MilestoneStatus
    completed_on: date | None = None


class FacultyStudentProgressOut(BaseModel):
    student_id: int
    student_name: str
    email: str
    program_year: int | None
    completed_milestones: int
    total_milestones: int
    remaining_milestones: int
    progress_percent: int
    milestones: list[StudentMilestoneDetailOut]
