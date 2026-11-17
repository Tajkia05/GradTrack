# presentations/schemas.py — THE DATA THE API ACCEPTS AND RETURNS
# FOR PRESENTATION SCHEDULING.

from datetime import datetime
from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
)


# ============================================================
# STUDENT: PROPOSING PRESENTATION DATES
# ============================================================


# One date the student proposes.
class OptionIn(BaseModel):
    # Date and time with its time zone.
    starts_at: AwareDatetime

    # External committee members who can attend this date.
    external_member_ids: list[int] = Field(
        default_factory=list,
        max_length=10,
    )

    # External members who will join by Zoom.
    # Used for hybrid presentations.
    external_online_ids: list[int] = Field(
        default_factory=list,
        max_length=10,
    )

    model_config = ConfigDict(extra="forbid")


# What the student sends when proposing presentation dates.
class PresentationIn(BaseModel):
    # In person, online, or hybrid.
    mode: Literal[
        "in_person",
        "online",
        "hybrid",
    ]

    # Room for in-person/hybrid presentations,
    # or meeting link for online presentations.
    location: str = Field(
        min_length=1,
        max_length=255,
    )

    # Zoom link for a hybrid presentation.
    meeting_link: str | None = Field(
        default=None,
        max_length=255,
    )

    # The student may propose 1 to 3 dates.
    options: list[OptionIn] = Field(
        min_length=1,
        max_length=3,
    )

    model_config = ConfigDict(extra="forbid")


# What the student sends when choosing the final date.
class DateChoiceIn(BaseModel):
    option_id: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


# ============================================================
# PRESENTATION AVAILABILITY
# ============================================================


# One committee member's answer for one proposed date.
class ResponseOut(BaseModel):
    # Committee member's name.
    name: str

    # True if they can attend.
    available: bool

    # How they will attend.
    # Empty when they cannot attend.
    attend_mode: Literal[
        "in_person",
        "online",
    ] | None = None


# One proposed date and all committee answers so far.
class OptionOut(BaseModel):
    # Proposed date ID.
    id: int

    # Date and time.
    starts_at: datetime

    # True if this is the final selected date.
    chosen: bool

    # Committee answers received so far.
    responses: list[ResponseOut]

    # True when everyone required can attend this date.
    everyone_available: bool

    # Committee members who have not answered yet.
    waiting_for: list[str]


# ============================================================
# STUDENT: PRESENTATION OUTPUT
# ============================================================


# Presentation shown on the student's milestone page.
class PresentationOut(BaseModel):
    # Presentation ID.
    id: int

    # First or second attempt.
    attempt: int

    # Current scheduling status.
    # "held" is shown when the selected date has passed.
    status: Literal[
        "awaiting_availability",
        "needs_new_dates",
        "scheduled",
        "held",
        "cancelled",
    ]

    # Presentation format.
    mode: Literal[
        "in_person",
        "online",
        "hybrid",
    ]

    # Room or online meeting link.
    location: str

    # Zoom link for hybrid presentations.
    meeting_link: str | None = None

    # Confirmed presentation date.
    scheduled_at: datetime | None

    # Proposed dates.
    options: list[OptionOut]


# External committee member shown while the student
# enters availability.
class ExternalMemberOut(BaseModel):
    id: int
    name: str


# ============================================================
# FACULTY: AVAILABILITY INPUT AND OUTPUT
# ============================================================


# What a faculty member sends when answering one proposed date.
class FacultyAvailabilityIn(BaseModel):
    # True if the faculty member can attend.
    available: bool

    # How they will attend.
    # Must be empty when available is False.
    attend_mode: Literal[
        "in_person",
        "online",
    ] | None = None

    model_config = ConfigDict(extra="forbid")


# The logged-in faculty member's saved answer.
class FacultyAvailabilityOut(BaseModel):
    available: bool

    attend_mode: Literal[
        "in_person",
        "online",
    ] | None = None


# One proposed date shown on the faculty dashboard.
class FacultyOptionOut(BaseModel):
    # Proposed date ID.
    id: int

    # Proposed date and time.
    starts_at: datetime

    # This logged-in faculty member's current answer.
    # None means they have not answered yet.
    my_response: FacultyAvailabilityOut | None = None

    # Committee members who still need to answer.
    waiting_for: list[str] = Field(
        default_factory=list,
    )


# ============================================================
# FACULTY: PRESENTATION DASHBOARD
# ============================================================


# One student's presentation shown on the faculty dashboard.
class AdvisorPresentationOut(BaseModel):
    # Student information.
    student_id: int
    student_name: str

    # Milestone information.
    milestone_id: int
    milestone_name: str

    # Current presentation stage.
    stage: Literal[
        "waiting_for_dates",
        "awaiting_availability",
        "needs_new_dates",
        "scheduled",
        "held",
        "revision_requested",
    ]

    # Final selected date, once one has been chosen.
    scheduled_at: datetime | None

    # Presentation format once dates have been proposed.
    mode: Literal[
        "in_person",
        "online",
        "hybrid",
    ] | None

    # Room or online meeting link.
    location: str | None

    # Zoom link for hybrid presentations.
    meeting_link: str | None = None

    # Number of proposed dates.
    option_count: int

    # Proposed dates and the logged-in faculty member's
    # availability responses.
    options: list[FacultyOptionOut] = Field(
        default_factory=list,
    )

    # Advisor records the final decision.
    # Committee members only provide availability.
    role: Literal[
        "advisor",
        "member",
    ] = "advisor"


# ============================================================
# DASHBOARD SUMMARY
# ============================================================


# Short presentation information used by milestone cards.
class PresentationSummary(BaseModel):
    status: str
    scheduled_at: datetime | None


# ============================================================
# STUDENT PRESENTATION STATE
# ============================================================


# Everything the student's presentation scheduling page needs.
class PresentationState(BaseModel):
    # Current presentation for this attempt.
    presentation: PresentationOut | None

    # Whether the student may propose dates now.
    can_propose: bool

    # Explanation or next action.
    message: str | None

    # Earliest allowed proposed date.
    earliest_at: datetime | None

    # External committee members whose availability
    # the student enters.
    external_members: list[ExternalMemberOut]
