#!/usr/bin/env bash
# stop_ai_server.sh — Stop the llama.cpp server and release wake lock
pkill -f "llama-server" 2>/dev/null && echo "Stopped llama-server." || echo "llama-server was not running."
termux-wake-unlock 2>/dev/null || true
