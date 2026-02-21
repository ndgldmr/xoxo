# XOXO Education — Word of the Day

WhatsApp "English Word/Phrase of the Day" service for Brazilian Portuguese speakers learning English. Generates AI-powered daily messages and delivers them to all enrolled students via WaSenderAPI.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [WaSenderAPI Setup](#wasenderapi-setup)
- [Running the Server](#running-the-server)
- [API Reference](#api-reference)
- [Student Management](#student-management)
- [CLI Reference](#cli-reference)
- [Cron Setup](#cron-setup)
- [Webhook: Opt-Out / Opt-In](#webhook-opt-out--opt-in)
- [Message Format](#message-format)
- [Validation Rules](#validation-rules)
- [Retry & Fallback Logic](#retry--fallback-logic)
- [Audit Log](#audit-log)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Features

- **AI-Generated Content** — Uses any OpenAI-compatible LLM (Gemini, GPT-4o, etc.) to generate a unique daily English word or phrase with translation, pronunciation, usage guidance, and bilingual examples
- **Multi-Recipient** — Sends to all active students stored in a PostgreSQL database
- **Strict Validation** — All 6 message fields are validated for format, length, language, and content rules before sending
- **Auto-Retry with Repair** — If validation fails, automatically retries with a repair prompt (up to 2 retries)
- **Fallback Safety** — Never crashes — a safe fallback message is always delivered if generation fails
- **Opt-Out / Opt-In** — Students send "STOP" or "START" via WhatsApp; the webhook updates the database and sends a PT-BR confirmation automatically
- **API Authentication** — All sensitive endpoints require an `X-API-Key` header
- **Webhook Signature Verification** — WaSenderAPI webhook requests are verified using a shared secret via `X-Webhook-Signature`
- **Idempotency** — Won't send duplicate messages on the same day (unless forced)
- **Audit Logging** — JSONL-based audit trail of every send with full per-student tracking
- **Dry Run Mode** — Test everything without actually sending messages
- **CLI & API** — Run via command line or FastAPI HTTP server

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      XOXO Education                          │
│                  Word of the Day Service                     │
└───────────────────────┬──────────────────────────────────────┘
                        │
          ┌─────────────┼──────────────────┐
          │             │                  │
     ┌────▼────┐  ┌─────▼──────┐   ┌──────▼────────┐
     │   CLI   │  │  FastAPI   │   │    Webhook    │
     │ main.py │  │  routes.py │   │ /webhook/     │
     └────┬────┘  └─────┬──────┘   │  whatsapp     │
          │             │          └──────┬────────┘
          └──────┬───────┘                │
                 │                        │
        ┌────────▼────────┐               │
        │ WordOfDayService│               │
        └────────┬────────┘               │
                 │                        │
    ┌────────────┼────────────┐           │
    │            │            │           │
┌───▼───┐  ┌────▼─────┐ ┌────▼──────┐   │
│  LLM  │  │ WhatsApp │ │  Student  │◄──┘
│Client │  │  Client  │ │   Repo    │
└───────┘  └──────────┘ └────┬──────┘
 (Gemini/                    │
  OpenAI)   (WaSender)       │
                      ┌──────▼──────┐
                      │  PostgreSQL │
                      │  (Supabase) │
                      └─────────────┘
```

### Request Flows

**Daily Send**
```
Trigger: CLI (send) or API (POST /send-word-of-day)
                       │
                       ▼
         Already sent today? ──Yes──► Skip (unless force=true)
                       │ No
                       ▼
         Fetch active subscribers from DB
                       │
                       ▼
            Generate 6 params via LLM
                       │
                       ▼
                 Validate params
                  │         │
                Pass       Fail
                  │         │
                  │    Repair prompt + retry (up to 2×)
                  │         │
                  │        Fail → Use fallback content
                  └────┬────┘
                       │
                ┌──────▼───────┐
                │ For each     │
                │ student:     │
                │  · Send msg  │
                │  · Log audit │
                └──────────────┘
```

**Opt-Out / Opt-In**
```
Student sends "STOP" or "START" via WhatsApp
                    │
                    ▼
  WaSenderAPI fires POST /webhook/whatsapp
  with X-Webhook-Signature header
                    │
                    ▼
  Verify signature against WASENDER_WEBHOOK_SECRET
                    │
                    ▼
  Parse phone number and message body
                    │
          ┌─────────┴──────────┐
         STOP                START
          │                    │
          ▼                    ▼
  Set whatsapp_messages    Set whatsapp_messages
       = False                  = True
          │                    │
          ▼                    ▼
  Send PT-BR confirmation  Send PT-BR confirmation
  Student excluded from    Student included in
  future sends             future sends
```

---

## Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) project (PostgreSQL database)
- An LLM API key — [Google Gemini](https://aistudio.google.com/apikey) (free tier available) or [OpenAI](https://platform.openai.com/api-keys)
- A [WaSenderAPI](https://wasenderapi.com) account with an active WhatsApp session

---

## Installation

```bash
# Install uv (fast Python package manager), if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

---

## Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

### All Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_API_KEY` | Yes | — | API key for your LLM provider |
| `LLM_MODEL` | No | `gpt-4o-mini` | Model name (e.g. `gemini-flash-latest`) |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | LLM API base URL |
| `LLM_TIMEOUT` | No | `30` | LLM request timeout in seconds |
| `WASENDER_API_KEY` | Yes | — | WaSenderAPI bearer token |
| `WASENDER_WEBHOOK_SECRET` | Yes | — | Webhook secret from WaSenderAPI dashboard |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `API_KEY` | Yes | — | Secret key required by all protected API endpoints |
| `DRY_RUN` | No | `true` | If `true`, prints messages instead of sending |
| `AUDIT_LOG_PATH` | No | `audit_log.jsonl` | Path to the JSONL audit log file |
| `SEND_DELAY_SECONDS` | No | `0.5` | Delay between sends in multi-recipient mode |

### Example `.env` (production)

```env
# LLM — Google Gemini
LLM_API_KEY=your_gemini_api_key
LLM_MODEL=gemini-flash-latest
LLM_BASE_URL=https://generativelanguage.googleapis.com
LLM_TIMEOUT=60

# WaSenderAPI
WASENDER_API_KEY=your_wasender_api_key
WASENDER_WEBHOOK_SECRET=your_webhook_secret

# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# API Authentication
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
API_KEY=your_generated_api_key

# Application
DRY_RUN=false
AUDIT_LOG_PATH=audit_log.jsonl
SEND_DELAY_SECONDS=6
```

> **Tip:** For high-concurrency deployments, use Supabase's connection pooler URL (port 6543) instead of the direct connection (port 5432). Find it under Project Settings → Database → Connection pooling.

---

## Database Setup

The app uses PostgreSQL via [Supabase](https://supabase.com). After setting `DATABASE_URL` in your `.env`, create all tables by running:

```bash
python scripts/init_db.py
```

Expected output:
```
Initializing database...
✓ Database initialized successfully!
  Tables created: students
```

### Students Table Schema

| Column | Type | Description |
|---|---|---|
| `phone_number` | `VARCHAR(20)` PK | E.164 format, e.g. `+5511999999999` |
| `first_name` | `VARCHAR(100)` nullable | Student's first name |
| `last_name` | `VARCHAR(100)` nullable | Student's last name |
| `english_level` | `VARCHAR(20)` | `beginner` or `intermediate` |
| `whatsapp_messages` | `BOOLEAN` | `true` = subscribed, `false` = opted out |
| `is_active` | `BOOLEAN` | `false` = soft-deleted |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Auto-set on creation |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Auto-updated on change |

---

## WaSenderAPI Setup

1. Sign up at [wasenderapi.com](https://wasenderapi.com)
2. Create a WhatsApp session and scan the QR code with your phone
3. Generate an API key from the dashboard — set it as `WASENDER_API_KEY`
4. Go to **Session Settings → Webhook**:
   - Set the **Webhook URL** to `https://your-domain.com/webhook/whatsapp`
   - Enable the **`messages.received`** event
   - Copy the **Webhook Secret** — set it as `WASENDER_WEBHOOK_SECRET`

> The webhook URL does **not** need an `?api_key=` query parameter. Authentication is handled via the `X-Webhook-Signature` header that WaSenderAPI attaches automatically using your webhook secret.

---

## Running the Server

```bash
uvicorn app.api.routes:app --host 0.0.0.0 --port 8000
```

For local development with auto-reload:
```bash
uvicorn app.api.routes:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## API Reference

### Authentication

All endpoints except `GET /`, `GET /health`, and `POST /webhook/whatsapp` require an `X-API-Key` header:

```
X-API-Key: your_api_key
```

Requests missing or sending the wrong key receive a `401 Unauthorized` response.

---

### `GET /`

Returns basic service info. No authentication required.

**Response**
```json
{
  "service": "XOXO Education - Word of the Day",
  "version": "0.1.0",
  "endpoints": {
    "send": "POST /send-word-of-day",
    "health": "GET /health",
    "list_students": "GET /students",
    "add_student": "POST /students",
    "remove_student": "DELETE /students/{phone_number}"
  }
}
```

---

### `GET /health`

Returns configuration status. No authentication required.

**Response**
```json
{
  "status": "ready",
  "checks": {
    "llm_configured": true,
    "wasender_configured": true,
    "database_configured": true,
    "dry_run": false
  }
}
```

`status` is `"ready"` only when LLM and WaSenderAPI are both configured.

---

### `POST /send-word-of-day`

Generates and sends a Word of the Day message to all active subscribers. **Requires `X-API-Key`.**

**Request body**
```json
{
  "theme": "daily life",
  "level": "beginner",
  "force": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `theme` | string | `"daily life"` | Topic theme for the LLM prompt (e.g. `"work"`, `"travel"`, `"food"`) |
| `level` | string | `"beginner"` | `"beginner"` or `"intermediate"` |
| `force` | boolean | `false` | If `true`, sends even if a message was already sent today |

**Response**
```json
{
  "status": "success",
  "sent_count": 2,
  "failed_count": 0,
  "total_recipients": 2,
  "date": "2026-02-20",
  "used_fallback": false,
  "validation_errors": [],
  "preview": "Word: Have breakfast",
  "sends": [
    {
      "phone_number": "+5511999999999",
      "student_id": "+5511999999999",
      "first_name": "Maria",
      "sent": true,
      "provider_message_id": "WASENDER_ABC123",
      "error_message": null
    },
    {
      "phone_number": "+5521888888888",
      "student_id": "+5521888888888",
      "first_name": "João",
      "sent": true,
      "provider_message_id": "WASENDER_DEF456",
      "error_message": null
    }
  ]
}
```

| `status` value | Meaning |
|---|---|
| `"success"` | All recipients received the message |
| `"partial"` | Some recipients received it, some failed |
| `"error"` | No recipients received it |
| `"skipped"` | Already sent today and `force` was `false` |

**Example**
```bash
curl -X POST https://your-domain.com/send-word-of-day \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"theme": "work", "level": "intermediate", "force": false}'
```

---

### `GET /students`

Lists all students. **Requires `X-API-Key`.**

**Query parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `include_inactive` | boolean | `false` | If `true`, includes soft-deleted students |

**Response**
```json
[
  {
    "phone_number": "+5511999999999",
    "first_name": "Maria",
    "last_name": "Silva",
    "english_level": "beginner",
    "whatsapp_messages": true,
    "is_active": true
  }
]
```

**Example**
```bash
# Active students only
curl https://your-domain.com/students \
  -H "X-API-Key: your_api_key"

# All students including removed
curl "https://your-domain.com/students?include_inactive=true" \
  -H "X-API-Key: your_api_key"
```

---

### `POST /students`

Adds a new student. **Requires `X-API-Key`.**

**Request body**
```json
{
  "phone_number": "+5511999999999",
  "first_name": "Maria",
  "last_name": "Silva",
  "english_level": "beginner",
  "whatsapp_messages": true
}
```

| Field | Required | Description |
|---|---|---|
| `phone_number` | Yes | E.164 format (e.g. `+5511999999999`) |
| `first_name` | No | Student's first name |
| `last_name` | No | Student's last name |
| `english_level` | No | `"beginner"` (default) or `"intermediate"` |
| `whatsapp_messages` | No | `true` (default) — whether to send messages |

Returns `201 Created` with the created student object, or `409 Conflict` if the phone number already exists.

**Example**
```bash
curl -X POST https://your-domain.com/students \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+5511999999999",
    "first_name": "Maria",
    "last_name": "Silva",
    "english_level": "beginner",
    "whatsapp_messages": true
  }'
```

---

### `DELETE /students/{phone_number}`

Hard-deletes a student by phone number. **Requires `X-API-Key`.**

Returns `204 No Content` on success, or `404 Not Found` if the student doesn't exist.

**Example**
```bash
curl -X DELETE "https://your-domain.com/students/+5511999999999" \
  -H "X-API-Key: your_api_key"
```

---

### `POST /webhook/whatsapp`

Receives incoming WhatsApp messages from WaSenderAPI. Handles `"STOP"` and `"START"` commands.

**Authentication** — This endpoint does not use `X-API-Key`. Instead, WaSenderAPI signs every request with the `X-Webhook-Signature` header, which is verified against `WASENDER_WEBHOOK_SECRET`. Requests with an invalid or missing signature are rejected with `401 Unauthorized`.

This endpoint should only be called by WaSenderAPI — you do not need to call it manually.

**Behaviour**

| Student sends | DB change | Confirmation sent |
|---|---|---|
| `STOP` (case-insensitive) | `whatsapp_messages = false` | PT-BR opt-out confirmation + re-enrol instructions |
| `START` (case-insensitive) | `whatsapp_messages = true` | PT-BR welcome-back confirmation |
| Anything else | No change | No reply |

---

## Student Management

Students can be managed via the API (above) or via the CLI management script.

### CLI Student Management

```bash
# Add a student
python scripts/manage_students.py add-student \
  --phone "+5511999999999" \
  --first-name "Maria" \
  --last-name "Silva" \
  --level beginner \
  --whatsapp

# List all active students
python scripts/manage_students.py list-students

# List all students including inactive
python scripts/manage_students.py list-students --include-inactive

# Filter by level
python scripts/manage_students.py list-students --level beginner

# Deactivate (soft-delete) a student
python scripts/manage_students.py remove-student --phone "+5511999999999"

# Manually opt a student out of WhatsApp messages
python scripts/manage_students.py opt-out --phone "+5511999999999"
```

> Phone numbers must be in **E.164 format**: `+` followed by country code and number, no spaces or dashes (e.g. `+5511999999999` for Brazil).

---

## CLI Reference

The main CLI (`python -m app.main`) is used for sending and previewing messages.

### Health Check

Validates all configuration and counts active subscribers.

```bash
python -m app.main health
```

Example output:
```
============================================================
HEALTH CHECK
============================================================
LLM API Key: ✓ Configured
LLM Model: gemini-flash-latest
LLM Base URL: https://generativelanguage.googleapis.com

WaSenderAPI: ✓ Configured

Recipient Configuration:
  Mode: Multi-Recipient (Database)
  Database URL: postgresql://...
  Active Subscribers: 12

General Settings:
  Dry Run: False
  Audit Log Path: audit_log.jsonl
  Send Delay: 6s

Overall Status: ✓ READY
============================================================
```

### Preview

Generates and validates a message without sending it. Useful for checking what the LLM produces.

```bash
python -m app.main preview
python -m app.main preview --theme work --level intermediate
```

### Send

Generates and sends a Word of the Day to all active subscribers.

```bash
# Send with defaults (theme: daily life, level: beginner)
python -m app.main send

# Custom theme and level
python -m app.main send --theme travel --level intermediate

# Force send even if already sent today
python -m app.main send --force
```

**Available themes:** `daily life`, `work`, `travel`, `emotions`, `food`, `shopping`, `health`, `technology`, and more — any topic phrase works.

**Available levels:** `beginner`, `intermediate`

---

## Cron Setup

To send the Word of the Day automatically every morning at 8 AM:

```bash
crontab -e
```

Add the following line (adjust paths to your installation):

```cron
0 8 * * * cd /path/to/xoxo && /path/to/.venv/bin/python -m app.main send >> /var/log/xoxo.log 2>&1
```

The app is idempotent — if triggered twice on the same day, the second run is skipped automatically (unless `--force` is used).

---

## Webhook: Opt-Out / Opt-In

### How It Works

WaSenderAPI forwards all incoming WhatsApp messages to your webhook URL. The handler:

1. Verifies the `X-Webhook-Signature` header matches `WASENDER_WEBHOOK_SECRET`
2. Ignores all events that are not `messages.received`
3. Checks if the message body contains `"stop"` or `"start"` (case-insensitive)
4. Updates `whatsapp_messages` in the database
5. Sends a Portuguese confirmation message back to the student

### Opt-Out Confirmation (sent on STOP)

> Você foi removido da lista de mensagens da XOXO Education. Para voltar a receber as mensagens de Palavra/Frase do Dia, envie "START".

### Opt-In Confirmation (sent on START)

> Você foi inscrito novamente na lista de mensagens da XOXO Education. A próxima Palavra/Frase do Dia chegará amanhã. Para cancelar, envie "STOP".

### WaSenderAPI Dashboard Configuration

- **Webhook URL:** `https://your-domain.com/webhook/whatsapp`
- **Events:** enable `messages.received`
- **Webhook Secret:** copy the value and set it as `WASENDER_WEBHOOK_SECRET` in your `.env`

---

## Message Format

Each message is generated from 6 structured parameters and delivered as a formatted WhatsApp text:

```
🇺🇸  *Palavra/Frase do Dia:* Have breakfast

📝 *Significado:* Tomar o café da manhã

🔊 *Pronúncia:* hav BREK-fust

💡 *Quando usar:* Use quando estiver falando sobre sua rotina matinal

🇧🇷  *Exemplo:* Eu tomo café da manhã às 7h todo dia.

🇺🇸  *Exemplo:* I have breakfast at 7 AM every day.

Envie "STOP" para cancelar o recebimento de mensagens da Palavra/Frase do Dia.
```

### The 6 Parameters

| Field | Language | Max Length | Description |
|---|---|---|---|
| `word_phrase` | English | 40 chars | The English word or phrase |
| `meaning_pt` | Portuguese | 300 chars | Explanation in Brazilian Portuguese |
| `pronunciation` | Phonetic | 40 chars | Pronunciation guide for PT speakers |
| `when_to_use` | Portuguese | 300 chars | When/where to use it (in PT) |
| `example_pt` | Portuguese | 180 chars | Example sentence in Portuguese |
| `example_en` | English | 120 chars | Same example sentence in English |

---

## Validation Rules

All 6 parameters are validated on every send:

1. All 6 fields must be present and non-empty
2. Each field must not exceed its character limit (see table above)
3. No URLs allowed in any field
4. No markdown symbols (e.g. `*`, `_`, `~`) in any field
5. `word_phrase`, `pronunciation`, and `example_en` must be predominantly ASCII (English)
6. `meaning_pt`, `when_to_use`, and `example_pt` must contain Portuguese-language indicators

---

## Retry & Fallback Logic

1. **Attempt 1** — Generate 6 parameters with the LLM
2. **Validate** — Check all rules above
3. **Attempt 2** — If invalid, regenerate using a repair prompt that includes the specific validation errors
4. **Attempt 3** — Retry repair once more if still invalid
5. **Fallback** — If all 3 attempts fail, use a safe deterministic fallback message ("Hello")
6. **Always sends** — The job never fails silently; a message is always delivered

---

## Audit Log

Every send is appended to `audit_log.jsonl`. Each line is one JSON object representing a single send event.

```json
{
  "timestamp": "2026-02-20T11:00:00Z",
  "date": "2026-02-20",
  "theme": "daily life",
  "level": "beginner",
  "valid": true,
  "sent": true,
  "used_fallback": false,
  "provider": "wasender",
  "provider_message_id": "WASENDER_ABC123",
  "phone_number": "+5511999999999",
  "student_id": "+5511999999999",
  "template_params": {
    "word_phrase": "Have breakfast",
    "meaning_pt": "Tomar o café da manhã",
    "pronunciation": "hav BREK-fust",
    "when_to_use": "Use quando estiver falando sobre sua rotina matinal",
    "example_pt": "Eu tomo café da manhã às 7h.",
    "example_en": "I have breakfast at 7 AM."
  },
  "errors": []
}
```

The audit log is also used for idempotency — it is checked at the start of each run to determine whether a message has already been sent today.

---

## Testing

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Run a single test file
pytest tests/test_validators.py

# With coverage report
pytest --cov=app tests/
```

### Development Workflow

1. **Always dry-run first** — set `DRY_RUN=true` in `.env` before any real sends
2. **Preview before sending** — use `python -m app.main preview` to inspect generated content
3. **Check the health endpoint** — run `python -m app.main health` to confirm all services are configured
4. **Review the audit log** — `audit_log.jsonl` shows a full history of every send attempt

---

## File Structure

```
app/
├── main.py                     # CLI entry point (send, preview, health)
├── config.py                   # Environment variable configuration
├── api/
│   ├── routes.py               # FastAPI app and all HTTP endpoints
│   └── webhook_routes.py       # Webhook handler (STOP/START opt-outs)
├── services/
│   └── word_of_day_service.py  # Orchestration: generate → validate → send
├── domain/
│   ├── validators.py           # Message validation rules
│   └── fallback.py             # Safe fallback message parameters
├── integrations/
│   ├── llm_client.py           # LLM API client (OpenAI-compatible)
│   └── wasender_client.py      # WaSenderAPI client
├── logging/
│   └── audit_log.py            # JSONL audit trail
├── db/
│   ├── base.py                 # SQLAlchemy Base and TimestampMixin
│   ├── session.py              # Database engine and session management
│   └── models/
│       └── student.py          # Student ORM model
└── repositories/
    └── student.py              # Student CRUD operations

scripts/
├── init_db.py                  # Create all database tables
└── manage_students.py          # Student management CLI (add, list, remove, opt-out)

tests/
├── test_validators.py          # Validation rule tests
└── test_service_happy_path.py  # Service integration tests
```

---

## Troubleshooting

### Messages not sending

- Run `python -m app.main health` to check all services are configured
- Confirm `DRY_RUN=false` in `.env`
- Verify your WaSenderAPI session is active in the dashboard (the WhatsApp phone must be connected)
- Check that recipient numbers are in E.164 format

### LLM errors

- Verify `LLM_API_KEY` and `LLM_BASE_URL` are correct for your provider
- Increase the timeout: `LLM_TIMEOUT=60`
- Check your API quota and rate limits
- Run `python -m app.main preview` to isolate generation issues

### Validation failures

- Run `python -m app.main preview` to inspect the generated content
- Review `audit_log.jsonl` for the specific validation errors
- The app will automatically retry and fall back to a safe message — validation failures do not stop the send

### Database errors

- Confirm `DATABASE_URL` is set correctly in `.env`
- If tables don't exist, run `python scripts/init_db.py`
- Check Supabase dashboard to confirm your project is active

### Webhook not triggering (STOP/START not working)

- Confirm the webhook URL and `messages.received` event are configured in the WaSenderAPI dashboard
- Confirm `WASENDER_WEBHOOK_SECRET` in `.env` matches the secret shown in the WaSenderAPI dashboard exactly
- If running locally, use [ngrok](https://ngrok.com) to expose your server: `ngrok http 8000`
- Check your server logs — a `401` response means the signature is not matching

### API returning 401

- Confirm you are passing the `X-API-Key` header with the correct value
- The value must match `API_KEY` in your `.env`
- The `/health`, `/`, and `/webhook/whatsapp` endpoints do not require this header

---

## License

MIT License — XOXO Education
