# Semptify Legal Intel Engine

A local-only intelligence engine for crawling Minnesota court records (MCRO), Secretary of State business filings, federal cases (CourtListener), and PlainSite. Stores everything in PostgreSQL and exposes a FastAPI interface for pattern analysis.

## Project Structure

```text
legal_intel/
  app/
    __init__.py
    main.py              # FastAPI app
    config.py            # Database settings
    db.py                # Async SQLAlchemy setup
    models.py            # PostgreSQL schema
    schemas.py           # Pydantic models
    routers/
      __init__.py
      crawl.py           # Crawl endpoints
      intel.py           # Pattern analysis endpoints
    crawlers/
      __init__.py
      mcro.py            # MCRO scraper (Playwright)
      sos.py             # MN SOS scraper (Playwright)
      plainsite.py       # PlainSite scraper (httpx)
      courtlistener.py   # CourtListener API (httpx)
    services/
      __init__.py
      patterns.py        # Pattern detection engine
      unified_crawler.py # Crawl orchestrator
  requirements.txt
  .env.example
```

## Setup

1. **Install dependencies:**

```bash
cd legal_intel
pip install -r requirements.txt
playwright install chromium
```text

1. **Configure database:**

```bash
cp .env.example .env
## Edit .env with your PostgreSQL connection string
```

1. **Create database:**

```bash
createdb legal_intel
```text

1. **Run the server:**

```bash
uvicorn app.main:app --reload
```

## API Endpoints

### Crawl Endpoints

- `POST /crawl/attorney/{bar_number}` - Trigger background crawl for an attorney by bar number
- `POST /crawl/entity/{entity_name}?state=MN` - Crawl entity information from Secretary of State

### Intel Endpoints

- `GET /intel/attorney/by-bar/{bar_number}` - Get attorney ID by bar number
- `GET /intel/entity/by-name/{entity_name}` - Get entity ID by name
- `GET /intel/patterns/attorney/{attorney_id}` - Get pattern analysis for an attorney
  - Returns: total_cases, default_rate, settlement_rate, avg_time_to_first_motion_days, top_entities, court_distribution
- `GET /intel/patterns/entity/{entity_id}` - Get pattern analysis for an entity
  - Returns: total_cases, top_attorneys, attorney_counts, court_distribution
- `GET /intel/clusters/shell-llcs` - Detect potential shell LLC clusters
  - Returns: agent_clusters (entities sharing registered agents), address_clusters (entities sharing addresses)

## GUI

A Tkinter GUI is provided for easy interaction with the API.

### Running the GUI

1. Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```text

1. In a separate terminal, run the GUI:

```bash
python gui.py
```

### GUI Features

- **Attorney Crawl**: Enter bar number to crawl attorney cases from MCRO
- **Entity Crawl**: Enter entity name and state to crawl from Secretary of State
- **Show Patterns**: View pattern analysis for attorneys and entities
- **Shell LLC Clusters**: Detect entities sharing registered agents or addresses
- **Activity Log**: Real-time logging of all operations

## Database Schema

- **attorneys** - Attorney profiles (name, bar number, firm, etc.)
- **entities** - Business entities (LLCs, corporations, registered agents)
- **cases** - Court cases (case number, court, type, status)
- **dockets** - Docket entries for each case
- **relationships** - Entity-to-entity relationships
- **search_cache** - Cached HTML from crawlers

## TODO Items

The crawlers have placeholder selectors that need to be updated to match the actual HTML structure of each target:

1. **MCRO crawler** (`app/crawlers/mcro.py`):
   - Update form selectors for attorney search
   - Update table selectors for case results
   - Update docket table selectors

2. **SOS crawler** (`app/crawlers/sos.py`):
   - Update search form selectors
   - Update result table selectors
   - Add detail page extraction for registered agent and address

3. **PlainSite crawler** (`app/crawlers/plainsite.py`):
   - Add BeautifulSoup parsing for attorney profiles
   - Extract entity litigation history

4. **CourtListener crawler** (`app/crawlers/courtlistener.py`):
   - Normalize API response data
   - Map to internal schema

5. **Pattern engine** (`app/services/patterns.py`):
   - Implement docket analysis for default/settlement detection
   - Add motion timing analysis
   - Enhance entity relationship detection

## Data Sources

- **MCRO**: <https://publicaccess.courts.state.mn.us/> (Minnesota Court Records)
- **MN SOS**: <https://mblsportal.sos.state.mn.us/Business/Search> (Business filings)
- **ND SOS**: <https://firststop.sos.nd.gov/search/business> (North Dakota business search)
- **CourtListener**: <https://www.courtlistener.com/api/rest/v3/> (Federal cases API)
- **PlainSite**: <https://www.plainsite.org/> (Attorney and entity litigation)
