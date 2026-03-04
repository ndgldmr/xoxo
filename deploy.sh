#!/usr/bin/env bash
# deploy.sh — Build, push, and deploy the XOXO backend to Cloud Run.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated  (gcloud auth login)
#   - backend/.env populated with production values
#
# Usage:
#   ./deploy.sh
#
# Configuration can be overridden via environment variables:
#   GCP_PROJECT_ID=my-project ./deploy.sh

set -euo pipefail

# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="us-central1"
SERVICE_NAME="xoxo"
SERVICE_URL="https://xoxo-1041229952625.us-central1.run.app"
REPO_NAME="xoxo"          # Artifact Registry repository name

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}"
ENV_FILE="backend/.env"

# Default schedule used only when the Cloud Scheduler job is created for the
# first time. Afterwards, manage the schedule via the Schedule tab in the admin UI.
DEFAULT_CRON="0 11 * * *"          # 11:00 UTC = 08:00 America/Sao_Paulo
DEFAULT_TIMEZONE="America/Sao_Paulo"

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

abort() { echo ""; echo "ERROR: $*" >&2; exit 1; }

step() {
  echo ""
  echo "==> $*"
}

# ══════════════════════════════════════════════════════════════════════════════
# Pre-flight checks
# ══════════════════════════════════════════════════════════════════════════════

command -v gcloud >/dev/null 2>&1 || abort "gcloud CLI not found. Install it from https://cloud.google.com/sdk/docs/install"
command -v python3 >/dev/null 2>&1 || abort "python3 not found."

[[ -z "$PROJECT_ID" ]] && abort "GCP project ID not set. Run: gcloud config set project YOUR_PROJECT_ID  (or export GCP_PROJECT_ID=...)"
[[ ! -f "$ENV_FILE" ]] && abort "$ENV_FILE not found. Copy backend/.env.example to backend/.env and fill in all values."

echo ""
echo "┌──────────────────────────────────────────────┐"
echo "│  XOXO — Cloud Run Deploy                     │"
echo "├──────────────────────────────────────────────┤"
printf "│  Project : %-34s│\n" "$PROJECT_ID"
printf "│  Region  : %-34s│\n" "$REGION"
printf "│  Service : %-34s│\n" "$SERVICE_NAME"
printf "│  Image   : %-34s│\n" "${IMAGE##*/}:latest"
echo "└──────────────────────────────────────────────┘"

# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Enable required GCP APIs
# ══════════════════════════════════════════════════════════════════════════════

step "[1/6] Enabling GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  --project="$PROJECT_ID" \
  --quiet

# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Ensure Artifact Registry repository exists
# ══════════════════════════════════════════════════════════════════════════════

step "[2/6] Checking Artifact Registry repository..."
if ! gcloud artifacts repositories describe "$REPO_NAME" \
     --location="$REGION" \
     --project="$PROJECT_ID" \
     --quiet 2>/dev/null; then
  echo "    Repository not found — creating '$REPO_NAME'..."
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --quiet
else
  echo "    Repository '$REPO_NAME' already exists."
fi

# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — Build and push image via Cloud Build (no local Docker required)
# ══════════════════════════════════════════════════════════════════════════════

step "[3/6] Building and pushing image via Cloud Build..."
gcloud builds submit \
  --tag="${IMAGE}:latest" \
  --project="$PROJECT_ID" \
  backend/

# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — Deploy to Cloud Run
# ══════════════════════════════════════════════════════════════════════════════

step "[4/5] Deploying to Cloud Run..."

# Convert backend/.env to a YAML env vars file for --env-vars-file.
# Handles quoted values and = signs in values (e.g. DATABASE_URL).
TMPFILE=$(mktemp /tmp/xoxo-env-XXXXXX.yaml)
trap 'rm -f "$TMPFILE"' EXIT

# Keys explicitly set below — skip them when reading .env to avoid duplicates.
OVERRIDE_KEYS="GCP_PROJECT_ID GCP_LOCATION GCP_SCHEDULER_JOB_ID SERVICE_URL DRY_RUN"

python3 - "$ENV_FILE" "$OVERRIDE_KEYS" << 'PYEOF' > "$TMPFILE"
import sys, re

env_file = sys.argv[1]
skip = set(sys.argv[2].split())

with open(env_file) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, val = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if key in skip:
            continue
        val = val.strip()
        # Strip matching surrounding quotes
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        # Strip inline comments (e.g. "value  # comment" -> "value")
        val = re.sub(r'\s+#.*$', '', val)
        # Escape backslashes and double-quotes for YAML double-quoted strings
        val = val.replace("\\", "\\\\").replace('"', '\\"')
        print(f'{key}: "{val}"')
PYEOF

# Append production overrides — these take precedence over anything in .env.
# DRY_RUN is always forced to false in production.
cat >> "$TMPFILE" << EOF
GCP_PROJECT_ID: "$PROJECT_ID"
GCP_LOCATION: "$REGION"
GCP_SCHEDULER_JOB_ID: "xoxo-daily-send"
SERVICE_URL: "$SERVICE_URL"
DRY_RUN: "false"
EOF

gcloud run deploy "$SERVICE_NAME" \
  --image="${IMAGE}:latest" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --min-instances=0 \
  --max-instances=3 \
  --env-vars-file="$TMPFILE" \
  --quiet

# ══════════════════════════════════════════════════════════════════════════════
# Step 6 — Create or update Cloud Scheduler job
# ══════════════════════════════════════════════════════════════════════════════

step "[5/5] Configuring Cloud Scheduler job..."

API_KEY=$(grep '^API_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
[[ -z "$API_KEY" ]] && abort "API_KEY not found in $ENV_FILE"

JOB_ID="xoxo-daily-send"
JOB_URI="${SERVICE_URL}/send-word-of-day"
JOB_BODY='{"theme":"daily life","force":false}'
JOB_HEADERS="Content-Type=application/json,X-API-Key=${API_KEY}"

if gcloud scheduler jobs describe "$JOB_ID" \
   --location="$REGION" \
   --project="$PROJECT_ID" \
   --quiet 2>/dev/null; then
  # Job already exists — update only the target URI and auth headers.
  # The schedule and timezone are managed via the Schedule tab in the admin UI.
  echo "    Job exists — updating URI and auth headers (schedule unchanged)."
  gcloud scheduler jobs update http "$JOB_ID" \
    --uri="$JOB_URI" \
    --http-method=POST \
    --update-headers="$JOB_HEADERS" \
    --message-body="$JOB_BODY" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --quiet
else
  echo "    Job not found — creating with default schedule."
  echo "    Schedule: '$DEFAULT_CRON' ($DEFAULT_TIMEZONE)"
  echo "    You can update the schedule from the Schedule tab in the admin UI."
  gcloud scheduler jobs create http "$JOB_ID" \
    --schedule="$DEFAULT_CRON" \
    --time-zone="$DEFAULT_TIMEZONE" \
    --uri="$JOB_URI" \
    --http-method=POST \
    --headers="$JOB_HEADERS" \
    --message-body="$JOB_BODY" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --quiet
fi

# ══════════════════════════════════════════════════════════════════════════════
# Done
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "✓ Deploy complete."
echo "  Service URL : $SERVICE_URL"
echo "  Scheduler   : $JOB_ID ($DEFAULT_CRON $DEFAULT_TIMEZONE)"
echo ""
