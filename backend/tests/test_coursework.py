# Tests for coursework. Run from backend: python -m unittest discover -s tests -v
# All data lives in an isolated in-memory database; Neon is never used.

# unittest is Python's built-in test tool.
import unittest
# date sets the pretend "today" for these tests.
from datetime import date
# Decimal is how the users table returns a GPA.
from decimal import Decimal
# patch replaces a function during a test.
from unittest.mock import patch

# select builds database queries.
from sqlalchemy import select

# Reuse the same test users and milestones as the dashboard tests.
import test_student_dashboard as fixtures
# The coursework tables.
from app.modules.coursework.models import Course, StudentCourse
# The milestone statuses and each student's milestone progress.
from app.modules.milestones.models import MilestoneStatus, StudentMilestone
# The notifications table.
from app.modules.notifications.models import Notification
# The Spring/Fall choice.
from app.modules.users.models import Term

# The courses used in these tests: (id, code, min credits, max credits, area, is research).
COURSES = [
    (1, "CSI 503", 3, 3, "core", False),  # Core.
    (2, "CSI 790", 3, 3, "core", False),  # Core.
    (3, "CSI 509", 3, 3, "theory", False),  # Breadth: Theoretical CS.
    (4, "CSI 535", 3, 3, "ai_ml", False),  # Breadth: AI & ML.
    (5, "CSI 536", 3, 3, "ai_ml", False),  # A second AI & ML course, which should become an elective.
    (6, "CSI 508", 3, 3, "systems", False),  # Breadth: Systems.
    (7, "CSI 518", 4, 4, "systems", False),  # Breadth: Systems, worth 4 credits.
    (8, "CSI 898", 1, 12, "dissertation", True),  # Dissertation research.
    (9, "CSI 890", 3, 19, None, True),  # Elective, independent study.
    (10, "CSI 502", 3, 3, None, False),  # Elective.
    (11, "CSI 511", 3, 3, None, False),  # Elective.
    (12, "CSI 517", 3, 3, None, False),  # Elective.
    (13, "CSI 520", 3, 3, None, False),  # Elective.
    (14, "CSI 523", 3, 3, None, False),  # Elective.
]
# The Coursework milestone's id in the shared test data.
COURSEWORK = 1


