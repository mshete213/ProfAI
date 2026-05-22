#!/usr/bin/env bash
# One-command developer setup for the EdTech RAG Platform.
#
# Equivalent to `make setup`, but works without `make` installed.
# Prereqs: Python 3.12+, Node 20+, Docker (for the full stack)

set -e

cd "$(dirname "$0")"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
green() { printf "\033[32m%s\033[0m\n" "$1"; }
red() { printf "\033[31m%s\033[0m\n" "$1"; }

bold "==> Checking prerequisites"

missing=()
command -v python3 >/dev/null 2>&1 || missing+=("python3 (3.12+)")
command -v node    >/dev/null 2>&1 || missing+=("node (20+)")
command -v npm     >/dev/null 2>&1 || missing+=("npm")
command -v docker  >/dev/null 2>&1 || echo "  (warn) Docker not found — make up will fail until you install Docker Desktop"

if [ ${#missing[@]} -gt 0 ]; then
  red "Missing required tools: ${missing[*]}"
  echo "Install them, then re-run ./setup.sh"
  exit 1
fi

green "  All required tools found."

bold "==> Creating .env from .env.example (if missing)"
if [ ! -f .env ]; then
  cp .env.example .env
  green "  ✓ Created .env — edit it later with your API keys"
else
  echo "  .env already exists, leaving alone"
fi

bold "==> Creating Python virtualenv (.venv)"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  green "  ✓ Created .venv"
else
  echo "  .venv already exists"
fi

bold "==> Installing Python dependencies (backend + MCP server)"
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r backend/requirements.txt --quiet
green "  ✓ Backend deps installed"

bold "==> Installing frontend dependencies (npm)"
( cd frontend && npm install --silent )
green "  ✓ Frontend deps installed"

cat <<EOF

$(bold "Setup complete.")

Next steps:
  1. Edit .env and paste your ANTHROPIC_API_KEY, OPENAI_API_KEY, PINECONE_API_KEY
  2. Start the full stack:        $(green "docker compose up")
     (or for local dev without Docker, see README "Local development")
  3. Open the app:                http://localhost:3000
  4. API docs:                    http://localhost:8000/docs
EOF
