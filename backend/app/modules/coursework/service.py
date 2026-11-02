# coursework/service.py — THE COURSEWORK RULES AND CALCULATION.
# Rules come from the UAlbany Graduate Bulletin. Progress is calculated on every request, never stored.

# date builds semester dates, and datetime gives today's date.
from datetime import date, datetime
# Decimal stores the GPA as an exact number, matching the users table's GPA column.
from decimal import Decimal
# SimpleNamespace builds a small course-like object for manually entered courses.
from types import SimpleNamespace
# ZoneInfo sets the time zone used for that date.
from zoneinfo import ZoneInfo

# HTTPException sends an error message back to the frontend.
from fastapi import HTTPException
# select builds database queries.
from sqlalchemy import select
# IntegrityError is raised when a row breaks a database rule, such as a duplicate.
from sqlalchemy.exc import IntegrityError
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# The two coursework tables.
from app.modules.coursework.models import Course, StudentCourse
# The data formats this module returns and accepts.
from app.modules.coursework.schemas import CourseOut, CourseworkOut, RequirementProgress, StudentCourseIn, StudentCourseOut
# The milestone tables, used to mark Coursework as in progress.
from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
# Records a status change with its exact time, and tells the student.
from app.modules.submissions.history import record_status_change
# The dashboard's semester functions, so deadlines are worked out the same way everywhere.
from app.modules.student.service import semester_index, semester_label
# EnrollmentStatus doubles deadlines for part-time students, Term sorts courses by date, and User is the logged-in student.
from app.modules.users.models import EnrollmentStatus, Term, User

