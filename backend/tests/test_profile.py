# Tests for student and faculty profiles.
# Run from backend: python -m unittest discover -s tests -v
# All data lives in an isolated in-memory database; Neon is never used.

# base64 encodes test pictures the same way the page does.
import base64

# unittest is Python's built-in test tool.
import unittest

# Reuse the same test users as the dashboard tests.
import test_student_dashboard as fixtures


# The optional fields a student can edit.
EDITABLE = (
    "research_interests",
    "lab_name",
    "education",
    "bio",
    "portfolio_url",
    "github_url",
    "scholar_url",
    "linkedin_url",
)

# The start of a valid-looking PNG file.
PNG = b"\x89PNG\r\n\x1a\n test picture"

# The start of a valid-looking JPG file.
JPG = b"\xff\xd8\xff test picture"


# ----------------------------------------------------------------------
# Student profile tests
# ----------------------------------------------------------------------


class ProfileTests(unittest.TestCase):
    # Reuse the dashboard tests' helper that builds a request's login header.
    headers = fixtures.DashboardTests.headers

    # Reuse the dashboard tests' helper that creates a test student.
    student = staticmethod(fixtures.DashboardTests.student)

    # Reuse the dashboard tests' helper that adds a milestone progress row.
    progress = fixtures.DashboardTests.progress

    # Reuse the dashboard tests' setup.
    setUp = fixtures.DashboardTests.setUp

    # Saves a profile for Lisa, and returns the response.
    def save(self, **changes):
        # Valid values, with this test's changes on top.
        body = dict(
            full_name="Lisa Lee",
            research_interests="Databases",
            lab_name="Data Lab",
            education="MS, UAlbany",
            bio="I study databases.",
            portfolio_url="https://example.org/lisa",
            github_url="https://github.com/lisa",
            scholar_url="https://scholar.google.com/citations?user=lisa",
            linkedin_url="https://www.linkedin.com/in/lisa",
        )

        # Apply the changes.
        body.update(changes)

        # Send the request.
        return self.client.put(
            "/api/students/me/profile",
            headers=self.headers(self.lisa),
            json=body,
        )

    # Only students can use the student profile endpoints.
    def test_only_students_can_use_it(self):
        # A faculty member tries to read a student profile.
        response = self.client.get(
            "/api/students/me/profile",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # A student with no saved profile sees their name and empty fields.
    def test_new_profile_is_empty(self):
        # Read the profile.
        data = self.client.get(
            "/api/students/me/profile",
            headers=self.headers(self.lisa),
        ).json()

        # The name and email come from the account.
        self.assertEqual(
            (
                data["full_name"],
                data["email"],
            ),
            (
                "Lisa",
                "lisa@test.edu",
            ),
        )

        # The rest is empty.
        self.assertEqual(
            [data[field] for field in EDITABLE],
            [None] * len(EDITABLE),
        )

    # The student's program details are shown from their account.
    def test_program_details_are_shown(self):
        # Read Sam's profile.
        data = self.client.get(
            "/api/students/me/profile",
            headers=self.headers(self.sam),
        ).json()

        # They match his account, including his advisor's name.
        self.assertEqual(
            (
                data["advisor_name"],
                data["start_term"],
                data["start_year"],
                data["enrollment_status"],
                data["advanced_standing"],
            ),
            (
                "Faculty",
                "fall",
                2023,
                "full_time",
                False,
            ),
        )

    # A student with no advisor shows none.
    def test_no_advisor_is_empty(self):
        # Lisa hasn't declared one in this test data.
        data = self.client.get(
            "/api/students/me/profile",
            headers=self.headers(self.lisa),
        ).json()

        self.assertIsNone(
            data["advisor_name"]
        )

    # Program details can't be changed through this form.
    def test_program_details_cannot_be_changed(self):
        # Trying to change the advisor is refused.
        self.assertEqual(
            self.save(
                advisor_name="Someone"
            ).status_code,
            422,
        )

        # Trying to change the enrollment is refused.
        self.assertEqual(
            self.save(
                enrollment_status="part_time"
            ).status_code,
            422,
        )

    # Saving keeps every field.
    def test_saving_keeps_every_field(self):
        # Save the profile.
        self.assertEqual(
            self.save().status_code,
            200,
        )

        # Read it back.
        data = self.client.get(
            "/api/students/me/profile",
            headers=self.headers(self.lisa),
        ).json()

        # Everything was saved.
        self.assertEqual(
            (
                data["full_name"],
                data["research_interests"],
                data["lab_name"],
                data["education"],
                data["bio"],
                data["portfolio_url"],
                data["github_url"],
                data["scholar_url"],
                data["linkedin_url"],
            ),
            (
                "Lisa Lee",
                "Databases",
                "Data Lab",
                "MS, UAlbany",
                "I study databases.",
                "https://example.org/lisa",
                "https://github.com/lisa",
                "https://scholar.google.com/citations?user=lisa",
                "https://www.linkedin.com/in/lisa",
            ),
        )

    # A new name shows everywhere, because it's saved on the account.
    def test_new_name_updates_the_account_and_dashboard(self):
        # Change the name.
        self.save(
            full_name="Lisa Marie Lee"
        )

        # The account has the new name.
        account = self.client.get(
            "/api/users/me",
            headers=self.headers(self.lisa),
        ).json()

        self.assertEqual(
            account["full_name"],
            "Lisa Marie Lee",
        )

        # The dashboard has the new name.
        dashboard = self.client.get(
            "/api/students/me/milestones",
            headers=self.headers(self.lisa),
        ).json()

        self.assertEqual(
            dashboard["student"]["full_name"],
            "Lisa Marie Lee",
        )

    # Saving twice updates the same profile.
    def test_saving_twice_updates_the_profile(self):
        # The first save.
        self.save()

        # The second save, with a change.
        response = self.save(
            bio="New biography."
        )

        self.assertEqual(
            response.json()["bio"],
            "New biography.",
        )

    # Optional fields can be cleared.
    def test_blank_fields_are_cleared(self):
        # The first save fills them in.
        self.save()

        # The second save blanks them.
        data = self.save(
            **{
                field: "  "
                for field in EDITABLE
            }
        ).json()

        # They're now empty.
        self.assertEqual(
            [data[field] for field in EDITABLE],
            [None] * len(EDITABLE),
        )

    # A name can't be empty.
    def test_name_cannot_be_empty(self):
        # Only spaces count as empty.
        self.assertEqual(
            self.save(
                full_name="   "
            ).status_code,
            422,
        )

    # Only ordinary web links are allowed, in all four link fields.
    def test_links_must_be_web_links(self):
        # Check each link field.
        for field in (
            "portfolio_url",
            "github_url",
            "scholar_url",
            "linkedin_url",
        ):
            # These aren't allowed, including one that could run code.
            for link in (
                "javascript:alert(1)",
                "example.org",
                "ftp://example.org",
                "https://",
            ):
                self.assertEqual(
                    self.save(
                        **{field: link}
                    ).status_code,
                    422,
                    f"{field}: {link}",
                )

    # Other account fields can't be changed through this form.
    def test_other_account_fields_cannot_be_changed(self):
        # Try to change the GPA.
        self.assertEqual(
            self.save(
                gpa="4.00"
            ).status_code,
            422,
        )

        # Try to change the email.
        self.assertEqual(
            self.save(
                email="new@test.edu"
            ).status_code,
            422,
        )

    # Saving only changes the logged-in student's own profile.
    def test_saving_only_changes_your_own_profile(self):
        # Lisa saves hers.
        self.save()

        # Sam's stays empty.
        data = self.client.get(
            "/api/students/me/profile",
            headers=self.headers(self.sam),
        ).json()

        self.assertIsNone(
            data["research_interests"]
        )

    # Uploads a picture for a student, and returns the response.
    def upload(self, data=PNG, user=None):
        # Lisa is the default student.
        return self.client.put(
            "/api/students/me/profile/picture",
            headers=self.headers(
                user or self.lisa
            ),
            json=dict(
                data_base64=base64.b64encode(
                    data
                ).decode()
            ),
        )

    # Reads a student's picture.
    def picture(self, user=None):
        # Lisa is the default student.
        return self.client.get(
            "/api/students/me/profile/picture",
            headers=self.headers(
                user or self.lisa
            ),
        )

    # A student with no picture gets an empty reply, not an error.
    def test_no_picture_is_an_empty_reply(self):
        # Nothing is sent.
        self.assertEqual(
            self.picture().status_code,
            204,
        )

    # Uploading a PNG works, and it can be read back.
    def test_png_can_be_uploaded_and_read(self):
        # The upload says she now has a picture.
        self.assertTrue(
            self.upload().json()["has_picture"]
        )

        # Read it back.
        response = self.picture()

        # She gets the original file, with the right type.
        self.assertEqual(
            (
                response.status_code,
                response.content,
                response.headers["content-type"],
            ),
            (
                200,
                PNG,
                "image/png",
            ),
        )

    # JPG pictures also work.
    def test_jpg_can_be_uploaded(self):
        # Upload one.
        self.upload(JPG)

        # It has the right type.
        self.assertEqual(
            self.picture().headers["content-type"],
            "image/jpeg",
        )

    # A new picture replaces the old one.
    def test_new_picture_replaces_the_old_one(self):
        # Upload a PNG.
        self.upload()

        # Upload a JPG.
        self.upload(JPG)

        # Only the JPG remains.
        self.assertEqual(
            self.picture().content,
            JPG,
        )

    # Other file types are refused, based on their contents.
    def test_other_file_types_are_refused(self):
        # SVG files can contain code, so they're refused.
        self.assertEqual(
            self.upload(
                b"<svg onload='alert(1)'></svg>"
            ).status_code,
            422,
        )

        # Plain text is refused.
        self.assertEqual(
            self.upload(
                b"just text"
            ).status_code,
            422,
        )

    # Pictures over 2 MB are refused.
    def test_large_picture_is_refused(self):
        # This PNG is one byte over the limit.
        large_picture = (
            PNG
            + b"x"
            * (
                2 * 1024 * 1024
                - len(PNG)
                + 1
            )
        )

        self.assertEqual(
            self.upload(
                large_picture
            ).status_code,
            422,
        )

    # Text that isn't valid base64 is refused.
    def test_unreadable_picture_is_refused(self):
        # Send invalid text.
        response = self.client.put(
            "/api/students/me/profile/picture",
            headers=self.headers(self.lisa),
            json=dict(
                data_base64="not base64!"
            ),
        )

        # It's refused.
        self.assertEqual(
            response.status_code,
            422,
        )

    # A picture can be removed.
    def test_picture_can_be_removed(self):
        # Upload one.
        self.upload()

        # Remove it.
        response = self.client.delete(
            "/api/students/me/profile/picture",
            headers=self.headers(self.lisa),
        )

        self.assertFalse(
            response.json()["has_picture"]
        )

        # It's gone.
        self.assertEqual(
            self.picture().status_code,
            204,
        )

    # Saving the profile keeps the picture.
    def test_saving_the_profile_keeps_the_picture(self):
        # Upload a picture.
        self.upload()

        # Save the other details.
        self.save()

        # The picture is still there.
        self.assertEqual(
            self.picture().content,
            PNG,
        )

    # A student only ever reaches their own picture.
    def test_pictures_are_separate_for_each_student(self):
        # Lisa uploads one.
        self.upload()

        # Sam has none.
        self.assertEqual(
            self.picture(
                self.sam
            ).status_code,
            204,
        )

    # Only students can use the picture endpoints.
    def test_only_students_can_use_pictures(self):
        # A faculty member is refused.
        self.assertEqual(
            self.picture(
                self.faculty
            ).status_code,
            403,
        )


# ----------------------------------------------------------------------
# Faculty profile tests
# ----------------------------------------------------------------------


class FacultyProfileTests(unittest.TestCase):
    # Reuse the dashboard tests' helper that builds a request's login header.
    headers = fixtures.DashboardTests.headers

    # The shared dashboard setup expects this student helper.
    student = staticmethod(fixtures.DashboardTests.student)

    # The shared dashboard setup also expects the progress helper.
    progress = fixtures.DashboardTests.progress

    # Reuse the same isolated database, users, and test client.
    setUp = fixtures.DashboardTests.setUp

    # Creates a complete valid faculty profile request.
    def faculty_profile_body(self, **changes):
        body = {
            "full_name": "Dr. Faculty Updated",
            "title": "Associate Professor",
            "department": "Computer Science",
            "affiliation": "University at Albany",
            "research_interests": "Machine Learning and Data Mining",
            "lab_name": "Intelligent Systems Lab",
            "accepting_students": True,
            "academic_url": "https://example.org/faculty",
            "bio": "I study machine learning and intelligent systems.",
        }

        body.update(changes)

        return body

    # A faculty member with no saved profile still sees
    # their account name and email.
    def test_new_faculty_profile_uses_account_information(self):
        response = self.client.get(
            "/api/faculty/me/profile",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["full_name"],
            self.faculty.full_name,
        )

        self.assertEqual(
            data["email"],
            self.faculty.email,
        )

        self.assertIsNone(
            data["title"]
        )

        self.assertIsNone(
            data["department"]
        )

        self.assertIsNone(
            data["affiliation"]
        )

        self.assertIsNone(
            data["research_interests"]
        )

        self.assertIsNone(
            data["lab_name"]
        )

        self.assertIsNone(
            data["accepting_students"]
        )

        self.assertIsNone(
            data["academic_url"]
        )

        self.assertIsNone(
            data["bio"]
        )

    # Faculty can save all of their profile information.
    def test_faculty_can_save_profile(self):
        response = self.client.put(
            "/api/faculty/me/profile",
            headers=self.headers(self.faculty),
            json=self.faculty_profile_body(),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["full_name"],
            "Dr. Faculty Updated",
        )

        self.assertEqual(
            data["email"],
            self.faculty.email,
        )

        self.assertEqual(
            data["title"],
            "Associate Professor",
        )

        self.assertEqual(
            data["department"],
            "Computer Science",
        )

        self.assertEqual(
            data["affiliation"],
            "University at Albany",
        )

        self.assertEqual(
            data["research_interests"],
            "Machine Learning and Data Mining",
        )

        self.assertEqual(
            data["lab_name"],
            "Intelligent Systems Lab",
        )

        self.assertTrue(
            data["accepting_students"]
        )

        self.assertEqual(
            data["academic_url"],
            "https://example.org/faculty",
        )

        self.assertEqual(
            data["bio"],
            "I study machine learning and intelligent systems.",
        )

    # Reading the profile after saving returns the saved information.
    def test_saved_faculty_profile_can_be_read_back(self):
        save_response = self.client.put(
            "/api/faculty/me/profile",
            headers=self.headers(self.faculty),
            json=self.faculty_profile_body(),
        )

        self.assertEqual(
            save_response.status_code,
            200,
        )

        response = self.client.get(
            "/api/faculty/me/profile",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["title"],
            "Associate Professor",
        )

        self.assertEqual(
            data["department"],
            "Computer Science",
        )

        self.assertEqual(
            data["affiliation"],
            "University at Albany",
        )

        self.assertEqual(
            data["research_interests"],
            "Machine Learning and Data Mining",
        )

        self.assertEqual(
            data["lab_name"],
            "Intelligent Systems Lab",
        )

        self.assertTrue(
            data["accepting_students"]
        )

        self.assertEqual(
            data["academic_url"],
            "https://example.org/faculty",
        )

    # Updating the faculty profile name also updates the user account.
    def test_faculty_profile_name_updates_account(self):
        response = self.client.put(
            "/api/faculty/me/profile",
            headers=self.headers(self.faculty),
            json=self.faculty_profile_body(
                full_name="Dr. New Faculty Name"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        account_response = self.client.get(
            "/api/users/me",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            account_response.status_code,
            200,
        )

        self.assertEqual(
            account_response.json()["full_name"],
            "Dr. New Faculty Name",
        )

    # Saving twice updates the existing faculty profile.
    def test_faculty_can_update_existing_profile(self):
        first_response = self.client.put(
            "/api/faculty/me/profile",
            headers=self.headers(self.faculty),
            json=self.faculty_profile_body(),
        )

        self.assertEqual(
            first_response.status_code,
            200,
        )

        second_response = self.client.put(
            "/api/faculty/me/profile",
            headers=self.headers(self.faculty),
            json=self.faculty_profile_body(
                title="Professor",
                bio="Updated faculty biography.",
                accepting_students=False,
            ),
        )

        self.assertEqual(
            second_response.status_code,
            200,
        )

        data = second_response.json()

        self.assertEqual(
            data["title"],
            "Professor",
        )

        self.assertEqual(
            data["bio"],
            "Updated faculty biography.",
        )

        self.assertFalse(
            data["accepting_students"]
        )
        

    # A student cannot read a faculty profile through the faculty endpoint.
    def test_student_cannot_read_faculty_profile(self):
        response = self.client.get(
            "/api/faculty/me/profile",
            headers=self.headers(self.lisa),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # A student cannot update a faculty profile.
    def test_student_cannot_update_faculty_profile(self):
        response = self.client.put(
            "/api/faculty/me/profile",
            headers=self.headers(self.lisa),
            json=self.faculty_profile_body(),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # Faculty profile endpoints require a logged-in user.
    def test_faculty_profile_requires_login(self):
        response = self.client.get(
            "/api/faculty/me/profile"
        )

        self.assertEqual(
            response.status_code,
            401,
        )


# Lets this file be run directly.
if __name__ == "__main__":
    # Run all the tests above.
    unittest.main()
