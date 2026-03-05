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
- [Admin Dashboard](#admin-dashboard)
- [Deploying to GCP](#deploying-to-gcp)
- [API Reference](#api-reference)
- [Student Management](#student-management)
- [Dashboard Stats](#dashboard-stats)
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
- **Level-Differentiated Messages** — Separate content is generated for each English level (Beginner, Intermediate, Advanced) so every student receives age-appropriate material
- **Pre-Generated Message Store** — Daily messages are generated at midnight and stored in the database; the send job reads from the store rather than calling the LLM at send time, ensuring all students receive identical, validated content
- **Message Preview** — Admins can see the exact WhatsApp message queued for each level in the Schedule tab, and regenerate any level on demand
- **Strict Validation** — All 6 message fields are validated for format, length, language, and content rules before sending
- **Auto-Retry with Repair** — If validation fails, automatically retries with a repair prompt (up to 2 retries)
- **Resilient LLM Pipeline** — On 503 errors, automatically retries the primary model (10s then 30s); if still unavailable, falls back to `gemini-2.0-flash-lite`; if both fail, no message is sent rather than delivering stale content
- **Welcome Message** — When a student is added with `whatsapp_messages: true`, a Portuguese welcome WhatsApp message is sent to them automatically
- **Opt-Out / Opt-In** — Students send "STOP" or "START" via WhatsApp; the webhook updates the database and sends a PT-BR confirmation automatically
- **API Authentication** — All sensitive endpoints require an `X-API-Key` header
- **Webhook Signature Verification** — WaSenderAPI webhook requests are verified using a shared secret via `X-Webhook-Signature`
- **Idempotency** — Won't send duplicate messages on the same day (unless forced)
- **Audit Logging** — JSONL-based audit trail of every send with full per-student tracking
- **Dry Run Mode** — Test everything without actually sending messages
- **CLI & API** — Run via command line or FastAPI HTTP server
- **Admin Dashboard** — React web UI for managing students (add, edit, deactivate, reactivate, delete), configuring the send schedule, and broadcasting announcements
- **Announcements** — Admins can send a custom WhatsApp message to all active students at once, with optional filtering by English level

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

**Daily Generate (midnight)**
```
Trigger: GCP Cloud Scheduler (xoxo-daily-generate) → POST /messages/generate
                       │
                       ▼
          ┌────────────┼────────────┐
       beginner  intermediate   advanced
          │            │            │
          ▼            ▼            ▼
      Generate      Generate     Generate
      params        params       params
      via LLM       via LLM      via LLM
          │            │            │
          ▼            ▼            ▼
       Validate     Validate     Validate
       (retry/      (retry/      (retry/
       fallback)    fallback)    fallback)
          │            │            │
          └────────────┼────────────┘
                       │
                ┌──────▼───────────────┐
                │ Upsert to messages   │
                │ table (date + level) │
                └──────────────────────┘
```

**Daily Send (morning)**
```
Trigger: GCP Cloud Scheduler (xoxo-daily-send) → POST /send-word-of-day
                       │
                       ▼
         Already sent today? ──Yes──► Skip (unless force=true)
                       │ No
                       ▼
         Fetch active subscribers from DB
                       │
                       ▼
         Group students by english_level
                       │
          ┌────────────┼────────────┐
       beginner  intermediate   advanced
          │            │            │
          ▼            ▼            ▼
      Load stored   Load stored  Load stored
      message from  message from message from
      messages DB   messages DB  messages DB
      (fallback:    (fallback:   (fallback:
       LLM)          LLM)         LLM)
          │            │            │
          └────────────┼────────────┘
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

**Backend**
- Python 3.11+
- A [Supabase](https://supabase.com) project (PostgreSQL database)
- An LLM API key — [Google Gemini](https://aistudio.google.com/apikey) (free tier available) or [OpenAI](https://platform.openai.com/api-keys)
- A [WaSenderAPI](https://wasenderapi.com) account with an active WhatsApp session

**Frontend**
- Node.js 18+

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
| `LLM_FALLBACK_MODEL` | No | `gemini-2.0-flash-lite` | Fallback model tried if primary returns 503 after retries (same API key/URL). Set to empty string to disable. |
| `WASENDER_API_KEY` | Yes | — | WaSenderAPI bearer token |
| `WASENDER_WEBHOOK_SECRET` | Yes | — | Webhook secret from WaSenderAPI dashboard |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `API_KEY` | Yes | — | Secret key required by all protected API endpoints |
| `GCP_PROJECT_ID` | No | — | GCP project ID (production only, for schedule management) |
| `GCP_LOCATION` | No | — | GCP region where the Cloud Scheduler jobs live (e.g. `us-central1`) |
| `GCP_SCHEDULER_JOB_ID` | No | — | Send job name (e.g. `xoxo-daily-send`) |
| `GCP_GENERATE_JOB_ID` | No | — | Generate job name (e.g. `xoxo-daily-generate`) |
| `SERVICE_URL` | No | — | Cloud Run service URL (e.g. `https://xoxo-....run.app`) |
| `DRY_RUN` | No | `true` | If `true`, prints messages instead of sending |
| `AUDIT_LOG_PATH` | No | `audit_log.jsonl` | Path to the JSONL audit log file |
| `SEND_DELAY_SECONDS` | No | `0.5` | Delay between sends in multi-recipient mode |
| `ALLOWED_ORIGINS` | No | `""` (allow all) | Comma-separated list of CORS origins allowed to call the API (e.g. `https://xoxo.vercel.app,http://localhost:5173`) |

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

# GCP Cloud Scheduler (production-only; leave blank for local dev)
GCP_PROJECT_ID=your_gcp_project_id
GCP_LOCATION=us-central1
GCP_SCHEDULER_JOB_ID=xoxo-daily-send
GCP_GENERATE_JOB_ID=xoxo-daily-generate
SERVICE_URL=https://your-cloud-run-service-url

# Application
DRY_RUN=false
AUDIT_LOG_PATH=audit_log.jsonl
SEND_DELAY_SECONDS=6

# CORS — allow the Vercel dashboard (and local dev)
ALLOWED_ORIGINS=https://xoxo.vercel.app,http://localhost:5173
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
  Tables created: students, messages
```

> Tables are also created automatically on app startup (via the FastAPI lifespan event), so `init_db.py` is mainly useful for local setup before the server has run.

### Students Table Schema

| Column | Type | Description |
|---|---|---|
| `phone_number` | `VARCHAR(20)` PK | E.164 format, e.g. `+5511999999999` |
| `first_name` | `VARCHAR(100)` nullable | Student's first name |
| `last_name` | `VARCHAR(100)` nullable | Student's last name |
| `english_level` | `VARCHAR(20)` | `beginner`, `intermediate`, or `advanced` |
| `whatsapp_messages` | `BOOLEAN` | `true` = subscribed, `false` = opted out |
| `is_active` | `BOOLEAN` | `false` = soft-deleted |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Auto-set on creation |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Auto-updated on change |

### Messages Table Schema

Pre-generated daily messages are stored here. The send job reads from this table instead of calling the LLM at send time.

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER` PK | Auto-increment primary key |
| `date` | `DATE` | The calendar date the message was generated for |
| `level` | `VARCHAR(20)` | `beginner`, `intermediate`, or `advanced` |
| `theme` | `VARCHAR(255)` | The theme used when generating the message |
| `template_params` | `JSONB` | The 6 structured fields produced by the LLM |
| `formatted_message` | `TEXT` | The verbatim WhatsApp message text |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Auto-set on creation |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Auto-updated on change |

The `(date, level)` pair is unique — re-generating a level upserts the row.

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

## Admin Dashboard

A React single-page app for managing students. It talks directly to the backend API using your `API_KEY`.

### Installation

```bash
cd frontend
npm install
```

### Configuration

```bash
cp .env.example .env
```

Set `VITE_API_URL` in `frontend/.env` to point at your backend:

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL (default: `http://localhost:8000`) |

### Running locally

```bash
# Terminal 1 — backend
cd backend && uvicorn app.api.routes:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```

The dashboard opens at `http://localhost:5173`.

### Login

The dashboard has a login screen. Enter your `API_KEY` (the same value as `API_KEY` in the backend `.env`). The key is verified against the live backend and stored in `sessionStorage` for the duration of the browser tab — it is cleared on logout or when the tab is closed.

### Students tab

| Action | Description |
|---|---|
| **Add Student** | Opens a dialog — enter phone number, first/last name, and level (Beginner / Intermediate / Advanced) |
| **Edit** | Opens a pre-filled dialog to update first name, last name, or level (phone number is read-only) |
| **Deactivate** | Soft-disables a student; they stop receiving messages |
| **Reactivate** | Re-enables a previously deactivated student |
| **Delete** | Hard-deletes a student after a confirmation dialog |
| **Show inactive** | Toggle to include/exclude inactive students in the table |
| **Search** | Filter students by name or phone number |
| **Level filter** | Filter students by English level |

### Schedule tab

Two panels side by side:

**Schedule config** — Configure the automated daily send schedule. Changes are applied live to the GCP Cloud Scheduler jobs.

| Field | Description |
|---|---|
| **Send time** | Time of day to send the message (HH:MM) |
| **Timezone** | IANA timezone for the send time (e.g. `America/Sao_Paulo`) |
| **Theme** | Topic hint passed to the LLM (e.g. `"travel"`, `"work"`). Saved to both the send job and the generate job automatically. |

Use the **Save changes** button (top-right of the panel) to apply edits. A **Reset** button appears next to it while there are unsaved changes.

**Today's Messages** — Shows the exact WhatsApp message that is queued for each English level today. Messages are pre-generated at midnight by the `xoxo-daily-generate` Cloud Scheduler job.

- Each level row shows a green dot (message ready) or grey dot (not yet generated), plus the generation timestamp.
- Click any level row to open a dialog with the full message rendered as rich text (WhatsApp formatting — `*bold*`, `_italic_`, `~strikethrough~` — is displayed as styled text).
- The dialog has a **Regenerate** button to re-generate that level's message on demand (saves new content to the database).
- A **Regenerate All** button (top-right of the panel) re-generates all three levels at once.
- Regeneration is disabled while the theme form has unsaved changes — save first.

> **Note:** The Schedule tab returns a 503 error in local development unless all GCP environment variables (`GCP_PROJECT_ID`, `GCP_LOCATION`, `GCP_SCHEDULER_JOB_ID`, `GCP_GENERATE_JOB_ID`, `SERVICE_URL`) are configured.

### Send Announcement tab

Send a one-off custom WhatsApp message to all active, opted-in students.

| Field | Description |
|---|---|
| **Recipients** | Filter by English level (`All levels`, `Beginner`, `Intermediate`, `Advanced`) |
| **Message** | The message text to send |

Only students who are active (`is_active = true`) and have not opted out (`whatsapp_messages = true`) will receive the message. After sending, the tab shows how many students the message was delivered to.

### Frontend deployment (Vercel)

1. Push the repo to GitHub
2. Create a new Vercel project pointed at the `frontend/` directory
3. Set `VITE_API_URL` in Vercel's Environment Variables to your Cloud Run URL (e.g. `https://xoxo-....run.app`)
4. Add the Vercel deployment URL to `ALLOWED_ORIGINS` in the backend `.env` (or Cloud Run environment variables)

---

## Deploying to GCP

The `deploy.sh` script in the repo root handles the full backend deployment in one command. It requires only the `gcloud` CLI — no Docker needed, since builds run remotely via Cloud Build.

### Prerequisites

- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- Active GCP project set (`gcloud config set project YOUR_PROJECT_ID`)
- `backend/.env` populated with all production values
- `python3` available (used to parse `.env` into Cloud Run's env vars format)

### What the script does

| Step | Action |
|---|---|
| 1 | Enables `run`, `cloudbuild`, `cloudscheduler`, and `artifactregistry` GCP APIs |
| 2 | Creates the Artifact Registry Docker repository if it doesn't exist |
| 3 | Builds and pushes the Docker image via Cloud Build (runs remotely, `linux/amd64`) |
| 4 | Deploys the new image to Cloud Run with all env vars from `backend/.env` |
| 5 | Creates or updates the daily **send** Cloud Scheduler job (`xoxo-daily-send`) |
| 6 | Creates or updates the midnight **generate** Cloud Scheduler job (`xoxo-daily-generate`) |
| 7 | Prints a summary with both job names and the Cloud Run service URL |

> **Note:** `DRY_RUN` is always forced to `false` in the deployed service, regardless of what is set in `backend/.env`. The Scheduler jobs' cron schedules and timezones are **not** overwritten on re-deploys — manage those via the Schedule tab in the admin UI.

### Usage

```bash
./deploy.sh
```

To override the GCP project without changing your active `gcloud` config:

```bash
GCP_PROJECT_ID=my-other-project ./deploy.sh
```

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
    "broadcast": "POST /broadcast",
    "health": "GET /health",
    "stats": "GET /stats",
    "schedule": "GET /schedule",
    "update_schedule": "PATCH /schedule",
    "generate_messages": "POST /messages/generate",
    "today_messages": "GET /messages/today",
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
  "force": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `theme` | string | `"daily life"` | Topic theme for the LLM prompt (e.g. `"work"`, `"travel"`, `"food"`) |
| `force` | boolean | `false` | If `true`, sends even if a message was already sent today |

In multi-recipient mode (database configured), students are automatically grouped by their `english_level` and separate level-appropriate content is generated for each group. The LLM is called once per distinct level present in the active subscriber list.

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
  "preview": "beginner: Have breakfast | intermediate: Buyer's remorse",
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
  -d '{"theme": "work", "force": false}'
```

---

### `POST /broadcast`

Sends a custom message to all active, opted-in students. Optionally filters by English level. **Requires `X-API-Key`.**

**Request body**
```json
{
  "message": "Classes are cancelled this Friday. See you next week!",
  "level": "beginner"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | The message text to send |
| `level` | string | No | Restrict recipients to `"beginner"`, `"intermediate"`, or `"advanced"`. Omit (or `null`) to send to all levels. |

**Response**
```json
{
  "sent_count": 38,
  "failed_count": 1,
  "total_recipients": 39
}
```

**Example**
```bash
curl -X POST https://your-domain.com/broadcast \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"message": "No class this Monday!", "level": null}'
```

---

### `GET /schedule`

Returns the current schedule config read live from the GCP Cloud Scheduler job. **Requires `X-API-Key`.** Returns `503` if GCP env vars are not set.

**Response**
```json
{
  "theme": "daily life",
  "send_time": "08:00",
  "timezone": "America/Sao_Paulo"
}
```

**Example**
```bash
curl https://your-domain.com/schedule \
  -H "X-API-Key: your_api_key"
```

---

### `PATCH /schedule`

Updates the schedule config in the GCP Cloud Scheduler job. All fields are optional — only provided fields are changed. **Requires `X-API-Key`.** Returns `503` if GCP env vars are not set.

**Request body** (all fields optional)
```json
{
  "theme": "travel",
  "send_time": "09:00",
  "timezone": "America/Sao_Paulo"
}
```

| Field | Type | Validation |
|---|---|---|
| `theme` | string | Any non-empty string |
| `send_time` | string | `HH:MM` format (e.g. `"09:00"`) |
| `timezone` | string | IANA timezone string (e.g. `"America/Sao_Paulo"`) |

Returns the full updated `ScheduleConfigResponse` after applying changes. If `theme` or `timezone` is updated, the generate job (`GCP_GENERATE_JOB_ID`) is also synced automatically.

**Example** — update only the send time:
```bash
curl -X PATCH https://your-domain.com/schedule \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"send_time": "09:00"}'
```

---

### `POST /messages/generate`

Pre-generates and stores today's Word of the Day message(s) in the database. Called automatically at midnight by the `xoxo-daily-generate` Cloud Scheduler job; also available for admins to trigger regeneration on demand. **Requires `X-API-Key`.**

**Request body**
```json
{
  "theme": "travel",
  "level": "beginner"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `theme` | string | Yes | Topic hint for the LLM |
| `level` | string | No | If provided, generates only for that level (`"beginner"`, `"intermediate"`, or `"advanced"`). Omit to generate all three levels. |

**Response**
```json
{
  "date": "2026-03-04",
  "results": [
    {
      "level": "beginner",
      "theme": "travel",
      "formatted_message": "🇺🇸  *Palavra/Frase do Dia:* ...",
      "valid": true,
      "validation_errors": []
    }
  ]
}
```

Each result has `valid: false` and a populated `validation_errors` list if the LLM failed to produce a valid message after all retries. Valid results are upserted to the `messages` table.

**Example**
```bash
# Generate all levels
curl -X POST https://your-domain.com/messages/generate \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"theme": "travel"}'

# Regenerate only beginner
curl -X POST https://your-domain.com/messages/generate \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"theme": "travel", "level": "beginner"}'
```

---

### `GET /messages/today`

Returns the stored messages for today. **Requires `X-API-Key`.**

**Response**
```json
{
  "date": "2026-03-04",
  "messages": [
    {
      "level": "beginner",
      "theme": "travel",
      "formatted_message": "🇺🇸  *Palavra/Frase do Dia:* Have a safe trip\n\n📝 ...",
      "generated_at": "2026-03-04T00:00:12.345678"
    },
    {
      "level": "intermediate",
      "theme": "travel",
      "formatted_message": "...",
      "generated_at": "2026-03-04T00:00:18.123456"
    }
  ]
}
```

Returns an empty `messages` array if no messages have been generated for today yet.

**Example**
```bash
curl https://your-domain.com/messages/today \
  -H "X-API-Key: your_api_key"
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

### `GET /students/{phone_number}`

Returns a single student by phone number. **Requires `X-API-Key`.**

Returns `404 Not Found` if the student doesn't exist.

**Example**
```bash
curl "https://your-domain.com/students/%2B5511999999999" \
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
| `phone_number` | Yes | E.164 format (e.g. `+5511999999999`). Light normalization is applied automatically — formatting characters such as spaces, dashes, parentheses, and dots are stripped, and a leading `+` is added if missing. The result must be `+` followed by 7–15 digits. |
| `first_name` | No | Student's first name |
| `last_name` | No | Student's last name |
| `english_level` | No | `"beginner"` (default), `"intermediate"`, or `"advanced"` |
| `whatsapp_messages` | No | `true` (default) — whether to send messages |

Returns `201 Created` with the created student object, or `409 Conflict` if the phone number already exists.

When a student is created with `whatsapp_messages: true`, a Portuguese welcome WhatsApp message is sent to them immediately:

> *Olá [Nome]! 👋 Você foi cadastrado(a) no serviço Palavra do Dia da XOXO Education.*
>
> *A partir de agora, você receberá uma mensagem diária com uma palavra ou frase em inglês para turbinar seu vocabulário! Para cancelar, basta responder STOP.*

If the welcome message fails (e.g. due to a transient WaSenderAPI error), the failure is logged as a warning and the student is still created — `201` is still returned.

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

### `PATCH /students/{phone_number}`

Updates one or more fields for an existing student. All fields are optional — only provided fields are changed. **Requires `X-API-Key`.**

**Request body** (all fields optional)
```json
{
  "first_name": "Maria",
  "last_name": "Silva",
  "english_level": "intermediate",
  "whatsapp_messages": true
}
```

Returns the updated student object, or `404 Not Found` if the student doesn't exist.

**Example** — update level only:
```bash
curl -X PATCH "https://your-domain.com/students/+5511999999999" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"english_level": "advanced"}'
```

---

### `POST /students/{phone_number}/deactivate`

Soft-deletes a student — sets `is_active = false` so they no longer receive messages but remain in the database. **Requires `X-API-Key`.**

Returns `200` with the updated student object, or `404 Not Found` if the student doesn't exist.

**Example**
```bash
curl -X POST "https://your-domain.com/students/%2B5511999999999/deactivate" \
  -H "X-API-Key: your_api_key"
```

---

### `POST /students/{phone_number}/reactivate`

Re-enables a previously deactivated student — sets `is_active = true`. **Requires `X-API-Key`.**

Returns `200` with the updated student object, or `404 Not Found` if the student doesn't exist.

**Example**
```bash
curl -X POST "https://your-domain.com/students/%2B5511999999999/reactivate" \
  -H "X-API-Key: your_api_key"
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
| `STOP` (exact, case-insensitive) | `whatsapp_messages = false` | PT-BR opt-out confirmation + re-enrol instructions |
| `START` (exact, case-insensitive) | `whatsapp_messages = true` | PT-BR welcome-back confirmation |
| Anything else | No change | No reply |

---

### `GET /stats`

Returns aggregate dashboard statistics. **Requires `X-API-Key`.**

**Response**
```json
{
  "total_students": 15,
  "active_students": 12,
  "inactive_students": 3,
  "subscribed_students": 11,
  "opted_out_students": 1,
  "sent_today": true,
  "sends_today": 11
}
```

**Example**
```bash
curl https://your-domain.com/stats \
  -H "X-API-Key: your_api_key"
```

---

### `GET /audit-log`

Returns paginated audit log entries with optional filtering. **Requires `X-API-Key`.**

**Query parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_str` | string | — | ISO date string to filter by (e.g. `2026-02-20`) |
| `phone_number` | string | — | Filter to a specific student's phone number |
| `limit` | integer | `50` | Maximum entries to return |
| `offset` | integer | `0` | Number of entries to skip (for pagination) |

**Example**
```bash
# All entries for today
curl "https://your-domain.com/audit-log?date_str=2026-02-20" \
  -H "X-API-Key: your_api_key"

# A specific student's history
curl "https://your-domain.com/audit-log?phone_number=%2B5511999999999&limit=10" \
  -H "X-API-Key: your_api_key"
```

---

## Dashboard Stats

The `GET /stats` endpoint provides real-time counts used by the admin dashboard:

- **total / active / inactive** — student counts
- **subscribed / opted_out** — WhatsApp opt-in status counts
- **sent_today / sends_today** — whether a message was sent today and how many students received it (based on the JSONL audit log)

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

**Available levels:** `beginner`, `intermediate`, `advanced`

---

## Cron Setup

### Production — GCP Cloud Scheduler

In production, two GCP Cloud Scheduler jobs drive the daily workflow:

| Job | Default time | Endpoint | Purpose |
|---|---|---|---|
| `xoxo-daily-generate` | 12:00 AM | `POST /messages/generate` | Generate and store messages for each level |
| `xoxo-daily-send` | 8:00 AM (configurable) | `POST /send-word-of-day` | Read stored messages and deliver to students |

Both jobs are created/updated by `deploy.sh`. You can update the send schedule (time, timezone, theme) via the admin dashboard Schedule tab or the API — changes propagate to both Cloud Scheduler jobs automatically.

```bash
# View current schedule
curl https://your-domain.com/schedule -H "X-API-Key: your_api_key"

# Change send time to 9 AM
curl -X PATCH https://your-domain.com/schedule \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"send_time": "09:00"}'
```

Or manage directly via the GCP Console → Cloud Scheduler, or with `gcloud`:

```bash
gcloud scheduler jobs list --location=us-central1
gcloud scheduler jobs describe xoxo-daily-send --location=us-central1
gcloud scheduler jobs describe xoxo-daily-generate --location=us-central1
```

### Local dev — system cron

For local development without GCP, add a crontab entry:

```bash
crontab -e
```

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
3. Checks if the message body is exactly `"stop"` or `"start"` (case-insensitive — messages containing these words alongside other text are ignored)
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

**LLM availability (503 errors)**

1. Primary model called — if 503, wait 10s and retry
2. If still 503, wait 30s and retry once more
3. If still failing, try the fallback model (`LLM_FALLBACK_MODEL`, default `gemini-2.0-flash-lite`) using the same API key
4. If both models are unavailable, **no message is sent** for that run

**Validation failures**

1. **Attempt 1** — Generate 6 parameters with the LLM
2. **Validate** — Check all rules
3. **Attempt 2** — If invalid, regenerate using a repair prompt that includes the specific validation errors
4. **Attempt 3** — Retry repair once more if still invalid
5. If all 3 attempts fail validation, **no message is sent**

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
backend/
├── app/
│   ├── main.py                     # CLI entry point (send, preview, health)
│   ├── config.py                   # Environment variable configuration
│   ├── api/
│   │   ├── routes.py               # FastAPI app factory and router registration
│   │   ├── deps.py                 # Shared FastAPI dependencies (auth, DB, GCP client)
│   │   ├── schemas.py              # Shared Pydantic request/response models
│   │   ├── webhook_routes.py       # Webhook handler (STOP/START opt-outs)
│   │   └── routers/
│   │       ├── students.py         # Student CRUD endpoints
│   │       ├── messages.py         # POST /send-word-of-day, POST /broadcast, POST /messages/generate, GET /messages/today
│   │       ├── admin.py            # GET /health, GET /stats, GET /audit-log
│   │       └── schedule.py         # GET /schedule, PATCH /schedule (syncs both GCP jobs)
│   ├── services/
│   │   └── word_of_day_service.py  # Orchestration: generate → validate → send
│   ├── domain/
│   │   ├── validators.py           # Message validation rules
│   │   └── fallback.py             # Safe fallback message parameters
│   ├── integrations/
│   │   ├── llm_client.py           # LLM API client (OpenAI-compatible)
│   │   ├── wasender_client.py      # WaSenderAPI client
│   │   └── gcp_scheduler.py        # GCP Cloud Scheduler client (get/update job)
│   ├── logging/
│   │   └── audit_log.py            # JSONL audit trail
│   ├── db/
│   │   ├── base.py                 # SQLAlchemy Base and TimestampMixin
│   │   ├── session.py              # Database engine and session management
│   │   └── models/
│   │       ├── student.py          # Student ORM model
│   │       └── message.py          # Message ORM model (pre-generated daily messages)
│   └── repositories/
│       ├── student.py              # Student CRUD operations
│       └── message.py              # Message upsert and lookup by date/level
├── scripts/
│   ├── init_db.py                  # Create all database tables
│   └── manage_students.py          # Student management CLI (add, list, remove, opt-out)
├── deploy.sh                       # One-command GCP deployment (Cloud Build + Cloud Run + Scheduler)
├── tests/
│   ├── test_validators.py          # Validation rule tests
│   ├── test_service_happy_path.py  # Service integration tests (including stored message logic)
│   ├── test_enrollment.py          # Phone normalization, welcome message, and POST /students tests
│   ├── test_broadcast.py           # POST /broadcast endpoint tests
│   ├── test_message_repository.py  # MessageRepository unit tests (SQLite in-memory)
│   └── test_generate_endpoint.py   # POST /messages/generate and GET /messages/today tests
├── Dockerfile
└── pyproject.toml

frontend/
├── src/
│   ├── api/
│   │   ├── client.ts               # Base fetch wrapper (attaches X-API-Key, throws on non-2xx)
│   │   ├── students.ts             # Typed functions for all student endpoints
│   │   ├── schedule.ts             # Typed functions for GET/PATCH /schedule
│   │   └── messages.ts             # Typed functions for POST /broadcast, POST /messages/generate, GET /messages/today
│   ├── components/
│   │   ├── ui/                     # shadcn/ui primitives (Button, Table, Dialog, etc.)
│   │   ├── LoginScreen.tsx         # API key entry form
│   │   ├── StudentsTab.tsx         # Student table with search, filter, and CRUD actions
│   │   ├── ScheduleTab.tsx         # Schedule config form + Today's Messages preview with per-level dialogs
│   │   ├── AnnouncementTab.tsx     # Broadcast message form (message, level filter)
│   │   ├── AddStudentDialog.tsx    # Add student form dialog
│   │   ├── EditStudentDialog.tsx   # Edit student form dialog (pre-filled)
│   │   └── DeleteConfirmDialog.tsx # Hard-delete confirmation dialog
│   ├── lib/
│   │   └── utils.ts                # shadcn/ui utility (cn)
│   ├── App.tsx                     # Auth gate + tab navigation (Students, Schedule, Send Announcement)
│   ├── main.tsx                    # React Query provider + render
│   └── index.css                   # Tailwind + shadcn CSS variables
├── .env.example                    # VITE_API_URL=http://localhost:8000
├── components.json                 # shadcn/ui config
├── package.json
├── tsconfig.json
└── vite.config.ts
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
- The app will automatically retry with a repair prompt; if all repair attempts fail, no message is sent for that run

### Database errors

- Confirm `DATABASE_URL` is set correctly in `.env`
- If tables don't exist, run `python scripts/init_db.py`
- Check Supabase dashboard to confirm your project is active

### Webhook not triggering (STOP/START not working)

- Confirm the webhook URL and `messages.received` event are configured in the WaSenderAPI dashboard
- Confirm `WASENDER_WEBHOOK_SECRET` in `.env` matches the secret shown in the WaSenderAPI dashboard exactly
- If running locally, use [ngrok](https://ngrok.com) to expose your server: `ngrok http 8000`
- Check your server logs — a `401` response means the signature is not matching

### `GET /schedule` or `PATCH /schedule` returning 503

The schedule endpoints are production-only and require all five GCP env vars to be set: `GCP_PROJECT_ID`, `GCP_LOCATION`, `GCP_SCHEDULER_JOB_ID`, `GCP_GENERATE_JOB_ID`, `SERVICE_URL`. Leave them blank in local dev and the 503 is expected.

If the vars are set but you're still getting an error, make sure Application Default Credentials are configured:

```bash
gcloud auth application-default login
```

### API returning 401

- Confirm you are passing the `X-API-Key` header with the correct value
- The value must match `API_KEY` in your `.env`
- The `/health`, `/`, and `/webhook/whatsapp` endpoints do not require this header

---

## License

MIT License — XOXO Education