# The grade points for each grade that earns graduate credit. C-, D+, D, E and U earn none.
GRADE_POINTS = {"A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7, "C+": 2.3, "C": 2.0}
# Grades that earn credit: the ones above, plus S (satisfactory).
CREDIT_GRADES = set(GRADE_POINTS) | {"S"}
# Grades that can count toward core and breadth. The bulletin treats S as a B or better.
B_OR_BETTER = {"A", "A-", "B+", "B", "S"}
# Courses the bulletin says can be repeated for credit. CSI 898 is added because its 15 credits need several registrations.
REPEATABLE = {"CSI 660", "CSI 661", "CSI 662", "CSI 663", "CSI 665", "CSI 666", "CSI 667", "CSI 668",
              "CSI 680", "CSI 694", "CSI 696", "CSI 697", "CSI 890", "CSI 898"}

# Credits needed for core.
CORE_CREDITS = 6
# Credits one breadth area needs. Any extra credits (CSI 518's fourth) go to electives.
BREADTH_AREA_CREDITS = 3
# Each breadth area's value in the courses table, with the name shown to students.
BREADTH_AREAS = {"theory": "Breadth: Theoretical CS", "ai_ml": "Breadth: AI & ML", "systems": "Breadth: Systems or CSI 518"}
# Credits needed for electives.
ELECTIVE_CREDITS = 30
# The most independent study or research credits that can count as electives.
MAX_RESEARCH_CREDITS = 15
# Credits needed for CSI 898.
DISSERTATION_CREDITS = 15
# Coursework credits: everything except CSI 898, which comes to 45.
COURSEWORK_CREDITS = CORE_CREDITS + BREADTH_AREA_CREDITS * len(BREADTH_AREAS) + ELECTIVE_CREDITS
# The core and breadth average that must be reached: B+.
MIN_CORE_BREADTH_AVERAGE = 3.3
# The last semester to pass CSI 790 for full-time students with advanced standing, from the bulletin.
CSI_790_SEMESTER_ADVANCED = 2
# The last semester to pass CSI 790 for full-time students without advanced standing, from the bulletin.
CSI_790_SEMESTER_REGULAR = 6


# Sorts rows by date: earliest year first, with Spring before Fall.
def _date_order(pair):
    # Each pair is one (StudentCourse, Course).
    student_course, _ = pair
    # Return the year, then 0 for Spring or 1 for Fall.
    return student_course.year, student_course.term == Term.FALL


# Keeps only the rows that count: they earned credit, and a repeat counts once unless repeatable.
def _counted_rows(rows):
    # The rows that are kept.
    kept = []
    # The best row so far for each course that can't be repeated, as {course id: row}.
    best = {}
    # Go through each of the student's rows.
    for pair in rows:
        # Split the pair into the student's row and the course.
        student_course, course = pair
        # Skip courses in progress and grades that earn no credit.
        if student_course.grade not in CREDIT_GRADES:
            # Move on to the next row.
            continue
        # A repeatable course always counts.
        if course.code in REPEATABLE:
            # Keep this row.
            kept.append(pair)
        # Otherwise, keep this row only if it's the first or has a higher grade (the bulletin's rule).
        elif course.id not in best or _points(student_course.grade) > _points(best[course.id][0].grade):
            # Remember this as the best row for the course.
            best[course.id] = pair
    # Join both lists and sort them by date.
    return sorted(kept + list(best.values()), key=_date_order)


# Returns a grade's points for comparing grades. S has no points, so it's treated as a B.
def _points(grade):
    # Look up the grade, using 3.0 if it isn't in the table.
    return GRADE_POINTS.get(grade, 3.0)


# Returns the credit-weighted average of the rows with letter grades. Returns None if there are none.
def _average(rows):
    # Keep only letter grades, because S has no grade points on the bulletin's scale.
    graded = [(student_course.credits, GRADE_POINTS[student_course.grade])
              for student_course, _ in rows if student_course.grade in GRADE_POINTS]
    # Add up the credits.
    total_credits = sum(credits for credits, _ in graded)
    # Return None if there's nothing to average, otherwise points ÷ credits, to 2 decimals.
    return round(sum(credits * points for credits, points in graded) / total_credits, 2) if total_credits else None


# Works out the progress from a student's rows, given as a list of (StudentCourse, Course).
def calculate_progress(rows):
    # Keep only the rows that count, sorted by date.
    counted = _counted_rows(rows)
    # Credits that go to electives, not counting research courses.
    elective_credits = 0
    # Independent study or research credits, which are limited later.
    research_credits = 0
    # Core courses with a B or better.
    core_rows = []
    # The course filling each breadth area, as {area: row}.
    breadth_rows = {}
    # Credits taken of CSI 898.
    dissertation_credits = 0

    # Put each counted row into the right group.
    for pair in counted:
        # Split the pair into the student's row and the course.
        student_course, course = pair
        # CSI 898 has its own group.
        if course.area == "dissertation":
            # Add its credits to that group.
            dissertation_credits += student_course.credits
        # A core course with a B or better counts as core.
        elif course.area == "core" and student_course.grade in B_OR_BETTER:
            # Add it to the core list.
            core_rows.append(pair)
        # The first course with a B or better in an open breadth area fills that area.
        elif course.area in BREADTH_AREAS and course.area not in breadth_rows and student_course.grade in B_OR_BETTER:
            # Record it as this area's course.
            breadth_rows[course.area] = pair
            # Any credits above 3 (CSI 518's fourth) go to electives.
            elective_credits += student_course.credits - BREADTH_AREA_CREDITS
        # Research courses that reach this point count as research electives.
        elif course.is_research:
            # Add them to the research total.
            research_credits += student_course.credits
        # Everything else is an elective.
        else:
            # Add it to the elective total.
            elective_credits += student_course.credits

    # Add up core credits, with no more than the group needs.
    core_earned = min(sum(student_course.credits for student_course, _ in core_rows), CORE_CREDITS)
    # Add electives and allowed research credits, with no more than the group needs.
    electives_earned = min(elective_credits + min(research_credits, MAX_RESEARCH_CREDITS), ELECTIVE_CREDITS)

    # Build one progress bar per group, starting with core.
    requirements = [RequirementProgress(name="Core", earned_credits=core_earned, required_credits=CORE_CREDITS,
                                        complete=core_earned >= CORE_CREDITS)]
    # Add one bar per breadth area.
    for area, name in BREADTH_AREAS.items():
        # An area is earned once a course fills it.
        earned = BREADTH_AREA_CREDITS if area in breadth_rows else 0
        # Add this area's bar.
        requirements.append(RequirementProgress(name=name, earned_credits=earned, required_credits=BREADTH_AREA_CREDITS,
                                                complete=earned >= BREADTH_AREA_CREDITS))
    # Add the electives bar.
    requirements.append(RequirementProgress(name="Electives", earned_credits=electives_earned, required_credits=ELECTIVE_CREDITS,
                                            complete=electives_earned >= ELECTIVE_CREDITS))
    # Add up the credits for the 45-credit total, before adding the separate CSI 898 bar.
    coursework_credits = sum(requirement.earned_credits for requirement in requirements)
    # Limit CSI 898 to the credits it needs.
    dissertation_earned = min(dissertation_credits, DISSERTATION_CREDITS)
    # Add the CSI 898 bar, which doesn't count toward the 45.
    requirements.append(RequirementProgress(name="Dissertation research (CSI 898)", earned_credits=dissertation_earned,
                                            required_credits=DISSERTATION_CREDITS, complete=dissertation_earned >= DISSERTATION_CREDITS))
    # Average the courses counting toward core and breadth.
    core_breadth_average = _average(core_rows + list(breadth_rows.values()))
    # Return all the calculated values, which become part of the API response.
    return dict(requirements=requirements, coursework_credits=coursework_credits, coursework_required=COURSEWORK_CREDITS,
                percent=round(coursework_credits * 100 / COURSEWORK_CREDITS), core_breadth_average=core_breadth_average,
                core_breadth_average_met=core_breadth_average is not None and core_breadth_average >= MIN_CORE_BREADTH_AVERAGE,
                degree_gpa=_average(counted))


# Loads a student's rows as (StudentCourse, course). A manual row gets a course-like object, so the rules treat both the same.
def _load_rows(db: Session, student: User):
    # Load this student's rows with their listed course, if any, using the student from the login token.
    results = db.execute(select(StudentCourse, Course).outerjoin(Course).where(StudentCourse.student_id == student.id)
                         # Show the oldest courses first.
                         .order_by(StudentCourse.year, StudentCourse.term, StudentCourse.id))
    # The list being built.
    rows = []
    # Go through each result.
    for row, course in results:
        # A row with no listed course was entered manually.
        if course is None:
            # Build its course details. With no area, it can only count as an elective.
            course = SimpleNamespace(id=f"manual:{row.manual_code}", code=row.manual_code, title=row.manual_title,
                                     min_credits=None, max_credits=None, area=None, is_research=row.manual_is_research)
        # Add the row with its course.
        rows.append((row, course))
    # Return the finished list.
    return rows


# Explains each course that counts differently than a student might expect, as {row id: note}.
# It follows the same order and rules as calculate_progress, so the notes match the credits.
def course_notes(rows) -> dict:
    # The notes so far.
    notes = {}
    # The rows that count toward the degree, in date order.
    counted = _counted_rows(rows)
    # Their ids, so the rows left out can be found.
    counted_ids = {row.id for row, _ in counted}
    # Go through the rows left out.
    for row, course in rows:
        # A course in progress has no grade yet, so there's nothing to explain.
        if row.grade is None or row.id in counted_ids:
            # Move on to the next row.
            continue
        # Explain why this one was left out.
        notes[row.id] = ("Earns no graduate credit, because the grade is below C." if row.grade not in CREDIT_GRADES
                         # The only other reason is a repeat of a course that can't be repeated for credit.
                         else f"Not counted, because another attempt at {course.code} has a higher grade.")
    # The breadth areas filled so far.
    filled = set()
    # The independent study or research credits so far.
    research_credits = 0
    # Go through the counted rows in the same order as the calculation.
    for row, course in counted:
        # True if this grade is high enough for core and breadth.
        high_enough = row.grade in B_OR_BETTER
        # A core course below a B counts as an elective instead.
        if course.area == "core" and not high_enough:
            # Explain the rule.
            notes[row.id] = "Doesn't count toward Core, which needs a B or better. Counted as an elective."
        # Handle a course from a breadth area.
        elif course.area in BREADTH_AREAS:
            # The area's name, for the messages.
            area_name = BREADTH_AREAS[course.area]
            # A grade below a B can't fill an area.
            if not high_enough:
                # Explain the rule.
                notes[row.id] = f"Doesn't count toward {area_name}, which needs a B or better. Counted as an elective."
            # An earlier course already filled this area.
            elif course.area in filled:
                # Explain where it went.
                notes[row.id] = f"{area_name} is already filled, so this counts as an elective."
            # This course fills the area.
            else:
                # Remember the area is filled.
                filled.add(course.area)
                # Only CSI 518 has more credits than the area needs.
                if row.credits > BREADTH_AREA_CREDITS:
                    # Explain the split.
                    notes[row.id] = f"{BREADTH_AREA_CREDITS} credits count toward {area_name}, and the other {row.credits - BREADTH_AREA_CREDITS} toward electives."
        # Handle an independent study or research course. CSI 898 has its own group, so it's left out here.
        elif course.is_research and course.area != "dissertation":
            # Add its credits to the total.
            research_credits += row.credits
            # Explain if this course goes past the limit.
            if research_credits > MAX_RESEARCH_CREDITS:
                # State the rule.
                notes[row.id] = f"Only {MAX_RESEARCH_CREDITS} credits of independent study or research can count, so some or all of this course doesn't."
    # Return the notes.
    return notes


# Works out the CSI 790 deadline, and whether it's done or overdue, the same way as the dashboard's other deadlines.
def _csi_790_status(student: User, rows):
    # CSI 790 is done once it has a B or better, the same as any core course.
    complete = any(course.code == "CSI 790" and row.grade in B_OR_BETTER for row, course in rows)
    # The deadline can only be worked out when all of the student's details are recorded.
    known = None not in (student.advanced_standing, student.enrollment_status, student.start_term, student.start_year)
    # Without those details, there's no deadline to show.
    if not known:
        # Return the status with no deadline.
        return dict(csi_790_complete=complete, csi_790_deadline=None, csi_790_overdue=False)
    # Choose the deadline from the student's advanced standing.
    semesters = CSI_790_SEMESTER_ADVANCED if student.advanced_standing else CSI_790_SEMESTER_REGULAR
    # Part-time students get double the time.
    if student.enrollment_status == EnrollmentStatus.PART_TIME:
        # Double the deadline.
        semesters *= 2
    # Number the student's first semester, the same way as the dashboard.
    start = student.start_year * 2 + (student.start_term == Term.FALL)
    # Number the student's last allowed semester.
    last = start + semesters - 1
    # Return the status. It's overdue if the last allowed semester has passed and CSI 790 isn't done.
    return dict(csi_790_complete=complete, csi_790_deadline=semester_label(last),
                csi_790_overdue=not complete and semester_index(_today()) > last)


# Builds the whole coursework page's data for one student.
def get_coursework(db: Session, student: User) -> CourseworkOut:
    # Load the dropdown's courses in code order.
    courses = list(db.scalars(select(Course).order_by(Course.code)))
    # Load this student's rows, each with its course.
    rows = _load_rows(db, student)
    # Explain any course that counts differently than expected.
    notes = course_notes(rows)
    # Combine the course list, the student's courses and the calculated progress.
    return CourseworkOut(
        # Convert each course for the dropdown.
        courses=[CourseOut.model_validate(course) for course in courses],
        # Combine each student row with its course's details.
        my_courses=[StudentCourseOut(id=row.id, course_id=row.course_id, code=course.code, title=course.title,
                                     min_credits=course.min_credits, max_credits=course.max_credits,
                                     is_manual=row.course_id is None, department=row.manual_department,
                                     is_research=row.manual_is_research,
                                     credits=row.credits, term=row.term, year=row.year, grade=row.grade, note=notes.get(row.id))
                    for row, course in rows],
        # Add the calculated values.
        **calculate_progress(rows),
        # Add the CSI 790 deadline.
        **_csi_790_status(student, rows),
    )


# Returns today's date in New York time, the same as the rest of the app.
def _today() -> date:
    # Read the current date.
    return datetime.now(ZoneInfo("America/New_York")).date()


# Checks the semester has started, and that a grade is only entered once the semester has ended.
def _check_semester(body: StudentCourseIn) -> None:
    # Spring runs January 1 to May 31. Fall runs June 1 to December 31.
    start, end = ((date(body.year, 1, 1), date(body.year, 5, 31)) if body.term == Term.SPRING
                  # There's no summer term, so Fall starts the day after Spring ends.
                  else (date(body.year, 6, 1), date(body.year, 12, 31)))
    # The semester's name, for the messages below.
    semester = f"{body.term.value.capitalize()} {body.year}"
    # A semester that hasn't started can't be added.
    if _today() < start:
        # 422 means the submitted data isn't valid.
        raise HTTPException(422, f"{semester} hasn't started yet, so you can't add a course for it.")
    # A running semester can only be in progress.
    if body.grade is not None and _today() < end:
        # Tell the student when they can enter the grade.
        raise HTTPException(422, f"You can enter a grade for {semester} starting {end:%B} {end.day}, {end.year}. Until then, select In progress.")


# Checks the semester and the course, including that a manual course isn't on the list.
def _check_course(db: Session, body: StudentCourseIn) -> None:
    # Check the semester's dates first.
    _check_semester(body)
    # Check a manually entered course.
    if body.course_id is None:
        # Ignore spaces when comparing, so "CSI503" matches "CSI 503".
        manual_code = body.manual_code.replace(" ", "")
        # Go through the code of every listed course.
        for code in db.scalars(select(Course.code)):
            # A listed course must be selected, so its core and breadth rules apply.
            if code.replace(" ", "") == manual_code:
                # 422 means the submitted data isn't valid.
                raise HTTPException(422, f"{code} is on the course list. Select it from the list.")
        # A manual course has no other checks here.
        return
    # Find the selected course.
    course = db.get(Course, body.course_id)
    # Stop if it isn't on the course list.
    if course is None:
        # 422 means the submitted data isn't valid.
        raise HTTPException(422, "Choose a course from the list.")
    # Stop if the credits are outside this course's range.
    if not course.min_credits <= body.credits <= course.max_credits:
        # Tell the student the allowed range.
        raise HTTPException(422, f"{course.code} can be taken for {course.min_credits} to {course.max_credits} credits.")


# Saves the course change and updates the Coursework milestone together.
def _save(db: Session, student: User) -> None:
    # Try to send the course change to the database.
    try:
        # Send it without finishing the save, so the calculation below can see it.
        db.flush()
    # The database rejected a duplicate course in the same term.
    except IntegrityError:
        # Cancel the failed save.
        db.rollback()
        # 409 means this conflicts with existing data.
        raise HTTPException(409, "You already added this course for that term.")
    # Update the milestone from the student's new total.
    _update_milestone(db, student)
    # Update the student's stored GPA from their courses.
    update_gpa(db, student)
    # Finish the save, so all the changes succeed together.
    db.commit()


# Sets the student's stored GPA from their courses, so every page shows the same value. It doesn't save by itself.
def update_gpa(db: Session, student: User) -> None:
    # Calculate the GPA from the student's courses.
    gpa = calculate_progress(_load_rows(db, student))["degree_gpa"]
    # Store it as an exact number, or empty if the student has no courses with a letter grade yet.
    student.gpa = Decimal(str(gpa)) if gpa is not None else None


# Sets the Coursework milestone from the calculation: Approved when the requirements are met, otherwise In progress.
def _update_milestone(db: Session, student: User) -> None:
    # Find the Coursework milestone.
    milestone = db.scalar(select(Milestone).where(Milestone.name == "Coursework"))
    # Do nothing if it hasn't been set up.
    if milestone is None:
        # Leave without changing anything.
        return
    # Find this student's progress row for it.
    progress = db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == student.id,
                                                        StudentMilestone.milestone_id == milestone.id))
    # A missing row means not started, so create one.
    if progress is None:
        # Build the new progress row.
        progress = StudentMilestone(student_id=student.id, milestone_id=milestone.id)
        # Add it to this save.
        db.add(progress)
    # Work out the student's progress, including the change just made.
    result = calculate_progress(_load_rows(db, student))
    # The bulletin requires a B+ core and breadth average. None means those courses have no letter grades to average.
    average_ok = result["core_breadth_average"] is None or result["core_breadth_average_met"]
    # Remember whether it was already approved, so only a real change is recorded.
    was_approved = progress.status == MilestoneStatus.APPROVED
    # Check for all 45 credits and the required average.
    if result["coursework_credits"] >= COURSEWORK_CREDITS and average_ok:
        # Record today's date the first time it's approved, keeping any earlier date.
        if not was_approved or progress.completed_on is None:
            # Use today's date as the approval date.
            progress.completed_on = _today()
        # Mark the milestone as approved.
        progress.status = MilestoneStatus.APPROVED
        # A new approval goes in the history, and the student is told.
        if not was_approved:
            # Record it, with the student as the person whose change caused it.
            record_status_change(db, student.id, milestone.id, MilestoneStatus.APPROVED, student.id)
    # Otherwise, including after a course is edited or deleted, it isn't complete.
    else:
        # Mark the milestone as in progress.
        progress.status = MilestoneStatus.IN_PROGRESS
        # Clear the approval date.
        progress.completed_on = None
        # Losing an approval goes in the history, and the student is told.
        if was_approved:
            # Record it, with the student as the person whose change caused it.
            record_status_change(db, student.id, milestone.id, MilestoneStatus.IN_PROGRESS, student.id)


