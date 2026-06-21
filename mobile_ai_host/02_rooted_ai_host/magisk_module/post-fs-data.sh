#!/system/bin/sh
# post-fs-data.sh — runs early in boot, after /data is mounted but before zygote.
# We use this to read the config file and set up zram early.

# Load config if present
ENV_FILE="/data/ai_host.env"
if [ -f "$ENV_FILE" ]; then
  . "$ENV_FILE"
fi

# Defaults
AI_HOST_WIFI_ONLY="${AI_HOST_WIFI_ONLY:-0}"
AI_HOST_DISABLE_CELL="${AI_HOST_DISABLE_CELL:-0}"
AI_HOST_ZRAM_SIZE="${AI_HOST_ZRAM_SIZE:-512M}"
AI_HOST_CPU_GOVERNOR="${AI_HOST_CPU_GOVERNOR:-performance}"

# Set up zram swap (compresses RAM — effectively gives us ~1.5x RAM for AI workloads)
# Only set up if not already present
if [ ! -e /dev/block/zram0 ]; then
  echo 1 > /sys/block/zram0/reset 2>/dev/null
fi
if [ -e /sys/block/zram0/disksize ]; then
  echo "$AI_HOST_ZRAM_SIZE" > /sys/block/zram0/disksize 2>/dev/null
  mkswap /dev/block/zram0 2>/dev/null
  swapon /dev/block/zram0 2>/dev/null
  echo "[AI Host] zram enabled: $AI_HOST_ZRAM_SIZE"
fi

# Set CPU governor to performance on all cores
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  [ -f "$cpu" ] && echo "$AI_HOST_CPU_GOVERNOR" > "$cpu" 2>/dev/null
done
echo "[AI Host] CPU governor set to $AI_HOST_CPU_GOVERNOR"

# Disable CPU big.LITTLE migration (keep all cores online)
for cpu in /sys/devices/system/cpu/cpu*/online; do
  [ -f "$cpu" ] && echo 1 > "$cpu" 2>/dev/null
done

# Make the OOM killer friendlier to our AI process
# We'll set the actual oom_score_adj in service.sh once we know the PID
echo "[AI Host] post-fs-data complete"
