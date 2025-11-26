"""
LLM client abstraction for AI-powered message generation.
Provides a provider-agnostic interface with implementations for mock and real providers.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.core.prompts import build_message_generation_prompt
from app.schemas.message_generation import MessageGenerationPayload

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    def __init__(self, error_type: str, message: str, details: Optional[dict] = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)


class LLMClient(ABC):
    """
    Abstract base class for LLM clients.
    Defines the interface that all provider implementations must follow.
    """

    @abstractmethod
    async def generate_message_payload(
        self,
        *,
        category: Optional[str] = None,
        recent_subjects: Optional[list[str]] = None,
        exclude_subjects: Optional[list[str]] = None,
    ) -> MessageGenerationPayload:
        """
        Generate message content using the LLM.

        Args:
            category: Optional category slug for context
            recent_subjects: List of recently used subjects to avoid
            exclude_subjects: List of subjects to explicitly exclude (retry scenario)

        Returns:
            Validated MessageGenerationPayload

        Raises:
            LLMClientError: If generation fails for any reason
        """
        pass


class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing and development.
    Returns deterministic, valid payloads without making external API calls.
    """

    def __init__(
        self,
        *,
        subjects_pool: Optional[list[str]] = None,
        fail_on_subjects: Optional[list[str]] = None,
    ):
        """
        Initialize mock client.

        Args:
            subjects_pool: Pool of subjects to cycle through (default: predefined list)
            fail_on_subjects: List of subjects that should trigger a conflict (for testing retries)
        """
        self.subjects_pool = subjects_pool or [
            "Break the ice",
            "Piece of cake",
            "Hit the books",
            "Once in a blue moon",
            "Better late than never",
            "Call it a day",
            "Get the ball rolling",
            "Speak of the devil",
            "The best of both worlds",
            "See eye to eye",
        ]
        self.fail_on_subjects = fail_on_subjects or []
        self._call_count = 0

    async def generate_message_payload(
        self,
        *,
        category: Optional[str] = None,
        recent_subjects: Optional[list[str]] = None,
        exclude_subjects: Optional[list[str]] = None,
    ) -> MessageGenerationPayload:
        """
        Generate a mock message payload.

        Args:
            category: Optional category (influences subject selection)
            recent_subjects: Subjects to avoid
            exclude_subjects: Subjects to explicitly exclude

        Returns:
            Valid MessageGenerationPayload

        Raises:
            LLMClientError: If all subjects in pool are excluded (simulates failure)
        """
        logger.debug(
            f"MockLLMClient.generate_message_payload called (call #{self._call_count + 1})"
        )
        logger.debug(f"  category: {category}")
        logger.debug(f"  recent_subjects: {recent_subjects}")
        logger.debug(f"  exclude_subjects: {exclude_subjects}")

        # Build exclusion list
        all_excluded = set()
        if recent_subjects:
            all_excluded.update(recent_subjects)
        if exclude_subjects:
            all_excluded.update(exclude_subjects)

        # Find available subject
        available_subjects = [s for s in self.subjects_pool if s not in all_excluded]

        if not available_subjects:
            raise LLMClientError(
                error_type="AI_SUBJECT_EXHAUSTED",
                message="No available subjects after applying exclusions",
                details={
                    "pool_size": len(self.subjects_pool),
                    "excluded_count": len(all_excluded),
                },
            )

        # Select subject (use call count for deterministic cycling)
        subject = available_subjects[self._call_count % len(available_subjects)]
        self._call_count += 1

        # Build payload based on subject
        payload = MessageGenerationPayload(
            subject=subject,
            definition=f"A common English idiom meaning something related to {subject.lower()}",
            example=f'She said, "{subject}" and everyone understood immediately.',
            usage_tips=f"Use '{subject}' in casual conversations to sound more natural. It's widely understood in English-speaking countries.",
            cultural_notes=(
                f"The phrase '{subject}' is commonly used in everyday English conversation."
                if category
                else None
            ),
        )

        logger.debug(f"MockLLMClient generated subject: {subject}")
        return payload


class OpenAIClient(LLMClient):
    """
    OpenAI-compatible LLM client.
    Supports OpenAI API and OpenRouter (which uses OpenAI-compatible endpoints).
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        max_tokens: int = 500,
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: API key for authentication
            model: Model identifier (e.g., "gpt-4o-mini", "gpt-3.5-turbo")
            base_url: API base URL (use OpenRouter URL for OpenRouter)
            timeout: Request timeout in seconds
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens

    async def generate_message_payload(
        self,
        *,
        category: Optional[str] = None,
        recent_subjects: Optional[list[str]] = None,
        exclude_subjects: Optional[list[str]] = None,
    ) -> MessageGenerationPayload:
        """
        Generate message payload using OpenAI API.

        Args:
            category: Optional category slug
            recent_subjects: Recently used subjects to avoid
            exclude_subjects: Subjects to explicitly exclude

        Returns:
            Validated MessageGenerationPayload

        Raises:
            LLMClientError: If API call fails or response is invalid
        """
        # Build prompt
        prompt = build_message_generation_prompt(
            category=category,
            recent_subjects=recent_subjects,
            exclude_subjects=exclude_subjects,
        )

        logger.debug(f"OpenAIClient calling model: {self.model}")
        logger.debug(f"Prompt:\n{prompt}")

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert English teacher creating educational content. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": self.max_tokens,
        }

        # Make API call
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

            response_data = response.json()
            logger.debug(f"OpenAI response status: {response.status_code}")

        except httpx.TimeoutException as e:
            logger.error(f"OpenAI API timeout: {e}")
            raise LLMClientError(
                error_type="AI_TIMEOUT",
                message=f"OpenAI API request timed out after {self.timeout}s",
                details={"timeout": self.timeout},
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API HTTP error: {e.response.status_code} - {e.response.text}")
            raise LLMClientError(
                error_type="AI_API_ERROR",
                message=f"OpenAI API returned error: {e.response.status_code}",
                details={
                    "status_code": e.response.status_code,
                    "response": e.response.text[:200],
                },
            )
        except Exception as e:
            logger.error(f"OpenAI API unexpected error: {e}")
            raise LLMClientError(
                error_type="AI_NETWORK_ERROR",
                message=f"Failed to connect to OpenAI API: {str(e)}",
                details={"error": str(e)},
            )

        # Extract content
        try:
            content = response_data["choices"][0]["message"]["content"]
            logger.debug(f"Raw LLM response:\n{content}")
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid OpenAI response structure: {response_data}")
            raise LLMClientError(
                error_type="AI_RESPONSE_FORMAT_ERROR",
                message="OpenAI response missing expected fields",
                details={"error": str(e)},
            )

        # Parse JSON
        try:
            # Strip potential markdown code blocks
            content = content.strip()
            if content.startswith("```"):
                # Remove ```json or ``` prefix
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

            json_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {content}")
            raise LLMClientError(
                error_type="AI_JSON_PARSE_ERROR",
                message="Failed to parse LLM response as JSON",
                details={"parse_error": str(e), "content_preview": content[:200]},
            )

        # Validate with Pydantic
        try:
            payload = MessageGenerationPayload(**json_data)
            logger.info(f"Successfully generated message with subject: {payload.subject}")
            return payload
        except Exception as e:
            logger.error(f"Failed to validate LLM response: {e}")
            raise LLMClientError(
                error_type="AI_VALIDATION_ERROR",
                message=f"LLM response failed validation: {str(e)}",
                details={"validation_error": str(e), "json_data": json_data},
            )
