# Legal Intelligence Engine — Operations Manual

**Version:** 1.0  
**Location:** `c:\Semptify\Semptify-FastAPI\legal_intel\`  
**Purpose:** Crawl attorney and entity data from public courts (MCRO), Secretary of State, PlainSite, and CourtListener. Store results in PostgreSQL. Surface pattern intelligence via API and GUI.

---

## Table of Contents

1. [Requirements](#1-requirements)
2. [First-Time Setup](#2-first-time-setup)
3. [Starting the Server](#3-starting-the-server)
4. [Stopping the Server](#4-stopping-the-server)
5. [Running the GUI](#5-running-the-gui)
6. [Database Management](#6-database-management)
7. [Configuration & Adjustments](#7-configuration--adjustments)
8. [API Reference](#8-api-reference)
9. [Data Sources](#9-data-sources)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | 3.13 confirmed working |
| PostgreSQL | 16 | Already installed on your machine |
| Playwright | 1.58+ | For scraping JS-heavy sites |
| All Python packages | see `requirements.txt` | |

---

## 2. First-Time Setup

Open PowerShell and run these steps **once**:

```powershell
# Step 1: Navigate to the project
cd C:\Semptify\Semptify-FastAPI\legal_intel

# Step 2: Install Python dependencies
python -m pip install -r requirements.txt

# Step 3: Install Playwright browsers
python -m playwright install chromium

# Step 4: Create database tables (PostgreSQL must be running)
python init_db.py
```

If `init_db.py` prints:
```
✓ Database tables created successfully
```
You are ready to go.

---

## 3. Starting the Server

Open a PowerShell window and run:

```powershell
cd C:\Semptify\Semptify-FastAPI\legal_intel
uvicorn app.main:app --reload --port 8000
```

**What you will see:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

The server is now live at: **http://localhost:8000**

- Interactive API docs: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

**Run on a different port** (if 8000 is busy):
```powershell
uvicorn app.main:app --reload --port 8080
```
> If you change the port, also update `API_BASE` in `gui.py` to match.

---

## 4. Stopping the Server

In the terminal where the server is running, press:

```
Ctrl + C
```

The server shuts down cleanly. Your database data is preserved.

---

## 5. Running the GUI

The GUI requires the server to be running first (Step 3).

Open a **second** PowerShell window and run:

```powershell
cd C:\Semptify\Semptify-FastAPI\legal_intel
python gui.py
```

### GUI Layout

```
┌─────────────────────────────────────────────┐
│           Legal Intelligence Engine          │
├─────────────────────────────────────────────┤
│  Attorney Crawl                              │
│  Bar Number: [______________] [Crawl]        │
│                     [Show Patterns]          │
├─────────────────────────────────────────────┤
│  Entity Crawl                                │
│  Entity Name: [______________] [Crawl]       │
│  State: [MN]                [Show Patterns]  │
├─────────────────────────────────────────────┤
│  Intelligence                                │
│         [Show Shell LLC Clusters]            │
├─────────────────────────────────────────────┤
│  Activity Log                                │
│  [10:45:00] Ready to crawl...                │
│  [10:45:12] Crawl started for #12345         │
│                               [Clear Log]    │
└─────────────────────────────────────────────┘
```

### How to Use the GUI

**Crawl an Attorney:**
1. Type the MN bar number (e.g., `12345`) in the "Bar Number" box
2. Click **Crawl Attorney**
3. Watch the log — it starts a background crawl pulling cases from MCRO
4. After crawling, click **Show Patterns** to see default rates, settlement rates, and court distribution

**Crawl an Entity:**
1. Type a business name (e.g., `Example Properties LLC`) in "Entity Name"
2. Set state to `MN` or `ND`
3. Click **Crawl Entity**
4. Watch the log — it looks up the entity on Secretary of State and stores it
5. Click **Show Patterns** to see what attorneys sued them and how often

**Shell LLC Detection:**
1. Click **Show Shell LLC Clusters**
2. The log shows groups of entities sharing the same registered agent or address
3. This identifies potential shell company networks

---

## 6. Database Management

### Connection Details

| Field | Value |
|---|---|
| Host | localhost |
| Port | 5432 |
| Database | legal_intel |
| Username | semptify |
| Password | semptify |

### Connect with psql

```powershell
$env:PGPASSWORD='semptify'
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U semptify -d legal_intel
```

### Useful psql Commands

```sql
-- List all tables
\dt

-- Count attorneys
SELECT COUNT(*) FROM attorneys;

-- Count cases
SELECT COUNT(*) FROM cases;

-- See all entities
SELECT id, name, type, sos_id FROM entities LIMIT 20;

-- See cases for a specific attorney ID
SELECT case_number, case_title, court, status FROM cases WHERE attorney_id = 1;

-- See dockets for a specific case ID
SELECT date, entry_type, description FROM dockets WHERE case_id = 1 ORDER BY date;

-- Shell LLC check: entities sharing same registered agent
SELECT registered_agent, COUNT(*) as count, array_agg(name) as entities
FROM entities
WHERE registered_agent IS NOT NULL
GROUP BY registered_agent
HAVING COUNT(*) > 1
ORDER BY count DESC;

-- Exit psql
\q
```

### Start/Stop PostgreSQL Service

```powershell
# Check status
Get-Service -Name postgresql-x64-16

# Start PostgreSQL
Start-Service -Name postgresql-x64-16

# Stop PostgreSQL
Stop-Service -Name postgresql-x64-16

