"""Fallback message for when LLM generation fails."""

FALLBACK_MESSAGE = """🇺🇸 Word/Phrase of the Day:
Hello

📝 Meaning (em português):
Uma saudação comum usada para cumprimentar alguém.

🔊 Pronunciation:
heh-LOH

💡 When to use:
Use this greeting when meeting someone, starting a conversation, or answering the phone. It's appropriate in both formal and informal situations.

📌 Example:
Hello! How are you today?
Olá! Como você está hoje?"""


FALLBACK_TEMPLATE_PARAMS = {
    "word_phrase": "Hello",
    "meaning_pt": "Uma saudação comum usada para cumprimentar alguém.",
    "pronunciation": "heh-LOH",
    "when_to_use": "Use this greeting when meeting someone, starting a conversation, or answering the phone.",
    "example_pt": "Olá! Como você está hoje?",
    "example_en": "Hello! How are you today?",
}


def get_fallback_message() -> str:
    """
    Return a deterministic fallback message.

    This message is guaranteed to pass validation and is used when:
    - LLM API fails or times out
    - Validation fails after all retry attempts

    Returns:
        str: A valid Word of the Day message
    """
    return FALLBACK_MESSAGE


def get_fallback_template_params() -> dict:
    """
    Return deterministic fallback template parameters.

    This parameter set is guaranteed to pass validation and is used when:
    - LLM API fails or times out
    - Validation fails after all retry attempts

    Returns:
        dict: Valid template parameters with keys:
              word_phrase, meaning_pt, pronunciation, when_to_use, example_pt, example_en
    """
    return FALLBACK_TEMPLATE_PARAMS.copy()
