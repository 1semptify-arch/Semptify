#!/system/bin/sh
# service.sh — runs late in boot, after zygote and most services have started.
# This is where we kill the things we don't want and start the AI server.

# Wait for boot to complete
while [ "$(getprop sys.boot_completed)" != "1" ]; do
  sleep 1
done
sleep 5  # give system services a moment to settle

# Load config
ENV_FILE="/data/ai_host.env"
if [ -f "$ENV_FILE" ]; then
  . "$ENV_FILE"
fi

# Defaults
AI_HOST_WIFI_ONLY="${AI_HOST_WIFI_ONLY:-0}"
AI_HOST_DISABLE_CELL="${AI_HOST_DISABLE_CELL:-0}"
AI_HOST_KEEP_TELEPHONY="${AI_HOST_KEEP_TELEPHONY:-0}"
AI_HOST_KEEP_SYSTEMUI="${AI_HOST_KEEP_SYSTEMUI:-0}"
AI_HOST_PORT="${AI_HOST_PORT:-8080}"
AI_HOST_THREADS="${AI_HOST_THREADS:-4}"
AI_HOST_CTX="${AI_HOST_CTX:-2048}"
AI_HOST_MODEL="${AI_HOST_MODEL:-/data/data/com.termux/files/home/ai_host/models/qwen2-0.5b-instruct-q4_k_m.gguf}"
AI_HOST_CHARGE_LIMIT="${AI_HOST_CHARGE_LIMIT:-0}"

LOGFILE="/data/ai_host.log"
exec >> "$LOGFILE" 2>&1
echo "=== AI Host service.sh started: $(date) ==="

# --- 1. Disable Google services and bloat ---
# These are safe to force-stop. They'll restart only if something requests them.
SERVICES_TO_KILL="
  com.google.android.gms
  com.google.android.gms.ui
  com.google.android.gms.location
  com.google.android.gsf
  com.google.android.googlequicksearchbox
  com.google.android.apps.maps
  com.google.android.youtube
  com.google.android.apps.photos
  com.android.vending
  com.google.android.inputmethod.latin
  com.android.systemui
"

for pkg in $SERVICES_TO_KILL; do
  if [ "$AI_HOST_KEEP_SYSTEMUI" = "1" ] && [ "$pkg" = "com.android.systemui" ]; then
    echo "[AI Host] keeping SystemUI (AI_HOST_KEEP_SYSTEMUI=1)"
    continue
  fi
  am force-stop "$pkg" 2>/dev/null
  pm disable-user --user 0 "$pkg" 2>/dev/null
  echo "[AI Host] disabled $pkg"
done

# --- 2. Optionally disable cell radio ---
if [ "$AI_HOST_WIFI_ONLY" = "1" ] || [ "$AI_HOST_DISABLE_CELL" = "1" ]; then
  if [ "$AI_HOST_KEEP_TELEPHONY" != "1" ]; then
    svc data disable 2>/dev/null
    settings put global airplane_mode_on 1 2>/dev/null
    am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true 2>/dev/null
    sleep 2
    svc wifi enable 2>/dev/null
    echo "[AI Host] cell radio disabled, Wi-Fi enabled"
  fi
fi

# --- 3. Drop filesystem caches ---
sync
echo 3 > /proc/sys/vm/drop_caches
echo "[AI Host] caches dropped"

# --- 4. Optional: limit battery charge to 80% to prolong life ---
if [ "$AI_HOST_CHARGE_LIMIT" != "0" ]; then
  echo "$AI_HOST_CHARGE_LIMIT" > /sys/class/power_supply/battery/battery_charging_enabled 2>/dev/null || true
  echo "[AI Host] charge limit set to $AI_HOST_CHARGE_LIMIT"
fi

# --- 5. Free memory report ---
MemFree=$(awk '/MemAvailable/ {print int($2/1024) " MB"}' /proc/meminfo)
echo "[AI Host] RAM available after stripping: $MemFree"

# --- 6. Start the AI server via Termux ---
# We use am to start Termux with a specific command, then run the server.
TERMUX_HOME=/data/data/com.termux/files/home
TERMUX_SERVER="$TERMUX_HOME/ai_host/llama.cpp/build/bin/llama-server"

if [ ! -f "$TERMUX_SERVER" ]; then
  echo "[AI Host] ERROR: $TERMUX_SERVER not found. Run install_termux.sh in Termux first."
  exit 1
fi

if [ ! -f "$AI_HOST_MODEL" ]; then
  echo "[AI Host] ERROR: model $AI_HOST_MODEL not found."
  exit 1
fi

# Launch the server in background via nohup
nohup "$TERMUX_SERVER" \
  -m "$AI_HOST_MODEL" \
  --host 0.0.0.0 \
  --port "$AI_HOST_PORT" \
  -t "$AI_HOST_THREADS" \
  -c "$AI_HOST_CTX" \
  -ngl 0 \
  >> "$LOGFILE" 2>&1 &

SERVER_PID=$!
echo "[AI Host] llama-server started, PID=$SERVER_PID"

# Wait for it to come up
sleep 10

# Protect the server from the OOM killer (root lets us do this)
echo -17 > /proc/$SERVER_PID/oom_score_adj 2>/dev/null || true
echo -1000 > /proc/$SERVER_PID/oom_score_adj 2>/dev/null || true
echo "[AI Host] OOM protection applied to PID $SERVER_PID"

# Verify it's listening
if netstat -tln 2>/dev/null | grep -q ":$AI_HOST_PORT "; then
  echo "[AI Host] Server listening on port $AI_HOST_PORT — OK"
else
  echo "[AI Host] WARNING: server not listening on $AI_HOST_PORT yet"
fi

echo "=== AI Host service.sh complete: $(date) ==="
