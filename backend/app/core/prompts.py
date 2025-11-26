"""
Prompt templates for AI-powered message generation.
Stores and manages structured prompts for LLM interactions.
"""

from typing import Optional


def build_message_generation_prompt(
    *,
    category: Optional[str] = None,
    recent_subjects: Optional[list[str]] = None,
    exclude_subjects: Optional[list[str]] = None,
) -> str:
    """
    Build a structured prompt for generating Message of the Day content.

    This prompt targets CEFR A2-B1 English level (beginner-intermediate) with a
    friendly, encouraging tone suitable for XOXO Education's adult learners.

    Args:
        category: Optional category slug (e.g., "everyday_phrases", "black_history_month")
        recent_subjects: List of recently used subjects to help avoid repeats
        exclude_subjects: List of subjects to explicitly avoid (used on retry)

    Returns:
        Complete prompt string ready to send to LLM
    """
    # Base context
    prompt_parts = [
        "You are an expert English teacher creating daily learning content for adult English learners.",
        "Your target audience includes beginner to intermediate learners (CEFR A2-B1 level).",
        "Your tone should be friendly, encouraging, and clear.",
        "",
    ]

    # Category context
    if category:
        category_display = category.replace("_", " ").title()
        prompt_parts.append(
            f"Today's focus: Create content in the category '{category_display}'."
        )
        prompt_parts.append("")

    # Task description
    prompt_parts.extend(
        [
            "Generate a daily English learning message with the following components:",
            "1. SUBJECT: An English word or short phrase (2-4 words maximum)",
            "2. DEFINITION: A clear, simple definition in plain English",
            "3. EXAMPLE: A practical example sentence showing natural usage",
            "4. USAGE_TIPS: 1-2 sentences with helpful tips about when/how to use it",
            "5. CULTURAL_NOTES: Optional 1-2 sentences about cultural context or nuances",
            "",
        ]
    )

    # Constraints
    constraints = [
        "IMPORTANT CONSTRAINTS:",
        "- Choose subjects that are practical and useful for everyday communication",
        "- Keep language simple and accessible (avoid complex vocabulary in definitions)",
        "- Make examples realistic and relatable to adult learners",
        "- Focus on commonly used words and phrases",
    ]

    # Add recent subjects context
    if recent_subjects:
        subjects_list = ", ".join(f'"{s}"' for s in recent_subjects[:10])
        constraints.append(
            f"- Avoid these recently used subjects: {subjects_list}"
        )

    # Add explicit exclusions (for retry scenario)
    if exclude_subjects:
        exclude_list = ", ".join(f'"{s}"' for s in exclude_subjects)
        constraints.append(
            f"- DO NOT use these subjects (they conflict): {exclude_list}"
        )

    prompt_parts.extend(constraints)
    prompt_parts.append("")

    # Output format instructions
    prompt_parts.extend(
        [
            "CRITICAL: You MUST respond with ONLY valid JSON in this exact format:",
            "{",
            '  "subject": "your word or phrase",',
            '  "definition": "clear, simple definition",',
            '  "example": "A natural example sentence showing usage.",',
            '  "usage_tips": "Helpful tips about when and how to use it.",',
            '  "cultural_notes": "Optional cultural context or null"',
            "}",
            "",
            "Do NOT include any text before or after the JSON.",
            "Do NOT use markdown code blocks or backticks.",
            "Respond with ONLY the raw JSON object.",
        ]
    )

    return "\n".join(prompt_parts)


# Example usage (for documentation/testing):
EXAMPLE_PROMPT = build_message_generation_prompt(
    category="everyday_phrases",
    recent_subjects=["Hello", "Goodbye", "Thank you"],
)

EXAMPLE_EXPECTED_RESPONSE = """{
  "subject": "How are you?",
  "definition": "A friendly question asking about someone's wellbeing or current state",
  "example": "Hi Sarah! How are you? I haven't seen you in a while.",
  "usage_tips": "Use this as a casual greeting after saying hello. It shows genuine interest in the other person. Common responses include 'I'm good, thanks!' or 'Pretty well, how about you?'",
  "cultural_notes": "In English-speaking cultures, this is often a greeting rather than a literal question. People typically give brief positive responses even if they're not feeling great."
}"""
