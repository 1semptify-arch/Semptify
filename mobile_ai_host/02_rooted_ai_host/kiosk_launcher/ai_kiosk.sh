#!/usr/bin/env bash
# ai_kiosk.sh — Termux:Boot autostart script
# Runs after every reboot, launches the AI server in foreground.
# Place at: ~/.termux/boot/ai-kiosk.sh
set -euo pipefail

LOG="$HOME/.termux/boot/ai-kiosk.log"
exec >> "$LOG" 2>&1
echo "=== ai_kiosk.sh started: $(date) ==="

# Acquire wake lock so Android doesn't doze and kill us
termux-wake-lock 2>/dev/null || true

# Drop caches (best-effort; Magisk module does this with root)
sync 2>/dev/null || true
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true

# Load config
ENV_FILE="/data/ai_host.env"
if [ -f "$ENV_FILE" ]; then
  # Source only the vars we care about (file is root-owned but world-readable)
  AI_HOST_PORT=$(grep -E '^AI_HOST_PORT=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo 8080)
  AI_HOST_THREADS=$(grep -E '^AI_HOST_THREADS=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo 4)
  AI_HOST_CTX=$(grep -E '^AI_HOST_CTX=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo 2048)
  AI_HOST_MODEL=$(grep -E '^AI_HOST_MODEL=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "")
fi

AI_HOST_PORT="${AI_HOST_PORT:-8080}"
AI_HOST_THREADS="${AI_HOST_THREADS:-4}"
AI_HOST_CTX="${AI_HOST_CTX:-2048}"
AI_HOST_MODEL="${AI_HOST_MODEL:-$HOME/ai_host/models/qwen2-0.5b-instruct-q4_k_m.gguf}"

SERVER="$HOME/ai_host/llama.cpp/build/bin/llama-server"

if [ ! -f "$SERVER" ]; then
  echo "ERROR: $SERVER not found. Run install_termux.sh first."
  exit 1
fi

if [ ! -f "$AI_HOST_MODEL" ]; then
  echo "ERROR: model $AI_HOST_MODEL not found."
  exit 1
fi

echo ">>> Starting llama-server on 0.0.0.0:$AI_HOST_PORT"
echo ">>> Model: $AI_HOST_MODEL"
echo ">>> Threads: $AI_HOST_THREADS  Context: $AI_HOST_CTX"

# Foreground exec — Termux:Boot keeps the process alive
exec "$SERVER" \
  -m "$AI_HOST_MODEL" \
  --host 0.0.0.0 \
  --port "$AI_HOST_PORT" \
  -t "$AI_HOST_THREADS" \
  -c "$AI_HOST_CTX" \
  -ngl 0
