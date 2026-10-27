"""Advisor declaration uses the same isolated fixtures as the dashboard tests."""

import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import func, select

import test_student_dashboard as fixtures
from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
from app.modules.student.advisor_service import declare_advisor


class AdvisorDeclarationTests(unittest.TestCase):
    setUp = fixtures.DashboardTests.setUp
    student = staticmethod(fixtures.DashboardTests.student)
    progress = fixtures.DashboardTests.progress
    headers = fixtures.DashboardTests.headers

    def declare(self, advisor_id=1, user=None, **extra):
        return self.client.put("/api/students/me/advisor", headers=self.headers(user or self.lisa),
                               json={"advisor_id": advisor_id, **extra})

    def test_list_only_faculty_and_public_fields(self):
        response = self.client.get("/api/students/me/advisors", headers=self.headers(self.lisa))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{"id": 1, "full_name": "Faculty", "email": "faculty@test.edu", "advisee_count": 2}])

    def test_advisee_count_updates_after_declaration(self):
        self.assertEqual(self.declare().status_code, 200)
        response = self.client.get("/api/students/me/advisors", headers=self.headers(self.lisa))
        self.assertEqual(response.json()[0]["advisee_count"], 3)

    def test_faculty_without_students_has_zero_count(self):
        from app.modules.users.models import Role, User
        self.db.add(User(id=9, email="new@test.edu", full_name="New Faculty", role=Role.FACULTY, password_hash="unused"))
        self.db.commit()
        response = self.client.get("/api/students/me/advisors", headers=self.headers(self.lisa))
        self.assertEqual(next(a for a in response.json() if a["id"] == 9)["advisee_count"], 0)

    def test_declare_updates_profile_milestone_and_faculty_dashboard(self):
        response = self.declare()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["student"]["advisor_id"], 1)
        self.assertEqual(body["summary"]["completed"], 1)
        milestone = next(m for m in body["milestones"] if m["id"] == 2)
        self.assertEqual(milestone["status"], "approved")
        self.assertEqual(milestone["completed_on"], body["as_of"])
        comps = next(m for m in body["milestones"] if m["id"] == 4)
        self.assertEqual(comps["blocked_reasons"], ["Committee formation must be approved."])
        persisted = self.client.get("/api/students/me/milestones", headers=self.headers(self.lisa)).json()
        self.assertEqual(persisted["student"]["advisor_id"], 1)
        faculty = self.client.get("/api/faculty/me/dashboard", headers=self.headers(self.faculty)).json()
        self.assertIn(6, [s["id"] for s in faculty["students"]])
        self.assertFalse(any(r["student_id"] == 6 and r["milestone_id"] == 2 for r in faculty["pending_reviews"]))

    def test_retry_preserves_completion_date_and_does_not_duplicate(self):
        self.assertEqual(self.declare().status_code, 200)
        row = self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == 6, StudentMilestone.milestone_id == 2))
        row.completed_on = date(2026, 1, 1)
        self.db.commit()
        self.assertEqual(self.declare().status_code, 200)
        self.assertEqual(row.completed_on, date(2026, 1, 1))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(StudentMilestone).where(StudentMilestone.student_id == 6, StudentMilestone.milestone_id == 2)), 1)

    def test_existing_progress_is_completed_in_place(self):
        self.progress(6, 2, MilestoneStatus.IN_PROGRESS)
        self.db.commit()
        self.assertEqual(self.declare().status_code, 200)
        rows = list(self.db.scalars(select(StudentMilestone).where(StudentMilestone.student_id == 6, StudentMilestone.milestone_id == 2)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, MilestoneStatus.APPROVED)

    def test_rejects_nonfaculty_missing_invalid_and_extra_fields(self):
        for value in [4, 5, 6, 999, 0, -1, "1", True, None]:
            with self.subTest(value=value):
                self.assertEqual(self.declare(value).status_code, 422)
        self.assertEqual(self.declare(student_id=5).status_code, 422)
        self.assertIsNone(self.db.get(type(self.lisa), 6).advisor_id)

    def test_cannot_replace_existing_advisor(self):
        self.assertEqual(self.declare(999, self.sam).status_code, 409)
        self.assertEqual(self.db.get(type(self.sam), 5).advisor_id, 1)

    def test_both_routes_require_student(self):
        for method, path, payload in [("GET", "/api/students/me/advisors", None), ("PUT", "/api/students/me/advisor", {"advisor_id": 1})]:
            self.assertEqual(self.client.request(method, path, json=payload).status_code, 401)
            for user in [self.faculty, self.director]:
                self.assertEqual(self.client.request(method, path, json=payload, headers=self.headers(user)).status_code, 403)

    def test_missing_milestone_does_not_save_advisor(self):
        milestone = self.db.get(Milestone, 2)
        milestone.name = "Not configured"
        self.db.commit()
        self.assertEqual(self.declare().status_code, 409)
        self.assertIsNone(self.db.get(type(self.lisa), 6).advisor_id)

    def test_failed_commit_rolls_back_both_changes(self):
        with patch.object(self.db, "commit", side_effect=RuntimeError("Simulated database failure")):
            with self.assertRaises(RuntimeError):
                declare_advisor(self.db, 6, 1)
        self.assertIsNone(self.db.get(type(self.lisa), 6).advisor_id)
        self.assertIsNone(self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == 6, StudentMilestone.milestone_id == 2)))
