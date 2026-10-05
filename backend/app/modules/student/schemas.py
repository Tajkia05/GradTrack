"""Read-only student dashboard responses. Never expose authentication fields."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

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


class RequirementOut(BaseModel):
    name: str
    met: bool
    explanation: str


class MilestoneOut(BaseModel):
    id: int
    name: str
    status: MilestoneStatus
    category: Literal["current", "blocked", "upcoming", "completed"]
    completed_on: date | None
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
