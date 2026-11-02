"""Student dashboard responses and advisor input. Never expose authentication fields."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.milestones.models import MilestoneStatus
from app.modules.users.models import EnrollmentStatus, Term


class StudentProfile(BaseModel):
    full_name: str
    advanced_standing: bool | None
    enrollment_status: EnrollmentStatus | None
    start_term: Term | None
    start_year: int | None
    gpa: Decimal | None
    advisor_id: int | None
    advisor_name: str | None
    current_semester: int | None
    program_year: int | None


class AdvisorOut(BaseModel):
    id: int
    full_name: str
    email: str
    advisee_count: int
    department: str | None = None
    affiliation: str | None = None
    research_interests: str | None = None
    lab_name: str | None = None
    accepting_students: bool | None = None
    academic_url: str | None = None
    bio: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AdvisorDeclaration(BaseModel):
    advisor_id: int = Field(gt=0, strict=True)

    model_config = ConfigDict(extra="forbid")


class AdvisorDeclarationDetails(BaseModel):
    declared_on: date | None
    advisor: AdvisorOut


class RequirementOut(BaseModel):
    name: str
    met: bool
    explanation: str


class MilestoneOut(BaseModel):
    id: int
    name: str
    status: MilestoneStatus
    category: Literal["current", "blocked", "upcoming", "completed"]
    # True if the app completes this milestone by itself, so the page says "Completed" instead of "Approved".
    is_automatic: bool
    completed_on: date | None
    # The exact approval date and time. Empty if it isn't approved, or the time wasn't recorded.
    approved_at: datetime | None = None
    deadline_semester: int | None
    deadline_label: str | None
    overdue: bool
    eligible: bool
    requirements: list[RequirementOut]
    blocked_reasons: list[str]


class ProgressSummary(BaseModel):
    total: int
    completed: int
    current: int
    blocked: int
    upcoming: int
    percent: int


class DashboardOut(BaseModel):
    as_of: date
    student: StudentProfile
    summary: ProgressSummary
    milestones: list[MilestoneOut]
