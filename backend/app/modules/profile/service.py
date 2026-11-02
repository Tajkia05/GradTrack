# profile/service.py — READS AND SAVES A STUDENT'S PROFILE.

# base64 decodes the picture sent from the page, and binascii names its error.
import base64
import binascii

# HTTPException sends an error message back to the frontend.
from fastapi import HTTPException
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# The profile table.
from app.modules.profile.models import StudentProfileDetails
# The data formats this module returns and accepts.
from app.modules.profile.schemas import PictureIn, ProfileIn, ProfileOut
# User is the logged-in student.
from app.modules.users.models import User

# The optional details a student can edit, each saved in student_profiles.
EDITABLE_FIELDS = ("research_interests", "lab_name", "education", "bio", "portfolio_url", "github_url", "scholar_url", "linkedin_url")
# The largest picture allowed: 2 MB.
MAX_PICTURE_BYTES = 2 * 1024 * 1024
# The allowed picture types: {the bytes every such file starts with: browser type}. SVG isn't allowed, because it can contain code.
PICTURE_TYPES = {b"\x89PNG\r\n\x1a\n": "image/png", b"\xff\xd8\xff": "image/jpeg"}


# Finds the student's profile row, creating one in this save if it's their first time.
def _get_or_create_details(db: Session, student: User) -> StudentProfileDetails:
    # Find their row, if they have one.
    details = db.get(StudentProfileDetails, student.id)
    # Create one if not.
    if details is None:
        # Build the new row, using the student from the login token.
        details = StudentProfileDetails(user_id=student.id)
        # Add it to this save.
        db.add(details)
    # Return the row.
    return details


# Returns the student's profile. A student who hasn't saved one yet just has empty fields.
def get_profile(db: Session, student: User) -> ProfileOut:
    # Find their row, if they have one.
    details = db.get(StudentProfileDetails, student.id)
    # Find their advisor, if they've declared one.
    advisor = db.get(User, student.advisor_id) if student.advisor_id is not None else None
    # Copy each optional detail from the row, or leave it empty if there's no row.
    optional = {field: getattr(details, field) if details else None for field in EDITABLE_FIELDS}
    # Combine it with their name and email from the users table.
    return ProfileOut(full_name=student.full_name, email=student.email, **optional,
                      # Check the type, so the picture itself doesn't have to load.
                      has_picture=details is not None and details.picture_type is not None,
                      # The details the student can see but not edit.
                      advisor_name=advisor.full_name if advisor else None, start_term=student.start_term, start_year=student.start_year,
                      # The rest of those details.
                      enrollment_status=student.enrollment_status, advanced_standing=student.advanced_standing)


# Saves the logged-in student's profile.
def save_profile(db: Session, student: User, body: ProfileIn) -> ProfileOut:
    # Update their name in the users table.
    student.full_name = body.full_name
    # Find or create their row.
    details = _get_or_create_details(db, student)
    # Go through each optional detail.
    for field in EDITABLE_FIELDS:
        # Copy the new value onto the row.
        setattr(details, field, getattr(body, field))
    # Save the name and the details together.
    db.commit()
    # Return the saved profile.
    return get_profile(db, student)


# Saves the logged-in student's picture, replacing any earlier one.
def save_picture(db: Session, student: User, body: PictureIn) -> ProfileOut:
    # Decode the picture's contents.
    try:
        # Decode the text back into the original file.
        data = base64.b64decode(body.data_base64, validate=True)
    # The text wasn't valid.
    except binascii.Error:
        # 422 means the submitted data isn't valid.
        raise HTTPException(422, "This picture couldn't be read. Try choosing it again.")
    # Pictures over the limit are refused.
    if len(data) > MAX_PICTURE_BYTES:
        # Tell the student the limit.
        raise HTTPException(422, "The picture must be 2 MB or smaller.")
    # Find the type from the file's actual contents, not its name.
    picture_type = next((kind for signature, kind in PICTURE_TYPES.items() if data.startswith(signature)), None)
    # Anything else is refused.
    if picture_type is None:
        # Tell the student which types work.
        raise HTTPException(422, "The picture must be a PNG or JPG file.")
    # Find or create their row.
    details = _get_or_create_details(db, student)
    # Store the picture.
    details.picture = data
    # Store its type.
    details.picture_type = picture_type
    # Save the change.
    db.commit()
    # Return the updated profile.
    return get_profile(db, student)


# Removes the logged-in student's picture.
def remove_picture(db: Session, student: User) -> ProfileOut:
    # Find their row, if they have one.
    details = db.get(StudentProfileDetails, student.id)
    # Only a row with a picture needs changing.
    if details is not None:
        # Clear the picture.
        details.picture = None
        # Clear its type.
        details.picture_type = None
        # Save the change.
        db.commit()
    # Return the updated profile.
    return get_profile(db, student)


# Returns the logged-in student's (picture, type), or None if they don't have one.
def get_picture(db: Session, student: User) -> tuple[bytes, str] | None:
    # Find their row, if they have one.
    details = db.get(StudentProfileDetails, student.id)
    # Return the picture if there is one.
    return (details.picture, details.picture_type) if details is not None and details.picture_type else None
