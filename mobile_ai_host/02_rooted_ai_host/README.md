# Package 2 — Rooted AI Host (LG Stylo 4)

**Goal:** Maximize RAM available for AI by stripping Android background services via a Magisk module.
**RAM available for AI:** ~1.5 GB (vs ~500 MB no-root).
**Brick risk:** Low (Magisk is reversible; no system partition changes).
**Time to deploy:** ~2 hours (rooting + module install + model setup).

## What This Package Does

1. **Roots the phone** with Magisk (you do this — instructions below).
2. **Installs a Magisk module** that on every boot:
   - Disables Google Play Services, Play Store, and most system telemetry
   - Stops SystemUI, launcher, and other UI processes (phone runs headless)
   - Sets CPU governor to `performance`
   - Drops filesystem caches
   - Enables zram swap for more effective RAM
3. **Installs Termux + llama.cpp** (same as package 1, but with root privileges).
4. **Boots straight into AI server** via Termux:Boot + a kiosk launcher script.

## Step 1 — Root the LG Stylo 4

The Stylo 4 (LM-Q710) has known root paths. **Read carefully before starting.**

### Check your firmware version
```bash
Settings → About phone → Software info → Build number
```

### Rooting options (pick one based on firmware)

| Firmware | Method | Tool |
|----------|--------|------|
| Android 7.x (Nougat, older) | KingRoot one-click | kingroot.net |
| Android 8.x (Oreo) | Magisk via dirty santa | XDA thread: "Stylo 4 root" |
| Android 9 (Pie, latest) | Magisk via patched boot.img | See XDA: `LM-Q710` root thread |

### Recommended: Magisk via patched boot.img

1. On a PC, install `adb` and `fastboot` (Android Platform Tools).
2. Enable USB debugging on the phone (Settings → Developer options).
3. Connect phone to PC, authorize the PC.
4. Download the **stock boot.img** for your exact firmware from XDA.
5. Install Magisk Manager APK on the phone.
6. In Magisk Manager → Install → "Select and Patch a File" → choose the stock boot.img.
7. Magisk produces `magisk_patched.img` in `/sdcard/Download/`.
8. Pull it to the PC: `adb pull /sdcard/Download/magisk_patched.img`
9. Boot phone to fastboot: `adb reboot bootloader`
10. Flash: `fastboot flash boot magisk_patched.img`
11. Reboot: `fastboot reboot`
12. Open Magisk Manager — you should see "Installed" with a green check.

### If dirty santa is required (older firmware)

Follow the XDA thread for your specific carrier variant (Sprint, T-Mobile, Verizon, unlocked).
The exploit differs per variant. **Do not skip reading the thread.**

### Verify root

```bash
# In Termux:
su
# Magisk will prompt "Grant root access?" — tap Grant
id
# Should show: uid=0(root)...
exit
```

## Step 2 — Install Termux and Build llama.cpp

Same as package 1 — run `install_termux.sh` from inside Termux.
The build is identical; root is not required for the build itself.

## Step 3 — Install the Magisk AI Host Module

```bash
# On the phone, copy the magisk_module/ folder to /sdcard/
adb push 02_rooted_ai_host/magisk_module /sdcard/ai_host_module

# Open Magisk Manager
# → Modules (icon at bottom)
# → "Install from storage"
# → Select /sdcard/ai_host_module/ai_host_module.zip
# → Reboot when prompted
```

To create the zip first:
```bash
cd 02_rooted_ai_host/magisk_module
zip -r ../ai_host_module.zip .
```

## Step 4 — Install Termux:Boot for Autostart

1. Install Termux:Boot from F-Droid (`com.termux.boot`).
2. Open it once (just to launch — this registers it with Android).
3. In Termux:
   ```bash
   mkdir -p ~/.termux/boot
   cp 02_rooted_ai_host/kiosk_launcher/ai_kiosk.sh ~/.termux/boot/ai-kiosk.sh
   chmod +x ~/.termux/boot/ai-kiosk.sh
   ```

## Step 5 — Reboot and Verify

Reboot the phone. After ~60 seconds:

- The screen should be black or show the boot animation (SystemUI is killed).
- The AI server should be running on port 8080.

Test from a laptop on the same Wi-Fi:
```bash
curl http://<phone-ip>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2-0.5b","messages":[{"role":"user","content":"Hello"}]}'
```

## How to Recover if Something Breaks

**The Magisk module is reversible.** If the phone boots but something is broken:

1. Boot to safe mode (hold volume down during boot animation).
2. Magisk disables all modules in safe mode.
3. Open Magisk Manager → Modules → disable "AI Host Service Stripper".
4. Reboot normally.

If the phone doesn't boot at all:
- You flashed a bad patched boot.img. Re-flash stock boot.img via fastboot.
- This is why we keep the original boot.img on the PC.

## What the Module Kills (and Why)

| Service | RAM freed | Why |
|---------|-----------|-----|
| Google Play Services (GMS)   | ~400 MB | Telemetry, location, push — not needed for AI |
| Google Play Store            | ~80 MB  | No app installs needed post-setup |
| SystemUI (status bar, nav)   | ~150 MB | Phone runs headless |
| Launcher3 / default launcher | ~60 MB  | No UI needed |
| Telephony (optional)         | ~120 MB | Only if you don't need cell service |
| Various carrier bloat        | ~100 MB | Varies by carrier |
| **Total**                    | **~900 MB** | |

## Optional: Disable Cell Radio (Saves More Battery)

If the phone is Wi-Fi-only (recommended for an AI host):

```bash
# In a root shell:
svc data disable
svc wifi enable
# Or fully disable cell radio:
settings put global airplane_mode_on 1
am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true
# Then re-enable Wi-Fi:
svc wifi enable
```

The Magisk module's `service.sh` does this if you set `AI_HOST_WIFI_ONLY=1` in
`/data/ai_host.env`.

## Battery Longevity

- Sustained AI inference on a Stylo 4 draws ~3W and produces ~2W of heat.
- The battery will swell after 6–12 months of 24/7 plugged-in use.
- **Remove the battery and run on USB power** if you're deploying long-term
  (the Stylo 4's battery is removable — pop the back cover and pull it).
- Or set the Magisk module to charge only to 80% (prolongs battery life):
  ```bash
  echo 80 > /sys/class/power_supply/battery/battery_charging_enabled 2>/dev/null
  ```
