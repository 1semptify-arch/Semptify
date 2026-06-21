# Kiosk Launcher — Boots Straight to AI Server

## What This Does

On boot, Termux:Boot runs `ai_kiosk.sh`, which:
1. Acquires a wake lock (prevents Android doze).
2. Drops filesystem caches.
3. Launches `llama-server` in the foreground.
4. Logs to `/data/ai_host.log`.

The phone's screen stays black (SystemUI is killed by the Magisk module).
The phone is controlled entirely over Wi-Fi via the OpenAI-compatible HTTP API.

## Install

```bash
# In Termux (after install_termux.sh has run):
mkdir -p ~/.termux/boot
cp ai_kiosk.sh ~/.termux/boot/ai-kiosk.sh
chmod +x ~/.termux/boot/ai-kiosk.sh

# Reboot to test:
reboot
```

## Verify After Reboot

From a laptop on the same Wi-Fi:

```bash
# Find the phone's IP (check your router's DHCP list, or set a static IP)
curl http://<phone-ip>:8080/health
# Should return: {"status":"ok"}

curl http://<phone-ip>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2-0.5b","messages":[{"role":"user","content":"Hello"}]}'
```

## Stop the Server

SSH in (install Termux:SSH or use `sshd` from Termux) and:

```bash
pkill -f llama-server
```

Or just reboot the phone — the server will start again automatically.

## Disable Autostart

```bash
rm ~/.termux/boot/ai-kiosk.sh
reboot
```

## Logging

The Magisk module logs to `/data/ai_host.log` (root-only).
The kiosk script logs to `~/.termux/boot/ai-kiosk.log` (Termux user).

```bash
# View Magisk-side logs (root):
su -c 'tail -f /data/ai_host.log'

# View kiosk-side logs:
tail -f ~/.termux/boot/ai-kiosk.log
```

## Static IP Recommendation

Set a static IP on the phone so you can find it reliably:

```bash
# In Termux (no root needed for Termux:API):
termux-wifi-connectioninfo | python3 -m json.tool

# Better: set static IP in your router's DHCP reservation table
# using the phone's MAC address (Settings → About → Wi-Fi MAC)
```
