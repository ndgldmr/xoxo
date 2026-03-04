"""Service layer for Word of the Day message generation and sending."""
import time
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.domain.validators import validate_template_params, ValidationError
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
        fallback_llm_client: Optional[LLMClient] = None,
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
        self.fallback_llm_client = fallback_llm_client
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

        In multi-recipient mode, recipients are grouped by their english_level and
        separate content is generated for each level. The level parameter is only
        used in single-recipient mode.

        Args:
            theme: Topic theme for content generation
            level: Difficulty level — only used in single-recipient mode
            force: If True, send even if already sent today

        Returns:
            Dict with:
            - status: "success", "partial", "skipped", or "error"
            - sent_count, failed_count, total_recipients
            - date, used_fallback, validation_errors, preview
            - sends: list of per-recipient results (dict in single-recipient mode)
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

        recipients = self._get_recipients()

        if not recipients:
            return {
                "status": "error",
                "sent_count": 0,
                "failed_count": 0,
                "total_recipients": 0,
                "date": date.today().isoformat(),
                "used_fallback": False,
                "validation_errors": ["No recipients found"],
                "preview": None,
                "sends": [],
            }

        if self.use_multi_recipient:
            return self._run_by_level(theme=theme, recipients=recipients)

        # Single-recipient mode: use the provided level
        params, validation_errors, used_fallback = self._generate_and_validate(
            theme=theme, level=level
        )
        if params is None:
            return {
                "status": "error",
                "sent_count": 0,
                "failed_count": 1,
                "total_recipients": 1,
                "date": date.today().isoformat(),
                "used_fallback": False,
                "validation_errors": validation_errors,
                "preview": None,
                "sends": [],
            }
        send_result = self._send_to_recipient(
            recipient=recipients[0],
            params=params,
            theme=theme,
            level=level,
            used_fallback=used_fallback,
        )
        return {
            "status": "success" if send_result["sent"] else "error",
            "sent_count": 1 if send_result["sent"] else 0,
            "failed_count": 0 if send_result["sent"] else 1,
            "total_recipients": 1,
            "date": date.today().isoformat(),
            "used_fallback": used_fallback,
            "validation_errors": validation_errors,
            "preview": f"Word: {params.get('word_phrase', 'N/A')}",
            "sends": send_result,
        }

    def _run_by_level(self, theme: str, recipients: List[Dict]) -> Dict:
        """
        Group recipients by english_level, generate level-appropriate content
        for each group, and send. Called only in multi-recipient mode.
        """
        from collections import defaultdict
        from datetime import date

        groups: Dict[str, List[Dict]] = defaultdict(list)
        for r in recipients:
            groups[r["english_level"]].append(r)

        sends: List[Dict] = []
        sent_count = 0
        failed_count = 0
        any_fallback = False
        all_validation_errors: List[str] = []
        previews: List[str] = []
        is_first_send = True

        for lvl, group in groups.items():
            params, validation_errors, used_fallback = self._generate_and_validate(
                theme=theme, level=lvl
            )
            any_fallback = any_fallback or used_fallback
            all_validation_errors.extend(validation_errors)

            if params is None:
                for recipient in group:
                    sends.append({
                        "phone_number": recipient["phone_number"],
                        "student_id": recipient.get("student_id"),
                        "first_name": recipient.get("first_name"),
                        "sent": False,
                        "provider_message_id": None,
                        "error_message": validation_errors[0] if validation_errors else "LLM unavailable",
                    })
                    failed_count += 1
                continue

            previews.append(f"{lvl}: {params.get('word_phrase', 'N/A')}")

            for recipient in group:
                if not is_first_send:
                    time.sleep(self.send_delay)
                is_first_send = False

                send_result = self._send_to_recipient(
                    recipient=recipient,
                    params=params,
                    theme=theme,
                    level=lvl,
                    used_fallback=used_fallback,
                )
                sends.append(send_result)
                if send_result["sent"]:
                    sent_count += 1
                else:
                    failed_count += 1

        total = len(recipients)
        if sent_count == total:
            status = "success"
        elif sent_count > 0:
            status = "partial"
        else:
            status = "error"

        return {
            "status": status,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "total_recipients": total,
            "date": date.today().isoformat(),
            "used_fallback": any_fallback,
            "validation_errors": all_validation_errors,
            "preview": " | ".join(previews) if previews else None,
            "sends": sends,
        }

    def _generate_and_validate(
        self, theme: str, level: str
    ) -> tuple[dict, List[str], bool]:
        """
        Generate and validate 6 template parameters.

        Attempt order:
          1. Primary LLM (with built-in 503 retries)
          2. Fallback LLM if primary raises LLMError (e.g. still unavailable after retries)
          3. Hardcoded fallback content

        After obtaining params from any LLM, validation failures trigger up to
        two repair attempts using whichever client succeeded.

        Returns:
            (params dict, validation_errors list, used_fallback bool)
        """
        # Step 1: get initial params from primary LLM
        params = None
        active_client = None
        try:
            params = self.llm_client.generate_message_params(theme=theme, level=level)
            active_client = self.llm_client
        except LLMError as e:
            print(f"LLM generation failed: {e}")
            if self.fallback_llm_client:
                print(f"Trying fallback model ({self.fallback_llm_client.model})...")
                try:
                    params = self.fallback_llm_client.generate_message_params(
                        theme=theme, level=level
                    )
                    active_client = self.fallback_llm_client
                except LLMError as e2:
                    print(f"Fallback LLM also failed: {e2}")

        if params is None:
            return None, ["LLM unavailable — message not sent"], False

        # Step 2: validate and repair (up to 2 repair attempts)
        max_retries = 2
        validation_errors = []
        for attempt in range(max_retries + 1):
            try:
                validate_template_params(params)
                return params, [], False
            except ValidationError as e:
                validation_errors = e.errors
                print(
                    f"Validation failed (attempt {attempt + 1}/{max_retries + 1}): {validation_errors}"
                )
                if attempt >= max_retries:
                    break
                try:
                    params = active_client.generate_repair_message_params(
                        previous_output=params,
                        validation_errors=validation_errors,
                        theme=theme,
                        level=level,
                    )
                except LLMError as e:
                    print(f"LLM repair failed on attempt {attempt + 1}: {e}")
                    break

        return None, validation_errors, False

    def _get_recipients(self) -> List[Dict]:
        """Return a list of recipient dicts with phone_number, first_name, english_level."""
        if self.use_multi_recipient:
            from app.repositories.student import StudentRepository
            repo = StudentRepository(self.db_session)
            students = repo.get_active_subscribers()
            return [
                {
                    "phone_number": s.phone_number,
                    "student_id": s.phone_number,
                    "first_name": s.first_name,
                    "english_level": s.english_level,
                }
                for s in students
            ]
        return [
            {
                "phone_number": self.to_number,
                "student_id": None,
                "first_name": None,
                "english_level": "beginner",
            }
        ]

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
