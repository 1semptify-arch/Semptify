# Dakota County Eviction Defense Module

## Quad-lingual interactive eviction defense system for Dakota County, Minnesota tenants

## Features

- 🌐 **Quad-lingual Support**: English, Spanish, Somali, Arabic
- 📝 **Answer to Eviction**: Step-by-step wizard to respond to eviction complaints
- ⚖️ **Counterclaims**: File claims against your landlord
- 📋 **Motions**: Dismiss, continuance, stay, fee waiver
- 🎯 **Hearing Prep**: Checklists and guidance for court appearances
- 💻 **Zoom Court Helper**: Tips for virtual hearings
- 📚 **Forms Library**: Official MN court forms with instructions
- 📥 **PDF Export**: Generate court-ready documents
- 📦 **ZIP Bundles**: Complete defense packets

## Quick Start

```powershell
## Navigate to module directory
cd C:\Semptify\Semptify\semptify_dakota_eviction

## Install dependencies
pip install -r requirements.txt

## Run the server
python run.py
```text

Server starts at: <http://localhost:8001>

API docs at: <http://localhost:8001/docs>

## Directory Structure

```

semptify_dakota_eviction/
├── app/
│   ├── main.py           # FastAPI application
│   ├── routes/
│   │   ├── flows.py      # Answer, Counterclaim, Motion, Hearing flows
│   │   └── forms.py      # Court forms library
│   ├── services/
│   │   ├── i18n.py       # Internationalization (EN/ES/SO/AR)
│   │   ├── pdf.py        # PDF generation (WeasyPrint)
│   │   └── zip_service.py # ZIP bundle creation
│   ├── templates/        # Jinja2 templates
│   │   ├── layouts/      # Base templates
│   │   ├── flows/        # Wizard step templates
│   │   └── forms/        # Forms library templates
│   ├── static/           # CSS, JS, images
│   └── assets/
│       └── forms.json    # Court forms manifest
├── requirements.txt
├── run.py
└── README.md

```text

## Integration with Semptify

To integrate with the main Semptify FastAPI app, add to `main.py`:

```python
from semptify_dakota_eviction.app.routes.flows import router as dakota_flows
from semptify_dakota_eviction.app.routes.forms import router as dakota_forms

app.include_router(dakota_flows, prefix="/dakota/flows", tags=["Dakota Eviction Defense"])
app.include_router(dakota_forms, prefix="/dakota/forms", tags=["Dakota Court Forms"])
```

## API Endpoints

### Flows

- `GET /flows/answer` - Answer to Eviction wizard
- `POST /flows/answer/generate` - Generate Answer PDF
- `GET /flows/counterclaim` - Counterclaim wizard
- `POST /flows/counterclaim/generate` - Generate Counterclaim PDF
- `GET /flows/motions` - Motions menu
- `POST /flows/motions/generate` - Generate Motion PDF
- `GET /flows/hearing` - Hearing preparation
- `POST /flows/complete-packet` - Generate complete defense packet ZIP

### Forms

- `GET /forms/library` - Forms library UI
- `GET /forms/api/list` - List all forms (JSON)
- `GET /forms/api/form/{id}` - Get form details
- `GET /forms/download/{id}` - Redirect to official form download

### API

- `GET /api/strings/{lang}` - Get all translated strings
- `GET /api/forms` - Get forms manifest
- `GET /api/resources` - Get legal aid resources
- `GET /flows/api/deadlines` - Calculate deadlines

## Languages

Switch language by adding `?lang=XX` to any URL:

- `?lang=en` - English (default)
- `?lang=es` - Español
- `?lang=so` - Soomaali  
- `?lang=ar` - العربية (RTL supported)

## Court Forms Included

| Form ID | Name | Category |
| --------- | ------ | ---------- |
| HOU301 | Answer to Eviction Complaint | answer |
| HOU302 | Motion to Dismiss Eviction | motion |
| HOU303 | Tenant Counterclaim Form | counterclaim |
| HOU304 | Request for Expungement | expungement |
| HOU305 | Request for Continuance | motion |
| HOU306 | Motion to Stay Writ | motion |
| HOU307 | Fee Waiver Application (IFP) | fee_waiver |
| HOU308 | Habitability Complaint Checklist | evidence |
| HOU309 | Rent Escrow Petition | rent_escrow |
| HOU310 | Affidavit of Service | service |

## Legal Resources

- **HomeLine Tenant Hotline**: 612-728-5767
- **Southern MN Regional Legal Services**: 651-222-5863
- **Minnesota Legal Aid**: lawhelpmn.org
- **Dakota County Court**: 651-438-4325

## Disclaimer

This tool provides legal information, not legal advice. For legal advice specific to your situation, consult an attorney.

---

**Part of Semptify 5.0** - Tenant Rights Protection Platform
