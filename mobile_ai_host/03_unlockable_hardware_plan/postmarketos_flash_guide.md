# Flashing postmarketOS on Pixel 4a (sunfish)

This guide walks you through replacing Android with postmarketOS on a used Pixel 4a.
**This wipes everything on the phone. Back up first.**

## Prerequisites

- A used Pixel 4a with **bootloader unlocked** (see `hardware_comparison.md`)
- A PC with `adb` and `fastboot` installed (Android Platform Tools)
- A USB cable capable of data transfer (not charge-only)
- About 1 hour of time

## What is postmarketOS?

postmarketOS (pmOS) is a touch-optimized, Alpine-based Linux distribution for phones.
It uses the **mainline Linux kernel** (not Android's fork), which means:
- Real Linux userland (apk package manager, OpenRC, musl libc)
- Standard tools work (ssh, docker via postmarketOS, python, gcc)
- No Android services, no Google, no Play Services — pure Linux
- All 6GB RAM available to your AI process

For an AI host, you'll install the **phosh** UI (minimal GNOME-based shell) or
the **console** UI (no GUI at all — best for AI host, frees more RAM).

## Step 1 — Install pmOS Installer on PC

```bash
# Linux:
sudo apt install postmarketos-installer  # or your distro's equivalent

# Or use the Python installer:
pip3 install --user pmbootstrap

# macOS:
brew install postmarketos-installer

# Windows:
# Download from https://postmarketos.org/install/
```

## Step 2 — Initialize pmOS for Pixel 4a

```bash
pmbootstrap init
```

Answer the prompts:
- **Device:** `google-sunfish` (Pixel 4a)
- **User:** your username (e.g., `ai`)
- **UI:** `console` (no GUI — best for AI host, frees ~200MB)
  - If you want a minimal UI for debugging, pick `phosh`
- **Release:** `edge` (latest, has the newest kernel with best AI support)
- **Hostname:** `ai-host-1` (or whatever you want)

## Step 3 — Build the Image

```bash
pmbootstrap install
```

This downloads the kernel, builds the rootfs, and produces a flashable image.
Takes ~20 minutes on a fast PC, longer on a slow one.

## Step 4 — Flash to the Phone

```bash
# Put phone in fastboot mode
adb reboot bootloader

# Verify it's connected
fastboot devices

# Flash everything
pmbootstrap flasher flash
```

This flashes:
- `boot` partition (kernel + initramfs)
- `system` partition (rootfs)
- `userdata` partition (empty)

## Step 5 — First Boot

The phone will reboot into postmarketOS. First boot takes ~2 minutes
(generates SSH keys, resizes rootfs).

If you picked `console` UI, the screen will be black after boot — that's normal.
The phone is reachable over USB networking by default.

```bash
# From PC, over USB:
ssh ai@10.15.19.82

# Default password is "147147" — change it immediately:
passwd
```

## Step 6 — Set Up Wi-Fi

```bash
# Over SSH:
sudo nmcli device wifi connect "YOUR_WIFI_SSID" password "YOUR_WIFI_PASSWORD"

# Find the phone's new IP on Wi-Fi:
ip addr show wlan0
```

## Step 7 — Install llama.cpp

```bash
# Update the system
sudo apk update && sudo apk upgrade

# Install build deps
sudo apk add build-base cmake git python3 py3-pip wget curl

# Clone and build llama.cpp
cd ~
git clone --depth 1 https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_ARM_NATIVE=ON \
  -DLLAMA_OPENMP=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=OFF \
  -DLLAMA_BUILD_SERVER=ON
cmake --build . --target llama-server -- -j$(nproc)

# Verify
ls bin/llama-server
```

## Step 8 — Download a Model

```bash
mkdir ~/models
cd ~/models

# Llama-3.2-3B (good fit for 6GB RAM)
wget https://huggingface.co/lmstudio-community/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf

# Or Qwen2-1.5B (faster, smaller)
wget https://huggingface.co/Qwen/Qwen2-1.5B-Instruct-GGUF/resolve/main/qwen2-1_5b-instruct-q4_k_m.gguf
```

## Step 9 — Start the AI Server

```bash
~/llama.cpp/build/bin/llama-server \
  -m ~/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -t 8 \
  -c 4096 \
  -ngl 0
```

Test from your PC:
```bash
curl http://<phone-ip>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.2-3b","messages":[{"role":"user","content":"Hello"}]}'
```

Expected: ~5 tokens/sec on Llama-3.2-3B Q4 on Pixel 4a.

## Step 10 — Autostart on Boot

Create an OpenRC service:

```bash
sudo tee /etc/init.d/ai-host <<'EOF'
#!/sbin/openrc-run

name="ai-host"
description="llama.cpp AI inference server"
command="/home/ai/llama.cpp/build/bin/llama-server"
command_args="-m /home/ai/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf --host 0.0.0.0 --port 8080 -t 8 -c 4096 -ngl 0"
command_background=true
pidfile="/run/ai-host.pid"
output_log="/var/log/ai-host.log"
error_log="/var/log/ai-host.log"

depend() {
  need net
  after firewall
}
EOF

sudo chmod +x /etc/init.d/ai-host
sudo rc-update add ai-host default
sudo rc-service ai-host start
```

## Step 11 — Performance Tuning

```bash
# CPU governor: performance
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  echo performance | sudo tee "$cpu"
done

# Keep all cores online
for cpu in /sys/devices/system/cpu/cpu*/online; do
  echo 1 | sudo tee "$cpu"
done

# Add zram swap (compresses RAM — effectively gives ~9GB from 6GB)
sudo apk add zram-init
sudo rc-update add zram-init default
# Configure /etc/conf.d/zram-init with size=2G

# Disable Bluetooth, NFC (frees kernel memory)
sudo rc-update del bluetooth default
sudo rc-update del nfc default
```

## Step 12 — Thermal Management

The Pixel 4a will throttle under sustained AI load. To monitor:

```bash
# Watch CPU temp
watch -n 1 'cat /sys/class/thermal/thermal_zone*/temp'

# If temp > 75°C, the phone is throttling. Improve cooling:
# - Remove any case
# - Place on a metal surface (heat sink)
# - Add a small USB fan blowing across the back
```

## Recovery

If the phone won't boot:
```bash
# Reboot to fastboot:
# Hold power + volume down for 10 seconds

# Reflash stock Android:
# Download factory image from https://developers.google.com/android/images#sunfish
# Unzip and run:
./flash-all.sh
```

## What's Next

Once you have one Pixel 4a running reliably:
- Buy a second one.
- Follow `cluster_architecture.md` to wire them into a single inference endpoint.
- Add nodes as your budget allows.
