"""Service layer for Word of the Day message generation and sending."""
import time
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.domain.validators import validate_template_params, ValidationError
from app.domain.fallback import get_fallback_template_params
from app.integrations.llm_client import LLMClient, LLMError
from app.integrations.wasender_client import WaSenderClient, WhatsAppError
from app.logging.audit_log import AuditLog


class WordOfDayService:
    """Orchestrates Word of the Day message generation, validation, and sending."""

    def __init__(
        self,
        llm_client: LLMClient,
        whatsapp_client: WaSenderClient,
        audit_log: AuditLog,
        db_session: Optional[Session] = None,
        to_number: Optional[str] = None,
        send_delay: float = 0.5,
    ):
        """
        Initialize service.

        Recipient modes:
        - Multi-recipient: if db_session is provided, sends to all active students
        - Single-recipient: if to_number is provided, sends to one number

        Args:
            llm_client: LLM client for content generation
            whatsapp_client: WaSenderAPI client for sending
            audit_log: Audit log for tracking sends
            db_session: Database session (enables multi-recipient mode)
            to_number: Destination number (for single-recipient mode)
            send_delay: Seconds to wait between sends in multi-recipient mode
        """
        self.llm_client = llm_client
        self.whatsapp_client = whatsapp_client
        self.audit_log = audit_log
        self.db_session = db_session
        self.to_number = to_number
        self.send_delay = send_delay

        self.use_multi_recipient = db_session is not None

        if not self.use_multi_recipient and not self.to_number:
            raise ValueError("to_number is required for single-recipient mode")

    def run_daily_job(
        self,
        theme: str = "daily life",
        level: str = "beginner",
        force: bool = False,
    ) -> Dict:
        """
        Run the daily Word of the Day job.

        Workflow:
        1. Check if already sent today (unless force=True)
        2. Generate 6 template parameters with LLM
        3. Validate parameters
        4. If invalid, retry with repair prompt (up to 2 retries)
        5. If still invalid, use fallback parameters
        6. Get recipients (all active DB students, or single to_number)
        7. Send to each recipient with delay between sends
        8. Log each send

        Args:
            theme: Topic theme for content generation
            level: Difficulty level ("beginner" or "intermediate")
            force: If True, send even if already sent today

        Returns:
            Dict with:
            - status: "success", "partial", "skipped", or "error"
            - sent_count, failed_count, total_recipients
            - date, used_fallback, validation_errors, preview
            - sends: list of per-recipient results
        """
        from datetime import date

        if not force and self.audit_log.was_sent_today():
            return {
                "status": "skipped",
                "sent_count": 0,
                "failed_count": 0,
                "total_recipients": 0,
                "date": None,
                "used_fallback": False,
                "validation_errors": ["Message already sent today. Use force=true to send anyway."],
                "preview": None,
                "sends": [],
            }

        # Step 1: Generate and validate content
        params, validation_errors, used_fallback = self._generate_and_validate(
            theme=theme, level=level
        )

        # Step 2: Get recipients
        recipients = self._get_recipients()

        if not recipients:
            return {
                "status": "error",
                "sent_count": 0,
                "failed_count": 0,
                "total_recipients": 0,
                "date": date.today().isoformat(),
                "used_fallback": used_fallback,
                "validation_errors": ["No recipients found"],
                "preview": None,
                "sends": [],
            }

        # Step 3: Send to each recipient
        sends = []
        sent_count = 0
        failed_count = 0

        for idx, recipient in enumerate(recipients):
            if idx > 0:
                time.sleep(self.send_delay)

            send_result = self._send_to_recipient(
                recipient=recipient,
                params=params,
                theme=theme,
                level=level,
                used_fallback=used_fallback,
            )
            sends.append(send_result)

            if send_result["sent"]:
                sent_count += 1
            else:
                failed_count += 1

        if sent_count == len(recipients):
            status = "success"
        elif sent_count > 0:
            status = "partial"
        else:
            status = "error"

        return {
            "status": status,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "total_recipients": len(recipients),
            "date": date.today().isoformat(),
            "used_fallback": used_fallback,
            "validation_errors": validation_errors,
            "preview": f"Word: {params.get('word_phrase', 'N/A')}",
            "sends": sends if self.use_multi_recipient else sends[0] if sends else None,
        }

    def _generate_and_validate(
        self, theme: str, level: str
    ) -> tuple[dict, List[str], bool]:
        """
        Generate and validate 6 template parameters with LLM retry logic.

        Returns:
            (params dict, validation_errors list, used_fallback bool)
        """
        params = None
        validation_errors = []
        used_fallback = False
        valid = False

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                if attempt == 0:
                    try:
                        params = self.llm_client.generate_message_params(
                            theme=theme, level=level
                        )
                    except LLMError as e:
                        print(f"LLM generation failed: {e}")
                        params = None
                        break
                else:
                    try:
                        params = self.llm_client.generate_repair_message_params(
                            previous_output=params,
                            validation_errors=validation_errors,
                            theme=theme,
                            level=level,
                        )
                    except LLMError as e:
                        print(f"LLM repair failed on attempt {attempt}: {e}")
                        break

                valid, _ = validate_template_params(params)
                validation_errors = []
                break

            except ValidationError as e:
                validation_errors = e.errors
                print(
                    f"Validation failed (attempt {attempt + 1}/{max_retries + 1}): {validation_errors}"
                )
                if attempt >= max_retries:
                    break

        if not valid or params is None:
            print("Using fallback content")
            params = get_fallback_template_params()
            used_fallback = True
            validation_errors = []

        return params, validation_errors, used_fallback

    def _get_recipients(self) -> List[Dict]:
        """Return a list of recipient dicts with phone_number, first_name."""
        if self.use_multi_recipient:
            from app.repositories.student import StudentRepository
            repo = StudentRepository(self.db_session)
            students = repo.get_active_subscribers()
            return [
                {
                    "phone_number": s.phone_number,
                    "student_id": s.phone_number,
                    "first_name": s.first_name,
                }
                for s in students
            ]
        return [{"phone_number": self.to_number, "student_id": None, "first_name": None}]

    def _send_to_recipient(
        self,
        recipient: Dict,
        params: dict,
        theme: str,
        level: str,
        used_fallback: bool,
    ) -> Dict:
        """Send to a single recipient and log the event."""
        phone_number = recipient["phone_number"]
        student_id = recipient.get("student_id")
        first_name = recipient.get("first_name")

        provider_message_id = None
        provider_response = None
        sent = False
        error_message = None

        content_variables = {
            "1": params["word_phrase"],
            "2": params["meaning_pt"],
            "3": params["pronunciation"],
            "4": params["when_to_use"],
            "5": params["example_pt"],
            "6": params["example_en"],
        }

        try:
            response = self.whatsapp_client.send_template_message(
                to_number=phone_number,
                content_sid="",  # Not used by WaSenderAPI
                content_variables=content_variables,
            )
            provider_message_id = response["sid"]
            provider_response = response
            sent = True
            print(f"Sent to {phone_number} — ID: {response['sid']}, status: {response['status']}")
        except WhatsAppError as e:
            error_message = str(e)
            print(f"Failed to send to {phone_number}: {e}")

        self.audit_log.log_event(
            theme=theme,
            level=level,
            valid=True,
            sent=sent,
            provider="wasender",
            provider_message_id=provider_message_id,
            used_fallback=used_fallback,
            provider_response=provider_response,
            student_id=student_id,
            phone_number=phone_number,
            template_params=params,
        )

        return {
            "phone_number": phone_number,
            "student_id": student_id,
            "first_name": first_name,
            "sent": sent,
            "provider_message_id": provider_message_id,
            "error_message": error_message,
        }

    def preview_message(
        self,
        theme: str = "daily life",
        level: str = "beginner",
    ) -> Dict:
        """
        Generate and validate parameters without sending.

        Returns:
            Dict with valid, content (the 6-param dict), and validation_errors
        """
        try:
            params = self.llm_client.generate_message_params(theme=theme, level=level)
            try:
                validate_template_params(params)
                return {"valid": True, "content": params, "validation_errors": []}
            except ValidationError as e:
                return {"valid": False, "content": params, "validation_errors": e.errors}
        except LLMError as e:
            return {
                "valid": False,
                "content": None,
                "validation_errors": [f"LLM generation failed: {e}"],
            }
