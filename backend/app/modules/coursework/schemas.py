# coursework/schemas.py — THE DATA THE API ACCEPTS AND RETURNS FOR COURSEWORK.

# Literal limits a field to a fixed list of values.
from typing import Literal

# BaseModel describes the data, ConfigDict sets options, Field adds limits, and model_validator checks fields together.
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Term is the existing Spring/Fall choice from the users module.
from app.modules.users.models import Term

# The grades on the Graduate Bulletin's grade scale that a student can select.
Grade = Literal["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "E", "S", "U"]


# One course in the dropdown.
class CourseOut(BaseModel):
    # The course's id, which the frontend sends back when the student selects it.
    id: int
    # The course code, e.g. "CSI 503".
    code: str
    # The course name.
    title: str
    # The fewest credits it can be taken for.
    min_credits: int
    # The most credits it can be taken for.
    max_credits: int
    # The group it's shown under in the dropdown: core, theory, ai_ml, systems or dissertation. Empty = other courses.
    area: str | None

    # Allows this to be filled directly from a Course database row.
    model_config = ConfigDict(from_attributes=True)


# What the frontend sends when a student adds or edits a course.
class StudentCourseIn(BaseModel):
    # The selected course's id. Empty when the course is entered manually.
    course_id: int | None = Field(default=None, gt=0)
    # The code of a course that isn't on the list, e.g. "MAT 520".
    manual_code: str | None = Field(default=None, min_length=1, max_length=20)
    # The name of a course that isn't on the list.
    manual_title: str | None = Field(default=None, min_length=1, max_length=255)
    # The department of a course that isn't on the list: "cs" or "non_cs".
    manual_department: Literal["cs", "non_cs"] | None = None
    # True if a course that isn't on the list is independent study or research.
    manual_is_research: bool = False
    # The credits taken. 19 is the highest on the course list, and listed courses are also checked against their own range.
    credits: int = Field(gt=0, le=19)
    # The term it was taken: "spring" or "fall".
    term: Term
    # The year it was taken, limited to sensible values.
    year: int = Field(ge=2000, le=2100)
    # The grade from the list above. Empty = still in progress.
    grade: Grade | None = None

    # Rejects any field that isn't listed above, and trims spaces around text.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Checks the fields together after each one has passed its own check.
    @model_validator(mode="after")
    # This runs on every submitted form.
    def check_course_source(self):
        # True if any manual field was filled in.
        has_manual = bool(self.manual_code or self.manual_title or self.manual_department or self.manual_is_research)
        # A course can't be both selected and entered manually.
        if self.course_id is not None and has_manual:
            # Send this message back to the student.
            raise ValueError("Select a course from the list or enter one manually, not both.")
        # A manual course needs its code, name and department.
        if self.course_id is None and not (self.manual_code and self.manual_title and self.manual_department):
            # Send this message back to the student.
            raise ValueError("Select a course, or enter its code, name and department.")
        # Store manual codes the same way, so "mat  520" and "MAT 520" match.
        if self.manual_code:
            # Use capital letters and single spaces.
            self.manual_code = " ".join(self.manual_code.upper().split())
        # Return the checked form.
        return self


# One course the student has added, as shown in their list.
class StudentCourseOut(BaseModel):
    # This row's id, used to edit or delete it.
    id: int
    # The selected course's id. Empty for a manually entered course.
    course_id: int | None
    # The course code, e.g. "CSI 503".
    code: str
    # The course name.
    title: str
    # The fewest credits a listed course can be taken for, used by the edit form. Empty for a manual course.
    min_credits: int | None
    # The most credits a listed course can be taken for, used by the edit form. Empty for a manual course.
    max_credits: int | None
    # True if the student entered this course manually.
    is_manual: bool
    # A manual course's department: "cs" or "non_cs". Empty for a listed course.
    department: str | None
    # True if a manual course is independent study or research.
    is_research: bool
    # The credits taken.
    credits: int
    # The term it was taken.
    term: Term
    # The year it was taken.
    year: int
    # The grade. Empty = still in progress.
    grade: str | None


# The progress for one requirement group, shown as one progress bar.
class RequirementProgress(BaseModel):
    # The group's name, e.g. "Core".
    name: str
    # The credits that count toward this group so far.
    earned_credits: int
    # The credits this group needs.
    required_credits: int
    # True once the group's credits are all earned.
    complete: bool


# Everything the coursework page needs in one response.
class CourseworkOut(BaseModel):
    # The courses for the dropdown.
    courses: list[CourseOut]
    # The courses this student has added.
    my_courses: list[StudentCourseOut]
    # Core, the three breadth areas, electives and dissertation research.
    requirements: list[RequirementProgress]
    # Credits counted toward the 45 needed for coursework (everything except CSI 898).
    coursework_credits: int
    # The total coursework credits needed, which is 45.
    coursework_required: int
    # How much of the 45 credits is done, from 0 to 100.
    percent: int
    # The average grade across core and breadth courses. Empty = none graded yet.
    core_breadth_average: float | None
    # True if that average is B+ (3.3) or higher.
    core_breadth_average_met: bool
    # The average across all graded courses that count toward the degree. Empty = none graded yet.
    degree_gpa: float | None
    # True once CSI 790 has a B or better.
    csi_790_complete: bool
    # The last semester to pass CSI 790, e.g. "Fall 2028". Empty = the student's details aren't recorded.
    csi_790_deadline: str | None
    # True if that semester has passed and CSI 790 isn't complete.
    csi_790_overdue: bool
