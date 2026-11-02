# main.py — THE STARTING POINT of the backend.
# Run it with:  uvicorn app.main:app --reload
# Then open http://localhost:8000/docs to see and test every endpoint.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.users.router import router as users_router
from app.modules.student.router import router as student_router
from app.modules.faculty.router import router as faculty_router
# The student coursework endpoints.
from app.modules.coursework.router import router as coursework_router
# The student committee endpoints.
from app.modules.committee.router import router as committee_router
# The endpoint for reading notifications.
from app.modules.notifications.router import router as notifications_router
# The milestone submission and document endpoints.
from app.modules.submissions.router import router as submissions_router
# The student profile endpoints.
from app.modules.profile.router import router as profile_router

# Create the backend app.
app = FastAPI(title="GradTrack API")

# CORS: allow our React app (running on a different port) to call this API.
# Without this, the browser would block the requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Plug in each module's endpoints, all starting with /api.
# Example: users router's "/users" becomes "/api/users".
# When a NEW module is added (e.g. student), import its router above and add it here.
app.include_router(users_router, prefix="/api")
app.include_router(student_router, prefix="/api")
app.include_router(faculty_router, prefix="/api")
# Plug in the coursework endpoints, which also start with /api.
app.include_router(coursework_router, prefix="/api")
# Plug in the committee endpoints.
app.include_router(committee_router, prefix="/api")
# Plug in the notifications endpoint.
app.include_router(notifications_router, prefix="/api")
# Plug in the milestone submission endpoints.
app.include_router(submissions_router, prefix="/api")
# Plug in the student profile endpoints.
app.include_router(profile_router, prefix="/api")


# A simple "is the server running?" check. Visit /api/health to test.
@app.get("/api/health")
def health():
    return {"status": "ok"}
