# Semptify Help & Resource Directory — Developer Inventory

A living catalog of resources, lookup patterns, and direct-connect options for the Semptify help/resource directory. The goal is to get users to the right help as fast as possible, with realistic time-to-help estimates, filtered by their jurisdiction (state → county → city → zip code).

This document is a planning/reference artifact. Developers can cherry-pick sections for implementation in any Semptify app or module.

---

## 0. New Standalone App

The user requested a **standalone** resource directory app (not wired into Semptify). That app is now built at:

`C:\master-repo\resource-directory-standalone`

It is a self-contained FastAPI + Jinja2 + SQLite app that implements all three requested approaches:

- **Static help page** — `GET /help-standalone` (works without JS or API calls).
- **Database-driven directory** — `GET /api/resources` with state/county/city/zip/category filters.
- **Public API bridge** — `include_external=true` triggers 211, SAMHSA FindTreatment, and LawHelp lookups.

See its `README.md` for run, test, and API instructions.

## 1. Existing Semptify Infrastructure

For any later integration back into Semptify, reuse before building.

| Component | Path | What it does |
|-----------|------|--------------|
| Resource Directory API | `app/modules/resource_directory/router.py` | `GET /api/resources` (public, filter by `category`, `service_area`, `language`); `POST/PUT/DELETE /admin/resources` (admin-gated); CSV import at `/admin/resources/import`; stale tracking at `/admin/resources/stale`. |
| Resource schemas | `app/modules/resource_directory/schemas.py` | `ResourceRead`, `ResourceCreate`, `ResourceContactInfo` (phone, email, website, address), `last_verified`, staleness. |
| Location service | `app/services/location_service.py` | `UserLocation` (state, county, city, zip, lat/lon), `STATES_INFO` with support levels (full/partial/minimal), `MN_COUNTIES` with court contacts. |
| Tenant help page | `app/templates/pages/tenant_help.html` | Hard-coded Minnesota legal aid and crisis resources. |
| Public standalone help | `static/public/semptify-help-standalone.html` | Self-contained, no-backend emergency page for Minnesota. |
| Resource tests | `tests/test_resource_directory.py` | Round-trip, CSV import, staleness, admin gating. |

**Cherry-pick option A — Minimal:** Extend `tenant_help.html` and `semptify-help-standalone.html` with more states.

**Cherry-pick option B — Structured:** Use `Resource` DB model + `location_service.py` to drive `/api/resources` by jurisdiction.

**Cherry-pick option C — Hybrid:** Keep a static national baseline, query 211/SAMHSA/LawHelp APIs by zip for real-time local results.

---

## 2. Resource Categories

Group every listing by what the user needs. A single resource can appear in multiple categories.

| Category | Description | Direct-connect priority |
|----------|-------------|-------------------------|
| `crisis` | Immediate danger, suicide, domestic violence, unsafe housing | Immediate — 24/7 phone/text |
| `mental_health` | Counseling, crisis lines, peer support | Immediate for crisis; appointment for ongoing |
| `emergency_shelter` | Homeless/housing emergency, domestic violence shelter | Same-day or 24h intake |
| `legal_aid` | Free or sliding-scale legal representation | Intake within business hours; may have waitlists |
| `tenant_hotline` | Tenant rights advice, not full representation | Same-day phone/chat, business hours |
| `housing_assistance` | Rental assistance, eviction prevention, housing navigators | Hours vary; 211 bridges after hours |
| `court_help` | Court self-help, housing court, forms, clerk | Business hours |
| `government_agency` | Attorney general, HUD, state/county human services | Business hours; phone + web forms |
| `know_your_rights` | Plain-language guides, statutes, handbooks | Self-serve, instant via web |
| `food_benefits` | SNAP, food shelves, WIC | Varies by program |
| `utilities` | Energy/heat assistance, utility shutoff help | Business hours; 211 for after-hours bridge |

---

## 3. Direct-Connect Capabilities

Every resource entry should expose every way a user can reach help, not just a website.

| Capability | UI pattern | When to use | Time-to-help |
|------------|------------|-------------|--------------|
| `tel:` phone link | `<a href="tel:988">` | All phone resources | Instant dial |
| `sms:` text link | `<a href="sms:898211?body=ZIP">` | Services that accept text intake (e.g. United Way 211) | Seconds |
| Live chat embed | iframe or link to org chat | Legal aid, DV hotline, some 211s | Minutes |
| Web form / intake | Link to external intake portal | Legal aid, rental assistance | Hours to days |
| Email | `mailto:` for non-urgent | Government offices, some legal aid | Days |
| Website | External link with `rel="noopener"` | Self-serve info, forms, handbooks | Instant |
| Address / map | Link to map URL or embedded map | In-person clinics, courthouses | Travel time |
| Translation note | Show offered languages | Non-English speakers | No delay if language matches |
| TTY / Deaf / VP | Dedicated relay numbers | Accessibility requirement | Instant |
| Hotline wait estimate | If API provides queue/availability | 211, some crisis lines | Real-time where available |

