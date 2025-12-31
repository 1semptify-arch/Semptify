# Semptify Crawler System Documentation

## Overview

Semptify includes multiple crawler components for gathering tenant rights information from public sources. These crawlers are designed for ethical, rate-limited web scraping of government and legal aid websites.

---

## Crawler Components

### 1. API Crawler (`app/routers/crawler.py` + `app/services/crawler.py`)

**Purpose:** Real-time API for crawling public legal information.

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crawler/sources` | GET | List all available data sources |
| `/api/crawler/crawl` | POST | Crawl a specific URL |
| `/api/crawler/search` | POST | Search crawled content |
| `/api/crawler/statute/{chapter}` | GET | Look up MN statute by chapter |

**Configuration:**
```python
class CrawlerConfig:
    USER_AGENT = "Semptify/5.0 (Tenant Rights Research Bot)"
    RATE_LIMIT_SECONDS = 1.0  # Min seconds between requests
    REQUEST_TIMEOUT = 30.0
    MAX_RETRIES = 3
    CACHE_DIR = Path("data/crawler_cache")
    CACHE_TTL_HOURS = 24
    MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB
```

**Supported Sources (Minnesota):**
- MN Courts (`mncourts.gov`) - Court records, forms
- MN Revisor (`revisor.mn.gov`) - State statutes
- Dakota County (`co.dakota.mn.us`) - Property records
- MN SOS (`sos.state.mn.us`) - Business registry
- LawHelpMN (`lawhelpmn.org`) - Legal aid resources

---

### 2. Eviction Crawler (`scripts/eviction_crawler.py`)

**Purpose:** Batch download of eviction defense documents for training data.

**Usage:**
```bash
cd C:\Semptify\Semptify-FastAPI
.venv\Scripts\python.exe scripts\eviction_crawler.py
```

**What it downloads:**
1. MN Courts eviction forms
2. Attorney General's tenant handbook
3. LawHelpMN resources
4. HOME Line tenant resources
5. HUD regulations

**Output directory:** `data/eviction_training/`

---

### 3. App Crawler (`tools/app_crawler.py`)

**Purpose:** Internal code quality auditor - scans the Semptify codebase itself.

**Usage:**
```bash
cd C:\Semptify\Semptify-FastAPI
.venv\Scripts\python.exe tools\app_crawler.py --help

# Options:
#   --fix       Auto-fix issues
#   --verbose   Detailed output
#   --json      Output JSON report
#   --html      Output HTML report
#   --no-api    Skip API testing
```

**What it checks:**
- HTML files for broken links/missing assets
- JavaScript for undefined variables
- Python for missing docstrings
- API endpoints for proper responses

---

## API Usage Examples

### List Available Sources
```bash
curl http://localhost:8000/api/crawler/sources
```

Response:
```json
{
  "sources": [
    {
      "name": "MN Courts",
      "url": "https://www.mncourts.gov",
      "type": "court_records",
      "description": "Minnesota court records and forms"
    }
  ]
}
```

### Crawl a URL
```bash
curl -X POST http://localhost:8000/api/crawler/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.lawhelpmn.org/topics/housing"}'
```

Response:
```json
{
  "url": "https://www.lawhelpmn.org/topics/housing",
  "title": "Housing - LawHelpMN",
  "text": "Content extracted from page...",
  "links": ["..."],
  "cached": false,
  "crawled_at": "2025-12-31T14:00:00Z"
}
```

### Look Up a Statute
```bash
curl http://localhost:8000/api/crawler/statute/504B
```

Response:
```json
{
  "chapter": "504B",
  "title": "Landlord and Tenant",
  "url": "https://www.revisor.mn.gov/statutes/cite/504B",
  "sections": [
    {"number": "504B.001", "title": "Definitions"},
    {"number": "504B.115", "title": "Tenant's Right to Know"},
    {"number": "504B.211", "title": "Tenant Remedies"}
  ]
}
```

---

## Ethical Crawling Guidelines

1. **Respect robots.txt** - Check before crawling
2. **Rate limiting** - 1 second minimum between requests
3. **Identify yourself** - User-Agent includes contact info
4. **Cache results** - Don't re-fetch unchanged content
5. **Public data only** - No login-required content

---

## Running the Eviction Crawler

### Full Crawl
```powershell
cd C:\Semptify\Semptify-FastAPI
.venv\Scripts\python.exe scripts\eviction_crawler.py
```

### Expected Output
```
============================================================
Minnesota Eviction & Tenant Rights Crawler
Focus: Eviction Defense + Sue the Landlord
============================================================

✓ Downloaded 15 court forms
✓ Downloaded 8 AG resources
✓ Downloaded 12 LawHelpMN resources
✓ Downloaded 6 HOME Line resources
✓ Downloaded 4 HUD regulations

Total: 45 documents saved to data/eviction_training/
```

### Output Structure
```
data/eviction_training/
├── court_forms/
│   ├── eviction_answer_form.pdf
│   ├── motion_to_dismiss.pdf
│   └── ...
├── ag_handbook/
│   ├── tenant_rights_handbook.pdf
│   └── ...
├── lawhelp/
│   ├── eviction_defense_guide.html
│   └── ...
├── homeline/
│   └── ...
└── hud/
    └── ...
```

---

## Troubleshooting

### "No module named 'bs4'"
```bash
pip install beautifulsoup4 lxml
```

### Rate Limit Errors
Increase `RATE_LIMIT_SECONDS` in config or wait before retrying.

### Timeouts
Some government sites are slow. Increase `REQUEST_TIMEOUT` if needed.

### Cache Issues
Clear the cache:
```bash
rm -rf data/crawler_cache/
```

---

## Adding New Sources

Edit `app/services/crawler.py`:

```python
MN_SOURCES = {
    "new_source": SourceInfo(
        name="New Source Name",
        base_url="https://example.gov",
        source_type=SourceType.LEGAL_AID,
        description="Description of what this source provides",
        robots_txt="https://example.gov/robots.txt"
    ),
    # ... existing sources
}
```

---

## Dependencies

Required packages (in `requirements.txt`):
```
beautifulsoup4>=4.12.0    # HTML parsing
lxml>=5.0.0               # Fast XML/HTML parser
httpx>=0.26.0             # Async HTTP client
```
