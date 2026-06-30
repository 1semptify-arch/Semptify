# Render.com Deployment Guide for Semptify

## Quick Deploy (Blueprint)

1. **Push to GitHub** - Ensure your repo is on GitHub
2. **Go to Render Dashboard** - https://dashboard.render.com
3. **New > Blueprint** - Click "New" → "Blueprint"
4. **Connect Repository** - Select your Semptify-FastAPI repo
5. **Deploy** - Render reads `render.yaml` and creates all services

## Manual Deploy (Web Service Only)

1. Go to https://dashboard.render.com
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `semptify-api`
   - **Region**: Oregon (or nearest)
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Environment Variables

Add these in Render Dashboard → Your Service → Environment:

### Required
| Variable | Value | Notes |
|----------|-------|-------|
| `SECRET_KEY` | (auto-generate) | Click "Generate" in Render |
| `SECURITY_MODE` | `enforced` | Production security |
| `DATABASE_URL` | (from Render PostgreSQL) | Auto-linked if using Blueprint |

### Optional - AI Features
| Variable | Value |
|----------|-------|
| `AI_PROVIDER` | `groq` or `openai` or `none` |
| `GROQ_API_KEY` | Your Groq API key |
| `OPENAI_API_KEY` | Your OpenAI API key |

### Optional - Cloud Storage
| Variable | Description |
|----------|-------------|
| `GOOGLE_DRIVE_CLIENT_ID` | Google OAuth |
| `GOOGLE_DRIVE_CLIENT_SECRET` | Google OAuth |
| `DROPBOX_APP_KEY` | Dropbox OAuth |
| `R2_ACCOUNT_ID` | Cloudflare R2 |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 |

## Database Options

### Option 1: Render PostgreSQL (Recommended)
- Blueprint auto-creates PostgreSQL
- Free tier: 1GB storage, 97-day retention
- `DATABASE_URL` auto-linked

### Option 2: External PostgreSQL
Set `DATABASE_URL` manually:
```
postgresql://user:password@host:5432/database
```

### Option 3: SQLite (Not Recommended for Production)
```
DATABASE_URL=sqlite+aiosqlite:///./semptify.db
```
⚠️ SQLite data is lost on redeploys (ephemeral filesystem)

## Health Check

The app exposes `/health` endpoint for Render health checks.

## Custom Domain

1. Go to Service → Settings → Custom Domains
2. Add your domain (e.g., `api.semptify.com`)
3. Configure DNS:
   - CNAME: `your-service.onrender.com`
   - Or use Render's DNS instructions

## Scaling (Paid Plans)

In `render.yaml`, change:
```yaml
plan: starter  # $7/mo - always on
# or
plan: standard  # $25/mo - more resources
```

## Troubleshooting

### Build Fails
- Check `requirements.txt` for version conflicts
- View build logs in Render dashboard

### App Crashes on Start
- Verify `DATABASE_URL` is set correctly
- Check logs: Dashboard → Logs

### 502 Bad Gateway
- App might be starting up (initial deploy takes ~2 min)
- Check health endpoint: `https://your-app.onrender.com/health`

### Database Connection Error
- Ensure PostgreSQL service is running
- Check `DATABASE_URL` format

## URLs After Deploy

- **API**: `https://semptify-api.onrender.com`
- **Docs**: `https://semptify-api.onrender.com/docs`
- **Welcome**: `https://semptify-api.onrender.com/static/welcome.html`
- **Health**: `https://semptify-api.onrender.com/health`

## Free Tier Limitations

- Web service spins down after 15 min of inactivity
- First request after sleep takes ~30-60 seconds
- PostgreSQL: 1GB storage, auto-deletes after 97 days of inactivity

Upgrade to **Starter** ($7/mo) for always-on service.
