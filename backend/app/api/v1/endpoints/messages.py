"""
Message API endpoints.

All message management endpoints require admin privileges.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin
from app.models.user import User as UserModel
from app.schemas.message import Message, MessageCreate, MessageUpdate
from app.services.message import MessageService

router = APIRouter()


@router.post("/", response_model=Message, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Create a new message (admin only).

    Creates a daily message with English word/phrase and learning content.

    **Business Rules:**
    - `subject` must be globally unique across all messages
    - `message_date` must be unique (one message per day)
    - `category` is normalized to slug format (e.g., "Black History Month" -> "black_history_month")

    Args:
        message_data: Message creation data
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Created message

    Raises:
        401: If not authenticated
        403: If not admin
        409: If subject or message_date already exists
        422: If validation fails (empty required fields, invalid date)
    """
    service = MessageService(db)
    return await service.create_message(message_data)


@router.get("/", response_model=list[Message])
async def get_messages(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    active_only: bool = Query(
        True, description="If true, return only active messages (default: true)"
    ),
    category: Optional[str] = Query(
        None, description="Filter by category (exact match)"
    ),
    message_date: Optional[date] = Query(
        None, description="Filter by message date (exact match, format: YYYY-MM-DD)"
    ),
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Get all messages with pagination and optional filters (admin only).

    Returns messages ordered by message_date descending (most recent first).

    **Filters:**
    - `active_only`: Filter for active/inactive messages
    - `category`: Exact category match
    - `message_date`: Exact date match

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (1-1000)
        active_only: If True, return only active messages (default: True)
        category: Filter by category (exact match)
        message_date: Filter by message_date (exact match)
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        List of messages matching filters, ordered by date descending

    Raises:
        401: If not authenticated
        403: If not admin
    """
    service = MessageService(db)
    return await service.get_messages(
        skip=skip,
        limit=limit,
        active_only=active_only,
        category=category,
        message_date=message_date,
    )


@router.get("/{message_id}", response_model=Message)
async def get_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Get a specific message by ID (admin only).

    Args:
        message_id: Message ID
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Message data

    Raises:
        401: If not authenticated
        403: If not admin
        404: If message not found
    """
    service = MessageService(db)
    return await service.get_message(message_id)


@router.put("/{message_id}", response_model=Message)
async def update_message(
    message_id: int,
    message_data: MessageUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Update an existing message (admin only).

    All fields are optional - only provided fields will be updated.
    Admins can update any field including `subject` and `message_date`.

    **Business Rules:**
    - If changing `subject`, new subject must be unique
    - If changing `message_date`, new date must be unique (one message per day)
    - `category` is normalized to slug format if provided

    Args:
        message_id: Message ID
        message_data: Message update data
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Updated message

    Raises:
        401: If not authenticated
        403: If not admin
        404: If message not found
        409: If subject or message_date change conflicts with existing message
        422: If validation fails
    """
    service = MessageService(db)
    return await service.update_message(message_id, message_data)


@router.delete("/{message_id}", response_model=Message)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Soft delete a message (admin only).

    This performs a soft delete by setting is_active=False. The message record
    remains in the database but is marked as inactive.

    Args:
        message_id: Message ID
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Deactivated message

    Raises:
        401: If not authenticated
        403: If not admin
        404: If message not found
    """
    service = MessageService(db)
    return await service.delete_message(message_id)


@router.post("/{message_id}/activate", response_model=Message)
async def activate_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    """
    Activate a message (admin only).

    Reactivates a previously deactivated message by setting is_active=True.

    Args:
        message_id: Message ID
        db: Database session
        admin_user: Current authenticated admin user

    Returns:
        Activated message

    Raises:
        401: If not authenticated
        403: If not admin
        404: If message not found
    """
    service = MessageService(db)
    return await service.activate_message(message_id)
