# profile/schemas.py — THE DATA THE API ACCEPTS AND RETURNS FOR A STUDENT'S PROFILE.

# urlparse splits a web address into its parts, so it can be checked.
from urllib.parse import urlparse

# BaseModel describes the data, and the others add options and checks.
from pydantic import BaseModel, ConfigDict, Field, field_validator

# EnrollmentStatus and Term describe the student's read-only program details.
from app.modules.users.models import EnrollmentStatus, Term


# What the page sends when a student saves their profile. Email, GPA and other records can't be changed here.
class ProfileIn(BaseModel):
    # The student's name, which can't be empty.
    full_name: str = Field(min_length=1, max_length=255)
    # What they research.
    research_interests: str | None = Field(default=None, max_length=2000)
    # Their lab or research group.
    lab_name: str | None = Field(default=None, max_length=255)
    # Their education background.
    education: str | None = Field(default=None, max_length=2000)
    # A short biography.
    bio: str | None = Field(default=None, max_length=2000)
    # A link to their personal website.
    portfolio_url: str | None = Field(default=None, max_length=500)
    # A link to their GitHub profile.
    github_url: str | None = Field(default=None, max_length=500)
    # A link to their Google Scholar profile.
    scholar_url: str | None = Field(default=None, max_length=500)
    # A link to their LinkedIn profile.
    linkedin_url: str | None = Field(default=None, max_length=500)

    # Rejects any field that isn't listed above, and trims spaces around text.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Saves a blank optional field as empty.
    @field_validator("research_interests", "lab_name", "education", "bio", "portfolio_url", "github_url", "scholar_url", "linkedin_url")
    # This runs on each of those fields.
    @classmethod
    def blank_means_empty(cls, value):
        # An empty string becomes no value.
        return value or None

    # Checks every link.
    @field_validator("portfolio_url", "github_url", "scholar_url", "linkedin_url")
    # This runs on each of those fields.
    @classmethod
    def check_link(cls, value):
        # An empty link is fine.
        if value is None:
            # Nothing to check.
            return value
        # Split the link into its parts.
        parts = urlparse(value)
        # Only ordinary web links are allowed, which also blocks links that run code, such as "javascript:".
        if parts.scheme not in ("http", "https") or not parts.netloc:
            # Send this message back to the student.
            raise ValueError("Enter full links starting with https:// or http://.")
        # Return the checked link.
        return value


# What the page sends when a student uploads a picture.
class PictureIn(BaseModel):
    # The picture's contents as base64 text. 2.8 million characters is just above a 2 MB picture, and the backend checks the exact size.
    data_base64: str = Field(min_length=1, max_length=2_800_000)

    # Rejects any field that isn't listed above.
    model_config = ConfigDict(extra="forbid")


# What the profile page shows.
class ProfileOut(BaseModel):
    # The student's name.
    full_name: str
    # Their login email, shown but not editable.
    email: str
    # What they research.
    research_interests: str | None
    # Their lab or research group.
    lab_name: str | None
    # Their education background.
    education: str | None
    # A short biography.
    bio: str | None
    # A link to their personal website.
    portfolio_url: str | None
    # A link to their GitHub profile.
    github_url: str | None
    # A link to their Google Scholar profile.
    scholar_url: str | None
    # A link to their LinkedIn profile.
    linkedin_url: str | None
    # True if they've uploaded a picture.
    has_picture: bool
    # Their declared advisor's name, shown but not editable here.
    advisor_name: str | None
    # The term they started, shown but not editable.
    start_term: Term | None
    # The year they started, shown but not editable.
    start_year: int | None
    # Full-time or part-time, shown but not editable.
    enrollment_status: EnrollmentStatus | None
    # Whether they have advanced standing, shown but not editable.
    advanced_standing: bool | None
