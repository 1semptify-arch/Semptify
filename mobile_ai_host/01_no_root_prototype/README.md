# Package 1 — No-Root AI Host Prototype (LG Stylo 4)

**Goal:** Prove that on-device AI inference works on your Stylo 4, without rooting.
**Time to deploy:** ~30 minutes.
**RAM available for AI:** ~500 MB (Android still runs underneath).
**Reversible:** Yes — uninstall Termux to fully undo.

## Step 1 — Install Termux (from F-Droid, NOT Play Store)

The Play Store version of Termux is deprecated and broken. You must install from F-Droid.

1. On the phone, open a browser and go to `https://f-droid.org/packages/com.termux/`
2. Download and install the APK. Allow "install from unknown apps" when prompted.
3. Open Termux. You should see a `$` prompt.

## Step 2 — Copy the install script to the phone

Easiest method: download from a gist, or transfer via USB / cloud drive.

```bash
## From inside Termux:
pkg install git -y
git clone https://github.com/<your-user>/mobile_ai_host.git
cd mobile_ai_host/01_no_root_prototype
```text

(If you don't have a git remote yet, just copy `install_termux.sh` to the phone via USB
or a cloud drive, then run it from Termux.)

## Step 3 — Run the installer

```bash
bash install_termux.sh
```

This will:

- Update pkg repositories
- Install a C++ toolchain, cmake, git, curl, wget
- Clone and build `llama.cpp` for ARM64 (takes ~15 min on Stylo 4)
- Download Qwen2-0.5B-Instruct Q4_K_M (~400 MB)
- Install Termux:API for battery/status queries

## Step 4 — Start the AI server

```bash
bash start_ai_server.sh
```text

This launches `llama-server` on port 8080 with the small model loaded.
You'll see a URL printed. Test from another device on the same Wi-Fi:

```bash
## From a laptop on the same network:
curl http://<phone-ip>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2-0.5b","messages":[{"role":"user","content":"Hello"}]}'
```

Or just run `bash test_inference.sh` on the phone itself.

## Step 5 — Stop the server

```bash
bash stop_ai_server.sh
```text

## Autostart on Boot (No-Root)

Without root, Termux cannot autostart on boot by default. Install **Termux:Boot**
from F-Droid (`com.termux.boot`), then:

```bash
mkdir -p ~/.termux/boot
cp start_ai_server.sh ~/.termux/boot/ai-server.sh
chmod +x ~/.termux/boot/ai-server.sh
```

Now the AI server starts automatically when the phone boots.

## Battery & Heat Notes

- Sustained inference drains the battery fast (~20%/hour at full load).
- **Keep the phone plugged in** during long sessions.
- Remove the phone case — the Stylo 4's Snapdragon 450 will throttle if it overheats.
- Place on a hard surface (wood/metal), not fabric.

## Memory Limits (No-Root)

Android will kill any process using too much RAM. Without root, you cannot change
the OOM killer settings. Stick to models under 600 MB on disk:

- Qwen2-0.5B-Instruct Q4_K_M (400 MB) ✅ recommended
- TinyLlama-1.1B Q4_K_M (670 MB) — borderline, may get killed
- Anything bigger — will not work without root

If the server keeps getting killed, switch to package 2 (rooted).

## Troubleshooting

| Symptom | Fix |
| --------- | ----- |
| `pkg update` fails | Run `termux-change-repo` and pick a different mirror |
| Build fails on cmake step | Run `pkg install cmake clang make -y` manually, retry |
| Server starts but no response | Check `http://127.0.0.1:8080/health` from Termux |
| Server killed after a few minutes | Model too big for no-root. Use Qwen2-0.5B. |
| Phone gets hot | Stop server, let cool, remove case, reduce `--threads` |
| Can't access from laptop | Phone's firewall — use `termux-wake-lock` and check Wi-Fi |
