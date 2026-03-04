"""LLM client for generating Word of the Day messages."""
import httpx
import json
from typing import Optional


class LLMError(Exception):
    """Raised when LLM API call fails."""
    pass


class LLMClient:
    """LLM client supporting OpenAI and Google Gemini APIs."""

    TEMPLATE_PARAMS_PROMPT = """You are generating content for XOXO Education's "English Word/Phrase of the Day" WhatsApp template for Brazilian Portuguese speakers learning English.

You must output a valid JSON object with exactly 6 fields:
{
  "word_phrase": "English word or phrase",
  "meaning_pt": "Clear explanation in Brazilian Portuguese",
  "pronunciation": "Simple phonetic pronunciation for Portuguese speakers",
  "when_to_use": "Short explanation in Brazilian Portuguese of when/where this is commonly used",
  "example_pt": "Example sentence in Brazilian Portuguese",
  "example_en": "Same example sentence in English"
}

CRITICAL REQUIREMENTS:
- Output ONLY valid JSON, no extra text or markdown formatting
- Do NOT include emojis, headers, or special formatting in any field
- "meaning_pt", "when_to_use", and "example_pt" MUST be written in Brazilian Portuguese
- "example_en" MUST be written in English
- Portuguese and English examples must be SEPARATE (not combined)
- Keep it simple and clear for language learners
- All text should be plain, conversational language"""

    BASE_PROMPT = """You are generating a WhatsApp message for XOXO Education's "English Word/Phrase of the Day" for Brazilian Portuguese speakers learning English.

You must output a WhatsApp-ready text message that follows EXACTLY this structure (no extra lines/sections):

🇺🇸 Word/Phrase of the Day:
<English word or phrase>

📝 Meaning (em português):
<Clear explanation in Brazilian Portuguese>

🔊 Pronunciation:
<Simple phonetic pronunciation adapted for Portuguese speakers>

💡 When to use:
<Short explanation of common situations where this word/phrase is used>

📌 Example:
<Example sentence in English>
<Same sentence translated into Brazilian Portuguese>

Do not include anything outside this structure."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
    ):
        """
        Initialize LLM client.

        Args:
            api_key: API key for authentication
            model: Model name to use
            base_url: Base URL for API endpoint
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Detect if using Gemini API
        self.is_gemini = "generativelanguage.googleapis.com" in base_url or model.startswith("gemini")

    def generate_message(
        self,
        theme: str = "daily life",
        level: str = "beginner",
        temperature: float = 0.7,
    ) -> str:
        """
        Generate a Word of the Day message.

        Args:
            theme: Topic theme (e.g., "work", "travel", "emotions", "daily life")
            level: Difficulty level ("beginner" or "intermediate")
            temperature: Sampling temperature for generation

        Returns:
            str: Generated message text

        Raises:
            LLMError: If API call fails
        """
        prompt = f"""{self.BASE_PROMPT}

Theme: {theme}
Level: {level}

Return ONLY the final message with the exact structure. No extra commentary."""

        if self.is_gemini:
            return self._generate_gemini(prompt, temperature)
        else:
            return self._generate_openai(prompt, temperature)

    def _generate_openai(self, prompt: str, temperature: float) -> str:
        """Generate using OpenAI-compatible API."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                    },
                )
                response.raise_for_status()

            data = response.json()
            message = data["choices"][0]["message"]["content"].strip()
            return message

        except httpx.TimeoutException as e:
            raise LLMError(f"Request timed out after {self.timeout}s: {e}")
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected API response format: {e}")
        except Exception as e:
            raise LLMError(f"LLM API call failed: {e}")

    def _generate_gemini(self, prompt: str, temperature: float) -> str:
        """Generate using Google Gemini API."""
        try:
            # Gemini API endpoint
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key,
                    },
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": temperature,
                            "maxOutputTokens": 2048,
                        }
                    },
                )
                response.raise_for_status()

            data = response.json()
            message = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return message

        except httpx.TimeoutException as e:
            raise LLMError(f"Request timed out after {self.timeout}s: {e}")
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected Gemini API response format: {e}")
        except Exception as e:
            raise LLMError(f"Gemini API call failed: {e}")

    def generate_repair_message(
        self,
        previous_output: str,
        validation_errors: list[str],
        theme: str = "daily life",
        level: str = "beginner",
    ) -> str:
        """
        Generate a repaired message after validation failure.

        Args:
            previous_output: The output that failed validation
            validation_errors: List of validation error messages
            theme: Topic theme
            level: Difficulty level

        Returns:
            str: Repaired message text

        Raises:
            LLMError: If API call fails
        """
        errors_text = "\n".join(f"- {err}" for err in validation_errors)

        repair_prompt = f"""Your previous output failed validation for these reasons:
{errors_text}

