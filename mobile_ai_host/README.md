# Mobile AI Host — Reuse Old Phones as On-Device AI Inference Servers

Target hardware: **LG Stylo 4** (Snapdragon 450, 2GB RAM, 32GB storage, ARM64).
Goal: maximize available RAM/CPU for local AI inference (llama.cpp + quantized small models).

## What This Is Not

- **Not a custom OS.** Writing a custom OS or custom bootloader for the Stylo 4 is not realistic
  (locked signed bootloader chain, no public bootrom exploit, LG's unlock program shut down in 2021).
- **Not a bootloader unlock exploit.** I will not write one. See `03_unlockable_hardware_plan/`
  for the realistic long-term path if you want a true Linux phone.

## What This Is

Three staged packages, in priority order:

| # | Package | Root needed | Brick risk | RAM for AI | Time to deploy |
|---|---------|-------------|------------|------------|----------------|
| 1 | `01_no_root_prototype/`   | No  | None      | ~500 MB | ~30 min (test today) |
| 2 | `02_rooted_ai_host/`      | Yes | Low       | ~1.5 GB | ~2 hours  |
| 3 | `03_unlockable_hardware_plan/` | No (on supported phone) | Medium (flashing) | ~4–7 GB | Days (buy phone first) |

## Recommended Path

1. **Today:** Run package 1 (no-root). Proves the concept works on your Stylo 4.
2. **Next week:** If package 1 works and you want more RAM, root the phone and run package 2.
3. **Long-term:** If you're serious about a multi-phone AI cluster, switch to unlockable
   hardware (Pixel 4a, OnePlus 7, Fairphone 4) and follow package 3.

## Safety

- **Rooting can brick your phone.** Follow package 2 instructions exactly. I am not responsible
  for bricked devices.
- **No-root package 1 is fully reversible** — just uninstall Termux.
- **Keep the phone plugged in and cool.** Sustained AI inference heats the SoC. Remove any case
  and place on a hard surface, not fabric.
- **Use a dedicated Google account** if you root — not your daily account. Rooting can trip
  SafetyNet/Play Integrity and break banking apps on that account's devices.

## Models That Fit

| Model | Size (Q4_K_M) | RAM used | Fits package |
|-------|---------------|----------|--------------|
| Qwen2-0.5B-Instruct   | ~400 MB  | ~600 MB  | 1, 2, 3 |
| TinyLlama-1.1B        | ~670 MB  | ~900 MB  | 2, 3 (tight on 1) |
| Phi-1.5-1.3B          | ~790 MB  | ~1.0 GB  | 2, 3 |
| Llama-3.2-1B-Instruct | ~660 MB  | ~900 MB  | 2, 3 |
| Qwen2-1.5B-Instruct   | ~990 MB  | ~1.3 GB  | 3 only |

Bigger models (3B+) will not run on the Stylo 4's 2GB RAM. They work on package 3 hardware.

## Quick Start

```bash
# On the phone, install Termux from F-Droid (NOT Play Store — that version is deprecated)
# Then:
cd mobile_ai_host/01_no_root_prototype
# Read README.md and run install_termux.sh from inside Termux
```

## Repository Layout

```
mobile_ai_host/
├── README.md                              (this file)
├── 01_no_root_prototype/                  Test today, no root
│   ├── README.md
│   ├── install_termux.sh
│   ├── start_ai_server.sh
│   ├── stop_ai_server.sh
│   ├── test_inference.sh
│   └── models.txt
├── 02_rooted_ai_host/                     Magisk module + kiosk
│   ├── README.md
│   ├── magisk_module/
│   │   ├── module.prop
│   │   ├── install.sh
│   │   ├── post-fs-data.sh
│   │   ├── service.sh
│   │   └── system/etc/init/ai_host.rc
│   ├── kiosk_launcher/
│   │   ├── README.md
│   │   └── ai_kiosk.sh
│   └── bootstrap_rooted.sh
└── 03_unlockable_hardware_plan/           Long-term cluster plan
    ├── README.md
    ├── hardware_comparison.md
    ├── postmarketos_flash_guide.md
    └── cluster_architecture.md
```

## License

These scripts are MIT-licensed. Use at your own risk. No warranty.
Models keep their own licenses — check before deployment.
