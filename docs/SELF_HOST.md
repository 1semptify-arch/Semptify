# Run Semptify yourself — the self-host kit

Semptify's code is open, and running your own copy is a supported use: an
advocate, a tenant group, or a developer can run the same software that runs
semptify.org. This page is the honest how-to — what works today, what it
takes, and where the limits are.

**What this is not:** there is no one-click installer or packaged appliance
yet. That is the long-term goal this kit is a first step toward. Today,
running Semptify means a normal Python web-app setup.

---

## What you need

- **Python 3.11.x.** The codebase is pinned to 3.11.9 — the app refuses to
  start on a different major/minor line. Do not use 3.12+.
- **A machine that can run a FastAPI app** — Linux, macOS, or Windows. Docker
  works too (see below).
- **Disk and memory for a typical Python web app.** Some optional features
  (the local embedding model) need more memory; the core runs without them.

## The three honest paths

### 1. Look at it / develop against it — open mode, SQLite

This is the fastest way to see and evaluate the whole application. In open
security mode no cloud-storage account is required.

```bash
git clone https://github.com/1semptify-arch/Semptify.git
cd Semptify
python3.11 -m venv venv311
source venv311/bin/activate        # Windows: .\venv311\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.template .env              # Windows: Copy-Item .env.template .env
```

The template already sets `SECURITY_MODE=open` and
`DATABASE_URL=sqlite+aiosqlite:///./semptify.db`. Generate a `SECRET_KEY`
(any long random string) and set it in `.env`.

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On Windows the repo's canonical launcher is `.\start-semptify.ps1`; on
Linux/macOS, `uvicorn` as above is the same thing the Dockerfile runs. The
app listens on the port you choose — open `http://127.0.0.1:8000/` and the
API docs at `http://127.0.0.1:8000/api/docs`.

### 2. Run it for real tenants — enforced mode

Enforced mode is what semptify.org runs: every tenant's records live in
**their own** cloud storage. That is the privacy model — Semptify (or your
copy of it) never holds their documents.

The real setup cost is the OAuth applications: you register your own app
with each storage provider you want to offer (Google Drive, Dropbox,
OneDrive) and put the client IDs/secrets in `.env`. That registration is a
human process on each provider's developer console — it cannot be automated
or shipped with the kit.

Set `SECURITY_MODE=enforced`, a strong `SECRET_KEY`, and a real
`DATABASE_URL` (PostgreSQL is what production uses; SQLite works for a small
deployment).

### 3. Docker

```bash
docker build -t semptify .
docker run -p 8000:8000 --env-file .env semptify
```

The included `Dockerfile` builds on `python:3.11-slim` and runs the same
`uvicorn` command above. `.env` supplies the same settings — nothing else is
required for open mode.

## What still needs outside services

Honest limits — none of these are hidden requirements:

- **Tenant storage (enforced mode):** OAuth apps you register yourself with
  the cloud providers. Without them, run open mode.
- **Database:** SQLite by default. PostgreSQL for anything serious.
- **Email** (contact/feedback delivery): uses Resend. With no `RESEND_API_KEY`
  set, submissions are logged and accepted — the forms still work, nothing
  is sent.
- **AI features:** need a provider key (`AI_PROVIDER`/`OPENAI`/`ANTHROPIC`/
  etc. in `.env`). The app runs without one; AI-backed functions stay off.

## Where this is going

A packaged version — an archive or appliance an advocate can unpack and run
without touching Python — is the goal the Toolbox lists as long-term. This
guide is the working path until then. When the packaged kit exists, this
page will say so.
