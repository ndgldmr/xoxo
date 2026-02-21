"""Webhook routes for handling incoming WhatsApp messages."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_session
from app.integrations.wasender_client import WaSenderClient
from app.repositories.student import StudentRepository

router = APIRouter(prefix="/webhook", tags=["webhooks"])

STOP_CONFIRMATION = (
    'Você foi removido da lista de mensagens da XOXO Education. '
    'Para voltar a receber as mensagens de Palavra/Frase do Dia, envie "START".'
)

START_CONFIRMATION = (
    'Você foi inscrito novamente na lista de mensagens da XOXO Education. '
    'A próxima Palavra/Frase do Dia chegará amanhã. Para cancelar, envie "STOP".'
)


def get_db():
    """Database dependency for FastAPI."""
    with get_session() as session:
        yield session


def get_whatsapp_client() -> WaSenderClient:
    settings = get_settings()
    return WaSenderClient(api_key=settings.wasender_api_key, dry_run=settings.dry_run)


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle incoming WhatsApp messages from WaSender.

    - "STOP": opts the student out and sends a PT-BR confirmation with re-enrollment instructions.
    - "START": opts the student back in and sends a PT-BR welcome-back confirmation.

    WaSender payload structure:
        {
            "event": "messages.received",
            "data": {
                "messages": {
                    "key": { "cleanedSenderPn": "+5511999999999" },
                    "messageBody": "STOP"
                }
            }
        }
    """
    settings = get_settings()
    if settings.wasender_webhook_secret:
        signature = request.headers.get("x-webhook-signature", "")
        if signature != settings.wasender_webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
        print(f"Webhook payload: {payload}")

        if payload.get("event") != "messages.received":
            print(f"Ignored event: {payload.get('event')}")
            return {"status": "ok", "message": "Event ignored"}

        messages = payload.get("data", {}).get("messages", {})
        phone_number = messages.get("key", {}).get("cleanedSenderPn", "").strip()
        if phone_number and not phone_number.startswith("+"):
            phone_number = "+" + phone_number
        body = messages.get("messageBody", "").strip()

        if not phone_number:
            return {"status": "ok", "message": "No phone number found"}

        whatsapp = get_whatsapp_client()
        repo = StudentRepository(db)

        if "stop" in body.lower():
            print(f"STOP request received from {phone_number}")
            success = repo.update_whatsapp_opt_out(phone_number)
            if success:
                print(f"Student {phone_number} opted out successfully")
            else:
                print(f"Warning: Student {phone_number} not found in database")
            whatsapp.send_message(to_number=phone_number, message=STOP_CONFIRMATION)

        elif "start" in body.lower():
            print(f"START request received from {phone_number}")
            success = repo.update_whatsapp_opt_in(phone_number)
            if success:
                print(f"Student {phone_number} opted in successfully")
            else:
                print(f"Warning: Student {phone_number} not found in database")
            whatsapp.send_message(to_number=phone_number, message=START_CONFIRMATION)

        return {"status": "ok", "message": "Webhook received"}

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}
