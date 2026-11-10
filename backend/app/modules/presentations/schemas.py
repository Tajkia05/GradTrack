# presentations/schemas.py — THE DATA THE API ACCEPTS AND RETURNS FOR PRESENTATION SCHEDULING.

# datetime is a date and time.
from datetime import datetime
# Literal limits a field to a few fixed values.
from typing import Literal

# AwareDatetime only accepts a date and time with its time zone, BaseModel describes the data, ConfigDict sets options, and Field adds limits.
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


# One date the student proposes.
class OptionIn(BaseModel):
    # The date and time, with its time zone, so it means the same moment for everyone.
    starts_at: AwareDatetime
    # The external committee members who said they can attend on this date.
    external_member_ids: list[int] = Field(default_factory=list, max_length=10)
    # Of those, the ones joining by Zoom. Only for a hybrid presentation; online means everyone joins by Zoom.
    external_online_ids: list[int] = Field(default_factory=list, max_length=10)

    # Rejects any field that isn't listed above.
    model_config = ConfigDict(extra="forbid")


# What the page sends to propose presentation dates.
class PresentationIn(BaseModel):
    # In person, online, or hybrid (a room, with a Zoom link for those joining online).
    mode: Literal["in_person", "online", "hybrid"]
    # A room for in person or hybrid, or a meeting link for online.
    location: str = Field(min_length=1, max_length=255)
    # The Zoom link for a hybrid presentation. Leave it out otherwise.
    meeting_link: str | None = Field(default=None, max_length=255)
    # 1 to 3 proposed dates.
    options: list[OptionIn] = Field(min_length=1, max_length=3)

    # Rejects any field that isn't listed above.
    model_config = ConfigDict(extra="forbid")


# What the page sends when the student chooses the date.
class DateChoiceIn(BaseModel):
    # The proposed date's id.
    option_id: int = Field(gt=0)

    # Rejects any field that isn't listed above.
    model_config = ConfigDict(extra="forbid")


# One committee member's answer for one date.
class ResponseOut(BaseModel):
    # The member's name.
    name: str
    # True if they can attend.
    available: bool
    # How they'll join: "in_person" or "online". Empty when they can't attend, or it wasn't given.
    attend_mode: Literal["in_person", "online"] | None = None


# One proposed date and the answers so far.
class OptionOut(BaseModel):
    # The option's id.
    id: int
    # The date and time.
    starts_at: datetime
    # True if the advisor confirmed this date.
    chosen: bool
    # The committee members' answers so far.
    responses: list[ResponseOut]
    # True if everyone on the committee, including the advisor, can attend, so the student can choose it.
    everyone_available: bool
    # The committee members who haven't answered for this date yet.
    waiting_for: list[str]


# The presentation shown in the submission popup.
class PresentationOut(BaseModel):
    # The presentation's id.
    id: int
    # 1 for the first attempt, 2 for the second.
    attempt: int
    # Where the scheduling is. "held" means the confirmed date has passed.
    status: Literal["awaiting_availability", "needs_new_dates", "scheduled", "held", "cancelled"]
    # In person, online, or hybrid.
    mode: Literal["in_person", "online", "hybrid"]
    # A room, or a meeting link for online.
    location: str
    # The Zoom link for a hybrid presentation. Empty otherwise.
    meeting_link: str | None = None
    # The confirmed date and time. Empty until the advisor confirms one.
    scheduled_at: datetime | None
    # The proposed dates, earliest first.
    options: list[OptionOut]


# An external committee member, so the student can enter which dates they can attend.
class ExternalMemberOut(BaseModel):
    # The member's row id.
    id: int
    # The member's name.
    name: str


# One student's presentation on the advisor's dashboard, with the stage it's at.
class AdvisorPresentationOut(BaseModel):
    # The student's id.
    student_id: int
    # The student's name.
    student_name: str
    # The milestone's id.
    milestone_id: int
    # The milestone's name.
    milestone_name: str
    # Where it is: waiting for dates, waiting for availability, new dates needed, upcoming, done, or waiting for a revision.
    stage: Literal["waiting_for_dates", "awaiting_availability", "needs_new_dates", "scheduled", "held", "revision_requested"]
    # The chosen date, once there is one.
    scheduled_at: datetime | None
    # In person, online or hybrid, once dates are proposed.
    mode: Literal["in_person", "online", "hybrid"] | None
    # The room or link, once dates are proposed.
    location: str | None
    # The Zoom link for a hybrid presentation. Empty otherwise.
    meeting_link: str | None = None
    # How many dates were proposed.
    option_count: int
    # "advisor" if the viewer advises this student and records the decision, or "member" if they're on the committee.
    role: Literal["advisor", "member"] = "advisor"


# A short version for the dashboard card.
class PresentationSummary(BaseModel):
    # Where the scheduling is, the same values as above.
    status: str
    # The confirmed date and time, if there is one.
    scheduled_at: datetime | None


# Everything the popup needs to show and propose presentation dates.
class PresentationState(BaseModel):
    # The current presentation for this attempt. Empty if no dates have been proposed.
    presentation: PresentationOut | None
    # True if the student can propose dates right now.
    can_propose: bool
    # Why the student can't propose dates, or what to do next. Empty when there's nothing to say.
    message: str | None
    # The earliest date the student may propose. Empty when they can't propose.
    earliest_at: datetime | None
    # The external members who need their availability entered by the student.
    external_members: list[ExternalMemberOut]
