"""WhatsApp client for sending messages via WaSenderAPI."""
from typing import Optional

import httpx


class WhatsAppError(Exception):
    """Raised when WhatsApp message sending fails."""
    pass


def format_template_params_as_text(params: dict) -> str:
    """
    Format 6 template parameters into a plain-text WhatsApp message.

    Args:
        params: Dict with keys: word_phrase, meaning_pt, pronunciation,
                when_to_use, example_pt, example_en

    Returns:
        Formatted text message string
    """
    return (
        f"🇺🇸  *Palavra/Frase do Dia:* {params['word_phrase']}\n\n"
        f"📝 *Significado:* {params['meaning_pt']}\n\n"
        f"🔊 *Pronúncia:* {params['pronunciation']}\n\n"
        f"💡 *Quando usar:* {params['when_to_use']}\n\n"
        f"🇧🇷  *Exemplo:* {params['example_pt']}\n\n"
        f"🇺🇸  *Exemplo:* {params['example_en']}\n\n"
        f"Envie *STOP* para cancelar o recebimento de mensagens da Palavra/Frase do Dia."
    )


class WaSenderClient:
    """WaSenderAPI client for sending WhatsApp messages."""

    BASE_URL = "https://www.wasenderapi.com/api"

    def __init__(
        self,
        api_key: str,
        from_number: str = "",
        dry_run: bool = True,
        timeout: int = 30,
    ):
        """
        Initialize WaSender client.

        Args:
            api_key: WaSenderAPI bearer token
            from_number: Not used by WaSender (kept for interface compatibility)
            dry_run: If True, print message instead of sending
            timeout: HTTP request timeout in seconds
        """
        self.api_key = api_key
        self.from_number = from_number
        self.dry_run = dry_run
        self.timeout = timeout

    def _clean_number(self, number: str) -> str:
        """Strip whatsapp: prefix; WaSenderAPI uses plain E.164 format."""
        return number.replace("whatsapp:", "").strip()

    def send_message(self, to_number: str, message: str) -> dict:
        """
        Send a plain-text WhatsApp message.

        Args:
            to_number: Destination number (with or without whatsapp: prefix)
            message: Message text to send

        Returns:
            dict with sid, status, and other response fields

        Raises:
            WhatsAppError: If sending fails
        """
        to = self._clean_number(to_number)

        if self.dry_run:
            print("\n" + "=" * 60)
            print("DRY RUN - WaSender message would be sent:")
            print(f"To: {to}")
            print("-" * 60)
            print(message)
            print("=" * 60 + "\n")
            return {
                "sid": "DRY_RUN",
                "status": "dry_run",
                "error_code": None,
                "error_message": None,
                "date_created": None,
                "date_updated": None,
                "price": None,
                "price_unit": None,
                "full_response": {"dry_run": True},
            }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.BASE_URL}/send-message",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"to": to, "text": message},
                )
                response.raise_for_status()

            data = response.json()
            return {
                "sid": data.get("id") or data.get("messageId") or "WASENDER",
                "status": data.get("status", "sent"),
                "error_code": None,
                "error_message": None,
                "date_created": None,
                "date_updated": None,
                "price": None,
                "price_unit": None,
                "full_response": data,
            }

        except httpx.HTTPStatusError as e:
            raise WhatsAppError(
                f"WaSenderAPI HTTP error {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            raise WhatsAppError(f"Failed to send WaSender message: {e}")

    def send_welcome_message(self, to_number: str, first_name: Optional[str] = None) -> dict:
        """Send a Portuguese welcome message to a newly enrolled student.

        Args:
            to_number: Destination number in E.164 format
            first_name: Student's first name, used to personalise the greeting

        Returns:
            dict with send result
        """
        name_part = f" {first_name}" if first_name else ""
        message = (
            f"Olá{name_part}! 👋 Você foi cadastrado(a) no serviço *Palavra do Dia* da XOXO Education.\n\n"
            f"A partir de agora, você receberá uma mensagem diária com uma palavra ou frase em inglês "
            f"para turbinar seu vocabulário! Para cancelar, basta responder *STOP*."
        )
        return self.send_message(to_number=to_number, message=message)

    def send_template_message(
        self, to_number: str, content_sid: str, content_variables: dict
    ) -> dict:
        """
        Send a template message formatted as plain text.

        WaSenderAPI doesn't support WhatsApp templates, so the 6 content
        variables are formatted into a structured text message that mirrors
        the approved template layout.

        Args:
            to_number: Destination number
            content_sid: Ignored (kept for interface compatibility)
            content_variables: Dict with keys "1"-"6" mapping to template params

        Returns:
            dict with send result
        """
        # Map numeric keys back to named params for formatting
        params = {
            "word_phrase":  content_variables.get("1", ""),
            "meaning_pt":   content_variables.get("2", ""),
            "pronunciation": content_variables.get("3", ""),
            "when_to_use":  content_variables.get("4", ""),
            "example_pt":   content_variables.get("5", ""),
            "example_en":   content_variables.get("6", ""),
        }

        message = format_template_params_as_text(params)
        return self.send_message(to_number=to_number, message=message)
