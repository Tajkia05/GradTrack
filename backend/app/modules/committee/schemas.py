# committee/schemas.py — THE DATA THE API ACCEPTS AND RETURNS FOR A STUDENT'S COMMITTEE.

# date is the day an invitation was sent.
from datetime import date

# BaseModel describes the data, ConfigDict sets options, Field adds limits, and model_validator checks fields together.
from pydantic import BaseModel, ConfigDict, Field, model_validator


# One faculty member the student can invite.
class FacultyOption(BaseModel):
    # The faculty member's user id, which the frontend sends back when inviting them.
    id: int
    # Their name.
    full_name: str
    # Their department. Empty = not recorded, so they don't count as CS.
    department: str | None


# What the frontend sends to add a person: a faculty_id, or an external member's name and affiliation.
class CommitteeInvite(BaseModel):
    # The faculty member being invited. Empty for an external member.
    faculty_id: int | None = Field(default=None, gt=0)
    # An external member's name.
    external_name: str | None = Field(default=None, min_length=1, max_length=255)
    # An external member's university or company.
    external_affiliation: str | None = Field(default=None, min_length=1, max_length=255)

    # Rejects any field that isn't listed above, and trims spaces around text.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Checks the fields together after each one has passed its own check.
    @model_validator(mode="after")
    # This runs on every submitted form.
    def check_member_type(self):
        # True if any external field was filled in.
        has_external = bool(self.external_name or self.external_affiliation)
        # A person can't be both a faculty member and an external member.
        if self.faculty_id is not None and has_external:
            # Send this message back to the student.
            raise ValueError("Choose a faculty member or enter an external member, not both.")
        # An external member needs a name and an affiliation.
        if self.faculty_id is None and not (self.external_name and self.external_affiliation):
            # Send this message back to the student.
            raise ValueError("Choose a faculty member, or enter an external member's name and affiliation.")
        # Return the checked form.
        return self


# One person on the committee, as shown in the list.
class CommitteeMemberOut(BaseModel):
    # This row's id, used to remove the person. Empty for the advisor, who has no row.
    id: int | None
    # The person's name.
    name: str
    # Their department or, for an external member, their affiliation.
    detail: str | None
    # True for the advisor, who is the committee chair.
    is_chair: bool
    # True for someone with no GradTrack account.
    is_external: bool
    # True if they count toward the 3 CS members.
    is_cs: bool
    # "pending", "approved" or "declined".
    status: str
    # The day they were added. Empty for the advisor.
    invited_on: date | None
    # True if the student can remove them right now.
    can_remove: bool


# Everything the committee popup needs in one response.
class CommitteeOut(BaseModel):
    # False until the student has declared an advisor, who must come first.
    advisor_declared: bool
    # Everyone on the committee, with the chair first.
    members: list[CommitteeMemberOut]
    # The faculty members who can still be invited.
    faculty_options: list[FacultyOption]
    # How many members have approved, including the chair.
    approved_count: int
    # How many approved members are needed, which is 4.
    required_members: int
    # How many approved members are from CS.
    cs_count: int
    # How many approved CS members are needed, which is 3.
    required_cs: int
    # True once both requirements are met.
    complete: bool
