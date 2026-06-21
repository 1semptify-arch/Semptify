#!/usr/bin/env bash
# start_ai_server.sh — Launch llama.cpp HTTP server on the phone (no-root)
# Works inside Termux on LG Stylo 4 and other ARM64 Android phones.
set -euo pipefail

WORKDIR="$HOME/ai_host"
SERVER="$WORKDIR/llama.cpp/build/bin/llama-server"
MODEL="$WORKDIR/models/qwen2-0.5b-instruct-q4_k_m.gguf"
PORT="${AI_PORT:-8080}"
THREADS="${AI_THREADS:-4}"
CTX="${AI_CTX:-2048}"

if [ ! -f "$SERVER" ]; then
  echo "ERROR: $SERVER not found."
  echo "Run install_termux.sh first."
  exit 1
fi

if [ ! -f "$MODEL" ]; then
  echo "ERROR: $MODEL not found."
  echo "Run install_termux.sh first, or set AI_MODEL to a different path."
  exit 1
fi

# Allow override of model path
if [ -n "${AI_MODEL:-}" ]; then
  MODEL="$AI_MODEL"
fi

# Prevent Android from killing us during long inferences
termux-wake-lock 2>/dev/null || true

# Best-effort cache drop (no root: silently fails, that's fine)
sync 2>/dev/null || true
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true

# Print device info
echo "=== AI Server (No-Root) ==="
echo "Device: $(getprop ro.product.model 2>/dev/null || echo 'unknown')"
echo "RAM free: $(awk '/MemAvailable/ {print int($2/1024) " MB"}' /proc/meminfo)"
echo "Model: $MODEL"
echo "Threads: $THREADS  Context: $CTX  Port: $PORT"
echo "IP: $(ip addr show wlan0 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 || echo 'unknown')"
echo "Test: curl http://127.0.0.1:$PORT/v1/chat/completions ..."
echo ""

# Launch server in foreground so we see logs
exec "$SERVER" \
  -m "$MODEL" \
  --host 0.0.0.0 \
  --port "$PORT" \
  -t "$THREADS" \
  -c "$CTX" \
  -ngl 0 \
  --color
