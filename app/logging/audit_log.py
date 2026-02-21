"""Audit logging for Word of the Day message sends."""
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List


class AuditLog:
    """JSONL-based audit log for tracking message sends."""

    def __init__(self, log_path: str = "audit_log.jsonl"):
        """
        Initialize audit log.

        Args:
            log_path: Path to JSONL audit log file
        """
        self.log_path = Path(log_path)
        # Create file if it doesn't exist
        self.log_path.touch(exist_ok=True)

    def log_event(
        self,
        theme: str,
        level: str,
        valid: bool,
        sent: bool,
        message_text: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        provider: str = "wasender",
        provider_message_id: Optional[str] = None,
        used_fallback: bool = False,
        provider_response: Optional[dict] = None,
        student_id: Optional[str] = None,
        phone_number: Optional[str] = None,
        template_params: Optional[dict] = None,
    ) -> None:
        """
        Log a message send event.

        Args:
            theme: Theme used for generation
            level: Level used for generation
            valid: Whether the message passed validation
            sent: Whether the message was successfully sent
            message_text: The message that was sent (plain text mode)
            validation_errors: List of validation errors (if any)
            provider: WhatsApp provider (default: "wasender")
            provider_message_id: Message ID from provider
            used_fallback: Whether fallback message was used
            provider_response: Full response from provider for debugging
            student_id: Student ID (for multi-recipient mode)
            phone_number: Phone number of recipient
            template_params: Template parameters dict
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "date": date.today().isoformat(),
            "theme": theme,
            "level": level,
            "valid": valid,
            "sent": sent,
            "used_fallback": used_fallback,
            "provider": provider,
            "provider_message_id": provider_message_id,
            "errors": validation_errors or [],
            "provider_response": provider_response or {},
        }

        # Add optional fields (for backward compatibility)
        if message_text is not None:
            event["text"] = message_text

        if student_id is not None:
            event["student_id"] = student_id

        if phone_number is not None:
            event["phone_number"] = phone_number

        if template_params is not None:
            event["template_params"] = template_params

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def get_today_events(self) -> List[dict]:
        """
        Get all events logged for today.

        Returns:
            List of event dictionaries for today's date
        """
        today = date.today().isoformat()
        events = []

        if not self.log_path.exists():
            return events

        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    if event.get("date") == today:
                        events.append(event)

        return events

    def was_sent_today(self) -> bool:
        """
        Check if a message was already sent today.

        Returns:
            bool: True if a message was sent today
        """
        today_events = self.get_today_events()
        return any(event.get("sent", False) for event in today_events)