You must output a WhatsApp-ready text message that follows EXACTLY this structure (no extra lines/sections):

🇺🇸 Word/Phrase of the Day:
<English word or phrase>

📝 Meaning (em português):
<Clear explanation in Brazilian Portuguese>

🔊 Pronunciation:
<Simple phonetic pronunciation adapted for Portuguese speakers>

💡 When to use:
<Short explanation of common situations where this word/phrase is used>

📌 Example:
<Example sentence in English>
<Same sentence translated into Brazilian Portuguese>

Requirements:
- All headers must be present in this exact order
- No extra headers or sections
- No URLs, no markdown symbols (*, #, ```)
- Word/Phrase: single line, max 40 characters
- Pronunciation: single line, max 40 characters
- Example: exactly 2 lines (English max 120 chars, Portuguese max 180 chars)
- Total message max 1500 characters
- Portuguese text should use common PT-BR words or accented characters

Theme: {theme}
Level: {level}

Return ONLY the corrected final message with the exact structure. No extra commentary."""

        if self.is_gemini:
            return self._generate_gemini(repair_prompt, temperature=0.5)
        else:
            return self._generate_openai(repair_prompt, temperature=0.5)

    def generate_message_params(
        self,
        theme: str = "daily life",
        level: str = "beginner",
        temperature: float = 0.7,
    ) -> dict:
        """
        Generate Word of the Day template parameters (6 separate fields).

        Args:
            theme: Topic theme (e.g., "work", "travel", "emotions", "daily life")
            level: Difficulty level ("beginner" or "intermediate")
            temperature: Sampling temperature for generation

        Returns:
            dict: Template parameters with keys:
                - word_phrase: English word or phrase
                - meaning_pt: Meaning in Portuguese
                - pronunciation: Pronunciation guide
                - when_to_use: When/where to use it
                - example_pt: Example in Portuguese
                - example_en: Example in English

        Raises:
            LLMError: If API call fails or response is invalid
        """
        prompt = f"""{self.TEMPLATE_PARAMS_PROMPT}

Theme: {theme}
Level: {level}

Return ONLY the JSON object, no extra commentary or markdown formatting."""

        if self.is_gemini:
            response_text = self._generate_gemini(prompt, temperature)
        else:
            response_text = self._generate_openai(prompt, temperature)

        # Parse JSON from response
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            params = json.loads(response_text)

            # Validate all required keys are present
            required_keys = ["word_phrase", "meaning_pt", "pronunciation", "when_to_use", "example_pt", "example_en"]
            missing_keys = [key for key in required_keys if key not in params]
            if missing_keys:
                raise LLMError(f"Missing required keys in response: {missing_keys}")

            return params

        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse JSON response: {e}\nResponse: {response_text[:200]}")
        except Exception as e:
            raise LLMError(f"Failed to extract template parameters: {e}")

    def generate_repair_message_params(
        self,
        previous_output: dict,
        validation_errors: list[str],
        theme: str = "daily life",
        level: str = "beginner",
    ) -> dict:
        """
        Generate repaired template parameters after validation failure.

        Args:
            previous_output: The parameters dict that failed validation
            validation_errors: List of validation error messages
            theme: Topic theme
            level: Difficulty level

        Returns:
            dict: Repaired template parameters

        Raises:
            LLMError: If API call fails
        """
        errors_text = "\n".join(f"- {err}" for err in validation_errors)
        prev_json = json.dumps(previous_output, indent=2, ensure_ascii=False)

        repair_prompt = f"""Fix the following JSON so it passes all validation rules.

Validation errors to fix:
{errors_text}

Previous output:
{prev_json}

Rules:
- Output ONLY a valid JSON object with exactly these 6 keys: word_phrase, meaning_pt, pronunciation, when_to_use, example_pt, example_en
- word_phrase: English only, max 40 characters
- pronunciation: max 40 characters
- meaning_pt, when_to_use, example_pt: Brazilian Portuguese, use accented characters (ã, ç, é, etc.)
- example_en: English only, max 120 characters
- No markdown, no emojis, no URLs

Theme: {theme}, Level: {level}"""

        if self.is_gemini:
            response_text = self._generate_gemini(repair_prompt, temperature=0.5)
        else:
            response_text = self._generate_openai(repair_prompt, temperature=0.5)

        # Parse JSON from response
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            params = json.loads(response_text)

            # Validate all required keys are present
            required_keys = ["word_phrase", "meaning_pt", "pronunciation", "when_to_use", "example_pt", "example_en"]
            missing_keys = [key for key in required_keys if key not in params]
            if missing_keys:
                raise LLMError(f"Missing required keys in repaired response: {missing_keys}")

            return params

        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse repaired JSON response: {e}\nResponse: {response_text[:200]}")
        except Exception as e:
            raise LLMError(f"Failed to extract repaired template parameters: {e}")
