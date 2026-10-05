"""Run from backend: python -m unittest discover -s tests -v.

All data lives in an isolated in-memory database; Neon is never used.
"""

import unittest
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.modules.milestones.models import Milestone, MilestonePrerequisite, MilestoneStatus, StudentMilestone
from app.modules.student.service import get_dashboard
from app.modules.users.models import EnrollmentStatus, Role, Term, User


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        self.faculty = User(id=1, email="faculty@test.edu", full_name="Faculty", role=Role.FACULTY, password_hash="unused")
        self.director = User(id=4, email="director@test.edu", full_name="Director", role=Role.DIRECTOR, password_hash="unused")
        self.sam = self.student(5, "Sam", False, EnrollmentStatus.FULL_TIME, Term.FALL, 2023, "3.60", 1)
        self.lisa = self.student(6, "Lisa", True, EnrollmentStatus.PART_TIME, Term.SPRING, 2026, "3.20", None)
        self.raj = self.student(7, "Raj", True, EnrollmentStatus.FULL_TIME, Term.FALL, 2022, "2.90", 1)
        self.db.add_all([self.faculty, self.director, self.sam, self.lisa, self.raj])
        for mid, name, advanced, regular in [
            (1, "Coursework", None, None), (2, "Advisor declaration", 2, 6),
            (3, "Research methods course", 2, 6), (4, "Comprehensive exam", 4, 8),
            (5, "Committee formation", None, None), (6, "Dissertation proposal", None, None),
            (7, "Candidacy", None, None), (8, "Dissertation defense", 12, 16),
        ]:
            self.db.add(Milestone(id=mid, name=name, position=mid, deadline_semester_advanced=advanced, deadline_semester_regular=regular))
        for mid, required, gap in [(4, 2, 0), (4, 5, 0), (6, 4, 0), (6, 5, 0), (7, 1, 0), (7, 3, 0), (7, 4, 0), (8, 1, 0), (8, 6, 1)]:
            self.db.add(MilestonePrerequisite(milestone_id=mid, requires_id=required, min_gap_semesters=gap))
        self.progress(5, 1, MilestoneStatus.IN_PROGRESS)
        for mid, completed in [(2, "2024-01-15"), (3, "2024-05-10"), (4, "2025-11-20"), (5, "2025-03-01")]:
            self.progress(5, mid, MilestoneStatus.APPROVED, completed)
        self.progress(5, 6, MilestoneStatus.UNDER_REVIEW)
        self.progress(6, 1, MilestoneStatus.IN_PROGRESS)
        self.progress(6, 3, MilestoneStatus.IN_PROGRESS)
        for mid, completed in [(1, "2024-05-15"), (2, "2022-12-01"), (3, "2023-05-12"), (4, "2023-12-10"), (5, "2023-09-05"), (6, "2025-12-01")]:
            self.progress(7, mid, MilestoneStatus.APPROVED, completed)
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    @staticmethod
    def student(uid, name, advanced, enrollment, term, year, gpa, advisor):
        return User(id=uid, email=f"{name.lower()}@test.edu", full_name=name, role=Role.STUDENT,
                    password_hash="unused", advanced_standing=advanced, enrollment_status=enrollment,
                    start_term=term, start_year=year, gpa=Decimal(gpa), advisor_id=advisor)

    def progress(self, student, milestone, status, completed=None):
        self.db.add(StudentMilestone(student_id=student, milestone_id=milestone, status=status,
                                     completed_on=date.fromisoformat(completed) if completed else None))

    def dashboard(self, student, today=date(2026, 10, 5)):
        return get_dashboard(self.db, student, today)

    def milestone(self, student, mid, today=date(2026, 10, 5)):
        return next(m for m in self.dashboard(student, today).milestones if m.id == mid)

    def headers(self, user):
        return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}

    def test_sam_counts_and_missing_rows(self):
        dashboard = self.dashboard(self.sam)
        self.assertEqual(dashboard.summary.model_dump(), dict(total=8, completed=4, current=2, blocked=2, upcoming=0, percent=50))
        self.assertEqual(self.milestone(self.sam, 7).status, MilestoneStatus.NOT_STARTED)
        self.assertEqual(dashboard.student.program_year, 4)

    def test_lisa_part_time_deadlines_and_advisor(self):
        self.assertEqual(self.milestone(self.lisa, 2).deadline_semester, 4)
        self.assertEqual(self.milestone(self.lisa, 2).deadline_label, "Fall 2027")
        self.assertEqual(self.milestone(self.lisa, 4).deadline_semester, 8)
        self.assertEqual(self.milestone(self.lisa, 8).deadline_semester, 16)
        self.assertEqual(self.milestone(self.lisa, 8).deadline_label, "Fall 2033")
        self.assertIsNone(self.dashboard(self.lisa).student.advisor_id)
        self.assertEqual(self.dashboard(self.lisa).summary.completed, 0)

    def test_regular_part_time_defense_cap(self):
        self.lisa.advanced_standing = False
        self.assertEqual(self.milestone(self.lisa, 2).deadline_semester, 12)
        self.assertEqual(self.milestone(self.lisa, 8).deadline_semester, 16)

    def test_raj_gpa_blocks_only_candidacy(self):
        self.assertEqual(self.milestone(self.raj, 7).category, "blocked")
        self.assertIn("2.90", self.milestone(self.raj, 7).blocked_reasons[0])
        self.assertEqual(self.milestone(self.raj, 8).category, "upcoming")
        self.raj.gpa = Decimal("3.00")
        self.assertTrue(self.milestone(self.raj, 7).eligible)

    def test_missing_gpa_blocks_candidacy(self):
        self.raj.gpa = None
        self.assertIn("not recorded", self.milestone(self.raj, 7).blocked_reasons[0])

    def test_defense_waits_for_next_semester(self):
        self.assertFalse(self.milestone(self.raj, 8, date(2025, 12, 20)).eligible)
        self.assertTrue(self.milestone(self.raj, 8, date(2026, 1, 1)).eligible)

    def test_missing_proposal_date_cannot_bypass_gap(self):
        row = self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == 7, StudentMilestone.milestone_id == 6))
        row.completed_on = None
        self.db.flush()
        self.assertIn("approval date", self.milestone(self.raj, 8).blocked_reasons[0])

    def test_advisor_required_even_with_approved_declaration(self):
        self.progress(6, 2, MilestoneStatus.APPROVED, "2026-01-10")
        self.progress(6, 5, MilestoneStatus.APPROVED, "2026-01-10")
        self.db.flush()
        self.assertEqual(self.milestone(self.lisa, 4).blocked_reasons, ["A research advisor must be declared."])
        self.lisa.advisor_id = 1
        self.assertTrue(self.milestone(self.lisa, 4).eligible)

    def test_proposal_requires_both_comps_and_committee(self):
        self.progress(6, 4, MilestoneStatus.APPROVED, "2026-01-10")
        self.db.flush()
        self.assertEqual(self.milestone(self.lisa, 6).blocked_reasons, ["Committee formation must be approved."])

    def test_new_student_has_all_milestones_without_inserting_rows(self):
        new = self.student(8, "New", False, EnrollmentStatus.FULL_TIME, Term.FALL, 2026, "3.5", None)
        self.db.add(new)
        self.db.commit()
        before = self.db.scalar(select(func.count()).select_from(StudentMilestone))
        result = self.dashboard(new)
        self.assertEqual(len(result.milestones), 8)
        self.assertTrue(all(m.status == MilestoneStatus.NOT_STARTED for m in result.milestones))
        self.assertEqual(result.summary.percent, 0)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(StudentMilestone)), before)

    def test_deadline_current_term_is_not_overdue(self):
        self.lisa.advanced_standing = False
        self.lisa.enrollment_status = EnrollmentStatus.FULL_TIME
        self.lisa.start_year = 2023
        self.lisa.start_term = Term.FALL
        self.assertFalse(self.milestone(self.lisa, 3, date(2026, 7, 31)).overdue)
        self.assertTrue(self.milestone(self.lisa, 3, date(2026, 8, 1)).overdue)
        self.assertFalse(self.milestone(self.sam, 3).overdue)

    def test_incomplete_profile_and_future_start(self):
        self.lisa.start_year = None
        self.assertIsNone(self.dashboard(self.lisa).student.program_year)
        self.assertIsNone(self.milestone(self.lisa, 2).deadline_label)
        self.lisa.start_year = 2027
        self.assertEqual(self.dashboard(self.lisa).student.program_year, 0)

    def test_no_milestones_returns_zero_percent(self):
        # A separate empty database avoids deleting fixtures or shared data.
        with Session(create_engine("sqlite://")) as empty:
            Base.metadata.create_all(empty.bind)
            self.lisa.advisor_id = None
            result = get_dashboard(empty, self.lisa, date(2026, 10, 5))
            self.assertEqual(result.summary.total, 0)
            self.assertEqual(result.summary.percent, 0)

    def test_api_rejects_missing_invalid_tokens_and_other_roles(self):
        path = "/api/students/me/milestones"
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get(path, headers={"Authorization": "Bearer invalid"}).status_code, 401)
        for user in [self.faculty, self.director]:
            self.assertEqual(self.client.get(path, headers=self.headers(user)).status_code, 403)

    def test_api_scopes_data_and_excludes_credentials(self):
        response = self.client.get("/api/students/me/milestones?student_id=7", headers=self.headers(self.lisa))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["student"]["full_name"], "Lisa")
        self.assertEqual(body["summary"]["completed"], 0)
        self.assertNotIn("password_hash", response.text)
        self.assertEqual(len(body["milestones"]), 8)


if __name__ == "__main__":
    unittest.main()
