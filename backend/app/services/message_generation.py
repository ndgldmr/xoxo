"""
Message generation service containing business logic for AI-powered message creation.
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsException
from app.core.llm_client import LLMClient, LLMClientError
from app.models.message import Message
from app.schemas.message import MessageCreate
from app.services.message import MessageService

logger = logging.getLogger(__name__)


class MessageGenerationService:
    """
    Service layer for AI-powered message generation.
    Orchestrates LLM client, message service, and implements retry logic.
    """

    def __init__(self, db: AsyncSession, llm_client: LLMClient, max_retries: int = 1):
        """
        Initialize message generation service.

        Args:
            db: Async database session
            llm_client: LLM client for AI generation
            max_retries: Maximum number of retries on subject conflict (default: 1)
        """
        self.db = db
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.message_service = MessageService(db)

    async def _get_recent_subjects(self, limit: int = 10) -> list[str]:
        """
        Get list of recently used subjects to help AI avoid duplicates.

        Args:
            limit: Number of recent subjects to retrieve (default: 10)

        Returns:
            List of subject strings, ordered by most recent first
        """
        stmt = (
            select(Message.subject)
            .order_by(desc(Message.message_date))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        subjects = [row[0] for row in result.all()]
        logger.debug(f"Retrieved {len(subjects)} recent subjects for context")
        return subjects

    async def generate_for_date(
        self, *, message_date: date, category: Optional[str] = None
    ) -> Message:
        """
        Generate and create a new message for the specified date using AI.

        This method orchestrates the full generation flow:
        1. Validates date is not already used
        2. Retrieves recent subjects for context
        3. Calls LLM to generate content
        4. Retries on subject conflict (up to max_retries)
        5. Creates message via MessageService

        Args:
            message_date: Target date for the message (must be unique)
            category: Optional category slug (e.g., "everyday_phrases")

        Returns:
            Created Message instance

        Raises:
            AlreadyExistsException: If message_date already has a message or subject conflicts
            LLMClientError: If AI generation fails after retries
        """
        logger.info(
            f"Starting AI generation for date={message_date}, category={category}"
        )

        # Step 1: Check if message already exists for this date
        existing_message = await self.message_service.get_message_by_date(message_date)
        if existing_message:
            logger.warning(
                f"Message already exists for date {message_date} (id={existing_message.id})"
            )
            raise AlreadyExistsException(
                f"Message for date {message_date} already exists. "
                "Only one message per day is allowed."
            )

        # Step 2: Get recent subjects for context
        recent_subjects = await self._get_recent_subjects(limit=10)

        # Step 3: Attempt generation with retry logic
        exclude_subjects: list[str] = []
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            attempt_num = attempt + 1
            logger.debug(
                f"Generation attempt {attempt_num}/{self.max_retries + 1} "
                f"(excluded: {exclude_subjects})"
            )

            try:
                # Call LLM
                payload = await self.llm_client.generate_message_payload(
                    category=category,
                    recent_subjects=recent_subjects,
                    exclude_subjects=exclude_subjects if exclude_subjects else None,
                )

                logger.info(
                    f"LLM generated subject: '{payload.subject}' on attempt {attempt_num}"
                )

                # Check if subject already exists
                existing_with_subject = await self.message_service.get_message_by_subject(
                    payload.subject
                )

                if existing_with_subject:
                    logger.warning(
                        f"Subject '{payload.subject}' already exists (id={existing_with_subject.id})"
                    )

                    # If we have retries left, add to exclusion list and retry
                    if attempt < self.max_retries:
                        exclude_subjects.append(payload.subject)
                        logger.info(
                            f"Retrying generation with excluded subject: {payload.subject}"
                        )
                        continue
                    else:
                        # No more retries
                        logger.error(
                            f"Subject conflict after {self.max_retries + 1} attempts"
                        )
                        raise AlreadyExistsException(
                            f"Message with subject '{payload.subject}' already exists. "
                            f"Failed to generate unique subject after {self.max_retries + 1} attempts."
                        )

                # Success! Subject is unique, create the message
                logger.info(f"Subject '{payload.subject}' is unique, creating message")

                message_create = MessageCreate(
                    message_date=message_date,
                    category=category,
                    subject=payload.subject,
                    definition=payload.definition,
                    example=payload.example,
                    usage_tips=payload.usage_tips,
                    cultural_notes=payload.cultural_notes,
                )

                created_message = await self.message_service.create_message(
                    message_create
                )

                logger.info(
                    f"Successfully created message id={created_message.id} "
                    f"for date={message_date} with subject='{created_message.subject}'"
                )

                return created_message

            except LLMClientError as e:
                logger.error(
                    f"LLM generation failed on attempt {attempt_num}: "
                    f"{e.error_type} - {e.message}"
                )
                last_error = e

                # Don't retry on LLM errors (API timeout, parse errors, etc.)
                # These are unlikely to succeed on retry
                raise

            except AlreadyExistsException:
                # Re-raise AlreadyExistsException (handled above)
                raise

            except Exception as e:
                logger.error(
                    f"Unexpected error during generation attempt {attempt_num}: {e}",
                    exc_info=True,
                )
                last_error = e
                # Don't retry on unexpected errors
                raise

        # Should not reach here, but if we do, raise the last error
        if last_error:
            raise last_error
        else:
            raise RuntimeError(
                f"Message generation failed after {self.max_retries + 1} attempts "
                "for unknown reasons"
            )
