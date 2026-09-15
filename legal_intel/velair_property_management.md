# Velair Property Management — Research Profile (Legal Intel)

> Research date: 2026-09-13. Sources: MCRO portal inspection, MN/Iowa Secretary of State
> aggregators (opencorpdata.com / iaopendata.com), MWF Properties public filings, news
> (southernminn.com), PACER Monitor, MN House committee reports.
> Prepared for the `legal_intel` engine (`entities` / `relationships` / `cases` schema).

## Summary

Velair Property Management is the **in-house management arm of MWF Properties**, a
Minneapolis/Richfield affordable-housing developer. It manages ~2,000–3,000 multifamily units
(affordable/LIHTC, age-restricted/senior, and market-rate) across **Minnesota, Iowa, and
Illinois**. Eviction/legal filings appear under several different entity names, not one.

HQ: **7645 Lyndale Ave S, Suite 210, Minneapolis, MN 55423** · phone 612-243-3111.

---

## 1. Entities (aliases used for filings)

| # | Entity name | Type | SOS / reg | Registered agent | Address |
|---|---|---|---|---|---|
| 1 | Velair Property Management, L.L.C. | LLC (management) | IA foreign #696428 (filed 2021-12-17) | Chris Stokka / Terry Parker (919 S 16th St, Ames IA 50010) | 7645 Lyndale Ave S, Ste 210, Minneapolis MN 55423 |
| 2 | MWF Properties, LLC (also "MWF Properties, Inc.") | Developer | IA foreign #515396 (2021-12-17) | Terry Parker | 7645 Lyndale Ave S, Minneapolis MN |
| 3 | Velair Development Company | Development arm | velairdc.com (since 1999, 3,000+ units) | — | 7645 Lyndale Ave S |
| 4 | MW Attainable | Nonprofit (affordable housing) | mwattainable.org (founded 1989, Harold Teasdale) | — | — |
| 5 | MWF IA3, Limited Partnership | LP (property owner) | IA (2015-01-30) | Chris Stokka / Terry Parker | 7645 Lyndale Ave S |
| 6 | MWF IA3, LLC | LLC | IA foreign (2015-01-30) | Terry Parker | 7645 Lyndale Ave S |
| 7 | MWF IA3GP, LLC | LLC (GP) | IA (2023-11-08) | MWF IA3, LP | 7645 Lyndale Ave S |
| 8 | Laverne Apartments, Limited Partnership | LP (property owner) | IA (2016-02-02) | Chris Stokka | 7645 Lyndale Ave S |
| 9 | Ames Group GP, LLC | LLC (GP) | IA (2016-03-21) | Terry Parker | 7645 Lyndale Ave S |
| 10 | Arbor Glen, L.P. / Arbor Group LLC | LP/LLC | IA (2002-01-04) | Sarah Kohler (differs from Stokka/Parker — probable, not certain) | 7645 Lyndale Ave S |
| 11 | Evergreen Knoll Limited Partnership | LP (owns Lofts at Evergreen Knoll) | MN Housing 2019 RFP doc | — | Faribault, MN |

**Principals:** Christopher Stokka (VP MWF Properties, VP Velair Development, board chair MW
Attainable), Terry Parker (IA registered agent), Harold Teasdale (founder, MW Attainable).

**Property DBAs (names tenants see — also possible filing names):** Lofts at Evergreen Knoll
(Faribault), Lofts on Rose (St Paul), Lyndale Flats & 108 Place (Bloomington), Thomas Avenue
Flats & Willow Ridge Apartments (St Paul), Washington Court (Minneapolis), Forest Oak (Forest
Lake), Harvestview Place / Valleyhigh Flats / Ashland Place / Century Heights / Northern Heights
/ Washington Village West / First Avenue Flats / Village on 3rd / The Meadows (Rochester), Rosa
Place I & II (Mankato), Red Rock Square (Newport), Lafayette Square (Davenport IA).

---

## 2. Known legal cases / incidents

