# profile/router.py — THE API ENDPOINTS (URLs) FOR A STUDENT'S OWN PROFILE.

# APIRouter groups these endpoints, Depends supplies what each endpoint needs, and Response sends a file.
from fastapi import APIRouter, Depends, Response
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# get_db gives each request its own database session.
from app.core.database import get_db
# require_role only lets users with the given role through.
from app.core.deps import require_role
# The data formats these endpoints accept and return.
from app.modules.profile.schemas import PictureIn, ProfileIn, ProfileOut
# The functions that do the work.
from app.modules.profile.service import get_picture, get_profile, remove_picture, save_picture, save_profile
# Role is the list of user types, and User is the logged-in user.
from app.modules.users.models import Role, User

# Group these endpoints under "Profile" on the /docs page.
router = APIRouter(tags=["Profile"])


# GET /api/students/me/profile — the student's own profile.
@router.get("/students/me/profile", response_model=ProfileOut)
# This function runs when that URL is requested.
def my_profile(
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Return the profile.
    return get_profile(db, student)


# PUT /api/students/me/profile — save the student's own profile.
@router.put("/students/me/profile", response_model=ProfileOut)
# This function runs when that URL is requested.
def update_my_profile(
    # The new values.
    body: ProfileIn,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Save the profile and return it.
    return save_profile(db, student, body)


# GET /api/students/me/profile/picture — the student's own picture.
@router.get("/students/me/profile/picture")
# This function runs when that URL is requested.
def my_picture(
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Find the picture, if there is one.
    picture = get_picture(db, student)
    # Having no picture is normal, so 204 ("nothing to send") is used rather than an error.
    if picture is None:
        # Send an empty reply.
        return Response(status_code=204)
    # Send the picture, and don't let the browser guess its type.
    return Response(content=picture[0], media_type=picture[1], headers={"X-Content-Type-Options": "nosniff"})


# PUT /api/students/me/profile/picture — upload or replace the student's picture.
@router.put("/students/me/profile/picture", response_model=ProfileOut)
# This function runs when that URL is requested.
def upload_my_picture(
    # The picture.
    body: PictureIn,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Save the picture and return the updated profile.
    return save_picture(db, student, body)


# DELETE /api/students/me/profile/picture — remove the student's picture.
@router.delete("/students/me/profile/picture", response_model=ProfileOut)
# This function runs when that URL is requested.
def remove_my_picture(
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Remove the picture and return the updated profile.
    return remove_picture(db, student)
