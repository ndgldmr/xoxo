"""Tests for message validators."""
import pytest
from app.domain.validators import validate_message, ValidationError


# Valid message for testing
VALID_MESSAGE = """🇺🇸 Word/Phrase of the Day:
Good morning

📝 Meaning (em português):
Uma saudação usada pela manhã para cumprimentar alguém.

🔊 Pronunciation:
gud MOR-ning

💡 When to use:
Use this greeting from sunrise until noon when you meet someone or start a conversation.

📌 Example:
Good morning! Did you sleep well?
Bom dia! Você dormiu bem?"""


def test_valid_message_passes():
    """Test that a properly formatted message passes validation."""
    valid, parsed = validate_message(VALID_MESSAGE)
    assert valid is True
    assert len(parsed.sections) == 5
    assert "🇺🇸 Word/Phrase of the Day:" in parsed.sections
    assert parsed.sections["🇺🇸 Word/Phrase of the Day:"] == "Good morning"


def test_missing_header_fails():
    """Test that missing a required header causes validation failure."""
    # Missing pronunciation header
    message = """🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
Uma saudação comum.

💡 When to use:
Always.

📌 Example:
Hello there!
Olá!"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("Missing required header" in err for err in exc_info.value.errors)


def test_wrong_order_fails():
    """Test that headers in wrong order cause validation failure."""
    # Pronunciation before Meaning
    message = """🇺🇸 Word/Phrase of the Day:
Hello

🔊 Pronunciation:
heh-LOH

📝 Meaning (em português):
Uma saudação.

💡 When to use:
Always.

📌 Example:
Hello!
Olá!"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("not in correct order" in err for err in exc_info.value.errors)


def test_extra_section_fails():
    """Test that extra sections cause validation failure."""
    message = """🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
Uma saudação.

🔊 Pronunciation:
heh-LOH

💡 When to use:
Always.

🎯 Extra Section:
This should not be here.

📌 Example:
Hello!
Olá!"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("Extra" in err or "unknown" in err.lower() for err in exc_info.value.errors)


def test_url_fails():
    """Test that URLs in message cause validation failure."""
    message = """🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
Uma saudação. Veja mais em https://example.com

🔊 Pronunciation:
heh-LOH

💡 When to use:
Always.

📌 Example:
Hello!
Olá!"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("URL" in err for err in exc_info.value.errors)


def test_markdown_fails():
    """Test that markdown symbols cause validation failure."""
    message = """🇺🇸 Word/Phrase of the Day:
**Hello**

📝 Meaning (em português):
Uma saudação.

🔊 Pronunciation:
heh-LOH

💡 When to use:
Always.

📌 Example:
Hello!
Olá!"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("markdown" in err.lower() or "*" in err for err in exc_info.value.errors)


def test_example_not_two_lines_fails():
    """Test that example section must have exactly 2 lines."""
    # Only one line in example
    message = """🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
Uma saudação.

🔊 Pronunciation:
heh-LOH

💡 When to use:
Always.

📌 Example:
Hello! How are you?"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("exactly 2 lines" in err for err in exc_info.value.errors)

    # Three lines in example
    message_three = """🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
Uma saudação.

🔊 Pronunciation:
heh-LOH

💡 When to use:
Always.

📌 Example:
Hello!
Olá!
Extra line"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message_three)

    assert any("exactly 2 lines" in err for err in exc_info.value.errors)


def test_word_phrase_too_long_fails():
    """Test that word/phrase exceeding 40 chars fails."""
    message = """🇺🇸 Word/Phrase of the Day:
This is a very long phrase that exceeds forty characters

📝 Meaning (em português):
Uma frase muito longa.

🔊 Pronunciation:
long phrase

💡 When to use:
Never.

📌 Example:
This is long.
Isso é longo."""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("too long" in err and "Word/Phrase" in err for err in exc_info.value.errors)


def test_pronunciation_too_long_fails():
    """Test that pronunciation exceeding 40 chars fails."""
    message = """🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
Uma saudação.

🔊 Pronunciation:
This pronunciation guide is way too long and exceeds forty characters

💡 When to use:
Always.

📌 Example:
Hello!
Olá!"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("too long" in err and "Pronunciation" in err for err in exc_info.value.errors)


def test_empty_section_fails():
    """Test that empty section content fails."""
    message = """🇺🇸 Word/Phrase of the Day:

📝 Meaning (em português):
Uma saudação.

🔊 Pronunciation:
heh-LOH

💡 When to use:
Always.

📌 Example:
Hello!
Olá!"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("Empty content" in err for err in exc_info.value.errors)


def test_message_too_long_fails():
    """Test that message exceeding 1500 chars fails."""
    # Create a very long message (need to exceed 1500 total chars)
    long_meaning = "Esta é uma explicação muito longa em português. " * 30  # ~1500 chars
    message = f"""🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
{long_meaning}

🔊 Pronunciation:
heh-LOH

💡 When to use:
Always and everywhere you go, in every situation imaginable.

📌 Example:
Hello there, how are you doing today my friend?
Olá, como você está hoje meu amigo?"""

    # Verify message is actually over 1500 chars
    assert len(message) > 1500, f"Test message is only {len(message)} chars"

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("too long" in err and "1500" in err for err in exc_info.value.errors)


def test_english_example_too_long_fails():
    """Test that English example exceeding 120 chars fails."""
    long_english = "A" * 121
    message = f"""🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
Uma saudação.

🔊 Pronunciation:
heh-LOH

💡 When to use:
Always.

📌 Example:
{long_english}
Olá!"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("English example too long" in err for err in exc_info.value.errors)


def test_portuguese_example_too_long_fails():
    """Test that Portuguese example exceeding 180 chars fails."""
    long_portuguese = "A" * 181
    message = f"""🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
Uma saudação.

🔊 Pronunciation:
heh-LOH

💡 When to use:
Always.

📌 Example:
Hello!
{long_portuguese}"""

    with pytest.raises(ValidationError) as exc_info:
        validate_message(message)

    assert any("Portuguese example too long" in err for err in exc_info.value.errors)