---

## 4. Jurisdiction Model

Match resources to the user's location, broadening the fallback when local data is sparse.

| Granularity | Source | Example match | Fallback order |
|-------------|--------|---------------|----------------|
| Zip code | User input or geolocation | `55401` | City → County → State → National |
| City | Zip → city lookup or user input | `Minneapolis` | County → State → National |
| County | Zip → county lookup or user input | `Hennepin County` | State → National |
| State | `state_code` in `UserLocation` | `MN` | National |
| National | Always shown | 988, 211, National DV Hotline | None |
| Tribal / territorial | Special jurisdiction flag | Tribal housing authority, Territory-specific hotline | State → National |

**Zip code resolution options:**

1. **USPS/ USPS Web Tools** — address/ZIP lookup, requires registration.
2. **Zippopotam.us** — free, open, no auth: `https://api.zippopotam.us/us/55401` returns city, state, county.
3. **Census Geocoder** — free: `https://geocoding.geo.census.gov/geocoder/geographies/address?format=json&...`.
4. **Client-side Geolocation API** — browser `navigator.geolocation` with permission.

---

## 5. National Baseline Resources (Always Shown)

These should appear regardless of jurisdiction. Phone numbers are short, nationwide, and free.

| Name | Phone / Text | What it's for | Hours | Direct connect |
|------|--------------|---------------|-------|----------------|
| 988 Suicide & Crisis Lifeline | Call/text `988` | Mental health crisis, emotional distress | 24/7 | `tel:988`, `sms:988` (where supported) |
| 211 United Way | Dial `211`; text zip to `898-211` | Housing, food, shelter, crisis referrals | 24/7 | `tel:211`, `sms:898211?body=ZIP` |
| National Domestic Violence Hotline | `1-800-799-7233` | DV safety planning, shelter, support | 24/7 | `tel:18007997233`; live chat online |
| National Sexual Assault Hotline | `1-800-656-4673` | RAINN support | 24/7 | `tel:18006564673` |
| SAMHSA National Helpline | `1-800-662-4357` | Substance use and mental health referrals | 24/7 | `tel:18006624357` |
| National Low Income Housing Coalition (NLIHC) | Website only | Tenant rights policy, state-by-state info | Self-serve | nlihc.org |
| HUD | Website; local office lookup | Fair housing complaints, housing counseling | Business hours | hud.gov, `https://www.hud.gov/states/STATE/renting` |
| Legal Services Corporation (LSC) | `lsc.gov/find-legal-aid` | Legal aid org finder by state | Self-serve | Finder map |
| LawHelp.org | `lawhelp.org` | State-specific legal info and orgs | Self-serve | Multi-state portal |
| CDC/ HUD Eviction Moratorium History | Website | Historical guidance, not active legal advice | Self-serve | Archive links |

---

## 6. State-Scoped Resources (Launch States)

Real content for the six launch states (MN, NY, CA, TX, FL, IL). For other states, use the `STATES_INFO` pattern in `location_service.py` and stub with state-level legal aid and 211.

### 6.1 Minnesota (FULL support)

| Resource | Category | Phone / Contact | Hours | Counties/Cities served |
|----------|----------|-----------------|-------|------------------------|
| HOME Line MN | tenant_hotline, legal_aid | `612-728-5767`; toll-free `1-866-866-3546`; homelinemn.org | Mon–Thu 9am–6pm, Fri 9am–3pm | Statewide |
| Minnesota Statewide Legal Aid | legal_aid | `1-877-696-6529`; lawhelpmn.org | Mon–Fri 8:30am–4:30pm | Statewide |
| Volunteer Lawyers Network | legal_aid | `612-752-6677` | Intake Mon–Thu 10am–1pm | Hennepin, Anoka, Ramsey |
| Hennepin Shelter Hotline | emergency_shelter | `612-204-8200` | M–F 8am–10pm; weekends 1pm–9pm | Hennepin County |
| Dakota County Housing Resource Line | housing_assistance, emergency_shelter | `651-554-5751`; crisis `952-891-7171` | M–F 8am–4:30pm; crisis 24/7 | Dakota County |
| Ramsey County Human Services | housing_assistance | `651-266-4444` | M–F 8am–4:30pm | Ramsey County |
| Anoka County Housing Help Desk | housing_assistance | `763-324-1490` | M–F 8am–4:30pm | Anoka County |
| MN Attorney General Landlord-Tenant Handbook | know_your_rights | Website | Self-serve | Statewide |
| MN Courts Eviction Info | court_help | Website | Self-serve | Statewide |