1. **Dale v. Velair Property Management** — U.S. District Court, D. Minn, **0:25-cv-00180**
   (removed from Hennepin County `27-CV-25-815`). Nature: 445 ADA **employment** discrimination.
   Filed 2025-01-15; terminated 2025-04-02 (docket shows a stipulation — consistent with early
   settlement; terms unconfirmed). Plaintiff Brian R. Dale (pro se); defense Gordon Rees Scully
   Mansukhani. **Not an eviction.**
2. **Lofts at Evergreen Knoll, Faribault (Jan 2023)** — after a minor grease fire (11 units
   water-damaged), Velair terminated the leases of three families citing the "fault or neglect"
   clause against all three, not just the tenant whose fire it was. **Defendants/tenants named:
   Nuria Noor, Abdi Osman, Abdi Muse** (represented by attorney Brian Lipford). News-documented
   (Faribault Daily News, 2023-02-18); a filed Rice County case was not confirmed.
3. **MWF Properties — "Subsidizing Abuse" (MN House report)** — MWF's **Amundson Flats (Edina)**
   project used contractor **Painting America**, which has documented wage-theft /
   misclassification findings (MN DOLI 2017-12-27). Labor finding against a contractor on an MWF
   project, not a suit against MWF.

---

## 3. MCRO search recipe (corrected — for `legal_intel/app/crawlers/mcro.py`)

The MCRO portal is **ASP.NET Core + jQuery**, NOT ASP.NET WebForms (the stub's comments and
`ctl00_*` selectors are wrong).

- Search page: `https://publicaccess.courts.state.mn.us/CaseSearch`
- Business-name form (loaded via `POST /CaseSearch/CaseSearchForm?formType=business`): fields
  `FormType=business`, `LastName` (labeled "Enter Business Name"), `Soundex`, `CaseCategoryKeys`
  (values `CV`/`CR`/`FAM`/`PR`), `CaseStatus` (`0`=All, `1`=Active, `2`=Inactive),
  `AllLocations=true`, `FiledDateExact=true`.
- Search submit: `POST /CaseSearch/CaseSearchSearch` with the form-serialized body +
  `__RequestVerificationToken` (ASP.NET antiforgery) and header `X-Requested-With: XMLHttpRequest`.
  Results render into `#CaseSearchResultsWrapper`.
- Terms acceptance is **client-side only**: set cookies `IsAcceptedTerms=true` and
  `TermsExpirationTime=<future date>`.
- **Evictions = case type "Housing" under the Civil (`CV`) category.**

### Blocker (do not rediscover this)

MCRO is behind **F5 Volterra bot defense** (server header `volt-adc`). An obfuscated challenge
script (`/js/mcro3keulkju.js`) sets an `OClmoOot` cookie. The **form endpoints load fine**, but
`POST /CaseSearch/CaseSearchSearch` returns `"The requested URL was rejected"` for automated /
headless clients (the challenge cookie rotates on each attempt = active rejection). The current
`mcro.py` uses `chromium.launch(headless=True)` → it will hit this wall. Options: human-in-the-loop
on the public portal, or a licensed data feed (UniCourt/Trellis API). Also note MCRO Terms state
the portal "should not be used for background checks" and that name searches are unreliable.

---

## 4. Machine-loadable seed (entities / relationships / cases)

