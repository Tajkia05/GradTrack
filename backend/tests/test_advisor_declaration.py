"""Advisor declaration uses the same isolated fixtures as the dashboard tests."""

import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import func, select

import test_student_dashboard as fixtures
from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
from app.modules.student.advisor_service import declare_advisor
from app.modules.faculty.models import FacultyProfile


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
        self.assertEqual(response.json(), [{"id": 1, "full_name": "Faculty", "email": "faculty@test.edu", "advisee_count": 2,
            "department": None, "affiliation": None, "research_interests": None,
            "lab_name": None, "accepting_students": None, "academic_url": None, "bio": None}])

    def test_profile_fields_are_returned_without_changing_advisee_count(self):
        fields = dict(department="Computer Science", affiliation="Test University", research_interests="Databases; AI",
                      lab_name="Test Lab", accepting_students=True, academic_url="https://example.org/faculty", bio="Test biography")
        self.db.add(FacultyProfile(user_id=1, **fields))
        self.db.commit()
        result = self.client.get("/api/students/me/advisors", headers=self.headers(self.lisa)).json()[0]
        for key, value in fields.items():
            self.assertEqual(result[key], value)
        self.assertEqual(result["advisee_count"], 2)
        self.assertEqual(self.declare().status_code, 200)

    def test_explicitly_unavailable_advisor_blocks_new_declaration(self):
        self.db.add(FacultyProfile(user_id=1, accepting_students=False))
        self.db.commit()
        self.assertEqual(self.declare().status_code, 409)
        self.assertIsNone(self.lisa.advisor_id)
        self.assertEqual(self.declare(user=self.sam).status_code, 200)

    def test_unknown_availability_remains_unknown_and_selectable(self):
        self.db.add(FacultyProfile(user_id=1))
        self.db.commit()
        result = self.client.get("/api/students/me/advisors", headers=self.headers(self.lisa)).json()[0]
        self.assertIsNone(result["accepting_students"])
        self.assertEqual(self.declare().status_code, 200)

    def test_one_profile_per_user(self):
        from sqlalchemy.exc import IntegrityError
        self.db.add(FacultyProfile(user_id=1))
        self.db.commit()
        self.db.add(FacultyProfile(user_id=1))
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_advisee_count_updates_after_declaration(self):
        self.assertEqual(self.declare().status_code, 200)
        response = self.client.get("/api/students/me/advisors", headers=self.headers(self.lisa))
        self.assertEqual(response.json()[0]["advisee_count"], 3)

    def test_completed_declaration_details_use_own_student_and_original_date(self):
        response = self.client.get("/api/students/me/advisor?student_id=7", headers=self.headers(self.sam))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["declared_on"], "2024-01-15")
        self.assertEqual(response.json()["advisor"]["id"], 1)
        self.assertNotIn("password_hash", response.text)

    def test_declaration_details_require_student_and_completed_declaration(self):
        path = "/api/students/me/advisor"
        self.assertEqual(self.client.get(path).status_code, 401)
        for user in [self.faculty, self.director]:
            self.assertEqual(self.client.get(path, headers=self.headers(user)).status_code, 403)
        self.assertEqual(self.client.get(path, headers=self.headers(self.lisa)).status_code, 404)
        self.assertEqual(self.declare().status_code, 200)
        self.assertEqual(self.client.get(path, headers=self.headers(self.lisa)).status_code, 200)

    def test_details_show_current_profile_and_preserve_unknown_date(self):
        self.db.add(FacultyProfile(user_id=1, department="Computer Science", accepting_students=False))
        row = self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == 5, StudentMilestone.milestone_id == 2))
        row.completed_on = None
        self.db.commit()
        response = self.client.get("/api/students/me/advisor", headers=self.headers(self.sam))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["declared_on"])
        self.assertEqual(response.json()["advisor"]["department"], "Computer Science")
        self.assertFalse(response.json()["advisor"]["accepting_students"])

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
        self.assertEqual(comps["blocked_reasons"], ["Committee formation must be completed."])
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