### 6.2 New York (NY)

| Resource | Category | Phone / Contact | Hours | Coverage |
|----------|----------|-----------------|-------|----------|
| NYC Tenant Helpline | tenant_hotline | 311 in NYC or `nyc.gov/311` | 24/7 | New York City |
| Housing Court Answers | court_help, tenant_hotline | `212-962-4795` | Hours vary | NYC |
| Legal Services NYC | legal_aid | `718-928-7200` | Intake M–F | NYC |
| NY Legal Assistance Group (NYLAG) | legal_aid | `nylag.org` | Intake by form | NYC and region |
| New York Statewide Legal Services | legal_aid | `lawhelpny.org` | Self-serve + intake | Statewide |
| HCR (NYS Homes and Community Renewal) | government_agency | `hcr.ny.gov` | Business hours | Statewide |

### 6.3 California (CA)

| Resource | Category | Phone / Contact | Hours | Coverage |
|----------|----------|-----------------|-------|----------|
| Tenant Together (SF Bay Area) | tenant_hotline | `415-495-8100` | Hours vary | Bay Area |
| Housing Rights, Inc. (SF) | tenant_hotline, legal_aid | `415-703-8634` | Hours vary | San Francisco |
| LA Tenants Union | tenant_union | `latenantsunion.org` | Varies | Los Angeles |
| CA Department of Consumer Affairs | government_agency | `dcb.ca.gov` | Business hours | Statewide |
| Legal Aid Association of CA | legal_aid | `laac.net` / county members | Intake by county | Statewide network |

### 6.4 Texas (TX)

| Resource | Category | Phone / Contact | Hours | Coverage |
|----------|----------|-----------------|-------|----------|
| Austin Tenants Council | tenant_hotline | `512-474-1961` | M–F | Central TX |
| Texas RioGrande Legal Aid | legal_aid | `1-888-995-8295` | Intake M–F | 68 South/West TX counties |
| Legal Aid of Northwest Texas | legal_aid | `1-888-529-5270` | Intake M–F | North/West TX |
| Lone Star Legal Aid | legal_aid | `1-800-733-8394` | Intake M–F | East/Southeast TX |
| Texas Law Help | know_your_rights | `texaslawhelp.org` | Self-serve | Statewide |

### 6.5 Florida (FL)

| Resource | Category | Phone / Contact | Hours | Coverage |
|----------|----------|-----------------|-------|----------|
| Florida Bar Lawyer Referral | legal_aid | `1-800-342-8011` | M–F | Statewide |
| Florida Legal Services | legal_aid | `floridalegal.org` | Intake by county | Statewide network |
| Community Legal Services of Mid-Florida | legal_aid | `1-800-222-3303` | Intake M–F | Central FL |

### 6.6 Illinois (IL)

| Resource | Category | Phone / Contact | Hours | Coverage |
|----------|----------|-----------------|-------|----------|
| Lawyers' Committee for Better Housing (LCBH) | legal_aid, tenant_hotline | `312-347-7600` | M–F | Cook County / Chicago |
| Chicago Renters' Resource | tenant_hotline | `311` or `chicago.gov/311` | 24/7 | Chicago |
| Illinois Legal Aid Online | legal_aid, know_your_rights | `illinoislegalaid.org` | Self-serve + intake | Statewide |
| Prairie State Legal Services | legal_aid | `1-800-860-1111` | Intake M–F | Outside Cook County |

---

## 7. County/City Granularity

For FULL-support states, add county and major-city rows. Model the existing `MN_COUNTIES` in `app/services/location_service.py`.

| County/City | Resource | Phone | Notes |
|-------------|----------|-------|-------|
| Hennepin County, MN | Housing Court | `612-348-2040` | Minneapolis, Bloomington, Eden Prairie |
| Ramsey County, MN | Housing Court | `651-266-8265` | St. Paul |
| Dakota County, MN | District Court | `651-438-4325` | Apple Valley, Burnsville, Eagan, Lakeville |
| Anoka County, MN | District Court | `763-422-7300` | Blaine, Coon Rapids |
| Hennepin County, MN | Shelter Hotline | `612-204-8200` | Same-day shelter triage |

