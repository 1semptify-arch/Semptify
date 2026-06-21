# Hardware Comparison — Phones with Official Bootloader Unlock

As of 2026, these phones have **manufacturer-supported** bootloader unlock.
No exploit needed. No LG-style "we shut down the unlock portal" risk.

## Top Picks for AI Hosting

### 🥇 Pixel 4a (sunfish) — Best Value
- **SoC:** Snapdragon 730G (8-core: 2× big + 6× small)
- **RAM:** 6 GB
- **Storage:** 128 GB
- **Used price:** ~$80 on eBay/Swappa
- **Bootloader unlock:** Official via Google's `fastboot flashing unlock`
- **postmarketOS:** Supported (mainline kernel, mostly working)
- **Linux distros:** postmarketOS, Ubuntu Touch, Alpine
- **AI performance:** ~5 tokens/sec on Llama-3.2-3B Q4
- **Pros:** Cheap, well-supported by custom ROM community, official unlock
- **Cons:** Battery may be degraded in used units (replaceable with iFixit guide)

### 🥈 OnePlus 7 (guacamole) — Best RAM per Dollar
- **SoC:** Snapdragon 855 (8-core, much faster than 730G)
- **RAM:** 6–8 GB variants
- **Storage:** 128–256 GB
- **Used price:** ~$120 (8GB variant)
- **Bootloader unlock:** Official via OnePlus unlock token
- **postmarketOS:** Partial support — check device page before buying
- **AI performance:** ~10 tokens/sec on Llama-3.2-3B Q4
- **Pros:** Fast SoC, lots of RAM, official unlock
- **Cons:** OnePlus unlock tokens require an online request (1-2 day wait)

### 🥉 Fairphone 4 — Most Ethical, Longest Support
- **SoC:** Snapdragon 750G (5G-capable)
- **RAM:** 6–8 GB
- **Storage:** 128–256 GB
- **Used price:** ~$200
- **Bootloader unlock:** Official, no token needed
- **postmarketOS:** Supported
- **AI performance:** ~6 tokens/sec on Llama-3.2-3B Q4
- **Pros:** Modular repairable design, 8-year software support, ethical supply chain
- **Cons:** More expensive, slower SoC than OnePlus 7

### Honorable Mentions

| Phone | RAM | Used $ | Unlock | Notes |
|-------|-----|--------|--------|-------|
| Pixel 5 (redfin)        | 8 GB | ~$150 | Official | 5G, IP68, great postmarketOS support |
| Pixel 6 (oriole)        | 8 GB | ~$180 | Official | Tensor chip — slower for AI than Snapdragon |
| OnePlus 6 (enchilada)   | 6-8 GB | ~$90 | Official | Older but cheap, well-supported |
| Motorola Edge 30 Neo    | 6-8 GB | ~$100 | Official | Limited postmarketOS support |
| Sony Xperia 10 III/IV   | 6-8 GB | ~$200 | Official | Good postmarketOS support, pricey |

## Phones to AVOID for AI Hosting

| Phone | Why avoid |
|-------|-----------|
| **Any LG phone (Stylo, G, V, Velvet)** | LG shut down unlock program in 2021. No new unlocks possible. |
| **Samsung Galaxy (S series, A series)** | US variants are locked. Exynos variants unlockable in some regions, but Snapdragons are not. |
| **Carrier-locked anything** | Carrier locks may persist even after manufacturer unlock. |
| **iPhone (any)** | No bootloader unlock, ever. Apple locks the boot chain. |
| **Huawei / Honor** | Unlock program shut down in 2018. No new unlocks. |
| **Nokia (HMD)** | Bootloader unlock available for some models but extremely limited. |

## How to Unlock a Pixel 4a (Step-by-Step)

```bash
# 1. On the phone: Settings → About phone → tap Build number 7 times
#    → Developer options → enable "OEM unlocking" and "USB debugging"

# 2. Connect to PC with USB cable. Authorize the PC when prompted.

# 3. From PC:
adb reboot bootloader

# 4. Once in fastboot mode:
fastboot flashing unlock

# 5. Phone will show a warning screen. Press volume up to confirm.
#    ALL DATA WILL BE WIPED.

# 6. Phone reboots. Bootloader is now unlocked.
fastboot reboot
```

That's it. No tokens, no waiting, no online portal. Google is the easiest
manufacturer for bootloader unlock.

## How to Unlock a OnePlus 7

```bash
# 1. Settings → About → tap Build number 7 times → Developer options
#    → enable "OEM unlocking"

# 2. Get the unlock token from OnePlus:
#    https://www.oneplus.com/unlock_token (or OnePlus support)
#    Requires: IMEI, device serial, your OnePlus account email
#    Takes 1-2 business days

# 3. Once you receive token.bin:
adb reboot bootloader
fastboot flash unlocktoken token.bin
fastboot reboot

# 4. Phone reboots, bootloader unlocked.
```

## Where to Buy Used Phones

| Source | Pros | Cons |
|--------|------|------|
| **Swappa** | Strict seller verification, no "for parts" listings allowed | Slightly higher prices |
| **eBay** | Cheapest, biggest selection | Risk of bad ESN, must read listings carefully |
| **Back Market** | Refurbished with warranty | More expensive than eBay |
| **Local Facebook Marketplace** | No shipping, can test before buying | Limited selection, safety concerns |
| **Google Store (refurbished)** | Warranty, clean ESN guaranteed | Limited stock, higher prices |

**Tips:**
- Search for "Pixel 4a cracked screen" — cosmetics don't matter for an AI host.
- Check the ESN/IMEI at `https://swappa.com/imei` before buying.
- Avoid "financed" phones — the seller's carrier may block the ESN later.
- Ask the seller to confirm "OEM unlock still works" before shipping.

## Recommended First Phone

**Pixel 4a (sunfish), 128GB, factory unlocked, ~$80 used.**

Reasons:
- Cheapest phone with 6GB RAM and official unlock.
- postmarketOS has mainline kernel support (not just a hybris hack).
- Big custom ROM community = lots of documentation.
- Non-removable battery, but easy to replace with iFixit guide.
- No carrier unlock drama (sold factory-unlocked in the US).

Buy one, follow `postmarketos_flash_guide.md` to flash Linux on it,
then run llama.cpp with Llama-3.2-3B. You'll get ~5 tokens/sec —
fast enough to be useful for an on-device assistant.
