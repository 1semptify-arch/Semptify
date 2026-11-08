# VERIFICATION PASS — 2026-10-23 (pre-Birnberg checks & balances)

*Math audit + external fact re-check + free data sources. Result: one real
defect found and fixed; every load-bearing external figure verified.*

## 1. Internal math audit

| Check | Model says | Recheck | Verdict |
|---|---|---|---|
| Default claims | 3% × 600K = 18,000 × $4,400 | $79.2M | OK |
| Damage claims | 15% turnover × 25% × $1,200 | 22,500 × $1,200 = $27M | OK |
| Total claims | ~$106M | $106.2M | OK |
| Net premium | $110M = claims×1.25 load − float | $132.75M − $23.4M = $109.35M ≈ $110M | OK — **only works with NET float** |
| Per-unit premium | $15.33/mo | $110M/600K/12 | OK |
| **Float figure** | "~$31M/yr netted" | Usable float = 3% (4% yield − 1% statutory to tenant) = **$23.4M** | **FIXED 10/23** — the $31M counted the tenant's own 1% |
| Braid split | float $4.33 + $7.67 + $7.67 | = $19.67/mo vs $15.33 needed — 28% over-collection | **FIXED** — restated ~$3.25 + ~$6 + ~$6 |
| Stress scenarios | $138M/$153M; $185M/$216M | direction + per-unit figures consistent | OK (float offset varies slightly — conservative direction) |
| Deposit base | ~$780M | 600K × $1,300 | OK |

## 2. External figures — re-verified 10/23

| Claim | Source found | Status |
|---|---|---|
| M1PR max $2,720, income cap $77,570 (TY2025) | MN Dept of Revenue, 2025 M1 instructions | VERIFIED |
| MN eviction filings | Judicial Branch: 25,847 (2023), 23,282 (2024), tracking ~25K (2025) | VERIFIED — docs sharpened to ~20–25K |
| ~1/3 serial filings | Eviction Lab/Social Forces: 30.4% of households, 44.6% of filings | VERIFIED |
| ~$9B rental debt + "coercion" phrase | CFPB annual debt-collection report, verbatim | VERIFIED |
| $5,600–7,400 per eviction taxpayer cost | Harris County i4J model: $199–260M / ~35–38K evictions | VERIFIED |
| Visale claws back paid claims | service-public.fr: Action Logement "se fait ensuite rembourser par le locataire" | VERIFIED — also: Visale is surety not insurance, does NOT cover deposits |
| Jetty class action SDNY 10/6 | verified 10/18 (Insurance Business Mag, openclassactions) | stands |

Modeled estimates left as-is (flagged in-doc): $310 filing fee, 3–7%
private pricing, $7,260 contested-eviction cost, ~1.5M renters/600K
households, 3% severe-default rate (conservative vs 2.4% filing rate).

## 3. Free data sources / APIs worth wiring in

| Source | What it gives | Use for |
|---|---|---|
| Census Bureau API (ACS) | Renter households, median rent, rent burden by county | Nails the "600K / $1,300" assumptions with live numbers — free key |
| FRED API (St. Louis Fed) | Treasury yields, savings rates | Float-yield assumption (currently 4%) — keeps the float line honest as rates move |
| LSC Civil Court Data | Monthly MN eviction filing feeds, all 87 counties | Live filings trend for the deck + fiscal note |
| Eviction Research Network (evictionresearch.net) | MN-specific filing series, serial-filing research | The strongest free MN eviction dataset |
| HUD FMR API + LIHTC database | Fair market rents; exact LIHTC properties/managers | Pilot targeting for the MHFA ask — real building lists |
| CourtListener API | Case law, dockets (already have MCP access) | Jetty docket tracking, deposit-case citations |
| BLS API | Unemployment series | Countercyclicality stress inputs |
| OpenStates/Plural | MN bill tracking | Watch competing/companion housing bills |

All free or free-key. No paid data needed for the packet.

## 4. What still needs an actuary

The open items the model itself flags: belongings-leg premium load
($10–15/mo est.), hardship-trigger loss frequency, split-ratio finality,
reinsurance/backstop sizing. These are correctly parked as drafting
questions — do not let the packet imply they're settled.