# All the coursework tests.
class CourseworkTests(unittest.TestCase):
    # Reuse the dashboard tests' helper that builds a request's login header.
    headers = fixtures.DashboardTests.headers
    # Reuse the dashboard tests' helper that creates a test student.
    student = staticmethod(fixtures.DashboardTests.student)
    # Reuse the dashboard tests' helper that adds a milestone progress row.
    progress = fixtures.DashboardTests.progress

    # Runs before every test.
    def setUp(self):
        # Build the shared users and milestones.
        fixtures.DashboardTests.setUp(self)
        # Set up a pretend "today", so these tests give the same result on any real date.
        today_patch = patch("app.modules.coursework.service._today", return_value=date(2026, 11, 1))
        # Turn it on, and keep it so a test can change the date.
        self.today = today_patch.start()
        # Turn it off when the test ends.
        self.addCleanup(today_patch.stop)
        # Go through the test courses.
        for course_id, code, low, high, area, research in COURSES:
            # Add each one to the course list.
            self.db.add(Course(id=course_id, code=code, title=code, min_credits=low, max_credits=high,
                               area=area, is_research=research))
        # Save the course list.
        self.db.commit()

    # Adds a course for a student through the API, and returns the response.
    def add(self, course_id, credits=3, grade="A", year=2025, term="fall", user=None):
        # Lisa is the default student.
        return self.client.post("/api/students/me/courses", headers=self.headers(user or self.lisa),
                                json=dict(course_id=course_id, credits=credits, term=term, year=year, grade=grade))

    # Finds one progress bar in a response by its name.
    def bar(self, data, name):
        # Return the first bar whose name starts with this text.
        return next(item for item in data["requirements"] if item["name"].startswith(name))

    # Returns a student's Coursework milestone row, re-read from the database.
    def milestone(self, student_id):
        # Discard cached rows so the latest values are read.
        self.db.expire_all()
        # Find the row for this student and the Coursework milestone.
        return self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == student_id,
                                                             StudentMilestone.milestone_id == COURSEWORK))

    # Gives Lisa 42 credits directly, so one more course through the API reaches 45.
    def nearly_complete(self, grade="A"):
        # Courses for core, breadth and electives, with one left out for the test to add.
        for course_id in (1, 2, 3, 4, 6, 10, 11, 12, 13):
            # Add each 3-credit course directly to the database.
            self.db.add(StudentCourse(student_id=self.lisa.id, course_id=course_id, credits=3, term=Term.SPRING, year=2024, grade=grade))
        # Add 15 credits of independent study, which is the most that can count.
        self.db.add(StudentCourse(student_id=self.lisa.id, course_id=9, credits=15, term=Term.SPRING, year=2024, grade=grade))
        # Save these rows.
        self.db.commit()

    # Only students can use the coursework endpoints.
    def test_only_students_can_use_it(self):
        # A faculty member tries to read the page.
        response = self.client.get("/api/students/me/coursework", headers=self.headers(self.faculty))
        # The request is refused.
        self.assertEqual(response.status_code, 403)

    # The page returns the course list for the dropdown.
    def test_page_lists_courses_for_the_dropdown(self):
        # Lisa opens the page.
        data = self.client.get("/api/students/me/coursework", headers=self.headers(self.lisa)).json()
        # Every test course is listed.
        self.assertEqual(len(data["courses"]), len(COURSES))
        # Lisa hasn't added any courses yet.
        self.assertEqual(data["my_courses"], [])

    # A graded course counts toward its group and the total.
    def test_adding_a_course_updates_progress(self):
        # Lisa adds CSI 503 with an A.
        response = self.add(1)
        # The course is created.
        self.assertEqual(response.status_code, 201)
        # Read the response data.
        data = response.json()
        # Core now has 3 credits.
        self.assertEqual(self.bar(data, "Core")["earned_credits"], 3)
        # The total now has 3 of 45 credits.
        self.assertEqual((data["coursework_credits"], data["coursework_required"]), (3, 45))
        # 3 of 45 is 7%.
        self.assertEqual(data["percent"], 7)

    # A course without a grade is in progress, so it doesn't count.
    def test_course_in_progress_does_not_count(self):
        # Lisa adds a course with no grade.
        data = self.add(1, grade=None).json()
        # It appears in her list.
        self.assertEqual(len(data["my_courses"]), 1)
        # It adds no credits.
        self.assertEqual(data["coursework_credits"], 0)

    # Adding a course moves a not-started milestone to in progress.
    def test_first_course_marks_milestone_in_progress(self):
        # Remove Lisa's existing Coursework row, so she starts as not started.
        self.db.delete(self.milestone(self.lisa.id))
        # Save the removal.
        self.db.commit()
        # Lisa adds a course.
        self.add(1)
        # The milestone is now in progress.
        self.assertEqual(self.milestone(self.lisa.id).status, MilestoneStatus.IN_PROGRESS)

    # Credits outside the course's range are refused.
    def test_credits_must_fit_the_course(self):
        # CSI 503 is a 3-credit course, so 4 isn't allowed.
        self.assertEqual(self.add(1, credits=4).status_code, 422)

    # A course must be on the course list.
    def test_unknown_course_is_refused(self):
        # No course has this id.
        self.assertEqual(self.add(999).status_code, 422)

    # A grade must be on the bulletin's scale.
    def test_unknown_grade_is_refused(self):
        # F isn't on the graduate scale.
        self.assertEqual(self.add(1, grade="F").status_code, 422)

    # The same course can't be added twice in one term, but can be in a later term.
    def test_duplicates_are_refused_but_repeats_are_allowed(self):
        # The first time works.
        self.assertEqual(self.add(1, grade="B-").status_code, 201)
        # The same term again is refused.
        self.assertEqual(self.add(1, grade="B-").status_code, 409)
        # A later year works.
        self.assertEqual(self.add(1, grade="A", year=2024).status_code, 201)

    # A repeated course counts once, using the higher grade.
    def test_repeated_course_counts_once_with_higher_grade(self):
        # Lisa earns a B- first.
        self.add(1, grade="B-", year=2024)
        # She repeats the course and earns an A.
        data = self.add(1, grade="A", year=2025).json()
        # Only 3 credits count, not 6.
        self.assertEqual(data["coursework_credits"], 3)
        # The degree GPA uses the higher grade.
        self.assertEqual(data["degree_gpa"], 4.0)

    # Core and breadth need a B or better.
    def test_core_needs_b_or_better(self):
        # Lisa earns a B- in a core course.
        data = self.add(1, grade="B-").json()
        # It doesn't count toward core.
        self.assertEqual(self.bar(data, "Core")["earned_credits"], 0)

    # Grades that earn no graduate credit don't count anywhere.
    def test_no_credit_grades_do_not_count(self):
        # Lisa earns an E.
        data = self.add(10, grade="E").json()
        # It adds no credits.
        self.assertEqual(data["coursework_credits"], 0)
        # It isn't included in the degree GPA.
        self.assertIsNone(data["degree_gpa"])

    # CSI 518 gives 3 credits to breadth and its fourth to electives.
    def test_csi_518_fourth_credit_goes_to_electives(self):
        # Lisa takes CSI 518 for 4 credits.
        data = self.add(7, credits=4).json()
        # The Systems area gets 3.
        self.assertEqual(self.bar(data, "Breadth: Systems")["earned_credits"], 3)
        # Electives get 1.
        self.assertEqual(self.bar(data, "Electives")["earned_credits"], 1)

    # A second course from a filled breadth area becomes an elective.
    def test_second_course_in_an_area_is_an_elective(self):
        # The first AI & ML course fills the area.
        self.add(4, year=2024)
        # The second one is added later.
        data = self.add(5).json()
        # The area stays at 3 credits.
        self.assertEqual(self.bar(data, "Breadth: AI")["earned_credits"], 3)
        # The second course counts as an elective.
        self.assertEqual(self.bar(data, "Electives")["earned_credits"], 3)

    # At most 15 independent study or research credits count as electives.
    def test_research_credits_stop_at_15(self):
        # Lisa takes 19 credits of independent study.
        data = self.add(9, credits=19, grade="S").json()
        # Only 15 count.
        self.assertEqual(self.bar(data, "Electives")["earned_credits"], 15)

    # CSI 898 has its own bar and stays out of the 45.
    def test_csi_898_is_separate_from_the_45(self):
        # Lisa takes 12 credits of CSI 898.
        data = self.add(8, credits=12, grade="S").json()
        # Its own bar shows 12.
        self.assertEqual(self.bar(data, "Dissertation")["earned_credits"], 12)
        # None of them count toward the 45.
        self.assertEqual(data["coursework_credits"], 0)

    # A student can't change another student's course.
    def test_cannot_edit_or_delete_another_students_course(self):
        # Lisa adds a course and its row id is read.
        row_id = self.add(1).json()["my_courses"][0]["id"]
        # The new values Sam tries to send.
        body = dict(course_id=1, credits=3, term="fall", year=2025, grade="E")
        # Sam tries to edit it, and it isn't found.
        self.assertEqual(self.client.put(f"/api/students/me/courses/{row_id}", headers=self.headers(self.sam), json=body).status_code, 404)
        # Sam tries to delete it, and it isn't found.
        self.assertEqual(self.client.delete(f"/api/students/me/courses/{row_id}", headers=self.headers(self.sam)).status_code, 404)

    # Editing a course updates the progress.
    def test_editing_a_course_updates_progress(self):
        # Lisa adds a course that's still in progress.
        row_id = self.add(1, grade=None).json()["my_courses"][0]["id"]
        # The same course, now with a grade.
        body = dict(course_id=1, credits=3, term="fall", year=2025, grade="A")
        # She edits it.
        data = self.client.put(f"/api/students/me/courses/{row_id}", headers=self.headers(self.lisa), json=body).json()
        # It now counts.
        self.assertEqual(data["coursework_credits"], 3)

    # The milestone is approved automatically at 45 credits, with the required average.
    def test_reaching_45_credits_approves_the_milestone(self):
        # Lisa has 42 credits.
        self.nearly_complete()
        # The last course takes her to 45.
        data = self.add(14).json()
        # The total is complete.
        self.assertEqual((data["coursework_credits"], data["percent"]), (45, 100))
        # Read her milestone.
        milestone = self.milestone(self.lisa.id)
        # It's approved.
        self.assertEqual(milestone.status, MilestoneStatus.APPROVED)
        # The approval date is recorded.
        self.assertIsNotNone(milestone.completed_on)
        # The student is told, with the date and time.
        self.assertIn("Coursework was completed on",self.db.scalars(select(Notification).where(Notification.user_id == self.lisa.id)).all()[-1].message)

    # 45 credits aren't enough if the core and breadth average is below B+.
    def test_low_average_does_not_approve_the_milestone(self):
        # Lisa has 42 credits, all with a B, which is below the B+ average.
        self.nearly_complete(grade="B")
        # The last course takes her to 45.
        data = self.add(14, grade="B").json()
        # She has all the credits.
        self.assertEqual(data["coursework_credits"], 45)
        # The average requirement isn't met.
        self.assertFalse(data["core_breadth_average_met"])
        # The milestone stays in progress.
        self.assertEqual(self.milestone(self.lisa.id).status, MilestoneStatus.IN_PROGRESS)

    # Dropping below 45 credits undoes the approval.
    def test_deleting_a_course_undoes_the_approval(self):
        # Lisa has 42 credits.
        self.nearly_complete()
        # The last course approves the milestone, and its row is found.
        row = next(item for item in self.add(14).json()["my_courses"] if item["course_id"] == 14)
        # She deletes that course.
        self.client.delete(f"/api/students/me/courses/{row['id']}", headers=self.headers(self.lisa))
        # Read her milestone.
        milestone = self.milestone(self.lisa.id)
        # It's back to in progress.
        self.assertEqual(milestone.status, MilestoneStatus.IN_PROGRESS)
        # The approval date is cleared.
        self.assertIsNone(milestone.completed_on)

    # Adds a manually entered course through the API, and returns the response.
    def add_manual(self, code="MAT 520", title="Algebra", department="non_cs", credits=3, grade="A", year=2025, research=False):
        # Lisa is the student, and no course_id is sent.
        return self.client.post("/api/students/me/courses", headers=self.headers(self.lisa),
                                json=dict(manual_code=code, manual_title=title, manual_department=department, manual_is_research=research,
                                          credits=credits, term="fall", year=year, grade=grade))

    # A non-CS manual course counts toward electives right away.
    def test_manual_non_cs_course_counts_as_elective(self):
        # Lisa enters a non-CS course.
        response = self.add_manual()
        # It's created.
        self.assertEqual(response.status_code, 201)
        # Read the response data.
        data = response.json()
        # Electives get its credits.
        self.assertEqual(self.bar(data, "Electives")["earned_credits"], 3)
        # Read the course from her list.
        row = data["my_courses"][0]
        # It keeps the code, name, department and manual marker.
        self.assertEqual((row["code"], row["title"], row["department"], row["is_manual"], row["course_id"]), ("MAT 520", "Algebra", "non_cs", True, None))

    # A CS manual course also counts toward electives.
    def test_manual_cs_course_counts_as_elective(self):
        # Lisa enters a CS course that isn't on the list.
        data = self.add_manual(code="CSI 700", department="cs").json()
        # Electives get its credits.
        self.assertEqual(self.bar(data, "Electives")["earned_credits"], 3)
        # The department is saved.
        self.assertEqual(data["my_courses"][0]["department"], "cs")

    # A listed course can't be entered manually, even when written differently.
    def test_listed_course_cannot_be_entered_manually(self):
        # Lisa types CSI 503 without a space or capitals.
        response = self.add_manual(code="csi503", department="cs")
        # It's refused.
        self.assertEqual(response.status_code, 422)
        # The message tells her to select it from the list.
        self.assertIn("CSI 503", response.json()["detail"])

    # A manual course needs its code, name and department.
    def test_manual_course_needs_all_its_fields(self):
        # Lisa leaves out the department.
        self.assertEqual(self.add_manual(department=None).status_code, 422)

    # A course can't be both selected and entered manually.
    def test_cannot_select_and_enter_a_course_together(self):
        # Send both a listed course and a manual code.
        response = self.client.post("/api/students/me/courses", headers=self.headers(self.lisa),
                                    json=dict(course_id=1, manual_code="MAT 520", credits=3, term="fall", year=2025))
        # It's refused.
        self.assertEqual(response.status_code, 422)

    # The same manual course can't be added twice in one term, even when written differently.
    def test_duplicate_manual_course_is_refused(self):
        # The first time works.
        self.assertEqual(self.add_manual().status_code, 201)
        # The same course in lowercase is refused.
        self.assertEqual(self.add_manual(code="mat  520").status_code, 409)

    # A repeated manual course counts once, using the higher grade.
    def test_repeated_manual_course_counts_once(self):
        # Lisa takes it first with a C.
        self.add_manual(grade="C", year=2024)
        # She repeats it with an A.
        data = self.add_manual(grade="A", year=2025).json()
        # Only 3 credits count.
        self.assertEqual(data["coursework_credits"], 3)
        # The degree GPA uses the higher grade.
        self.assertEqual(data["degree_gpa"], 4.0)

    # Manual research credits share the 15-credit limit.
    def test_manual_research_credits_share_the_limit(self):
        # Lisa has 15 listed research credits.
        self.add(9, credits=15, grade="S")
        # She adds 3 manual research credits.
        data = self.add_manual(research=True).json()
        # Electives stay at 15.
        self.assertEqual(self.bar(data, "Electives")["earned_credits"], 15)

    # A manual course in progress doesn't count.
    def test_manual_course_in_progress_does_not_count(self):
        # Lisa enters a course with no grade.
        data = self.add_manual(grade=None).json()
        # It adds no credits.
        self.assertEqual(data["coursework_credits"], 0)

    # A manual course can reach 45 credits and approve the milestone.
    def test_manual_course_can_approve_the_milestone(self):
        # Lisa has 42 credits.
        self.nearly_complete()
        # A manual course takes her to 45.
        self.assertEqual(self.add_manual().json()["coursework_credits"], 45)
        # The milestone is approved.
        self.assertEqual(self.milestone(self.lisa.id).status, MilestoneStatus.APPROVED)

    # A manual course can be edited and removed.
    def test_manual_course_can_be_edited_and_removed(self):
        # Lisa adds a course and its row id is read.
        row_id = self.add_manual().json()["my_courses"][0]["id"]
        # The new values, with a different department.
        body = dict(manual_code="MAT 521", manual_title="Analysis", manual_department="cs", credits=3, term="fall", year=2025, grade="B")
        # She edits it.
        edited = self.client.put(f"/api/students/me/courses/{row_id}", headers=self.headers(self.lisa), json=body).json()
        # The new code and department are saved.
        self.assertEqual((edited["my_courses"][0]["code"], edited["my_courses"][0]["department"]), ("MAT 521", "cs"))
        # She removes it.
        removed = self.client.delete(f"/api/students/me/courses/{row_id}", headers=self.headers(self.lisa)).json()
        # Her list is empty.
        self.assertEqual(removed["my_courses"], [])

    # Returns a student's GPA as stored in the users table, re-read from the database.
    def stored_gpa(self, student):
        # Discard cached rows so the latest value is read.
        self.db.expire_all()
        # Return the stored GPA.
        return student.gpa

    # Adding a course replaces the old stored GPA with the calculated one.
    def test_adding_a_course_updates_the_stored_gpa(self):
        # Lisa adds an A, which replaces her starting GPA of 3.20.
        data = self.add(1, grade="A").json()
        # The stored GPA is now 4.00.
        self.assertEqual(self.stored_gpa(self.lisa), Decimal("4.00"))
        # The Coursework page shows the same value.
        self.assertEqual(data["degree_gpa"], 4.0)

    # Editing a course's grade updates the stored GPA.
    def test_editing_a_grade_updates_the_stored_gpa(self):
        # Lisa adds an A and its row id is read.
        row_id = self.add(1, grade="A").json()["my_courses"][0]["id"]
        # The same course with a B.
        body = dict(course_id=1, credits=3, term="fall", year=2025, grade="B")
        # She edits it.
        self.client.put(f"/api/students/me/courses/{row_id}", headers=self.headers(self.lisa), json=body)
        # The stored GPA is now 3.00.
        self.assertEqual(self.stored_gpa(self.lisa), Decimal("3.00"))

    # Removing a student's only graded course empties the stored GPA.
    def test_removing_the_last_graded_course_empties_the_stored_gpa(self):
        # Lisa adds a course and its row id is read.
        row_id = self.add(1, grade="A").json()["my_courses"][0]["id"]
        # She removes it.
        self.client.delete(f"/api/students/me/courses/{row_id}", headers=self.headers(self.lisa))
        # No GPA is stored.
        self.assertIsNone(self.stored_gpa(self.lisa))

    # Courses in progress and no-credit grades aren't part of the stored GPA.
    def test_stored_gpa_ignores_ungraded_and_no_credit_courses(self):
        # Lisa earns a B.
        self.add(1, grade="B")
        # She adds a course in progress.
        self.add(2, grade=None)
        # She earns an E, which earns no credit.
        self.add(10, grade="E")
        # Only the B counts.
        self.assertEqual(self.stored_gpa(self.lisa), Decimal("3.00"))

    # A student's GPA stays the same on the dashboard and in the candidacy check.
    def test_dashboard_and_candidacy_use_the_calculated_gpa(self):
        # Lisa's only graded course is a B-, so her GPA drops to 2.70.
        self.add(1, grade="B-")
        # She opens her dashboard.
        dashboard = self.client.get("/api/students/me/milestones", headers=self.headers(self.lisa)).json()
        # The dashboard shows the calculated GPA.
        self.assertEqual(Decimal(dashboard["student"]["gpa"]), Decimal("2.70"))
        # Find the Candidacy milestone.
        candidacy = next(item for item in dashboard["milestones"] if item["name"] == "Candidacy")
        # Find its GPA requirement.
        requirement = next(item for item in candidacy["requirements"] if item["name"] == "GPA at least 3.00")
        # It isn't met, because 2.70 is below 3.00.
        self.assertFalse(requirement["met"])
        # The message shows the same GPA.
        self.assertIn("2.70", requirement["explanation"])

    # A running semester can't have a grade, and the message gives the date it opens.
    def test_running_semester_refuses_a_grade(self):
        # It's November 2026, so Fall 2026 is running.
        response = self.add(1, grade="A", year=2026, term="fall")
        # It's refused.
        self.assertEqual(response.status_code, 422)
        # The message gives the semester's end date.
        self.assertIn("December 31, 2026", response.json()["detail"])

    # A running semester can be added as in progress.
    def test_running_semester_allows_in_progress(self):
        # Lisa adds a Fall 2026 course with no grade.
        self.assertEqual(self.add(1, grade=None, year=2026, term="fall").status_code, 201)

    # The day before Fall ends, a grade is still refused.
    def test_fall_grade_is_refused_on_december_30(self):
        # Set today to December 30.
        self.today.return_value = date(2026, 12, 30)
        # The grade is refused.
        self.assertEqual(self.add(1, grade="A", year=2026, term="fall").status_code, 422)

    # A Fall grade is allowed from December 31.
    def test_fall_grade_is_allowed_on_december_31(self):
        # Set today to December 31.
        self.today.return_value = date(2026, 12, 31)
        # The grade is accepted.
        self.assertEqual(self.add(1, grade="A", year=2026, term="fall").status_code, 201)

    # The day before Spring ends, a grade is still refused.
    def test_spring_grade_is_refused_on_may_30(self):
        # Set today to May 30.
        self.today.return_value = date(2026, 5, 30)
        # The grade is refused.
        self.assertEqual(self.add(1, grade="A", year=2026, term="spring").status_code, 422)

    # A Spring grade is allowed from May 31.
    def test_spring_grade_is_allowed_on_may_31(self):
        # Set today to May 31.
        self.today.return_value = date(2026, 5, 31)
        # The grade is accepted.
        self.assertEqual(self.add(1, grade="A", year=2026, term="spring").status_code, 201)

    # A semester that hasn't started can't be added at all.
    def test_future_semester_is_refused(self):
        # Fall 2027 is refused with a grade, like the row in the screenshot.
        self.assertEqual(self.add(1, grade="A", year=2027, term="fall").status_code, 422)
        # It's also refused as in progress.
        self.assertEqual(self.add(1, grade=None, year=2027, term="fall").status_code, 422)

    # The rule also applies to manually entered courses.
    def test_manual_course_follows_the_semester_rule(self):
        # A manual course with a grade in the running semester is refused.
        self.assertEqual(self.add_manual(grade="A", year=2026).status_code, 422)

    # A student can't add a grade to a running semester's course by editing it.
    def test_editing_cannot_add_a_grade_early(self):
        # Lisa adds a running semester's course as in progress.
        row_id = self.add(1, grade=None, year=2026, term="fall").json()["my_courses"][0]["id"]
        # The same course with a grade.
        body = dict(course_id=1, credits=3, term="fall", year=2026, grade="A")
        # The edit is refused.
        self.assertEqual(self.client.put(f"/api/students/me/courses/{row_id}", headers=self.headers(self.lisa), json=body).status_code, 422)

    # Removing a course stays allowed, whatever the semester.
    def test_running_semester_course_can_be_removed(self):
        # Lisa adds a running semester's course.
        row_id = self.add(1, grade=None, year=2026, term="fall").json()["my_courses"][0]["id"]
        # She removes it, and it works.
        self.assertEqual(self.client.delete(f"/api/students/me/courses/{row_id}", headers=self.headers(self.lisa)).status_code, 200)

    # Completing Coursework tells the advisor, and losing it tells them too.
    def test_coursework_changes_notify_the_advisor(self):
        # Sam's advisor is faculty 1, and he starts with one course short of everything else.
        for course_id in (1, 2, 3, 4, 6, 10, 11, 12, 13):
            # Add each 3-credit course directly to the database.
            self.db.add(StudentCourse(student_id=self.sam.id, course_id=course_id, credits=3, term=Term.SPRING, year=2024, grade="A"))
        # Add 15 credits of independent study.
        self.db.add(StudentCourse(student_id=self.sam.id, course_id=9, credits=15, term=Term.SPRING, year=2024, grade="A"))
        # Save these rows.
        self.db.commit()
        # The last course takes him to 45, and its row is found.
        row = next(item for item in self.add(14, user=self.sam).json()["my_courses"] if item["course_id"] == 14)
        # Read the advisor's messages.
        messages = [item.message for item in self.db.scalars(select(Notification).where(Notification.user_id == 1).order_by(Notification.id))]
        # The advisor is told he completed it.
        self.assertIn("Sam completed Coursework on", messages[-1])
        # He removes that course.
        self.client.delete(f"/api/students/me/courses/{row['id']}", headers=self.headers(self.sam))
        # Read the advisor's messages again.
        messages = [item.message for item in self.db.scalars(select(Notification).where(Notification.user_id == 1).order_by(Notification.id))]
        # The advisor is told he no longer meets the requirements.
        self.assertEqual(messages[-1], "Sam no longer meets the requirements for Coursework.")

    # Returns the note on a course in the response, found by its course id.
    def note(self, data, course_id, year=2025):
        # Find the row for this course and year, then return its note.
        return next(row["note"] for row in data["my_courses"] if row["course_id"] == course_id and row["year"] == year)

    # A course that counts as normal has no note.
    def test_normal_course_has_no_note(self):
        # Lisa earns a B in a core course, which meets the requirement.
        self.assertIsNone(self.note(self.add(1, grade="B").json(), 1))

    # A course in progress has no note.
    def test_course_in_progress_has_no_note(self):
        # Lisa has no grade yet.
        self.assertIsNone(self.note(self.add(1, grade=None).json(), 1))

    # A low grade in a core course explains the rule.
    def test_low_core_grade_is_explained(self):
        # Lisa earns a B-.
        note = self.note(self.add(1, grade="B-").json(), 1)
        # It names the group and the required grade.
        self.assertIn("Doesn't count toward Core, which needs a B or better", note)
        # It says where the credits went.
        self.assertIn("Counted as an elective", note)

    # A low grade in a breadth course explains the rule.
    def test_low_breadth_grade_is_explained(self):
        # Lisa earns a C+ in an AI & ML course.
        data = self.add(4, grade="C+").json()
        # The note names the area.
        self.assertIn("Doesn't count toward Breadth: AI & ML, which needs a B or better", self.note(data, 4))
        # The credits match the note: the area is empty, and the elective has 3.
        self.assertEqual((self.bar(data, "Breadth: AI")["earned_credits"], self.bar(data, "Electives")["earned_credits"]), (0, 3))

    # A grade that earns no credit explains why.
    def test_no_credit_grade_is_explained(self):
        # Each of these earns no graduate credit.
        for offset, grade in enumerate(("C-", "D+", "D", "E", "U")):
            # Add one in a separate year, so they aren't duplicates.
            data = self.add(10, grade=grade, year=2020 + offset).json()
            # The note says so.
            self.assertIn("Earns no graduate credit", self.note(data, 10, 2020 + offset))

    # A repeated course explains which attempt doesn't count.
    def test_lower_repeat_is_explained(self):
        # Lisa earns a B- first.
        self.add(1, grade="B-", year=2024)
        # She repeats it and earns an A.
        data = self.add(1, grade="A", year=2025).json()
        # The lower attempt explains why it doesn't count.
        self.assertIn("another attempt at CSI 503 has a higher grade", self.note(data, 1, 2024))
        # The higher attempt has no note.
        self.assertIsNone(self.note(data, 1, 2025))

    # A second course in a filled breadth area explains where it went.
    def test_filled_breadth_area_is_explained(self):
        # The first AI & ML course fills the area.
        self.add(4, year=2024)
        # The second one is added later.
        data = self.add(5).json()
        # The first has no note.
        self.assertIsNone(self.note(data, 4, 2024))
        # The second explains that it became an elective.
        self.assertIn("already filled", self.note(data, 5))

    # CSI 518's split is explained.
    def test_csi_518_split_is_explained(self):
        # Lisa takes CSI 518 for 4 credits.
        self.assertIn("3 credits count toward Breadth: Systems or CSI 518, and the other 1 toward electives", self.note(self.add(7, credits=4).json(), 7))

    # Going past the research limit is explained.
    def test_research_limit_is_explained(self):
        # Lisa takes 19 credits of independent study.
        self.assertIn("Only 15 credits", self.note(self.add(9, credits=19, grade="S").json(), 9))

    # CSI 898 has its own group, so the research limit note doesn't apply.
    def test_csi_898_has_no_research_note(self):
        # Lisa takes 12 credits of CSI 898.
        self.assertIsNone(self.note(self.add(8, credits=12, grade="S").json(), 8))

    # Reads the coursework page data for a student.
    def page(self, user):
        # Return the response's data.
        return self.client.get("/api/students/me/coursework", headers=self.headers(user)).json()

    # Without advanced standing, full-time students have until semester 6, and passing it is overdue.
    def test_csi_790_overdue_without_advanced_standing(self):
        # Sam started in Fall 2023 full-time, and has no CSI 790 yet.
        data = self.page(self.sam)
        # His sixth semester is Spring 2026.
        self.assertEqual(data["csi_790_deadline"], "Spring 2026")
        # It's November 2026, so the deadline has passed.
        self.assertTrue(data["csi_790_overdue"])

    # Advanced standing gives semester 2, doubled to 4 for part-time students.
    def test_csi_790_deadline_for_part_time_advanced_standing(self):
        # Lisa started in Spring 2026 with advanced standing, part-time.
        data = self.page(self.lisa)
        # Her fourth semester is Fall 2027.
        self.assertEqual(data["csi_790_deadline"], "Fall 2027")
        # That hasn't passed yet.
        self.assertFalse(data["csi_790_overdue"])

    # Advanced standing gives semester 2 for full-time students.
    def test_csi_790_deadline_for_full_time_advanced_standing(self):
        # Raj started in Fall 2022 with advanced standing, full-time, so his second semester is Spring 2023.
        self.assertEqual(self.page(self.raj)["csi_790_deadline"], "Spring 2023")

    # The last allowed semester itself isn't overdue.
    def test_csi_790_is_not_overdue_during_the_last_semester(self):
        # Set today to the middle of Sam's last allowed semester, Spring 2026.
        self.today.return_value = date(2026, 3, 1)
        # It isn't overdue yet.
        self.assertFalse(self.page(self.sam)["csi_790_overdue"])

    # A B or better completes CSI 790 and clears the overdue flag.
    def test_csi_790_with_b_or_better_is_complete(self):
        # Sam takes CSI 790 and earns a B.
        data = self.add(2, grade="B", user=self.sam).json()
        # It's complete.
        self.assertTrue(data["csi_790_complete"])
        # It's no longer overdue.
        self.assertFalse(data["csi_790_overdue"])

    # A grade below B doesn't complete CSI 790.
    def test_csi_790_below_b_is_not_complete(self):
        # Sam takes CSI 790 and earns a B-.
        data = self.add(2, grade="B-", user=self.sam).json()
        # It isn't complete.
        self.assertFalse(data["csi_790_complete"])
        # It stays overdue.
        self.assertTrue(data["csi_790_overdue"])

    # A student with missing details gets no deadline.
    def test_csi_790_has_no_deadline_without_student_details(self):
        # Clear Lisa's advanced standing.
        self.lisa.advanced_standing = None
        # Save the change.
        self.db.commit()
        # Read her page.
        data = self.page(self.lisa)
        # There's no deadline to show.
        self.assertIsNone(data["csi_790_deadline"])
        # It can't be overdue.
        self.assertFalse(data["csi_790_overdue"])


# Lets this file be run directly.
if __name__ == "__main__":
    # Run all the tests above.
    unittest.main()