For major cities outside MN, maintain a `CITIES_INFO` table keyed by `state_code + city_name`, with court, tenant union, legal aid, and shelter hotlines.

---

## 8. Public APIs for Real-Time Lookup

Use these to supplement or replace static data. Cache aggressively; stale data is a safety risk.

| API | Endpoint pattern | Auth | Use case | Coverage |
|-----|------------------|------|----------|----------|
| 211 / United Way | `https://apiportal.211.org/search` or state-specific 211 APIs | API key required for some | Housing, food, shelter, crisis by zip/city | National (varies by state portal) |
| SAMHSA FindTreatment | `https://findtreatment.gov/locator/listing?sCity=CITY&sState=ST&sZip=ZIP...` | None apparent | Mental health / substance use facilities | National |
| LawHelp API v2 | `{state}.lawhelp.org/api/v2/resources?postalcode=ZIP&...` | None | Legal aid resources, guides | 24+ states on LawHelp platform |
| Publicaid | `https://publicaid.org/api/` | None | 150k+ social service listings | National |
| Zippopotam.us | `https://api.zippopotam.us/us/ZIP` | None | Zip → city, county, state | US only |
| Census Geocoder | `https://geocoding.geo.census.gov/geocoder/geographies/address` | None | Address → county, tract | US only |
| HUD Housing Counseling | `https://apps.hud.gov/offices/hsg/sfh/cc/csee.cfm` (web) | None | Find HUD-approved counselors | National |

---

## 9. Implementation Cherry-Pick Matrix

Pick one row per dimension to build a focused first version, then expand.

### Data source strategy

| Approach | Effort | Pros | Cons | Best for |
|----------|--------|------|------|----------|
| Static HTML/Jinja | Low | Works offline, fast, no API keys | Hard to maintain, no dynamic lookup | Standalone help page, MVP emergency page |
| Database (Resource model + CSV import) | Medium | Admin-gated, freshness tracking, filterable | Requires curation time | Core product, long-term maintainability |
| Public API (211/LawHelp/SAMHSA) | Medium-High | Always current, broad coverage | Rate limits, API keys, stale/unverified entries | Real-time zip lookup, scaling to 50 states |
| Hybrid: static national + API local | Medium | Best of both; works if API is down | More integration work | Production Semptify55 |

### Jurisdiction launch scope

| Scope | Effort | Coverage | Notes |
|-------|--------|----------|-------|
| Minnesota only | Low | Full | Convert existing help pages to data-driven |
| Six launch states | Medium | MN, NY, CA, TX, FL, IL | Add `StateInfo` rows and state help pages |
| 50 states with stubs | Medium-High | All states; real data for launch states, stub for rest | Use 211/LawHelp API for non-launch states |
| Nationwide + zip | High | Any US zip | Requires zip→county/city and API integration |

---

## 10. Suggested Next Steps

1. **Wire `/tenant/help` and `/help` to `/api/resources`** so the help pages are backed by the `Resource` model instead of hard-coded HTML.
2. **Add `zip_code` and `county` filters to `/api/resources`** — currently `service_area` is a free-text string; enhance with normalized fields.
3. **Seed the `Resource` table** from a CSV containing the national baseline + launch-state resources.
4. **Add a zip-to-jurisdiction helper** using Zippopotam.us or Census as a fallback when geolocation is not available.
5. **Implement a "Get help now" CTA** on every tenant-facing page with the nearest crisis + legal aid numbers based on `UserLocation`.
6. **Schedule weekly `help-page-review`** to verify hotlines and legal aid URLs are still live.

---

## 11. Freshness and Safety Notes

- Phone numbers for crisis hotlines must be verified at least weekly.
- Legal aid intake hours change often; include `last_verified` on every listing.
- Never show a resource without at least one direct-connect path (phone, text, or live chat) if it is tagged `crisis` or `emergency_shelter`.
- If a resource is stale (>365 days unverified), hide it or show a warning per the existing `stale` endpoint.
- Include the disclaimer: "Semptify is not a law firm. This is not legal advice. Contact a licensed attorney for advice specific to your situation."

---

## 12. File References

- `app/modules/resource_directory/router.py`
- `app/modules/resource_directory/schemas.py`
- `app/services/location_service.py`
- `app/templates/pages/tenant_help.html`
- `static/public/semptify-help-standalone.html`
- `tests/test_resource_directory.py`
