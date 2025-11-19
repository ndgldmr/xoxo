"""
User API endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.user import User, UserCreate, UserUpdate
from app.services.user import UserService

router = APIRouter()


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user.

    Args:
        user_data: User creation data
        db: Database session

    Returns:
        Created user

    Raises:
        409: If email already exists
    """
    service = UserService(db)
    return await service.create_user(user_data)


@router.get("/", response_model=list[User])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all users with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: If True, return only active users
        db: Database session

    Returns:
        List of users
    """
    service = UserService(db)
    if active_only:
        return await service.get_active_users(skip=skip, limit=limit)
    return await service.get_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific user by ID.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        User data

    Raises:
        404: If user not found
    """
    service = UserService(db)
    return await service.get_user(user_id)


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing user.

    Args:
        user_id: User ID
        user_data: User update data
        db: Database session

    Returns:
        Updated user

    Raises:
        404: If user not found
        409: If email change conflicts with existing user
    """
    service = UserService(db)
    return await service.update_user(user_id, user_data)


@router.delete("/{user_id}", response_model=User)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a user.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Deleted user

    Raises:
        404: If user not found
    """
    service = UserService(db)
    return await service.delete_user(user_id)


@router.post("/{user_id}/deactivate", response_model=User)
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate a user (soft delete).

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Deactivated user

    Raises:
        404: If user not found
    """
    service = UserService(db)
    return await service.deactivate_user(user_id)
