# Package 3 — Unlockable Hardware Plan (Long-Term AI Host Cluster)

**Goal:** Build a multi-phone on-device AI inference cluster using phones with
**official bootloader unlock** support. No exploits, no locked-bootloader fights.

## Why This Package Exists

Packages 1 and 2 work with your existing LG Stylo 4, but:
- 2GB RAM caps you at 1B-parameter models.
- Locked bootloader means you're fighting Android for every MB of RAM.
- No custom kernel = no real control over thermal/power/scheduler behavior.

For a serious "reuse phones as AI hosts" project, you want phones where you can:
- Unlock the bootloader **with the manufacturer's blessing** (no exploit needed).
- Flash a real Linux distribution (postmarketOS or Alpine).
- Run a custom kernel tuned for sustained inference workloads.
- Get 4–8 GB RAM so you can run 3B–7B models.

## The Plan

1. **Buy 1–4 used phones** with official bootloader unlock (see `hardware_comparison.md`).
2. **Unlock each phone's bootloader** via the manufacturer's official portal.
3. **Flash postmarketOS** (or Alpine Linux) on each phone (see `postmarketos_flash_guide.md`).
4. **Install llama.cpp + model** on each phone.
5. **Network them into a cluster** with a load balancer (see `cluster_architecture.md`).

## Cost Estimate

| Setup | Phones | Cost | Total RAM | Max model size |
|-------|--------|------|-----------|----------------|
| Single-node starter | 1× Pixel 4a | ~$80 | 6 GB | 3B params |
| 2-node cluster       | 2× Pixel 4a | ~$160 | 12 GB | 3B (parallel) |
| 4-node cluster       | 4× Pixel 4a | ~$320 | 24 GB | 7B (sharded) |
| Premium single-node  | 1× OnePlus 7 | ~$120 | 8 GB | 7B params |

Used prices on eBay/Swappa as of 2026. Look for "clean ESN, cracked screen OK"
— you don't care about cosmetics for an AI host.

## Recommended Path for You

Given you're starting from a Stylo 4 and want to prove the concept:

1. **Now:** Run package 1 on the Stylo 4. Confirm AI inference works for your use case.
2. **Next 2 weeks:** If it works, root the Stylo 4 and run package 2. Get more RAM.
3. **Next month:** Buy **one** used Pixel 4a (~$80). Unlock bootloader, flash postmarketOS.
   This is your "real" AI host — 6GB RAM runs Llama-3.2-3B comfortably.
4. **Later:** Add more Pixel 4a nodes as budget allows. Wire them into a cluster.

## Why Not Just Buy a Raspberry Pi?

A fair question. For pure AI inference, a Raspberry Pi 5 (8GB) is comparable to
a used Pixel 4a, and easier to work with. But:

| Factor | Used Pixel 4a | Raspberry Pi 5 8GB |
|--------|---------------|---------------------|
| Cost used | ~$80 | ~$80 (Pi 5 + case + PSU + SSD) |
| RAM | 6 GB | 8 GB |
| Storage | 128 GB built-in | Buy SD/SSD separately |
| Battery/UPS | Built-in (acts as UPS) | Buy separate UPS |
| Wi-Fi/Modem | Built-in | Buy separate dongle |
| Display | Built-in (debug) | Buy separate |
| Compute | Snapdragon 730G (8-core) | Broadcom BCM2712 (4-core) |
| AI acceleration | Hexagon DSP (qualcomm NNAPI) | None native |

**Verdict:** For a portable, self-contained AI host with built-in UPS, the phone wins.
For a rack-mounted always-on cluster, the Pi wins. Pick based on your use case.

## Files in This Package

- `hardware_comparison.md` — Detailed phone comparison, unlock procedures, where to buy
- `postmarketos_flash_guide.md` — Step-by-step flashing guide for Pixel 4a
- `cluster_architecture.md` — How to wire multiple phones into one inference endpoint

## Safety

- **Flashing postmarketOS can brick a phone** if you flash the wrong partition.
  Follow the guide exactly. We are not responsible for bricked devices.
- **Unlocking the bootloader wipes all data** on the phone. Back up first.
- **Used phones from eBay** — check the return policy. Buy from sellers with
  98%+ positive feedback. Avoid "for parts" listings.
- **Carrier-locked phones** may not unlock even with manufacturer approval.
  Buy "factory unlocked" or "carrier unlocked" devices.
