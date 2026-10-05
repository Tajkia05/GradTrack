# seed.py — CREATES THE DATABASE TABLES AND SOME TEST USERS.
# Run it from the backend folder:   python seed.py
# Safe to run more than once: it skips users that already exist.
#
# Teammates: add sample data for your modules here too (e.g. sample requirements).

from app.core.database import Base, SessionLocal, engine
from app.modules.users import service
from app.modules.users.models import Role

# One test account per role. FOR DEVELOPMENT ONLY — never use these passwords for real.
TEST_USERS = [
    ("student@gradtrack.edu", "Sam Student", Role.STUDENT),
    ("faculty@gradtrack.edu", "Fiona Faculty", Role.FACULTY),
    ("director@gradtrack.edu", "Dana Director", Role.DIRECTOR),
]
TEST_PASSWORD = "password123"


def main():
    # 1. Create any tables that don't exist yet (based on all the models.py files).
    Base.metadata.create_all(engine)

    # 2. Add the test users.
    with SessionLocal() as db:
        for email, name, role in TEST_USERS:
            if service.get_user_by_email(db, email):
                print(f"  exists:  {email}")
            else:
                service.create_user(db, email, name, role, TEST_PASSWORD)
                print(f"  created: {email}  ({role.value})")
    print(f"Done. Test password for all users: {TEST_PASSWORD}")


if __name__ == "__main__":
    main()
