#!/system/bin/sh
# bootstrap_rooted.sh — One-shot setup for the rooted AI host package.
# Run as root (su) after:
#   1. Phone is rooted with Magisk
#   2. Termux is installed from F-Droid
#   3. install_termux.sh has been run inside Termux (builds llama.cpp, downloads model)
#
# This script:
#   - Writes the config file /data/ai_host.env
#   - Zips the Magisk module
#   - Copies the kiosk launcher into Termux's boot dir
#   - Tells you what to do next (open Magisk Manager, install the zip)

set -e

if [ "$(id -u)" != "0" ]; then
  echo "ERROR: run this script as root. Run 'su' first."
  exit 1
fi

TERMUX_HOME=/data/data/com.termux/files/home
MODULE_SRC="/sdcard/ai_host_module_src"
MODULE_ZIP="/sdcard/ai_host_module.zip"

echo "=== AI Host Rooted Bootstrap ==="

# 1. Write config file
echo ">>> Writing /data/ai_host.env ..."
cat > /data/ai_host.env <<'EOF'
# AI Host configuration. Edit and reboot to apply.
# After changing, run:   reboot

# Network
AI_HOST_PORT=8080

# Performance
AI_HOST_THREADS=4
AI_HOST_CTX=2048

# Model (path inside Termux's home)
AI_HOST_MODEL=/data/data/com.termux/files/home/ai_host/models/qwen2-0.5b-instruct-q4_k_m.gguf

# Service stripping
AI_HOST_WIFI_ONLY=1
AI_HOST_DISABLE_CELL=1
AI_HOST_KEEP_TELEPHONY=0
AI_HOST_KEEP_SYSTEMUI=0

# zram (compresses RAM — gives ~1.5x effective RAM for AI)
AI_HOST_ZRAM_SIZE=512M
AI_HOST_CPU_GOVERNOR=performance

# Battery: limit charge to 80% to prolong life (0 = disabled, 80 = recommended)
AI_HOST_CHARGE_LIMIT=0
EOF
chmod 644 /data/ai_host.env
echo "    Config written. Edit with: su -c 'vi /data/ai_host.env'"

# 2. Zip the Magisk module
echo ">>> Zipping Magisk module..."
HERE="$(dirname "$(readlink -f "$0")")"
MODULE_DIR="$HERE/magisk_module"
if [ ! -d "$MODULE_DIR" ]; then
  echo "ERROR: $MODULE_DIR not found. Run this script from the package root."
  exit 1
fi
cd "$MODULE_DIR"
rm -f "$MODULE_ZIP"
zip -r "$MODULE_ZIP" . >/dev/null
echo "    Module zip: $MODULE_ZIP"

# 3. Copy kiosk launcher into Termux's boot dir
echo ">>> Installing kiosk launcher..."
TERMUX_BOOT="$TERMUX_HOME/.termux/boot"
mkdir -p "$TERMUX_BOOT"
cp "$HERE/kiosk_launcher/ai_kiosk.sh" "$TERMUX_BOOT/ai-kiosk.sh"
chown "$(stat -c %u "$TERMUX_HOME")":"$(stat -c %g "$TERMUX_HOME")" "$TERMUX_BOOT/ai-kiosk.sh"
chmod 755 "$TERMUX_BOOT/ai-kiosk.sh"
echo "    Installed: $TERMUX_BOOT/ai-kiosk.sh"

# 4. Done
echo ""
echo "=== Bootstrap complete ==="
echo ""
echo "Next steps:"
echo "  1. Open Magisk Manager"
echo "  2. Modules → Install from storage"
echo "  3. Select: $MODULE_ZIP"
echo "  4. Reboot when Magisk prompts"
echo ""
echo "After reboot, the phone will:"
echo "  - Kill Google services, SystemUI, launcher"
echo "  - Start llama-server on port $AI_HOST_PORT"
echo "  - Listen on 0.0.0.0:$AI_HOST_PORT (OpenAI-compatible API)"
echo ""
echo "Logs: su -c 'tail -f /data/ai_host.log'"
echo "Config: su -c 'cat /data/ai_host.env'"
