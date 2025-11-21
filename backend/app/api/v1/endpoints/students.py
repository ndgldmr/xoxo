"""
Student API endpoints.

All student management endpoints require admin privileges.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin
from app.models.user import User as UserModel
from app.schemas.student import Student, StudentCreate, StudentUpdate
from app.services.student import StudentService

router = APIRouter()


@router.post("/", response_model=Student, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: StudentCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Create a new student (admin only).

    Requires admin privileges. Students are NOT system users - they have no login credentials.

    Args:
        student_data: Student creation data
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Created student

    Raises:
        401: If not authenticated
        403: If not admin
        409: If email or phone number already exists
        422: If validation fails (email format, E.164 phone format)
    """
    service = StudentService(db)
    return await service.create_student(student_data)


@router.get("/", response_model=list[Student])
async def get_students(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    active_only: bool = Query(
        False, description="If true, return only active students"
    ),
    email: Optional[str] = Query(
        None, description="Filter by email (exact match, case-insensitive)"
    ),
    name: Optional[str] = Query(
        None, description="Filter by first or last name (substring match)"
    ),
    country: Optional[str] = Query(
        None, description="Filter by country (exact match, case-insensitive)"
    ),
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Get all students with pagination and optional filters (admin only).

    Supports pagination and multiple filter options to narrow down results.

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (1-1000)
        active_only: If True, return only active students
        email: Filter by exact email (case-insensitive)
        name: Filter by first or last name (substring search)
        country: Filter by country (exact match, case-insensitive)
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        List of students matching filters

    Raises:
        401: If not authenticated
        403: If not admin
    """
    service = StudentService(db)
    return await service.get_students(
        skip=skip,
        limit=limit,
        active_only=active_only,
        email=email,
        name=name,
        country=country,
    )


@router.get("/{student_id}", response_model=Student)
async def get_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Get a specific student by ID (admin only).

    Args:
        student_id: Student ID
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Student data

    Raises:
        401: If not authenticated
        403: If not admin
        404: If student not found
    """
    service = StudentService(db)
    return await service.get_student(student_id)


@router.put("/{student_id}", response_model=Student)
async def update_student(
    student_id: int,
    student_data: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Update an existing student (admin only).

    All fields are optional - only provided fields will be updated.

    Args:
        student_id: Student ID
        student_data: Student update data
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Updated student

    Raises:
        401: If not authenticated
        403: If not admin
        404: If student not found
        409: If email or phone number change conflicts with existing student
        422: If validation fails (email format, E.164 phone format)
    """
    service = StudentService(db)
    return await service.update_student(student_id, student_data)


@router.delete("/{student_id}", response_model=Student)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Soft delete a student (admin only).

    This performs a soft delete by setting is_active=False. The student record
    remains in the database but is marked as inactive.

    Args:
        student_id: Student ID
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Deactivated student

    Raises:
        401: If not authenticated
        403: If not admin
        404: If student not found
    """
    service = StudentService(db)
    return await service.delete_student(student_id)


@router.post("/{student_id}/activate", response_model=Student)
async def activate_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Activate a student (admin only).

    Reactivates a previously deactivated student by setting is_active=True.

    Args:
        student_id: Student ID
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Activated student

    Raises:
        401: If not authenticated
        403: If not admin
        404: If student not found
    """
    service = StudentService(db)
    return await service.activate_student(student_id)