# Restart PostgreSQL
Restart-Service -Name postgresql-x64-16
```

### Reset Database (Nuclear Option)

Only use this to wipe all data and start fresh:

```powershell
$env:PGPASSWORD='semptify'
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U semptify -d legal_intel -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO semptify;"
python init_db.py
```

---

## 7. Configuration & Adjustments

### `.env` File

Located at: `c:\Semptify\Semptify-FastAPI\legal_intel\.env`

```env
DATABASE_URL=postgresql+asyncpg://semptify:semptify@localhost:5432/legal_intel
```

Change this if you move to a different database host, user, or database name.

---

### `app/config.py` — Settings

```python
DATABASE_URL: str = "postgresql+asyncpg://semptify:semptify@localhost:5432/legal_intel"
```

Default fallback if `.env` is missing.

---

### `gui.py` — GUI Settings

At the top of `gui.py`:

```python
API_BASE = "http://localhost:8000"
```

**Change this if:**
- You run the server on a different port: `"http://localhost:8080"`
- You run the server on a different machine: `"http://192.168.1.x:8000"`

---

### `app/crawlers/mcro.py` — MCRO Crawler Tuning

```python
MCRO_BASE = "https://publicaccess.courts.state.mn.us/CaseSearch"
```

**Timeouts:** If MCRO is slow, find this line and increase the wait:
```python
await page.wait_for_selector(...)  # timeout in ms
```

**Headless mode:** To see the browser during crawl (for debugging), change:
```python
browser = await p.chromium.launch(headless=True)
# to:
browser = await p.chromium.launch(headless=False)
```

---

### `app/crawlers/sos.py` — SOS Crawler Tuning

Supports MN and ND Secretary of State.

```python
MN_SOS_BASE = "https://mblsportal.sos.state.mn.us/Business/Search"
ND_SOS_BASE = "https://firststop.sos.nd.gov/search/business"
```

---

### `app/services/patterns.py` — Pattern Keywords

Customize what the engine looks for in docket entries:

```python
DEFAULT_JUDGMENT_KEYWORDS = [
    "default judgment",
    "judgment by default",
    "entry of default",
    "default entered",
    "notice of default",
]

SETTLEMENT_KEYWORDS = [
    "stipulation of dismissal",
    "settlement agreement",
    "dismissal with prejudice",
    ...
]
```

Add any keywords that are relevant to your cases.

---

## 8. API Reference

All endpoints available at http://localhost:8000/docs (interactive).

### Crawl Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/crawl/attorney/{bar_number}` | Background crawl of attorney cases from MCRO |
| POST | `/crawl/entity/{entity_name}?state=MN` | Crawl entity from SOS |

### Intel Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/intel/attorney/by-bar/{bar_number}` | Look up attorney by bar number |
| GET | `/intel/entity/by-name/{entity_name}` | Look up entity by name |
| GET | `/intel/patterns/attorney/{attorney_id}` | Pattern analysis for attorney |
| GET | `/intel/patterns/entity/{entity_id}` | Pattern analysis for entity |
| GET | `/intel/clusters/shell-llcs` | Detect shell LLC clusters |

### Example: Crawl Attorney via curl

```bash
curl -X POST http://localhost:8000/crawl/attorney/12345
```

### Example: Get Patterns via curl

```bash
# Step 1: Get attorney ID
curl http://localhost:8000/intel/attorney/by-bar/12345

# Step 2: Get patterns using returned ID
curl http://localhost:8000/intel/patterns/attorney/1
```

---

## 9. Data Sources

| Source | What It Provides | Method |
|---|---|---|
| **MCRO** | MN state court cases, dockets | Playwright (browser automation) |
| **MN SOS** | MN business entities, registered agents | Playwright |
| **ND SOS** | ND business entities | Playwright |
| **PlainSite** | Cross-state litigation history | httpx + BeautifulSoup |
| **CourtListener** | Federal court cases, opinions | REST API (no key required) |

> **Note:** MCRO and SOS use Playwright because those sites require JavaScript rendering. Crawling takes 10–30 seconds per attorney due to page load times.

---

## 10. Troubleshooting

### Server won't start
```
Error: address already in use
```
Another process is using port 8000. Either kill it or use a different port:
```powershell
uvicorn app.main:app --reload --port 8001
```

---

### Database connection error
```
asyncpg.exceptions.InvalidPasswordError
```
Verify the semptify user password:
```powershell
$env:PGPASSWORD='postgres'
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "ALTER USER semptify PASSWORD 'semptify';"
```

---

### Tables don't exist
```
asyncpg.exceptions.UndefinedTableError
```
Re-run the database initializer:
```powershell
cd C:\Semptify\Semptify-FastAPI\legal_intel
python init_db.py
```

---

### MCRO/SOS returns no results
These are public sites that may change their HTML. If crawlers stop returning results:
1. Set `headless=False` in the crawler to watch what's happening
2. Update selectors in `app/crawlers/mcro.py` or `app/crawlers/sos.py`

---

### GUI shows "Connection refused"
The server is not running. Start it first:
```powershell
cd C:\Semptify\Semptify-FastAPI\legal_intel
uvicorn app.main:app --reload --port 8000
```

---

### Wrong DATABASE_URL loading
If the engine is picking up a cloud database URL instead of local, the `.env` file is being overridden by a parent directory's `.env`. The `app/config.py` explicitly loads from the `legal_intel/.env` path to prevent this.

---

*End of Manual*
