"""Validation rules for Word of the Day messages."""
import re
from typing import Dict, List, Tuple


class ValidationError(Exception):
    """Raised when message validation fails."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validation failed: {', '.join(errors)}")


class ParsedMessage:
    """Structured representation of a validated message."""

    def __init__(self, sections: Dict[str, str], raw_text: str):
        self.sections = sections
        self.raw_text = raw_text

    def __repr__(self):
        return f"ParsedMessage(sections={list(self.sections.keys())})"


# Expected headers in exact order
REQUIRED_HEADERS = [
    "🇺🇸 Word/Phrase of the Day:",
    "📝 Meaning (em português):",
    "🔊 Pronunciation:",
    "💡 When to use:",
    "📌 Example:",
]


def validate_message(text: str) -> Tuple[bool, ParsedMessage]:
    """
    Validate LLM-generated message against strict rules.

    Rules:
    1) Must contain all required headers exactly once, in order
    2) No extra headers or sections
    3) Each section must have non-empty content
    4) Word/Phrase: 1 line, <= 40 chars
    5) Pronunciation: 1 line, <= 40 chars
    6) Example: exactly 2 non-empty lines (English <= 120 chars, Portuguese <= 180 chars)
    7) No URLs (http://, https://, www.)
    8) No markdown symbols: *, #, ```
    9) Total length <= 1500 chars
    10) Basic language heuristics for word/phrase and examples

    Returns:
        Tuple of (is_valid, ParsedMessage)

    Raises:
        ValidationError: If validation fails, with list of error reasons
    """
    errors = []

    # Rule 9: Check total length
    if len(text) > 1500:
        errors.append(f"Message too long: {len(text)} chars (max 1500)")

    # Rule 7: Check for URLs
    if re.search(r"https?://|www\.", text, re.IGNORECASE):
        errors.append("Message contains URLs (not allowed)")

    # Rule 8: Check for markdown symbols
    forbidden_chars = ["*", "#", "```"]
    for char in forbidden_chars:
        if char in text:
            errors.append(f"Message contains forbidden markdown symbol: {char}")

    # Rule 1 & 2: Check headers are present in exact order
    sections = {}
    lines = text.split("\n")

    header_positions = []
    for i, line in enumerate(lines):
        for header in REQUIRED_HEADERS:
            if line.strip().startswith(header):
                header_positions.append((i, header, line.strip()))

    # Check all headers are present
    found_headers = [h for _, h, _ in header_positions]
    for header in REQUIRED_HEADERS:
        if header not in found_headers:
            errors.append(f"Missing required header: {header}")

    # Check headers appear in correct order
    if len(header_positions) == len(REQUIRED_HEADERS):
        for idx, (_, header, _) in enumerate(header_positions):
            if header != REQUIRED_HEADERS[idx]:
                errors.append(f"Headers not in correct order. Expected {REQUIRED_HEADERS[idx]}, found {header}")
                break

    # Check for duplicate headers
    if len(found_headers) != len(set(found_headers)):
        errors.append("Duplicate headers found")

    # Check for extra headers (lines with emojis that aren't our headers)
    for line in lines:
        stripped = line.strip()
        # Skip empty lines
        if not stripped:
            continue
        # Check if line starts with emoji but isn't a known header or content
        if re.match(r"^[\U0001F000-\U0001F9FF]", stripped):
            if stripped not in REQUIRED_HEADERS and not any(stripped.startswith(h) for h in REQUIRED_HEADERS):
                # Check if this is a header line (ends with colon)
                if ":" in stripped[:50]:  # Check first 50 chars
                    errors.append(f"Extra/unknown header found: {stripped[:40]}...")

    # If headers are correct, extract sections
    if len(header_positions) == len(REQUIRED_HEADERS) and not any("header" in e.lower() for e in errors):
        for idx, (line_idx, header, _) in enumerate(header_positions):
            # Find content between this header and next header (or end of text)
            start_idx = line_idx + 1
            end_idx = header_positions[idx + 1][0] if idx + 1 < len(header_positions) else len(lines)

            content_lines = [l for l in lines[start_idx:end_idx] if l.strip()]
            content = "\n".join(content_lines).strip()

            sections[header] = content

        # Rule 3: Check all sections have non-empty content
        for header, content in sections.items():
            if not content:
                errors.append(f"Empty content for section: {header}")

        # Rule 4: Word/Phrase validation
        if "🇺🇸 Word/Phrase of the Day:" in sections:
            word_phrase = sections["🇺🇸 Word/Phrase of the Day:"]
            if "\n" in word_phrase:
                errors.append("Word/Phrase must be a single line")
            if len(word_phrase) > 40:
                errors.append(f"Word/Phrase too long: {len(word_phrase)} chars (max 40)")
            # Rule 10: Should be mostly ASCII (basic English)
            ascii_ratio = sum(1 for c in word_phrase if ord(c) < 128) / len(word_phrase) if word_phrase else 0
            if ascii_ratio < 0.8:
                errors.append("Word/Phrase should be mostly ASCII characters")

        # Rule 5: Pronunciation validation
        if "🔊 Pronunciation:" in sections:
            pronunciation = sections["🔊 Pronunciation:"]
            if "\n" in pronunciation:
                errors.append("Pronunciation must be a single line")
            if len(pronunciation) > 40:
                errors.append(f"Pronunciation too long: {len(pronunciation)} chars (max 40)")

        # Rule 6: Example validation
        if "📌 Example:" in sections:
            example = sections["📌 Example:"]
            example_lines = [l.strip() for l in example.split("\n") if l.strip()]

            if len(example_lines) != 2:
                errors.append(f"Example must have exactly 2 lines (found {len(example_lines)})")
            else:
                english_line = example_lines[0]
                portuguese_line = example_lines[1]

                if len(english_line) > 120:
                    errors.append(f"English example too long: {len(english_line)} chars (max 120)")

                if len(portuguese_line) > 180:
                    errors.append(f"Portuguese example too long: {len(portuguese_line)} chars (max 180)")

                # Rule 10: English line should not have many accented characters
                accented_count = sum(1 for c in english_line if ord(c) > 127)
                if accented_count > len(english_line) * 0.1:
                    errors.append("English example has too many accented characters")

                # Rule 10: Portuguese line should have PT-BR indicators
                pt_tokens = ["que", "não", "para", "você", "uma", "um", "com", "por", "esta", "esse"]
                has_pt_token = any(token in portuguese_line.lower() for token in pt_tokens)
                has_accent = any(ord(c) > 127 for c in portuguese_line)

                if not (has_pt_token or has_accent):
                    errors.append("Portuguese example should contain Portuguese indicators (common words or accented characters)")

    if errors:
        raise ValidationError(errors)

    parsed = ParsedMessage(sections=sections, raw_text=text)
    return True, parsed


def validate_template_params(params: dict) -> Tuple[bool, dict]:
    """
    Validate template parameters for WhatsApp template messages.

    Template requires 6 parameters:
    - word_phrase: English word or phrase (max 40 chars, mostly ASCII)
    - meaning_pt: Meaning in Portuguese (no specific limits, but reasonable)
    - pronunciation: Pronunciation guide (max 40 chars)
    - when_to_use: When to use explanation (no specific limits, but reasonable)
    - example_pt: Portuguese example (max 180 chars, PT-BR indicators)
    - example_en: English example (max 120 chars, mostly ASCII)

    Validation rules:
    1) All 6 required keys must be present
    2) All values must be non-empty strings
    3) Character limits as specified above
    4) No URLs in any field
    5) No markdown symbols (*, #, ```) in any field
    6) Language heuristics for English vs Portuguese fields

    Args:
        params: Dict with template parameters

    Returns:
        Tuple of (is_valid, params)

    Raises:
        ValidationError: If validation fails, with list of error reasons
    """
    errors = []

    # Rule 1: Check all required keys are present
    required_keys = ["word_phrase", "meaning_pt", "pronunciation", "when_to_use", "example_pt", "example_en"]
    for key in required_keys:
        if key not in params:
            errors.append(f"Missing required parameter: {key}")

    # If keys are missing, can't proceed with further validation
    if errors:
        raise ValidationError(errors)

    # Rule 2: Check all values are non-empty strings
    for key, value in params.items():
        if not isinstance(value, str):
            errors.append(f"{key} must be a string, got {type(value).__name__}")
        elif not value.strip():
            errors.append(f"{key} cannot be empty")

    # Rule 3: Check character limits
    if len(params.get("word_phrase", "")) > 40:
        errors.append(f"word_phrase too long: {len(params['word_phrase'])} chars (max 40)")

    if len(params.get("pronunciation", "")) > 40:
        errors.append(f"pronunciation too long: {len(params['pronunciation'])} chars (max 40)")

    if len(params.get("example_en", "")) > 120:
        errors.append(f"example_en too long: {len(params['example_en'])} chars (max 120)")

    if len(params.get("example_pt", "")) > 180:
        errors.append(f"example_pt too long: {len(params['example_pt'])} chars (max 180)")

    # Reasonable limits for other fields (not strict, but prevent abuse)
    if len(params.get("meaning_pt", "")) > 300:
        errors.append(f"meaning_pt too long: {len(params['meaning_pt'])} chars (max 300)")

    if len(params.get("when_to_use", "")) > 300:
        errors.append(f"when_to_use too long: {len(params['when_to_use'])} chars (max 300)")

    # Rule 4: Check for URLs in any field
    url_pattern = r"https?://|www\."
    for key, value in params.items():
        if isinstance(value, str) and re.search(url_pattern, value, re.IGNORECASE):
            errors.append(f"{key} contains URLs (not allowed)")

    # Rule 5: Check for markdown symbols in any field
    forbidden_chars = ["*", "#", "```"]
    for key, value in params.items():
        if isinstance(value, str):
            for char in forbidden_chars:
                if char in value:
                    errors.append(f"{key} contains forbidden markdown symbol: {char}")

    # Rule 6: Language heuristics
    word_phrase = params.get("word_phrase", "")
    if word_phrase:
        ascii_ratio = sum(1 for c in word_phrase if ord(c) < 128) / len(word_phrase)
        if ascii_ratio < 0.8:
            errors.append("word_phrase should be mostly ASCII characters (English)")

    example_en = params.get("example_en", "")
    if example_en:
        accented_count = sum(1 for c in example_en if ord(c) > 127)
        if accented_count > len(example_en) * 0.1:
            errors.append("example_en has too many accented characters (should be English)")

    example_pt = params.get("example_pt", "")
    if example_pt:
        # Check for Portuguese indicators
        pt_tokens = ["que", "não", "para", "você", "uma", "um", "com", "por", "esta", "esse", "é", "de", "da", "do"]
        has_pt_token = any(token in example_pt.lower() for token in pt_tokens)
        has_accent = any(ord(c) > 127 for c in example_pt)

        if not (has_pt_token or has_accent):
            errors.append("example_pt should contain Portuguese indicators (common words or accented characters)")

    meaning_pt = params.get("meaning_pt", "")
    if meaning_pt:
        # Check for Portuguese indicators
        pt_tokens = ["que", "não", "para", "você", "uma", "um", "com", "por", "esta", "esse", "é", "de", "da", "do"]
        has_pt_token = any(token in meaning_pt.lower() for token in pt_tokens)
        has_accent = any(ord(c) > 127 for c in meaning_pt)

        if not (has_pt_token or has_accent):
            errors.append("meaning_pt should contain Portuguese indicators (common words or accented characters)")

    if errors:
        raise ValidationError(errors)

    return True, params
