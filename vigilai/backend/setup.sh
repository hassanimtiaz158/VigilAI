#!/usr/bin/env bash
# VigilAI Backend — Setup Script
# Creates virtual environment, installs dependencies, and initializes .env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

echo "============================================="
echo "  VigilAI Backend Setup"
echo "============================================="
echo ""

# ------------------------------------------------------------------ #
#  1. Create Python virtual environment
# ------------------------------------------------------------------ #
if [ ! -d "$VENV_DIR" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
  echo "      Created: $VENV_DIR"
else
  echo "[1/4] Virtual environment already exists — skipping"
fi

# Activate
# shellcheck disable=SC1091
if [ -f "$VENV_DIR/bin/activate" ]; then
  source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
  source "$VENV_DIR/Scripts/activate"
fi
echo ""

# ------------------------------------------------------------------ #
#  2. Install dependencies
# ------------------------------------------------------------------ #
echo "[2/4] Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "      Done"
echo ""

# ------------------------------------------------------------------ #
#  3. Initialize .env if missing
# ------------------------------------------------------------------ #
echo "[3/4] Checking .env file..."
if [ -f "$ENV_FILE" ]; then
  echo "      .env exists — skipping"
else
  if [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "      Copied .env.example → .env"
  else
    echo "      WARNING: .env.example not found — creating empty .env"
    touch "$ENV_FILE"
  fi
fi
echo ""

# ------------------------------------------------------------------ #
#  4. Post-install checklist
# ------------------------------------------------------------------ #
echo "[4/4] Setup complete!"
echo ""
echo "============================================="
echo "  Post-Install Checklist"
echo "============================================="
echo ""
echo "  [ ] Add GROQ_API_KEY to .env"
echo "      Get one free at: https://console.groq.com"
echo ""
echo "  [ ] Add GMAIL_USER and GMAIL_APP_PASSWORD to .env"
echo "      See: docs/alert-system-setup.md (Gmail section)"
echo ""
echo "  [ ] Add TWILIO credentials to .env"
echo "      Sign up free at: https://www.twilio.com"
echo ""
echo "  [ ] Add POLICE_EMAIL and POLICE_PHONE to .env"
echo ""
echo "  [ ] Add EMERGENCY_EMAIL and EMERGENCY_PHONE to .env"
echo ""
echo "  [ ] Add OWNER_EMAIL and OWNER_PHONE to .env"
echo ""
echo "  [ ] Place test video in: demo/samples/test.mp4"
echo ""
echo "  [ ] Start the server:"
echo "        cd $SCRIPT_DIR"
echo "        source venv/bin/activate   # or venv\\Scripts\\activate on Windows"
echo "        uvicorn main:app --reload"
echo ""
echo "  [ ] Test alert pipeline:"
echo "        curl -X POST http://localhost:8000/test-alert \\"
echo "          -H 'Content-Type: application/json' \\"
echo "          -d '{\"message\": \"VigilAI test alert\"}'"
echo ""
echo "============================================="