# Adds a course for the logged-in student.
def add_course(db: Session, student: User, body: StudentCourseIn) -> CourseworkOut:
    # Check the course and credits first.
    _check_course(db, body)
    # Add the row, using the student from the login token.
    db.add(StudentCourse(student_id=student.id, **body.model_dump()))
    # Save the course and update the milestone together.
    _save(db, student)
    # Return the updated page data.
    return get_coursework(db, student)


# Finds one of this student's rows, so a student can't reach another student's courses.
def _get_own_row(db: Session, student: User, row_id: int) -> StudentCourse:
    # Look for a row with this id that belongs to this student.
    row = db.scalar(select(StudentCourse).where(StudentCourse.id == row_id, StudentCourse.student_id == student.id))
    # Stop if there isn't one.
    if row is None:
        # 404 means not found.
        raise HTTPException(404, "Course not found. Refresh the page.")
    # Return the row.
    return row


# Edits one of the logged-in student's courses.
def update_course(db: Session, student: User, row_id: int, body: StudentCourseIn) -> CourseworkOut:
    # Make sure the row belongs to this student.
    row = _get_own_row(db, student, row_id)
    # Check the new course and credits.
    _check_course(db, body)
    # Go through each submitted field.
    for field, value in body.model_dump().items():
        # Copy the new value onto the row.
        setattr(row, field, value)
    # Save the course and update the milestone together.
    _save(db, student)
    # Return the updated page data.
    return get_coursework(db, student)


# Removes one of the logged-in student's courses.
def delete_course(db: Session, student: User, row_id: int) -> CourseworkOut:
    # Make sure the row belongs to this student, then mark it for deletion.
    db.delete(_get_own_row(db, student, row_id))
    # Save the deletion and update the milestone together.
    _save(db, student)
    # Return the updated page data.
    return get_coursework(db, student)
