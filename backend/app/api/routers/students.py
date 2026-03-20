"""Student CRUD endpoints."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_jwt, normalize_phone
from app.api.schemas import StudentCreate, StudentUpdate, StudentResponse
from app.integrations.wasender_client import WaSenderClient
from app.config import get_settings
from app.repositories.student import StudentRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/students", tags=["students"])

_auth = [Depends(verify_jwt)]


def _to_response(s) -> StudentResponse:
    return StudentResponse(
        phone_number=s.phone_number,
        first_name=s.first_name,
        last_name=s.last_name,
        english_level=s.english_level,
        whatsapp_messages=s.whatsapp_messages,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("", response_model=List[StudentResponse], dependencies=_auth)
async def list_students(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    """List all students."""
    repo = StudentRepository(db)
    return [_to_response(s) for s in repo.list_all(include_inactive=include_inactive)]


@router.post("", response_model=StudentResponse, status_code=201, dependencies=_auth)
async def create_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
):
    """Add a new student and send a welcome WhatsApp message if opted in."""
    repo = StudentRepository(db)
    if repo.get_by_phone(student.phone_number):
        raise HTTPException(status_code=409, detail="Student with this phone number already exists")

    new_student = repo.create(
        phone_number=student.phone_number,
        first_name=student.first_name,
        last_name=student.last_name,
        english_level=student.english_level,
        whatsapp_messages=student.whatsapp_messages,
    )

    if new_student.whatsapp_messages:
        try:
            settings = get_settings()
            whatsapp = WaSenderClient(api_key=settings.wasender_api_key, dry_run=settings.dry_run)
            whatsapp.send_welcome_message(
                to_number=new_student.phone_number,
                first_name=new_student.first_name,
            )
        except Exception as e:
            logger.warning("Welcome message failed for %s: %s", new_student.phone_number, e)

    return _to_response(new_student)


@router.get("/{phone_number}", response_model=StudentResponse, dependencies=_auth)
async def get_student(
    phone_number: str,
    db: Session = Depends(get_db),
):
    """Get a single student by phone number."""
    try:
        phone_number = normalize_phone(phone_number)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    repo = StudentRepository(db)
    student = repo.get_by_phone(phone_number)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return _to_response(student)


@router.patch("/{phone_number}", response_model=StudentResponse, dependencies=_auth)
async def update_student(
    phone_number: str,
    body: StudentUpdate,
    db: Session = Depends(get_db),
):
    """Update a student's name, level, or WhatsApp opt-in status."""
    try:
        phone_number = normalize_phone(phone_number)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields provided to update")

    repo = StudentRepository(db)
    student = repo.update(phone_number, updates)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return _to_response(student)


@router.post("/{phone_number}/deactivate", response_model=StudentResponse, dependencies=_auth)
async def deactivate_student(
    phone_number: str,
    db: Session = Depends(get_db),
):
    """Soft-delete a student (sets is_active=false, preserves record)."""
    try:
        phone_number = normalize_phone(phone_number)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    repo = StudentRepository(db)
    student = repo.get_by_phone(phone_number)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    repo.deactivate(phone_number)
    return _to_response(repo.get_by_phone(phone_number))


@router.post("/{phone_number}/reactivate", response_model=StudentResponse, dependencies=_auth)
async def reactivate_student(
    phone_number: str,
    db: Session = Depends(get_db),
):
    """Reactivate a previously deactivated student."""
    try:
        phone_number = normalize_phone(phone_number)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    repo = StudentRepository(db)
    student = repo.get_by_phone(phone_number)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    repo.reactivate(phone_number)
    return _to_response(repo.get_by_phone(phone_number))


@router.delete("/{phone_number}", status_code=204, dependencies=_auth)
async def delete_student(
    phone_number: str,
    db: Session = Depends(get_db),
):
    """Permanently delete a student record (hard delete)."""
    try:
        phone_number = normalize_phone(phone_number)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    repo = StudentRepository(db)
    if not repo.delete(phone_number):
        raise HTTPException(status_code=404, detail="Student not found")
