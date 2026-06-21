#!/usr/bin/env bash
# test_inference.sh — Quick smoke test for the AI server
# Run from Termux on the phone, OR from a laptop on the same Wi-Fi (set AI_HOST)
set -euo pipefail

HOST="${AI_HOST:-127.0.0.1}"
PORT="${AI_PORT:-8080}"
URL="http://$HOST:$PORT/v1/chat/completions"

echo ">>> Testing $URL"
echo ""

RESPONSE=$(curl -s --max-time 60 "$URL" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2-0.5b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant. Keep answers short."},
      {"role": "user", "content": "Say hello in one sentence."}
    ],
    "max_tokens": 50,
    "temperature": 0.7
  }')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Also test the /health endpoint
echo ">>> Health check:"
curl -s --max-time 5 "http://$HOST:$PORT/health" || echo "(health endpoint not available)"
echo ""