```json
{
  "entities": [
    {"name": "Velair Property Management, L.L.C.", "type": "LLC (property management)", "sos_id": "IA-696428", "registered_agent": "Chris Stokka / Terry Parker", "address": "7645 Lyndale Ave S, Ste 210, Minneapolis, MN 55423"},
    {"name": "MWF Properties, LLC", "type": "LLC (developer)", "sos_id": "IA-515396", "registered_agent": "Terry Parker", "address": "7645 Lyndale Ave S, Minneapolis, MN 55423"},
    {"name": "MWF Properties, Inc.", "type": "Corporation (developer)", "sos_id": null, "registered_agent": null, "address": "7645 Lyndale Ave S, Minneapolis, MN 55423"},
    {"name": "Velair Development Company", "type": "Development", "sos_id": null, "registered_agent": null, "address": "7645 Lyndale Ave S, Minneapolis, MN 55423"},
    {"name": "MW Attainable", "type": "Nonprofit", "sos_id": null, "registered_agent": null, "address": null},
    {"name": "MWF IA3, Limited Partnership", "type": "LP", "sos_id": null, "registered_agent": "Chris Stokka", "address": "7645 Lyndale Ave S, Minneapolis, MN 55423"},
    {"name": "MWF IA3, LLC", "type": "LLC", "sos_id": null, "registered_agent": "Terry Parker", "address": "7645 Lyndale Ave S, Minneapolis, MN 55423"},
    {"name": "MWF IA3GP, LLC", "type": "LLC (GP)", "sos_id": null, "registered_agent": "MWF IA3, LP", "address": "7645 Lyndale Ave S, Minneapolis, MN 55423"},
    {"name": "Laverne Apartments, Limited Partnership", "type": "LP", "sos_id": null, "registered_agent": "Chris Stokka", "address": "7645 Lyndale Ave S, Minneapolis, MN 55423"},
    {"name": "Ames Group GP, LLC", "type": "LLC (GP)", "sos_id": null, "registered_agent": "Terry Parker", "address": "7645 Lyndale Ave S, Minneapolis, MN 55423"},
    {"name": "Arbor Glen, L.P.", "type": "LP", "sos_id": null, "registered_agent": "Sarah Kohler", "address": "7645 Lyndale Ave S, Minneapolis, MN 55423", "note": "probable affiliate (agent differs)"},
    {"name": "Evergreen Knoll Limited Partnership", "type": "LP (property owner)", "sos_id": null, "registered_agent": null, "address": "Faribault, MN"}
  ],
  "relationships": [
    {"entity_a": "MWF Properties, LLC", "entity_b": "Velair Property Management, L.L.C.", "type": "parent/management"},
    {"entity_a": "MWF Properties, LLC", "entity_b": "Velair Development Company", "type": "affiliate"},
    {"entity_a": "MWF Properties, LLC", "entity_b": "MW Attainable", "type": "affiliate (nonprofit)"},
    {"entity_a": "Velair Property Management, L.L.C.", "entity_b": "Evergreen Knoll Limited Partnership", "type": "manages"}
  ],
  "cases": [
    {"court": "USDC D. Minn", "case_number": "0:25-cv-00180", "case_title": "Dale v. Velair Property Management", "case_type": "Civil - ADA employment", "filing_date": "2025-01-15", "status": "Terminated 2025-04-02", "note": "not an eviction"},
    {"court": "Hennepin County District", "case_number": "27-CV-25-815", "case_title": "Dale v. Velair Property Management (state)", "case_type": "Civil", "filing_date": "2025-01", "status": "removed to federal", "note": "underlying state case"}
  ],
  "eviction_defendants_identified": [
    {"name": "Nuria Noor", "property": "Lofts at Evergreen Knoll, Faribault", "date": "2023-01", "source": "Faribault Daily News"},
    {"name": "Abdi Osman", "property": "Lofts at Evergreen Knoll, Faribault", "date": "2023-01", "source": "Faribault Daily News"},
    {"name": "Abdi Muse", "property": "Lofts at Evergreen Knoll, Faribault", "date": "2023-01", "source": "Faribault Daily News"}
  ]
}
```

## 5. To complete the eviction record (human step)

Search MCRO (publicaccess.courts.state.mn.us/CaseSearch) with **Case Search → Business**, name =
each entity in section 1 (plus wildcard `Velair*`), **Case Category = Civil**, **Status = All**,
**Statewide**. Every result with case type **"Housing"** is an eviction; the entity is plaintiff,
the **tenant is the defendant** (name + county shown in the result row).
