"""Tests for the Faculty Dashboard and milestone review workflow."""

import unittest
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.modules.faculty.service import get_faculty_dashboard
from app.modules.milestones.models import (
    Milestone,
    MilestoneStatus,
    StudentMilestone,
)
from app.modules.users.models import (
    EnrollmentStatus,
    Role,
    Term,
    User,
)


class FacultyDashboardTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        Base.metadata.create_all(self.engine)

        self.db = Session(self.engine)

        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

        self.faculty = User(
            id=1,
            email="faculty@test.edu",
            full_name="Dr. Faculty",
            role=Role.FACULTY,
            password_hash="unused",
        )

        self.other_faculty = User(
            id=2,
            email="other@test.edu",
            full_name="Dr. Other",
            role=Role.FACULTY,
            password_hash="unused",
        )

        self.director = User(
            id=3,
            email="director@test.edu",
            full_name="Director",
            role=Role.DIRECTOR,
            password_hash="unused",
        )

        self.student = User(
            id=4,
            email="student@test.edu",
            full_name="Sam Student",
            role=Role.STUDENT,
            password_hash="unused",
            advanced_standing=False,
            enrollment_status=EnrollmentStatus.FULL_TIME,
            start_term=Term.FALL,
            start_year=2024,
            gpa=Decimal("3.50"),
            advisor_id=1,
        )

        self.other_student = User(
            id=5,
            email="otherstudent@test.edu",
            full_name="Other Student",
            role=Role.STUDENT,
            password_hash="unused",
            advanced_standing=False,
            enrollment_status=EnrollmentStatus.FULL_TIME,
            start_term=Term.FALL,
            start_year=2024,
            gpa=Decimal("3.40"),
            advisor_id=2,
        )

        self.db.add_all(
            [
                self.faculty,
                self.other_faculty,
                self.director,
                self.student,
                self.other_student,
            ]
        )

        self.db.add_all(
            [
                Milestone(
                    id=1,
                    name="Coursework",
                    position=1,
                    deadline_semester_advanced=None,
                    deadline_semester_regular=None,
                ),
                Milestone(
                    id=2,
                    name="Comprehensive Exam",
                    position=2,
                    deadline_semester_advanced=4,
                    deadline_semester_regular=8,
                ),
            ]
        )

        self.db.add_all(
            [
                StudentMilestone(
                    student_id=4,
                    milestone_id=1,
                    status=MilestoneStatus.APPROVED,
                    completed_on=date(2025, 5, 1),
                ),
                StudentMilestone(
                    student_id=4,
                    milestone_id=2,
                    status=MilestoneStatus.UNDER_REVIEW,
                ),
                StudentMilestone(
                    student_id=5,
                    milestone_id=1,
                    status=MilestoneStatus.APPROVED,
                    completed_on=date(2025, 5, 1),
                ),
            ]
        )

        self.db.commit()

        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(app.dependency_overrides.clear)

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def headers(self, user):
        token = create_access_token(
            user.id,
            user.role.value,
        )

        return {
            "Authorization": f"Bearer {token}"
        }

    def test_faculty_sees_only_assigned_students(self):
        result = get_faculty_dashboard(
            self.db,
            self.faculty,
            date(2026, 10, 7),
        )

        self.assertEqual(
            result.summary.assigned_students,
            1,
        )

        self.assertEqual(
            result.students[0].full_name,
            "Sam Student",
        )

        self.assertEqual(
            result.students[0].progress_percent,
            50,
        )

    def test_pending_review_count(self):
        result = get_faculty_dashboard(
            self.db,
            self.faculty,
            date(2026, 10, 7),
        )

        self.assertEqual(
            result.summary.pending_reviews,
            1,
        )

        self.assertEqual(
            result.pending_reviews[0].milestone_name,
            "Comprehensive Exam",
        )

        self.assertEqual(
            result.pending_reviews[0].status,
            MilestoneStatus.UNDER_REVIEW,
        )

    def test_other_faculty_student_is_hidden(self):
        result = get_faculty_dashboard(
            self.db,
            self.faculty,
            date(2026, 10, 7),
        )

        names = [
            student.full_name
            for student in result.students
        ]

        self.assertNotIn(
            "Other Student",
            names,
        )

    def test_api_allows_faculty(self):
        response = self.client.get(
            "/api/faculty/me/dashboard",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["faculty"]["full_name"],
            "Dr. Faculty",
        )

    def test_api_rejects_student(self):
        response = self.client.get(
            "/api/faculty/me/dashboard",
            headers=self.headers(self.student),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_rejects_director(self):
        response = self.client.get(
            "/api/faculty/me/dashboard",
            headers=self.headers(self.director),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_rejects_no_login(self):
        response = self.client.get(
            "/api/faculty/me/dashboard"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_faculty_can_approve_assigned_student_milestone(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.faculty),
            json={"status": "approved"},
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["status"],
            "approved",
        )

        progress = self.db.scalar(
            select(StudentMilestone).where(
                StudentMilestone.student_id == 4,
                StudentMilestone.milestone_id == 2,
            )
        )

        self.assertEqual(
            progress.status,
            MilestoneStatus.APPROVED,
        )

        self.assertIsNotNone(
            progress.completed_on,
        )

    def test_faculty_can_request_revision(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.faculty),
            json={"status": "revision_requested"},
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["status"],
            "revision_requested",
        )

    def test_faculty_can_reject_milestone(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.faculty),
            json={"status": "rejected"},
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["status"],
            "rejected",
        )

    def test_faculty_cannot_review_other_faculty_student(self):
        response = self.client.patch(
            "/api/faculty/students/5/milestones/1",
            headers=self.headers(self.faculty),
            json={"status": "approved"},
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_student_cannot_review_milestone(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.student),
            json={"status": "approved"},
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_invalid_review_status_is_rejected(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.faculty),
            json={"status": "in_progress"},
        )

        self.assertEqual(
            response.status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()